# Story

You are reviewing web requests that definitely look noisy and suspicious.

## What you need to decide

Should this traffic create an incident, or is this one of those cases where the system is supposed to stay quiet even though the requests look ugly?

## Questions to answer

- What makes the requests look suspicious?
- What field or condition explains why no alert should fire?
- What would you tell another analyst who only looked at the URL path and not the full context?

## Where to look

- The path and response code
- The user agent
- Any allowlist-related fields or labels
