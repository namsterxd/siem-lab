from __future__ import annotations

import unittest
from pathlib import Path

from siem_lab.cases import available_cases, load_case, render_suggested_filters
from siem_lab.cli import build_parser
from siem_lab.config import ENV_EXAMPLE_PATH, PACKS_DIR
from siem_lab.packs import prepare_pack_documents, render_splunk_events
from siem_lab.scenarios import available_scenarios, load_scenario


class PackTests(unittest.TestCase):
    def test_prepare_pack_documents_sets_run_and_scenario(self) -> None:
        result = prepare_pack_documents("baseline-benign", run_id="run123", scenario_id="baseline-benign")
        self.assertGreater(len(result.documents), 0)
        for doc in result.documents:
            self.assertEqual(doc["lab"]["run"]["id"], "run123")
            self.assertEqual(doc["lab"]["scenario"]["id"], "baseline-benign")
            self.assertEqual(doc["labels"]["lab_run_id"], "run123")
            self.assertEqual(doc["labels"]["lab_scenario_id"], "baseline-benign")
            self.assertTrue(doc["@timestamp"].endswith("Z"))

    def test_render_splunk_events_preserves_payload(self) -> None:
        events = render_splunk_events("windows-encoded-command")
        self.assertEqual(len(events), 2)
        self.assertIn("event", events[0])
        self.assertEqual(events[0]["source"], "siem-lab")


class ScenarioTests(unittest.TestCase):
    def test_all_scenarios_load(self) -> None:
        names = available_scenarios()
        self.assertIn("web-exploit-probe", names)
        for name in names:
            scenario = load_scenario(name)
            self.assertEqual(scenario.id, name)

    def test_replay_scenarios_reference_existing_packs(self) -> None:
        available = {path.stem for path in PACKS_DIR.glob("*.ndjson")}
        for name in available_scenarios():
            scenario = load_scenario(name)
            if scenario.mode != "replay":
                continue
            for pack in scenario.data.get("packs", []):
                self.assertIn(pack, available, f"Scenario {name} references missing pack {pack}")


class CaseTests(unittest.TestCase):
    def test_curated_cases_load(self) -> None:
        names = available_cases()
        self.assertEqual(
            names,
            [
                "baseline-benign",
                "false-positive-admin-login",
                "trusted-scanner",
                "web-exploit-probe",
                "windows-encoded-command",
            ],
        )
        for name in names:
            case = load_case(name)
            self.assertEqual(case.id, name)
            self.assertTrue(case.brief_path.exists())
            self.assertTrue(case.answer_path.exists())

    def test_cases_reference_real_scenarios(self) -> None:
        scenario_names = set(available_scenarios())
        for name in available_cases():
            case = load_case(name)
            self.assertIn(case.scenario_id, scenario_names)

    def test_case_filters_are_rendered_with_run_id(self) -> None:
        case = load_case("web-exploit-probe")
        rendered = render_suggested_filters(case, "run123")
        self.assertTrue(all("run123" in item for item in rendered))


class CLITests(unittest.TestCase):
    def test_cli_choices_include_expected_commands(self) -> None:
        parser = build_parser()
        parsed = parser.parse_args(["replay", "baseline-benign"])
        self.assertEqual(parsed.pack, "baseline-benign")

    def test_case_cli_choices_include_expected_commands(self) -> None:
        parser = build_parser()
        parsed = parser.parse_args(["case", "review", "web-exploit-probe", "--run-id", "run123"])
        self.assertEqual(parsed.name, "web-exploit-probe")
        self.assertEqual(parsed.run_id, "run123")


class PublicRepoTests(unittest.TestCase):
    def test_env_example_uses_bootstrap_placeholders(self) -> None:
        content = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
        self.assertIn("BOOTSTRAP_GENERATES_RANDOM_PASSWORD", content)
        self.assertIn("BOOTSTRAP_GENERATES_RANDOM_KEY", content)
        self.assertNotIn("LabElastic2026", content)

    def test_docs_example_is_synthetic(self) -> None:
        example = Path("docs/examples/web-exploit-probe-alerts.ndjson").read_text(encoding="utf-8")
        self.assertIn("sampleweb001", example)
        self.assertNotIn("/home/", example)
        self.assertNotIn("C:\\\\Users\\\\", example)

    def test_learning_path_doc_exists(self) -> None:
        self.assertTrue(Path("docs/learning-path.md").exists())


if __name__ == "__main__":
    unittest.main()
