from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import CASES_DIR, EXPORTS_DIR


REQUIRED_KEYS = {
    "id",
    "title",
    "scenario_id",
    "difficulty",
    "analyst_role",
    "case_type",
    "starter_path_order",
    "expected_verdict",
    "learning_objectives",
    "mitre_attack",
    "triage_questions",
    "evidence_to_check",
    "suggested_filters",
    "hints",
    "iocs",
    "escalation_guidance",
}


@dataclass(frozen=True)
class Case:
    path: Path
    data: dict[str, object]

    @property
    def id(self) -> str:
        return str(self.data["id"])

    @property
    def title(self) -> str:
        return str(self.data["title"])

    @property
    def scenario_id(self) -> str:
        return str(self.data["scenario_id"])

    @property
    def starter_path_order(self) -> int:
        return int(self.data["starter_path_order"])

    @property
    def brief_path(self) -> Path:
        return self.path / "brief.md"

    @property
    def answer_path(self) -> Path:
        return self.path / "answer.md"


def _load_case_data(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = REQUIRED_KEYS - data.keys()
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"Case {path.parent.name} is missing required keys: {missing_list}")
    return data


def load_case(name: str) -> Case:
    case_dir = CASES_DIR / name
    json_path = case_dir / "case.json"
    if not json_path.exists():
        raise FileNotFoundError(f"Case not found: {name}")
    case = Case(path=case_dir, data=_load_case_data(json_path))
    for doc_path in (case.brief_path, case.answer_path):
        if not doc_path.exists():
            raise FileNotFoundError(f"Case document missing: {doc_path}")
    return case


def available_cases() -> list[str]:
    return [case.id for case in load_all_cases()]


def load_all_cases() -> list[Case]:
    cases: list[Case] = []
    for path in sorted(CASES_DIR.glob("*/case.json")):
        cases.append(Case(path=path.parent, data=_load_case_data(path)))
    return sorted(cases, key=lambda item: (item.starter_path_order, item.id))


def read_case_doc(case: Case, doc_name: str) -> str:
    doc_path = case.path / f"{doc_name}.md"
    if not doc_path.exists():
        raise FileNotFoundError(f"Case document missing: {doc_path}")
    return doc_path.read_text(encoding="utf-8").strip()


def render_suggested_filters(case: Case, run_id: str) -> list[str]:
    filters = case.data.get("suggested_filters", [])
    return [str(item).replace("{run_id}", run_id) for item in filters]


def find_run_artifacts(run_id: str) -> list[Path]:
    return sorted(EXPORTS_DIR.glob(f"*-{run_id}.json"))
