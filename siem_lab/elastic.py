from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .config import RuntimeConfig


def _basic_auth(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


class ElasticClient:
    def __init__(self, config: RuntimeConfig):
        self.config = config

    def _request(
        self,
        method: str,
        url: str,
        *,
        payload: Any | None = None,
        kibana: bool = False,
        expected: tuple[int, ...] = (200,),
    ) -> Any:
        headers = {
            "Authorization": _basic_auth(
                self.config.kibana_username if kibana else self.config.elastic_username,
                self.config.kibana_password if kibana else self.config.elastic_password,
            )
        }
        if kibana:
            headers["kbn-xsrf"] = "siem-lab"
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request) as response:
                body = response.read().decode("utf-8")
                if response.status not in expected:
                    raise RuntimeError(f"{method} {url} returned {response.status}: {body}")
                if not body:
                    return {}
                try:
                    return json.loads(body)
                except json.JSONDecodeError:
                    return body
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code in expected:
                if not body:
                    return {}
                try:
                    return json.loads(body)
                except json.JSONDecodeError:
                    return body
            raise RuntimeError(f"{method} {url} failed with {exc.code}: {body}") from exc

    def wait_for_elasticsearch(self, timeout_seconds: int = 240) -> None:
        deadline = time.time() + timeout_seconds
        url = f"{self.config.elasticsearch_url}/_cluster/health"
        while time.time() < deadline:
            try:
                response = self._request("GET", url)
                if response.get("status") in {"green", "yellow"}:
                    return
            except Exception:
                pass
            time.sleep(5)
        raise RuntimeError("Elasticsearch did not become healthy in time.")

    def wait_for_kibana(self, timeout_seconds: int = 300) -> None:
        deadline = time.time() + timeout_seconds
        url = f"{self.config.kibana_url}/api/status"
        while time.time() < deadline:
            try:
                response = self._request("GET", url, kibana=True)
                level = response.get("status", {}).get("overall", {}).get("level")
                if level in {"available", "degraded"}:
                    return
            except Exception:
                pass
            time.sleep(5)
        raise RuntimeError("Kibana did not become healthy in time.")

    def put_index_template(self) -> None:
        payload = {
            "index_patterns": ["logs-lab.*"],
            "data_stream": {},
            "template": {
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {
                    "dynamic": True,
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "message": {"type": "text"},
                        "event": {
                            "properties": {
                                "dataset": {"type": "keyword"},
                                "action": {"type": "keyword"},
                                "category": {"type": "keyword"},
                                "type": {"type": "keyword"},
                                "kind": {"type": "keyword"},
                                "outcome": {"type": "keyword"},
                            }
                        },
                        "lab": {
                            "properties": {
                                "expected_outcome": {"type": "keyword"},
                                "source_type": {"type": "keyword"},
                                "run": {"properties": {"id": {"type": "keyword"}}},
                                "scenario": {"properties": {"id": {"type": "keyword"}}},
                            }
                        },
                    }
                },
            },
        }
        self._request(
            "PUT",
            f"{self.config.elasticsearch_url}/_index_template/siem-lab-template",
            payload=payload,
        )

    def ensure_data_view(self, title: str) -> None:
        payload = {
            "data_view": {
                "id": "siem-lab-data-view",
                "name": "SIEM Lab Logs",
                "title": title,
                "timeFieldName": "@timestamp",
            },
            "override": True,
        }
        self._request(
            "POST",
            f"{self.config.kibana_url}/api/data_views/data_view",
            payload=payload,
            kibana=True,
            expected=(200,),
        )
        self._request(
            "POST",
            f"{self.config.kibana_url}/api/data_views/default",
            payload={"data_view_id": "siem-lab-data-view", "force": True},
            kibana=True,
            expected=(200,),
        )

    def install_prebuilt_rule_assets(self) -> None:
        self._request(
            "PUT",
            f"{self.config.kibana_url}/api/detection_engine/rules/prepackaged",
            kibana=True,
            expected=(200,),
        )

    def upsert_custom_rules(self, path: Path) -> None:
        rules = json.loads(path.read_text(encoding="utf-8"))
        for rule in rules:
            try:
                self._request(
                    "POST",
                    f"{self.config.kibana_url}/api/detection_engine/rules",
                    payload=rule,
                    kibana=True,
                    expected=(200,),
                )
            except RuntimeError as exc:
                if "409" not in str(exc) and "already exists" not in str(exc).lower():
                    raise
                self._request(
                    "PUT",
                    f"{self.config.kibana_url}/api/detection_engine/rules",
                    payload=rule,
                    kibana=True,
                    expected=(200,),
                )

    def bulk_index(self, documents: list[dict[str, Any]]) -> list[str]:
        lines: list[str] = []
        for document in documents:
            index = document.pop("target_index")
            lines.append(json.dumps({"create": {"_index": index}}))
            lines.append(json.dumps(document))
        payload = ("\n".join(lines) + "\n").encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.elasticsearch_url}/_bulk?refresh=wait_for",
            data=payload,
            method="POST",
            headers={
                "Authorization": _basic_auth(self.config.elastic_username, self.config.elastic_password),
                "Content-Type": "application/x-ndjson",
            },
        )
        with urllib.request.urlopen(request) as response:
            body = json.loads(response.read().decode("utf-8"))
        if body.get("errors"):
            raise RuntimeError(f"Bulk index encountered errors: {json.dumps(body)[:500]}")
        ids: list[str] = []
        for item in body.get("items", []):
            create = item.get("create", {})
            doc_id = create.get("_id")
            if doc_id:
                ids.append(doc_id)
        return ids

    def get_alerts(self, source_document_ids: list[str]) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = [{"term": {"kibana.alert.rule.tags": "siem-lab"}}]
        if source_document_ids:
            filters.append({"terms": {"kibana.alert.ancestors.id": source_document_ids}})
        payload = {
            "size": 500,
            "sort": [{"@timestamp": {"order": "asc"}}],
            "query": {"bool": {"filter": filters}},
        }
        response = self._request(
            "POST",
            f"{self.config.elasticsearch_url}/.alerts-security.alerts-default/_search",
            payload=payload,
        )
        return [hit["_source"] for hit in response.get("hits", {}).get("hits", [])]

    def delete_lab_data(self) -> None:
        try:
            self._request(
                "DELETE",
                f"{self.config.elasticsearch_url}/_data_stream/logs-lab-*",
                expected=(200, 404),
            )
        except RuntimeError:
            pass
        try:
            self._request(
                "DELETE",
                f"{self.config.elasticsearch_url}/logs-lab-*",
                expected=(200, 404),
            )
        except RuntimeError:
            return
        delete_payload = {
            "query": {"term": {"kibana.alert.rule.tags": "siem-lab"}},
        }
        try:
            self._request(
                "POST",
                f"{self.config.elasticsearch_url}/.alerts-security.alerts-default,.internal.alerts-security.alerts-default-*/_delete_by_query?conflicts=proceed&ignore_unavailable=true",
                payload=delete_payload,
                expected=(200, 404),
            )
        except RuntimeError:
            pass

    def wait_for_alerts(self, source_document_ids: list[str], timeout_seconds: int) -> list[dict[str, Any]]:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            alerts = self.get_alerts(source_document_ids)
            if alerts:
                return alerts
            time.sleep(10)
        return []
