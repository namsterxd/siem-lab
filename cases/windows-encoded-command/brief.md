# Story

An endpoint alert fired on Windows process activity involving PowerShell.

## What you need to decide

Is this normal admin scripting, or does it look suspicious enough to raise as an incident?

## Questions to answer

- What is unusual about the PowerShell command line?
- What happened right after PowerShell started?
- What evidence would you keep in a case note?

## Where to look

- The PowerShell event
- The child process event
- The host and user fields
