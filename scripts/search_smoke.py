"""Prove which search tier actually served each query, today.

`docs/datasets.md` claims COUNSEL can research a decision on free sources. This
script is the evidence behind that sentence: it runs the real chain against real
queries and records the tier that answered, so the claim in the docs is a
measurement rather than an intention.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.api.core.search import (  # noqa: E402
    KeylessProvider,
    SearchChain,
    SearxngProvider,
    StubSearchProvider,
    UserLinksProvider,
)

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs/results/A4-search-smoke.json"

QUERIES = [
    "Dubai hypermarket footfall analytics pilot",
    "laminate manufacturing plant OEE improvement",
    "design thinking decision memo dissent log",
]


def main() -> int:
    chain = SearchChain(
        [SearxngProvider(), KeylessProvider(), UserLinksProvider([]), StubSearchProvider()]
    )
    report = {
        "generated_by": "scripts/search_smoke.py",
        "run_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tier_health": chain.health(),
        "queries": [],
    }

    for query in QUERIES:
        results = chain.search(query, limit=5)
        report["queries"].append(
            {
                "query": query,
                "served_by": results[0].provider if results else None,
                "degraded_from": list(chain.last_degraded_from),
                "n_results": len(results),
                "all_untrusted": all(r.trust == "untrusted" for r in results),
                "sample": [{"title": r.title, "url": r.url} for r in results[:2]],
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    for q in report["queries"]:
        print(f"  {q['served_by']:<20} {q['n_results']} results  <- {q['query']}")
        if q["degraded_from"]:
            print(f"    {' | '.join(q['degraded_from'])}")
    print(f"written to {OUT.relative_to(REPO)}")

    if not all(q["all_untrusted"] for q in report["queries"]):
        print("FAILED: a result escaped the untrusted tag", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
