"""Publish the OWASP scorecard, and fail if a risk has no test behind it.

The scorecard is generated from the suite, so this script cannot make the
project look safer than it is: a risk with no covering test prints as a GAP and
the script exits non-zero.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.api.security.scorecard import scorecard  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs/results/E1-owasp-scorecard.json"


def main() -> int:
    report = scorecard()
    report["run_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print(f"{'risk':<8}{'status':<17}tests")
    for row in report["risks"]:
        print(f"{row['id']:<8}{row['status']:<17}{len(row['tests'])}")
    print(
        f"\n{report['n_covered']} covered, {report['n_not_applicable']} not applicable, "
        f"{report['n_gaps']} gap(s), {report['n_assertions']} assertions"
    )
    print(f"written to {OUT.relative_to(REPO)}")

    if report["n_gaps"]:
        print(f"\nFAILED: uncovered risks: {report['gaps']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
