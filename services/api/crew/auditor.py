r"""The Auditor: what the room is not allowed to get away with.

WHAT THIS IS FOR
----------------
Phase B measured five mandates arguing a real decision on a local model, and
every source in the sample was invented — a Q3 footfall report, a Dubai Chamber
statistic, a policy clause, a customer quote, none of which exist
(docs/results/B4-mandate-differentiation.json). The room had been given no
documents, and rather than saying so, all five seats produced exactly the
citation-shaped evidence their mandates ask for.

That is not a prompt bug to be fixed with a firmer instruction. A mandate told
to cite will cite. So the Auditor is mechanical, deterministic, and runs on
every turn.

FOUR RULES, AND WHY EACH EXISTS
-------------------------------
  fabricated-source    A citation-shaped attribution — "(Source: ...)",
                       "(Dubai Chamber, 2023)", "Clause 4.2 of ..." — with no
                       resolvable citation on the turn. This is the B4 failure,
                       named.
  unsupported-number   A hard figure with nothing behind it and no hedge. A
                       boardroom runs on numbers; an unsourced one is an
                       assumption wearing a number's clothes, which is the CFO
                       mandate's own words.
  ad-hominem           An attack on a seat rather than on its argument. The
                       distinction is grammatical and is the whole difficulty:
                       "the CFO is short-sighted" is an attack, "the CFO's
                       calculation is short-sighted about the downside" is the
                       same objection made properly.
  stage-rule           Critique during Ideate, or a solution during
                       Empathise/Define. Divergence collapses the moment
                       someone starts evaluating, so the rule that protects it
                       has to be enforced rather than merely printed.

WHAT IT DOES NOT CATCH, STATED PLAINLY
--------------------------------------
A confident, well-hedged, entirely wrong argument with no numbers in it passes
cleanly. The Auditor checks the FORM of an argument — sourcing, target, and
stage discipline — not its truth. Judging truth is the room's job, and the
outcome ledger's.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Severity = Literal["high", "medium"]

SEATS = ("cfo", "cmo", "coo", "ethics officer", "ethics", "devil's advocate", "devil", "chair")
_SEAT_ALT = "|".join(re.escape(s) for s in sorted(SEATS, key=len, reverse=True))


@dataclass(frozen=True)
class Flag:
    turn_id: str
    rule: str
    severity: Severity
    excerpt: str
    why: str


# ── ad-hominem ──────────────────────────────────────────────────────────────
# The seat as SUBJECT of an evaluative predicate, or a dismissive vocative.
# A possessive ("the CFO's calculation") is deliberately not matched: that is an
# attack on the artefact, which is exactly what the room is for.
_JUDGEMENT = (
    r"short-?sighted|naive|naïve|contrarian|obtuse|lazy|paranoid|clueless|"
    r"allergic|incompetent|hysterical|obstructive|out of (?:their|his|her) depth"
)
_AD_HOMINEM = [
    re.compile(
        rf"\b(?:the\s+)?(?:{_SEAT_ALT})\s+(?:is|are|was|were)\s+(?:just\s+|simply\s+|being\s+)*(?:{_JUDGEMENT})\b",
        re.I,
    ),
    re.compile(rf"\byou\s+are\s+(?:just\s+|simply\s+|being\s+)*(?:{_JUDGEMENT})\b", re.I),
    re.compile(rf"\btypical\s+(?:{_SEAT_ALT})\b", re.I),
    re.compile(rf"\b(?:the\s+)?(?:{_SEAT_ALT})\s+always\s+\w+", re.I),
    re.compile(rf"\b(?:the\s+)?(?:{_SEAT_ALT})\s+(?:simply\s+)?does\s+not\s+understand\b", re.I),
    re.compile(rf"\b(?:the\s+)?(?:{_SEAT_ALT})\s+is\s+(?:just\s+)?being\s+\w+", re.I),
]

# ── fabricated source ───────────────────────────────────────────────────────
# Attribution shapes a model reaches for when it has nothing to cite.
_SOURCE_SHAPED = [
    re.compile(r"\(\s*(?:source|per|via|from)\s*[:,][^)]{3,80}\)", re.I),
    re.compile(r"\([A-Z][\w&.\- ]{2,40},\s*(?:19|20)\d{2}(?:-\d{2})?(?:-\d{2})?\s*\)"),
    re.compile(
        r"\((?:[A-Z][\w.\- ]{2,40}\s+)?(?:report|audit|study|survey|model|interview)[^)]{0,40}\)",
        re.I,
    ),
    re.compile(r"\bclause\s+\d+(?:\.\d+)*\s+of\s+the\s+[\w\s]{3,60}\b", re.I),
    re.compile(r"\bp(?:age|p)?\.\s?\d+\b", re.I),
    # A bare year inside a parenthetical. Added after held-out evaluation: the
    # Devil's Advocate wrote "(as seen in similar markets in 2022)", which is an
    # attribution in every respect except the capital letter and the comma the
    # earlier patterns keyed on.
    re.compile(r"\([^)]{0,70}\b(?:19|20)\d{2}\b[^)]{0,20}\)"),
]

# ── numbers ─────────────────────────────────────────────────────────────────
_NUMBER = re.compile(
    r"(?<![\w.])(?:"
    r"\d+(?:\.\d+)?\s?%"  # 12%, 14.2 %
    r"|(?:AED|USD|EUR|GBP|\$|€|£)\s?\d[\d,.]*\s?[kmbn]?"  # AED 2.4m
    r"|\d[\d,]{2,}"  # 250,000
    r"|\d+(?:\.\d+)?\s?(?:months?|weeks?|days?|hours?|units?|shifts?|bps)\b"
    r")",
    re.I,
)
#: Language that marks a figure as an estimate rather than a finding. A hedged
#: number is a contribution to an argument; an unhedged one is a claim.
_HEDGE = re.compile(
    r"\b(?:assume|assuming|suppose|supposing|roughly|approximately|about|around|"
    r"estimate[sd]?|order of magnitude|ballpark|if\b|hypothetical(?:ly)?|say\b|"
    r"not (?:a )?measured|have not verified|unverified|i am not claiming)\b",
    re.I,
)

# ── stage rules ─────────────────────────────────────────────────────────────
_CRITIQUE = re.compile(
    r"\b(?:will not work|won'?t work|that fails|does not work|doesn'?t work|"
    r"the problem with|i disagree|however|but that|too expensive|impossible|"
    r"cannot support|does not support)\b",
    re.I,
)
_SOLUTION = re.compile(
    r"\b(?:we should|the solution is|i recommend|let'?s|we will|we must|roll out|launch)\b",
    re.I,
)
_NO_CRITIQUE_STAGES = {"Ideate"}
_NO_SOLUTION_STAGES = {"Empathise", "Define"}


_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


def _sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE.split(text) if s.strip()]


def _excerpt(text: str, match: re.Match[str]) -> str:
    start = max(0, match.start() - 30)
    return text[start : min(len(text), match.end() + 30)].strip()


def audit_text(text: str, *, turn_id: str, stage: str, has_citation: bool) -> list[Flag]:
    """Audit one turn's text. Deterministic; no model involved.

    `has_citation` is whether the turn carries a resolvable Citation. It is the
    difference between quoting the room's own documents and inventing a source.
    """
    flags: list[Flag] = []

    for pattern in _AD_HOMINEM:
        m = pattern.search(text)
        if m:
            flags.append(
                Flag(
                    turn_id,
                    "ad-hominem",
                    "high",
                    _excerpt(text, m),
                    "This attacks the seat rather than its argument. The same objection about the "
                    "seat's reasoning, calculation or assumption is in order.",
                )
            )
            break

    if not has_citation:
        for pattern in _SOURCE_SHAPED:
            m = pattern.search(text)
            if m:
                flags.append(
                    Flag(
                        turn_id,
                        "fabricated-source",
                        "high",
                        _excerpt(text, m),
                        "This is shaped like an attribution but no citation on the turn resolves to "
                        "it. A source that cannot be opened is not a source.",
                    )
                )
                break

    if not has_citation:
        # Hedging is judged PER SENTENCE, not per turn. Held-out evaluation caught
        # this: a turn that opened "If conversion drops below 12%..." and then
        # asserted "the plant has a proven 15% conversion rate" passed entirely,
        # because one "If" two sentences earlier immunised every number after it.
        # A hedge covers the claim it is attached to, and no other.
        for sentence in _sentences(text):
            if _HEDGE.search(sentence):
                continue
            m = _NUMBER.search(sentence)
            if m:
                flags.append(
                    Flag(
                        turn_id,
                        "unsupported-number",
                        "medium",
                        _excerpt(sentence, m),
                        "A figure with no source and no hedge. Mark it as an estimate or cite it.",
                    )
                )
                break

    if stage in _NO_CRITIQUE_STAGES:
        m = _CRITIQUE.search(text)
        if m:
            flags.append(
                Flag(
                    turn_id,
                    "stage-rule",
                    "high",
                    _excerpt(text, m),
                    "Critique during Ideate. Divergence collapses the moment someone starts "
                    "evaluating; build on the idea instead.",
                )
            )
    if stage in _NO_SOLUTION_STAGES:
        m = _SOLUTION.search(text)
        if m:
            flags.append(
                Flag(
                    turn_id,
                    "stage-rule",
                    "high",
                    _excerpt(text, m),
                    f"A solution proposed during {stage}. This stage is for understanding the "
                    "problem, not choosing an answer.",
                )
            )

    return flags


def audit(turn, *, stage: str | None = None) -> list[Flag]:
    """Audit a Turn from a transcript."""
    return audit_text(
        turn.text,
        turn_id=turn.turn_id,
        stage=stage or turn.stage,
        has_citation=bool(turn.citations),
    )
