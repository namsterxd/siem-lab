# Story

An alert fired on a successful root login to a production database host.

## What you need to decide

Is this a real incident, or an alert that makes sense technically but does not represent malicious activity in this case?

## Questions to answer

- What exactly triggered the alert?
- Does the surrounding activity support compromise, or routine admin work?
- What would you write down if you had to close this alert cleanly?

## Where to look

- The root login event
- The follow-up sudo activity
- Shared fields like source IP, host name, and user
