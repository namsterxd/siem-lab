from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import parse, request

from .config import EXPORTS_DIR, SCENARIOS_DIR
from .docker import compose, docker_logs
from .elastic import ElasticClient
from .packs import prepare_pack_documents


@dataclass(frozen=True)
class Scenario:
    path: Path
    data: dict[str, Any]

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def mode(self) -> str:
        return self.data["mode"]


def load_scenario(name: str) -> Scenario:
    path = SCENARIOS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Scenario not found: {name}")
    return Scenario(path=path, data=json.loads(path.read_text(encoding="utf-8")))


def available_scenarios() -> list[str]:
    return sorted(path.stem for path in SCENARIOS_DIR.glob("*.json"))


def _run_live_requests(base_url: str, requests_spec: list[dict[str, Any]]) -> None:
    for spec in requests_spec:
        method = spec.get("method", "GET").upper()
        full_url = parse.urljoin(base_url, spec["path"])
        headers = spec.get("headers", {})
        body = None
        if "json" in spec:
            body = json.dumps(spec["json"]).encode("utf-8")
            headers = {"Content-Type": "application/json", **headers}
        elif "body" in spec:
            body = spec["body"].encode("utf-8")
        repeat = int(spec.get("repeat", 1))
        for _ in range(repeat):
            req = request.Request(full_url, data=body, method=method, headers=headers)
            try:
                with request.urlopen(req) as response:
                    response.read()
            except Exception:
                pass


def _wait_for_http(url: str, timeout_seconds: int = 90) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            req = request.Request(url, method="GET")
            with request.urlopen(req) as response:
                if response.status < 500:
                    return
        except Exception:
            time.sleep(2)
            continue
        time.sleep(2)
    raise RuntimeError(f"Scenario service did not become reachable: {url}")


def _parse_gateway_logs(raw_logs: str, scenario_id: str, run_id: str, expected_outcome: str) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for line in raw_logs.splitlines():
        if not line.startswith("{"):
            continue
        payload = json.loads(line)
        parsed_uri = parse.urlsplit(payload["request_uri"])
        labels = {}
        if payload.get("user_agent") == "TrustedScanner/1.0":
            labels["allowlisted"] = True
        labels["lab_run_id"] = run_id
        labels["lab_scenario_id"] = scenario_id
        documents.append(
            {
                "target_index": "logs-lab.web-default",
                "@timestamp": payload["ts"],
                "message": f'{payload["request_method"]} {payload["request_uri"]} -> {payload["status"]}',
                "event": {
                    "dataset": "lab.web",
                    "kind": "event",
                    "category": ["web"],
                    "type": ["access"],
                    "action": "http-request",
                    "outcome": "success" if int(payload["status"]) < 400 else "failure",
                },
                "http": {
                    "request": {"method": payload["request_method"]},
                    "response": {"status_code": int(payload["status"]), "bytes": int(payload["bytes_sent"])},
                },
                "url": {
                    "original": payload["request_uri"],
                    "path": parsed_uri.path or payload["path"],
                    "query": parsed_uri.query or payload.get("query", ""),
                },
                "source": {"ip": payload["remote_addr"]},
                "user_agent": {"original": payload.get("user_agent", "")},
                "labels": labels,
                "host": {"name": "siem-lab-web-gateway"},
                "lab": {
                    "run": {"id": run_id},
                    "scenario": {"id": scenario_id},
                    "expected_outcome": expected_outcome,
                    "source_type": "live-web",
                },
            }
        )
    return documents


def run_scenario(name: str, client: ElasticClient, alert_wait_seconds: int) -> dict[str, Any]:
    scenario = load_scenario(name)
    run_id = uuid.uuid4().hex[:12]
    result: dict[str, Any] = {
        "scenario_id": scenario.id,
        "run_id": run_id,
        "expected_alerts": scenario.data.get("expected_alerts", []),
        "expected_non_alerts": scenario.data.get("expected_non_alerts", []),
        "documents_indexed": 0,
        "source_document_ids": [],
    }

    if scenario.mode == "replay":
        all_docs: list[dict[str, Any]] = []
        for pack_name in scenario.data.get("packs", []):
            prepared = prepare_pack_documents(
                pack_name,
                run_id=run_id,
                scenario_id=scenario.id,
                expected_outcome_override=scenario.data.get("expected_outcome"),
            )
            all_docs.extend(prepared.documents)
        result["source_document_ids"] = client.bulk_index(all_docs)
        result["documents_indexed"] = len(all_docs)
    elif scenario.mode == "live-web":
        compose("--profile", "web-vuln", "up", "-d", "juice-shop", "web-gateway")
        started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        _wait_for_http(scenario.data["base_url"])
        _run_live_requests(scenario.data["base_url"], scenario.data.get("requests", []))
        raw_logs = docker_logs("siem-lab-web-gateway", started_at)
        docs = _parse_gateway_logs(raw_logs, scenario.id, run_id, scenario.data["expected_outcome"])
        result["source_document_ids"] = client.bulk_index(docs)
        result["documents_indexed"] = len(docs)
    else:
        raise RuntimeError(f"Unsupported scenario mode: {scenario.mode}")

    alerts = client.wait_for_alerts(result["source_document_ids"], alert_wait_seconds)
    result["alerts"] = alerts
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EXPORTS_DIR / f"scenario-{scenario.id}-{run_id}.json"
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["output_path"] = str(output_path)
    return result


def stop_scenario(name: str) -> None:
    scenario = load_scenario(name)
    if scenario.mode == "live-web":
        try:
            compose("stop", "web-gateway", "juice-shop")
        except RuntimeError:
            pass
