# Contributing

Thanks for helping.

The main goal of this repo is to stay easy to learn from.

## Good First Changes

- Make setup steps clearer
- Fix confusing words
- Add better examples
- Add safe new packs or scenarios
- Improve tests

## Local Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -q
```

If you work on live scenarios, make sure Docker is running first.

## Please Keep These Things In Mind

- Keep beginner docs simple
- Do not commit `.env`, `exports/`, or `state/`
- Do not commit screenshots with personal info
- Update docs when behavior changes
- Add tests when you add new behavior

## When Adding Scenarios

- Keep them safe to publish
- Keep them easy to repeat
- Say what should alert
- Say what should not alert
