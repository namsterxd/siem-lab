# agents.md

## repo purpose

this repo is a small local elastic siem lab for learning and validation. it is intentionally lightweight, beginner-friendly, and mostly standard-library python plus docker compose.

the core flow is:

1. bootstrap local secrets and working folders
2. start elasticsearch + kibana
3. replay packs or run scenarios
4. wait for alerts
5. export alerts tied to a `run_id`

## repo map

- `lab`: tiny shell entrypoint that runs `python3 -m siem_lab.cli`
- `siem_lab/cli.py`: main command parser and command handlers
- `siem_lab/config.py`: repo paths, `.env` handling, runtime config
- `siem_lab/docker.py`: docker / docker compose helpers
- `siem_lab/elastic.py`: elasticsearch + kibana api calls, indexing, alert lookup, cleanup
- `siem_lab/packs.py`: load `.ndjson` packs, resolve `__NOW_MINUS_*__` timestamps, add lab metadata
- `siem_lab/scenarios.py`: load scenario json, run replay or live-web scenarios, write run manifests
- `siem_lab/cases.py`: guided case loading, validation, and case review rendering
- `packs/`: replayable event data, one json document per line
- `scenarios/`: scenario definitions keyed by filename stem
- `cases/<case-id>/`: `case.json`, `brief.md`, and `answer.md`
- `rules/custom-rules.json`: custom lab detection rules
- `configs/nginx/default.conf`: web gateway config for live-web scenarios
- `compose.yaml`: local elastic/kibana/juice-shop stack
- `docs/`: quickstart, learning path, extending docs, and example artifacts
- `tests/`: unit tests and public-repo safety checks

## important behavior to preserve

- `./lab` and installed `siem-lab` should keep the same command structure unless the docs and tests are updated together.
- `run_id` linkage matters. replay/scenario output manifests, indexed documents, and exported alerts all need to stay connected by the same run metadata.
- indexed lab data should keep using the `logs-lab.*` pattern and custom rules should keep the `siem-lab` tagging/export assumptions intact.
- packs are expected to carry a `target_index`. `prepare_pack_documents()` mutates metadata into each document before indexing.
- scenario ids, case ids, and filenames should line up. tests assume real references between packs, scenarios, and cases.
- live web scenarios depend on docker compose services `juice-shop` and `web-gateway` and index parsed nginx logs back into elastic.

## editing rules

- keep docs simple, direct, and beginner-first. this repo explicitly optimizes for readability over cleverness.
- prefer small, boring python. the current codebase uses the standard library heavily and avoids framework sprawl.
- keep examples synthetic and safe to publish. do not add real credentials, real personal paths, or unsafe payloads that do not belong in a local learning lab.
- never commit real `.env` contents. do not commit `exports/` or `state/` artifacts.
- if behavior changes, update the relevant docs at the same time:
  - `README.md`
  - `docs/quickstart.md`
  - `docs/learning-path.md`
  - `docs/extending.md`
- add or update tests when changing cli behavior, scenario/case validation, pack shaping, or public-repo safety rules.

## data file conventions

### packs

- file location: `packs/<name>.ndjson`
- one json object per line
- each document should include `target_index`
- `@timestamp` may use placeholders like `__NOW_MINUS_150__`

### scenarios

- file location: `scenarios/<name>.json`
- filename stem should match `id`
- supported modes are currently `replay` and `live-web`
- replay scenarios reference packs by name
- live-web scenarios define `base_url`, request specs, and expected outcomes

### cases

- file location: `cases/<name>/`
- each case needs `case.json`, `brief.md`, and `answer.md`
- `case.json` must include all required keys enforced in `siem_lab/cases.py`
- `scenario_id` must point to a real scenario

## commands agents should use

### setup

```bash
./lab first-run
./lab bootstrap
./lab up core
```

### common flows

```bash
./lab first-run
./lab replay baseline-benign
./lab scenario run web-exploit-probe
./lab scenario stop web-exploit-probe
./lab case list
./lab case start web-exploit-probe
./lab case review web-exploit-probe --run-id <run-id>
./lab export alerts <run-id>
./lab export splunk-pack windows-encoded-command
./lab reset
```

### verification

```bash
python3 -m unittest discover -s tests -q
python3 tests/check_public_repo.py
```

## practical agent advice

- when changing cli behavior, start in `siem_lab/cli.py` and trace into the helper module instead of patching around it.
- when changing replay behavior, inspect both `siem_lab/packs.py` and the pack/scenario fixtures together.
- when changing case behavior, validate both the rendered output and the case content on disk.
- when touching docker or elastic integration, keep in mind the repo is meant to work on linux, wsl2, and macos as described in the README.
- do not silently change user-facing command names, filenames, or repo layout. this project is teaching material, so consistency matters more than novelty.
