"""Measure the Auditor against a labelled corpus, and fail if it is not good enough.

§3.8 targets the Auditor catching >= 90% of seeded stage-rule breaches. Recall
alone is trivially gamed — flag everything and score 1.0 — so the false-positive
rate is a gate too. The corpus is built so that the clean cases use the SAME
vocabulary as the breaches: "the CFO's calculation is short-sighted about the
downside" is clean, "the CFO is short-sighted" is not.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.api.crew.auditor import audit_text  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "tests/fixtures/audit/breaches.jsonl"
OUT = REPO / "docs/results/B5-auditor-recall.json"

MIN_RECALL = 0.90
MAX_FALSE_POSITIVE_RATE = 0.15


def evaluate() -> dict:
    cases = [json.loads(line) for line in CORPUS.read_text().splitlines() if line.strip()]
    per_rule: Counter[str] = Counter()
    per_rule_caught: Counter[str] = Counter()
    caught, missed, false_positives, clean_ok = 0, [], [], 0

    for case in cases:
        flags = audit_text(
            case["text"],
            turn_id=case["id"],
            stage=case["stage"],
            has_citation=case["has_citation"],
        )
        rules = {f.rule for f in flags}

        if case["label"] == "clean":
            if rules:
                false_positives.append(
                    {"id": case["id"], "flagged": sorted(rules), "text": case["text"]}
                )
            else:
                clean_ok += 1
            continue

        per_rule[case["label"]] += 1
        if case["label"] in rules:
            caught += 1
            per_rule_caught[case["label"]] += 1
        else:
            missed.append(
                {
                    "id": case["id"],
                    "expected": case["label"],
                    "got": sorted(rules),
                    "text": case["text"],
                }
            )

    n_breaches = sum(per_rule.values())
    n_clean = len(cases) - n_breaches
    recall = caught / n_breaches if n_breaches else 0.0
    fpr = len(false_positives) / n_clean if n_clean else 0.0

    return {
        "generated_by": "scripts/audit_recall.py",
        "run_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "corpus": str(CORPUS.relative_to(REPO)),
        "n_cases": len(cases),
        "n_breaches": n_breaches,
        "n_clean": n_clean,
        "thresholds": {
            "min_recall": MIN_RECALL,
            "max_false_positive_rate": MAX_FALSE_POSITIVE_RATE,
        },
        "recall": round(recall, 4),
        "false_positive_rate": round(fpr, 4),
        "recall_per_rule": {
            rule: {
                "caught": per_rule_caught[rule],
                "of": per_rule[rule],
                "recall": round(per_rule_caught[rule] / per_rule[rule], 4),
            }
            for rule in sorted(per_rule)
        },
        "missed": missed,
        "false_positives": false_positives,
        "passes": recall >= MIN_RECALL and fpr <= MAX_FALSE_POSITIVE_RATE,
    }


HELD_OUT = REPO / "docs/results/B4-mandate-differentiation.json"


def held_out() -> dict:
    """Run the Auditor over turns it was NOT tuned against.

    The corpus above was authored alongside the rules, so a perfect score on it
    measures internal consistency more than generalisation. These five turns were
    produced by qwen3:8b during the B4 measurement, before the Auditor existed,
    and every source in them is invented — which makes them the only honest test
    available of whether the rules catch anything they were not shaped around.
    """
    if not HELD_OUT.exists():
        return {"available": False}
    turns = json.loads(HELD_OUT.read_text())["turns"]
    rows = []
    for turn in turns:
        flags = audit_text(turn["text"], turn_id=turn["seat"], stage="Decide", has_citation=False)
        rows.append(
            {
                "seat": turn["seat"],
                "rules": sorted({f.rule for f in flags}),
                "n_flags": len(flags),
            }
        )
    return {
        "available": True,
        "source": str(HELD_OUT.relative_to(REPO)),
        "note": (
            "Five real qwen3:8b turns, authored by the model before the Auditor existed. "
            "The room had no documents, so every attribution in them is fabricated."
        ),
        "seats_with_a_fabricated_source_flag": sum(
            1 for r in rows if "fabricated-source" in r["rules"]
        ),
        "of_seats": len(rows),
        "rows": rows,
    }


def main() -> int:
    report = evaluate()
    report["held_out_evaluation"] = held_out()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print(f"corpus: {report['n_breaches']} breaches, {report['n_clean']} clean")
    print(f"recall               {report['recall']:.3f}  (need >= {MIN_RECALL})")
    print(
        f"false-positive rate  {report['false_positive_rate']:.3f}  (need <= {MAX_FALSE_POSITIVE_RATE})"
    )
    for rule, s in report["recall_per_rule"].items():
        print(f"   {rule:<20} {s['caught']}/{s['of']}")
    for m in report["missed"]:
        print(f"   MISSED {m['id']} ({m['expected']}): {m['text'][:70]!r}")
    for f in report["false_positives"]:
        print(f"   FALSE POSITIVE {f['id']} -> {f['flagged']}: {f['text'][:70]!r}")

    ho = report["held_out_evaluation"]
    if ho.get("available"):
        print(
            f"\nheld-out (real model turns, not authored here): "
            f"{ho['seats_with_a_fabricated_source_flag']}/{ho['of_seats']} seats flagged "
            "for a fabricated source"
        )
        for row in ho["rows"]:
            print(f"   {row['seat']:<8} {row['rules']}")

    if not report["passes"]:
        print("\nFAILED: the Auditor does not meet the thresholds in docs/crew.md", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
