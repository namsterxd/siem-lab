# Quickstart

This is the easiest path through the lab.

You will:

1. Run one setup command
2. Open Kibana
3. Run one example that should alert
4. Save the alerts to a file

## Before You Start

Make sure you have:

- Docker with `docker compose`
- Python 3.10+
- 6-8 GB of RAM free for Docker
- Ports `9200`, `5601`, and `8080` free

## Step 1: Run the easiest setup path

```bash
./lab first-run
```

This will:

- a local `.env` file
- random local passwords and keys
- `exports/` and `state/` folders
- Elasticsearch and Kibana running
- Kibana working at `http://127.0.0.1:5601`
- the `SIEM Lab Logs` data view created
- the built-in lab rules installed
- a baseline replay manifest in `exports/`

Log in with:

- Username: `elastic`
- Password: the `ELASTIC_PASSWORD` value in your `.env`

If you want the slower manual path instead, use:

```bash
./lab bootstrap
./lab up core
./lab replay baseline-benign
```

## Step 2: Run one example that should alert

```bash
./lab scenario run web-exploit-probe
```

You should see:

- the local practice web app start
- a printed `run_id`
- results that mention `siem-lab-web-exploit-probe`
- a new scenario file in `exports/`

## Step 3: Save the alerts

```bash
./lab export alerts <run-id>
```

You should see:

- a file like `exports/alerts-<run-id>.ndjson`
- one or more alert entries inside that file

You can compare with this sample file:

- [docs/examples/web-exploit-probe-alerts.ndjson](examples/web-exploit-probe-alerts.ndjson)
- [docs/examples/terminal-session.txt](examples/terminal-session.txt)

## If Something Goes Wrong

- No `docker compose` on macOS: install or restart Docker Desktop
- No alerts yet: wait a little and try again
- Port already in use: stop the app already using `9200`, `5601`, or `8080`

## After That

- Read [docs/learning-path.md](learning-path.md) if you want the SOC-style case flow
- Read [docs/extending.md](extending.md) if you want to add your own data, scenarios, or rules
