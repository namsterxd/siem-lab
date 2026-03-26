# SIEM Lab

SIEM Lab is a compact local Elastic lab for people who want to get a feel for what SOC-style alert review and detection work may look like.

It runs on a laptop, loads curated event data, triggers a few live scenarios, and shows you which rules fire. The goal is not to build a full production SIEM. The goal is to give you a clean place to see benign activity, false positives, obvious hits, and alert exports in one workflow.

![Kibana first-run reference](docs/assets/kibana-first-run.png)

## What It Includes

- Elasticsearch and Kibana running locally
- Replay packs for benign, suspicious, and intentionally noisy activity
- Live web scenarios against Juice Shop behind a logged Nginx gateway
- Custom detection rules for the included scenarios
- Alert export tied to a specific `run_id`
- Optional Splunk-style export rendering for the same sample data

## Who This Is For

- People taking a first step into SOC analyst work
- Detection engineers who want a small validation lab
- Instructors who need a repeatable demo environment

## Supported Environments

Officially supported for `v0.1.0`:

- Linux
- WSL2
- macOS

You will need:

- Docker with `docker compose`
- Python 3.10 or newer
- About 6-8 GB of RAM available to Docker
- Free local ports `9200`, `5601`, and `8080`

Notes:

- On Linux and WSL, `./lab bootstrap` and `./lab first-run` can install Docker Compose if it is missing.
- On macOS, Docker Desktop should already provide `docker compose`.

## Quick Start

### Fastest path

```bash
./lab first-run
```

This is the easiest setup path. It creates `.env` if needed, creates `exports/` and `state/`, checks Docker Compose, starts Elasticsearch and Kibana, installs the lab detections, and replays `baseline-benign`.

When it finishes, open:

- `http://127.0.0.1:5601`

Log in with:

- Username: `elastic`
- Password: the `ELASTIC_PASSWORD` value from your local `.env`

Then run one scenario that should alert:

```bash
./lab scenario run web-exploit-probe
```

This starts the vulnerable web app, sends a few suspicious requests through the gateway, waits for detections, and prints the results.

Then export the alerts:

```bash
./lab export alerts <run-id>
```

This writes the alerts for that run to `exports/alerts-<run-id>.ndjson`.

If you want the slower manual setup path, read [docs/quickstart.md](docs/quickstart.md).

## SOC Case Mode

If you want to use the lab more like a beginner SOC analyst exercise, start with the guided cases instead of raw scenarios.

```bash
./lab case list
./lab case start web-exploit-probe
./lab case review web-exploit-probe --run-id <run-id>
./lab case hint web-exploit-probe
./lab case answer web-exploit-probe
```

The curated learner path is in [docs/learning-path.md](docs/learning-path.md).

## Main Commands

```bash
./lab first-run
./lab bootstrap
./lab up core
./lab case list
./lab case start web-exploit-probe
./lab replay baseline-benign
./lab scenario run web-bruteforce
./lab scenario stop web-bruteforce
./lab export alerts <run-id>
./lab export splunk-pack windows-encoded-command
./lab reset
```

## Install The CLI

If you want to install the command instead of running `./lab` from the repo:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
siem-lab --help
```

## Included Scenarios

- `baseline-benign`: normal activity that should stay quiet
- `false-positive-admin-login`: activity that looks suspicious and should alert, even though it is intentionally allowed in the lab
- `trusted-scanner`: noisy scanner traffic that should stay suppressed
- `linux-reverse-shell`: Linux command activity that should alert
- `windows-encoded-command`: encoded PowerShell activity that should alert
- `web-bruteforce`: repeated failed logins against the practice app
- `web-exploit-probe`: suspicious web requests with scanner fingerprints

Taken together, these give you a decent first pass at the kinds of signals a SOC analyst has to sort through: normal background activity, obvious hits, and things that look bad but still need context.

## Suggested Order

1. Follow [docs/quickstart.md](docs/quickstart.md)
2. Work through [docs/learning-path.md](docs/learning-path.md)
3. Look at the sample alert file in [docs/examples/web-exploit-probe-alerts.ndjson](docs/examples/web-exploit-probe-alerts.ndjson)
4. Read the example guide in [docs/examples/README.md](docs/examples/README.md)
5. Read [docs/extending.md](docs/extending.md) if you want to add your own scenario

## Safety

- Use this locally on your own machine
- Do not expose it to the public internet
- Juice Shop is intentionally vulnerable, so only start it when you need it
- `./lab reset` deletes lab data and lab alerts
- Never commit your real `.env` file

## Testing

Run this from the repo root:

```bash
python3 -m unittest discover -s tests -q
```

## Troubleshooting

- If `docker compose` is missing on macOS, install or restart Docker Desktop
- If `./lab up core` takes a while, give Docker more memory
- If `./lab export alerts <run-id>` gives you nothing, wait a bit and try again

## Extra Docs

- [docs/quickstart.md](docs/quickstart.md)
- [docs/learning-path.md](docs/learning-path.md)
- [docs/extending.md](docs/extending.md)
- [docs/examples/README.md](docs/examples/README.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [SECURITY.md](SECURITY.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

If something in the README feels vague or over-explained, that is a docs bug.
