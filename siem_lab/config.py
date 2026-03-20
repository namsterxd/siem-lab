from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE_PATH = ROOT / ".env.example"
EXPORTS_DIR = ROOT / "exports"
STATE_DIR = ROOT / "state"
PACKS_DIR = ROOT / "packs"
RULES_PATH = ROOT / "rules" / "custom-rules.json"
SCENARIOS_DIR = ROOT / "scenarios"
CASES_DIR = ROOT / "cases"


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_env() -> dict[str, str]:
    defaults = parse_env_file(ENV_EXAMPLE_PATH)
    current = parse_env_file(ENV_PATH)
    merged = defaults.copy()
    merged.update(current)
    return merged


def ensure_directories() -> None:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _random_alnum(length: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def ensure_env_file() -> Path:
    if ENV_PATH.exists():
        return ENV_PATH
    generated_values = {
        "ELASTIC_PASSWORD": _random_alnum(20),
        "KIBANA_SYSTEM_PASSWORD": _random_alnum(20),
        "KIBANA_ENCRYPTION_KEY": _random_alnum(32),
        "REPORTING_ENCRYPTION_KEY": _random_alnum(32),
        "SECURITY_SESSION_KEY": _random_alnum(32),
    }
    lines: list[str] = []
    for raw_line in ENV_EXAMPLE_PATH.read_text(encoding="utf-8").splitlines():
        if "=" not in raw_line or raw_line.lstrip().startswith("#"):
            lines.append(raw_line)
            continue
        key, _, _ = raw_line.partition("=")
        if key in generated_values:
            lines.append(f"{key}={generated_values[key]}")
        else:
            lines.append(raw_line)
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ENV_PATH


@dataclass(frozen=True)
class RuntimeConfig:
    elasticsearch_url: str
    kibana_url: str
    elastic_username: str
    elastic_password: str
    kibana_username: str
    kibana_password: str
    alert_wait_seconds: int
    index_pattern: str


def runtime_config(env: dict[str, str]) -> RuntimeConfig:
    configured_pattern = env.get("LAB_INDEX_PATTERN", "logs-lab.*")
    if configured_pattern == "logs-lab-*":
        configured_pattern = "logs-lab.*"
    return RuntimeConfig(
        elasticsearch_url="http://127.0.0.1:9200",
        kibana_url="http://127.0.0.1:5601",
        elastic_username="elastic",
        elastic_password=env["ELASTIC_PASSWORD"],
        kibana_username="elastic",
        kibana_password=env["ELASTIC_PASSWORD"],
        alert_wait_seconds=int(env.get("LAB_ALERT_WAIT_SECONDS", "75")),
        index_pattern=configured_pattern,
    )
