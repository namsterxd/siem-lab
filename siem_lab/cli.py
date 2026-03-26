from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from .cases import available_cases, find_run_artifacts, load_case, read_case_doc, render_suggested_filters
from .config import (
    EXPORTS_DIR,
    RULES_PATH,
    ensure_directories,
    ensure_env_file,
    load_env,
    runtime_config,
)
from .docker import compose, compose_available, compose_install_help, compose_install_supported, ensure_docker, install_compose_plugin
from .elastic import ElasticClient
from .packs import available_packs, prepare_pack_documents, render_splunk_events
from .scenarios import available_scenarios, run_scenario, stop_scenario


def _client() -> ElasticClient:
    env = load_env()
    return ElasticClient(runtime_config(env))


def _ensure_bootstrap_ready() -> tuple[Path, dict[str, str]]:
    ensure_docker()
    env_path = ensure_env_file()
    ensure_directories()
    env = load_env()
    if not compose_available():
        if not compose_install_supported():
            raise RuntimeError(f"`docker compose` is required on this platform. {compose_install_help()}")
        install_compose_plugin(env["COMPOSE_PLUGIN_VERSION"])
        if not compose_available():
            raise RuntimeError("Docker Compose plugin installation completed, but docker compose is still unavailable.")
    return env_path, env


def _start_core_services(env: dict[str, str]) -> tuple[ElasticClient, str]:
    config = runtime_config(env)
    compose("--profile", "core", "up", "-d", "elasticsearch", "stack-setup", "kibana")
    client = ElasticClient(config)
    client.wait_for_elasticsearch()
    client.wait_for_kibana()
    client.put_index_template()
    client.ensure_data_view(config.index_pattern)
    client.install_prebuilt_rule_assets()
    client.upsert_custom_rules(RULES_PATH)
    return client, config.kibana_url


def _replay_pack(
    client: ElasticClient,
    pack: str,
    *,
    run_id: str | None = None,
    scenario_id: str | None = None,
    expected_outcome: str | None = None,
) -> dict[str, object]:
    resolved_run_id = run_id or uuid.uuid4().hex[:12]
    resolved_scenario_id = scenario_id or pack
    prepared = prepare_pack_documents(
        pack,
        run_id=resolved_run_id,
        scenario_id=resolved_scenario_id,
        expected_outcome_override=expected_outcome,
    )
    source_document_ids = client.bulk_index(prepared.documents)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": resolved_run_id,
        "scenario_id": resolved_scenario_id,
        "pack": pack,
        "documents_indexed": len(prepared.documents),
        "source_document_ids": source_document_ids,
    }
    output = EXPORTS_DIR / f"replay-{resolved_scenario_id}-{resolved_run_id}.json"
    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {**manifest, "output_path": str(output)}


def cmd_bootstrap(_: argparse.Namespace) -> int:
    env_path, _ = _ensure_bootstrap_ready()
    print(f"Environment ready: {env_path}")
    return 0


def cmd_up(args: argparse.Namespace) -> int:
    if args.target != "core":
        raise RuntimeError(f"Unsupported up target: {args.target}")
    _, env = _ensure_bootstrap_ready()
    _start_core_services(env)
    print("Elastic core is up and detections are configured.")
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    ensure_env_file()
    env = load_env()
    client = ElasticClient(runtime_config(env))
    manifest = _replay_pack(
        client,
        args.pack,
        run_id=args.run_id,
        scenario_id=args.scenario_id,
        expected_outcome=args.expected_outcome,
    )
    print(json.dumps(manifest, indent=2))
    return 0


def cmd_first_run(_: argparse.Namespace) -> int:
    env_path, env = _ensure_bootstrap_ready()
    client, kibana_url = _start_core_services(env)
    manifest = _replay_pack(client, "baseline-benign", scenario_id="baseline-benign")
    lines = [
        _format_heading("First Run Complete"),
        f"Kibana: {kibana_url}",
        "Username: elastic",
        f"Password: ELASTIC_PASSWORD in {env_path}",
        f"Baseline run id: {manifest['run_id']}",
        f"Baseline manifest: {manifest['output_path']}",
        "",
        _format_heading("Next Step"),
        "./lab scenario run web-exploit-probe",
    ]
    print("\n".join(lines))
    return 0


def cmd_scenario_run(args: argparse.Namespace) -> int:
    ensure_env_file()
    env = load_env()
    result = run_scenario(args.name, ElasticClient(runtime_config(env)), runtime_config(env).alert_wait_seconds)
    print(json.dumps(result, indent=2))
    return 0


