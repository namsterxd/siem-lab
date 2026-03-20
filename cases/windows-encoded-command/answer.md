# Verdict

True positive.

## Why

Encoded PowerShell is a common reason to take a closer look, and in this case it is followed by suspicious child-process behavior.

The combination is strong enough for escalation in a learner lab like this.

## What matters

- The `EncodedCommand` pattern is the key trigger
- PowerShell immediately leads to additional process activity
- The process chain is more important than any one field by itself

## What a SOC analyst would do

Escalate it as suspicious PowerShell execution, record the command line, note the child process, and attach the host and user context.
