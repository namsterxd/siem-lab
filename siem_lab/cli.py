from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

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


def cmd_bootstrap(_: argparse.Namespace) -> int:
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
    print(f"Environment ready: {env_path}")
    return 0


def cmd_up(args: argparse.Namespace) -> int:
    if args.target != "core":
        raise RuntimeError(f"Unsupported up target: {args.target}")
    ensure_env_file()
    env = load_env()
    compose("--profile", "core", "up", "-d", "elasticsearch", "stack-setup", "kibana")
    client = ElasticClient(runtime_config(env))
    client.wait_for_elasticsearch()
    client.wait_for_kibana()
    client.put_index_template()
    client.ensure_data_view(runtime_config(env).index_pattern)
    client.install_prebuilt_rule_assets()
    client.upsert_custom_rules(RULES_PATH)
    print("Elastic core is up and detections are configured.")
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    ensure_env_file()
    env = load_env()
    client = ElasticClient(runtime_config(env))
    run_id = args.run_id or uuid.uuid4().hex[:12]
    scenario_id = args.scenario_id or args.pack
    prepared = prepare_pack_documents(
        args.pack,
        run_id=run_id,
        scenario_id=scenario_id,
        expected_outcome_override=args.expected_outcome,
    )
    source_document_ids = client.bulk_index(prepared.documents)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "pack": args.pack,
        "documents_indexed": len(prepared.documents),
        "source_document_ids": source_document_ids,
    }
    output = EXPORTS_DIR / f"replay-{scenario_id}-{run_id}.json"
    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({**manifest, "output_path": str(output)}, indent=2))
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
