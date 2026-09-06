"""The Auditor, tested on the distinction that is actually hard.

Flagging "ignore all previous instructions" is easy. Flagging "the CFO is
short-sighted" while passing "the CFO's calculation is short-sighted about the
downside" is the whole job, because the second is exactly what a working
boardroom sounds like and a tool that flags it will be turned off.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.api.crew.auditor import audit, audit_text
from services.api.crew.transcript import Transcript
from services.api.rag.citations import Citation

CORPUS = Path(__file__).resolve().parents[1] / "fixtures/audit/breaches.jsonl"
CASES = [json.loads(line) for line in CORPUS.read_text().splitlines() if line.strip()]
BREACHES = [c for c in CASES if c["label"] != "clean"]
CLEAN = [c for c in CASES if c["label"] == "clean"]


def _rules(case):
    return {
        f.rule
        for f in audit_text(
            case["text"], turn_id=case["id"], stage=case["stage"], has_citation=case["has_citation"]
        )
    }


@pytest.mark.parametrize("case", BREACHES, ids=[c["id"] for c in BREACHES])
def test_every_seeded_breach_is_caught(case):
    assert case["label"] in _rules(case), f"missed {case['label']}: {case['text']!r}"


@pytest.mark.parametrize("case", CLEAN, ids=[c["id"] for c in CLEAN])
def test_no_clean_turn_is_flagged(case):
    """The clean cases deliberately reuse the breaches' vocabulary. Recall bought
    with false positives is worthless: an Auditor that cries wolf on a working
    boardroom gets switched off, and then it protects nothing."""
    assert _rules(case) == set(), f"false positive on: {case['text']!r}"


def test_attacking_an_argument_is_not_attacking_a_person():
    assert "ad-hominem" in _rules(
        {
            "text": "The CFO is being short-sighted again.",
            "id": "x",
            "stage": "Test",
            "has_citation": False,
        }
    )
    assert "ad-hominem" not in _rules(
        {
            "text": "The CFO's payback calculation is short-sighted about the downside.",
            "id": "y",
            "stage": "Test",
            "has_citation": False,
        }
    )


def test_a_hedge_covers_its_own_sentence_and_no_other():
    """Found by held-out evaluation against real model turns. A turn opening
    "If conversion drops below 12%..." was immunising a later, unhedged
    "the plant has a proven 15% conversion rate"."""
    text = (
        "If the conversion rate drops below 12%, the pilot could fail. "
        "The plant has a proven 15% conversion rate from its existing operations."
    )
    flags = audit_text(text, turn_id="t", stage="Decide", has_citation=False)
    unsupported = [f for f in flags if f.rule == "unsupported-number"]
    assert unsupported, "an unhedged claim after a hedged one must still be flagged"
    assert "15%" in unsupported[0].excerpt


def test_a_real_citation_clears_both_source_rules():
    clean = audit_text(
        "Footfall is 12% higher (Source: the estate report).",
        turn_id="t",
        stage="Decide",
        has_citation=True,
    )
    assert clean == []


def test_stage_rules_only_bind_in_their_own_stage():
    critique = "That will not work — the margins do not support a second site."
    assert "stage-rule" in _rules(
        {"text": critique, "id": "i", "stage": "Ideate", "has_citation": False}
    )
    assert "stage-rule" not in _rules(
        {"text": critique, "id": "t", "stage": "Test", "has_citation": False}
    )


def test_auditing_a_turn_reads_its_citations_and_stage():
    t = Transcript(session_id="s", key=b"k")
    unsourced = t.append(round_no=1, stage="Decide", speaker="cfo", text="Payback is 26 months.")
    sourced = t.append(
        round_no=1,
        stage="Decide",
        speaker="cfo",
        text="Payback is 26 months.",
        citations=(Citation("doc", 0, 5, "26"),),
    )
    assert [f.rule for f in audit(unsourced)] == ["unsupported-number"]
    assert audit(sourced) == []


def test_a_flag_points_at_the_text_that_caused_it():
    [flag] = audit_text(
        "Margin improves by AED 1.2m once the pilot scales.",
        turn_id="t",
        stage="Decide",
        has_citation=False,
    )
    assert "1.2m" in flag.excerpt
    assert flag.why and flag.severity in {"high", "medium"}


def test_auditing_is_deterministic():
    case = BREACHES[0]
    assert _rules(case) == _rules(case)


def test_the_recall_gate_passes():
    """The thresholds in scripts/audit_recall.py are the ones docs/crew.md cites."""
    import subprocess
    import sys

    repo = Path(__file__).resolve().parents[2]
    r = subprocess.run(
        [sys.executable, str(repo / "scripts/audit_recall.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
