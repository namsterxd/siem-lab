# Extending The Lab

Once the basic lab makes sense, you can add your own practice cases.

## Simple Idea

The lab is made of three main parts:

- A pack: sample events
- A scenario: what to run
- A rule: what should create an alert

## Add A New Pack

A pack is just a file of sample events.

1. Add a new `.ndjson` file in `packs/`
2. Put one JSON event on each line
3. Set `target_index` so the lab knows where to save it
4. If you want the event time to feel recent, use values like `__NOW_MINUS_150__`

## Add A New Scenario

A scenario tells the lab what example to run.

1. Add a new `.json` file in `scenarios/`
2. Set `mode` to `replay` or `live-web`
3. List the alerts you expect
4. Point to one or more packs, or list the web requests to send

## Add Or Change A Rule

A rule decides when the lab should create an alert.

1. Add or edit a rule in `rules/custom-rules.json`
2. Keep the `siem-lab` tag so exports and cleanup still work
3. Point the rule at `logs-lab.*`
4. Try to keep the rule stable and easy to repeat

## Check Your Work

Run these after you make changes:

- `python3 -m unittest discover -s tests -q`
- `./lab replay <new-pack>` if you changed a pack
- `./lab scenario run <new-scenario>` if you changed a scenario
- `./lab export alerts <run-id>` to make sure alerts are linked to the right run

## Before You Publish Anything

- Never commit your real `.env`
- Keep examples fake and safe to share
- Write down what the learner should see
