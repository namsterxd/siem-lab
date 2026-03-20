# SOC Learning Path

This is the quickest way to use the lab like a beginner SOC analyst instead of just running random scenarios.

## Recommended Order

### 1. Baseline Benign

Use this first so you know what normal activity looks like before you start chasing alerts.

```bash
./lab case start baseline-benign
```

### 2. False Positive Admin Login

This teaches an important SOC lesson: an alert can be technically correct and still not be a real incident.

```bash
./lab case start false-positive-admin-login
```

### 3. Trusted Scanner

This is about noisy traffic and suppression logic.

```bash
./lab case start trusted-scanner
```

### 4. Web Exploit Probe

This is a straightforward web true positive.

```bash
./lab case start web-exploit-probe
```

### 5. Windows Encoded Command

This is a straightforward endpoint true positive.

```bash
./lab case start windows-encoded-command
```

## Useful Commands

```bash
./lab case list
./lab case review <case-id> --run-id <run-id>
./lab case hint <case-id>
./lab case answer <case-id>
```

## What You Are Practicing

- knowing what normal looks like
- spotting obvious suspicious behavior
- separating true positives from false positives
- understanding why suppression exists
- writing short analyst-style conclusions