def cmd_scenario_stop(args: argparse.Namespace) -> int:
    stop_scenario(args.name)
    print(f"Stopped scenario services for {args.name}")
    return 0


def _format_heading(title: str) -> str:
    return f"{title}\n{'=' * len(title)}"


def _format_items(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _format_mitre(items: list[dict[str, object]]) -> str:
    if not items:
        return "- No ATT&CK technique is attached to this case."
    return "\n".join(f"- {item['id']}: {item['name']}" for item in items)


def cmd_case_list(_: argparse.Namespace) -> int:
    lines = [_format_heading("Available Cases")]
    for name in available_cases():
        case = load_case(name)
        lines.append(
            f"{case.id}: {case.title} | difficulty={case.data['difficulty']} | "
            f"type={case.data['case_type']} | verdict={case.data['expected_verdict']}"
        )
    print("\n".join(lines))
    return 0


def cmd_case_start(args: argparse.Namespace) -> int:
    ensure_env_file()
    env = load_env()
    case = load_case(args.name)
    result = run_scenario(case.scenario_id, ElasticClient(runtime_config(env)), runtime_config(env).alert_wait_seconds)
    lines = [
        _format_heading(f"Case: {case.title}"),
        f"Role: {case.data['analyst_role']}",
        f"Difficulty: {case.data['difficulty']}",
        f"Type: {case.data['case_type']}",
        f"Expected verdict: {case.data['expected_verdict']}",
        "",
        read_case_doc(case, "brief"),
        "",
        _format_heading("Run Result"),
        f"Run ID: {result['run_id']}",
        f"Scenario: {result['scenario_id']}",
        f"Documents indexed: {result['documents_indexed']}",
        f"Alerts found: {len(result.get('alerts', []))}",
        f"Manifest: {result['output_path']}",
        "",
        _format_heading("Next Steps"),
        f"./lab case review {case.id} --run-id {result['run_id']}",
        f"./lab case hint {case.id}",
        f"./lab export alerts {result['run_id']}",
    ]
    print("\n".join(lines))
    return 0


def cmd_case_review(args: argparse.Namespace) -> int:
    case = load_case(args.name)
    manifest_paths = find_run_artifacts(args.run_id)
    lines = [
        _format_heading(f"Case Review: {case.title}"),
        f"Run ID: {args.run_id}",
        f"Expected verdict: {case.data['expected_verdict']}",
    ]
    if manifest_paths:
        lines.append(f"Run artifact: {manifest_paths[-1]}")
    else:
        lines.append("Run artifact: not found yet in exports/")
    lines.extend(
        [
            "",
            _format_heading("Learning Goals"),
            _format_items([str(item) for item in case.data["learning_objectives"]]),
            "",
            _format_heading("MITRE ATT&CK"),
            _format_mitre([dict(item) for item in case.data["mitre_attack"]]),
            "",
            _format_heading("Triage Questions"),
            _format_items([str(item) for item in case.data["triage_questions"]]),
            "",
            _format_heading("Evidence To Check"),
            _format_items([str(item) for item in case.data["evidence_to_check"]]),
            "",
            _format_heading("Suggested Kibana Filters"),
            _format_items(render_suggested_filters(case, args.run_id)),
            "",
            _format_heading("Escalation Guidance"),
            str(case.data["escalation_guidance"]),
            "",
            _format_heading("Next Steps"),
            f"./lab case hint {case.id}",
            f"./lab case answer {case.id}",
            f"./lab export alerts {args.run_id}",
        ]
    )
    print("\n".join(lines))
    return 0


def cmd_case_hint(args: argparse.Namespace) -> int:
    case = load_case(args.name)
    lines = [
        _format_heading(f"Hints: {case.title}"),
        _format_items([str(item) for item in case.data["hints"]]),
    ]
    print("\n".join(lines))
    return 0


def cmd_case_answer(args: argparse.Namespace) -> int:
    case = load_case(args.name)
    lines = [
        _format_heading(f"Answer Key: {case.title}"),
        f"Expected verdict: {case.data['expected_verdict']}",
        "",
        read_case_doc(case, "answer"),
    ]
    if case.data["iocs"]:
        lines.extend(
            [
                "",
                _format_heading("Key IOCs"),
                _format_items([str(item) for item in case.data["iocs"]]),
            ]
        )
    print("\n".join(lines))
    return 0


def cmd_export_alerts(args: argparse.Namespace) -> int:
    ensure_env_file()
    client = _client()
    manifest_paths = sorted(EXPORTS_DIR.glob(f"*-{args.run_id}.json"))
    if not manifest_paths:
        raise RuntimeError(f"No replay/scenario manifest found for run id {args.run_id}")
    manifest = json.loads(manifest_paths[-1].read_text(encoding="utf-8"))
    alerts = client.get_alerts(manifest.get("source_document_ids", []))
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output = EXPORTS_DIR / f"alerts-{args.run_id}.ndjson"
    output.write_text("".join(json.dumps(item) + "\n" for item in alerts), encoding="utf-8")
    print(output)
    return 0


def cmd_export_splunk_pack(args: argparse.Namespace) -> int:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output = Path(args.output) if args.output else EXPORTS_DIR / f"{args.pack}-splunk-hec.ndjson"
    events = render_splunk_events(args.pack)
    output.write_text("".join(json.dumps(item) + "\n" for item in events), encoding="utf-8")
    print(output)
    return 0


def cmd_reset(_: argparse.Namespace) -> int:
    ensure_env_file()
    env = load_env()
    try:
        compose("stop", "web-gateway", "juice-shop")
    except RuntimeError:
        pass
    ElasticClient(runtime_config(env)).delete_lab_data()
    print("Scenario services stopped and SIEM lab data removed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="siem-lab", description="Control the local SIEM lab.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap", help="Create .env, directories, and ensure docker compose.")
    bootstrap.set_defaults(func=cmd_bootstrap)

    first_run = subparsers.add_parser("first-run", help="Do the easiest end-to-end local lab setup.")
    first_run.set_defaults(func=cmd_first_run)

    up = subparsers.add_parser("up", help="Start the lab core.")
    up.add_argument("target", choices=["core"])
    up.set_defaults(func=cmd_up)

    replay = subparsers.add_parser("replay", help="Replay a canonical pack into Elasticsearch.")
    replay.add_argument("pack", choices=available_packs())
    replay.add_argument("--run-id")
    replay.add_argument("--scenario-id")
    replay.add_argument("--expected-outcome")
    replay.set_defaults(func=cmd_replay)

    scenario = subparsers.add_parser("scenario", help="Run or stop scenarios.")
    scenario_sub = scenario.add_subparsers(dest="scenario_command", required=True)
    scenario_run = scenario_sub.add_parser("run", help="Run a scenario.")
    scenario_run.add_argument("name", choices=available_scenarios())
    scenario_run.set_defaults(func=cmd_scenario_run)
    scenario_stop = scenario_sub.add_parser("stop", help="Stop a scenario.")
    scenario_stop.add_argument("name", choices=available_scenarios())
    scenario_stop.set_defaults(func=cmd_scenario_stop)

    case = subparsers.add_parser("case", help="Run guided analyst cases.")
    case_sub = case.add_subparsers(dest="case_command", required=True)
    case_list = case_sub.add_parser("list", help="List the guided analyst cases.")
    case_list.set_defaults(func=cmd_case_list)
    case_start = case_sub.add_parser("start", help="Start a guided case.")
    case_start.add_argument("name", choices=available_cases())
    case_start.set_defaults(func=cmd_case_start)
    case_review = case_sub.add_parser("review", help="Review a case after running it.")
    case_review.add_argument("name", choices=available_cases())
    case_review.add_argument("--run-id", required=True)
    case_review.set_defaults(func=cmd_case_review)
    case_hint = case_sub.add_parser("hint", help="Show hints for a case.")
    case_hint.add_argument("name", choices=available_cases())
    case_hint.set_defaults(func=cmd_case_hint)
    case_answer = case_sub.add_parser("answer", help="Reveal the answer key for a case.")
    case_answer.add_argument("name", choices=available_cases())
    case_answer.set_defaults(func=cmd_case_answer)

    export = subparsers.add_parser("export", help="Export alerts or Splunk-style pack output.")
    export_sub = export.add_subparsers(dest="export_command", required=True)
    export_alerts = export_sub.add_parser("alerts", help="Export alerts by run id.")
    export_alerts.add_argument("run_id")
    export_alerts.set_defaults(func=cmd_export_alerts)
    export_splunk = export_sub.add_parser("splunk-pack", help="Render a pack into Splunk HEC-style events.")
    export_splunk.add_argument("pack", choices=available_packs())
    export_splunk.add_argument("--output")
    export_splunk.set_defaults(func=cmd_export_splunk_pack)

    reset = subparsers.add_parser("reset", help="Stop scenario services and remove lab data.")
    reset.set_defaults(func=cmd_reset)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
