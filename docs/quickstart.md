# Quickstart

This is the easiest path through the lab.

You will:

1. Set up local files
2. Start the main services
3. Load safe sample data
4. Run one example that should alert
5. Save the alerts to a file

## Before You Start

Make sure you have:

- Docker with `docker compose`
- Python 3.10+
- 6-8 GB of RAM free for Docker
- Ports `9200`, `5601`, and `8080` free

## Step 1: Set up the lab

```bash
./lab bootstrap
```

You should end up with:

- a local `.env` file
- random local passwords and keys
- `exports/` and `state/` folders

## Step 2: Start the main services

```bash
./lab up core
```

You should end up with:

- Kibana working at `http://127.0.0.1:5601`
- the `SIEM Lab Logs` data view created
- the built-in lab rules installed

Log in with:

- Username: `elastic`
- Password: the `ELASTIC_PASSWORD` value in your `.env`

## Step 3: Load normal sample data

```bash
./lab replay baseline-benign
```

You should see:

- a printed `run_id`
- a new file in `exports/`
- normal events inside Kibana

`run_id` means the ID for this one run.

## Step 4: Run one example that should alert

```bash
./lab scenario run web-exploit-probe
```

You should see:

- the local practice web app start
- a printed `run_id`
- results that mention `siem-lab-web-exploit-probe`
- a new scenario file in `exports/`

## Step 5: Save the alerts

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
