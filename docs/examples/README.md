# Example Files

These files are here so you can see what the lab output looks like before you run anything yourself.

## `web-exploit-probe-alerts.ndjson`

This is a sample alert export file.

In simple words, it shows:

- when the alert happened
- which rule created the alert
- which lab scenario it came from
- which suspicious request caused it

You do not need to understand every field.

The most useful ones to notice first are:

- `kibana.alert.rule.name`: the name of the rule
- `labels.lab_run_id`: the ID for that run
- `labels.lab_scenario_id`: which practice example was used
- `message`: the short human-readable event summary

## `terminal-session.txt`

This is a small example of what a normal lab run looks like in the terminal.
