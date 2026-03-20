from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def main() -> int:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for ignored in [".env", "exports/", "state/"]:
        if ignored not in gitignore:
            return fail(f"missing ignore rule for {ignored}")

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        in_git_repo = result.returncode == 0
    except OSError:
        in_git_repo = False

    if in_git_repo:
        for candidate in [".env", "exports", "state"]:
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", candidate],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if tracked.returncode == 0:
                return fail(f"tracked release artifact present: {candidate}")

    required = [
        ROOT / "README.md",
        ROOT / "pyproject.toml",
        ROOT / "docs/learning-path.md",
        ROOT / "docs/examples/web-exploit-probe-alerts.ndjson",
    ]
    for path in required:
        if not path.exists():
            return fail(f"missing expected public artifact: {path}")

    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    blocked_fragments = [
        "LabElastic2026",
        "LabKibana2026",
        "LabKibanaSavedObjectsKey2026AB",
        "LabKibanaReportingKey2026ABC",
        "LabKibanaSessionKey2026ABCD",
    ]
    for fragment in blocked_fragments:
        if fragment in env_example:
            return fail(".env.example still contains real-looking seeded secrets")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
