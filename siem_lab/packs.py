from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .config import PACKS_DIR


TIMESTAMP_PREFIX = "__NOW_MINUS_"
TIMESTAMP_SUFFIX = "__"


@dataclass(frozen=True)
class PackResult:
    documents: list[dict[str, Any]]
    run_id: str
    scenario_id: str


def available_packs() -> list[str]:
    return sorted(path.stem for path in PACKS_DIR.glob("*.ndjson"))


def load_pack(name: str) -> list[dict[str, Any]]:
    path = PACKS_DIR / f"{name}.ndjson"
    if not path.exists():
        raise FileNotFoundError(f"Pack not found: {name}")
    documents: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        documents.append(json.loads(line))
    return documents


def _resolve_timestamp(value: str) -> str:
    if value.startswith(TIMESTAMP_PREFIX) and value.endswith(TIMESTAMP_SUFFIX):
        seconds = int(value[len(TIMESTAMP_PREFIX) : -len(TIMESTAMP_SUFFIX)])
        resolved = datetime.now(UTC) - timedelta(seconds=seconds)
        return resolved.isoformat().replace("+00:00", "Z")
    return value


def prepare_pack_documents(
    name: str,
    *,
    run_id: str,
    scenario_id: str,
    expected_outcome_override: str | None = None,
) -> PackResult:
    documents = load_pack(name)
    prepared: list[dict[str, Any]] = []
    for document in documents:
        doc = json.loads(json.dumps(document))
        timestamp = doc.get("@timestamp")
        if isinstance(timestamp, str):
            doc["@timestamp"] = _resolve_timestamp(timestamp)
        labels = doc.setdefault("labels", {})
        labels["lab_run_id"] = run_id
        labels["lab_scenario_id"] = scenario_id
        lab = doc.setdefault("lab", {})
        run = lab.setdefault("run", {})
        scenario = lab.setdefault("scenario", {})
        run["id"] = run_id
        scenario["id"] = scenario_id
        if expected_outcome_override:
            lab["expected_outcome"] = expected_outcome_override
        prepared.append(doc)
    return PackResult(documents=prepared, run_id=run_id, scenario_id=scenario_id)


def render_splunk_events(name: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for document in load_pack(name):
        event = json.loads(json.dumps(document))
        timestamp = document.get("@timestamp")
        if isinstance(timestamp, str):
            resolved = _resolve_timestamp(timestamp)
            event_time = datetime.fromisoformat(resolved.replace("Z", "+00:00")).timestamp()
            event["@timestamp"] = resolved
        else:
            event_time = datetime.now(UTC).timestamp()
        host_name = document.get("host", {}).get("name", "siem-lab")
        sourcetype = document.get("event", {}).get("dataset", "lab:generic")
        events.append(
            {
                "time": event_time,
                "host": host_name,
                "source": "siem-lab",
                "sourcetype": sourcetype,
                "event": event,
            }
        )
    return events
