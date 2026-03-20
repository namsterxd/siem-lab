# SIEM Lab

SIEM Lab is a compact local Elastic lab for people who want to get a feel for what SOC-style alert review and detection work actually looks like.

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

- On Linux and WSL, `./lab bootstrap` can install Docker Compose if it is missing.
- On macOS, Docker Desktop should already provide `docker compose`.

## Quick Start

### 1. Bootstrap the lab

```bash
./lab bootstrap
```

This creates a local `.env` if you do not have one yet, generates random local secrets, creates the working folders, and checks Docker Compose.

### 2. Start the core services

```bash
./lab up core
```

This starts Elasticsearch and Kibana, waits for them to come up, and loads the built-in lab rules.

Then open:

- `http://127.0.0.1:5601`

Log in with:

- Username: `elastic`
- Password: the `ELASTIC_PASSWORD` value from your local `.env`

### 3. Load baseline data

```bash
./lab replay baseline-benign
```

This loads a small set of normal activity into the lab. It will print a `run_id` and write a result file into `exports/`.

Keep the `run_id`. That is how the lab ties alerts back to a specific run.

### 4. Run a scenario that should alert

```bash
./lab scenario run web-exploit-probe
```

This starts the vulnerable web app, sends a few suspicious requests through the gateway, waits for detections, and prints the results.

### 5. Export the alerts

```bash
./lab export alerts <run-id>
```

This writes the alerts for that run to `exports/alerts-<run-id>.ndjson`.

If you want the slower, step-by-step version, read [docs/quickstart.md](docs/quickstart.md).

## Main Commands

```bash
./lab bootstrap
./lab up core
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
2. Look at the sample alert file in [docs/examples/web-exploit-probe-alerts.ndjson](docs/examples/web-exploit-probe-alerts.ndjson)
3. Read the example guide in [docs/examples/README.md](docs/examples/README.md)
4. Read [docs/extending.md](docs/extending.md) if you want to add your own scenario

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
- [docs/extending.md](docs/extending.md)
- [docs/examples/README.md](docs/examples/README.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [SECURITY.md](SECURITY.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

If something in the README feels vague or over-explained, that is a docs bug.
