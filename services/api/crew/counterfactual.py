"""Which single piece of evidence would flip this decision.

WHAT THIS IS
------------
Every score records the evidence ids it rests on. Remove one id, drop every
score that depended on it, re-aggregate, and see whether the winner changes.
That is the whole mechanism, and it is arithmetic — deterministic, instant, and
identical every run.

WHAT THIS IS NOT, AND WHY IT MATTERS THAT YOU KNOW
--------------------------------------------------
It is **not** a re-run of the argument. The room is not asked to reconsider
without e2; the scores that cited e2 are simply set aside. A real re-debate
might land somewhere else entirely — a seat that leaned on e2 might find another
reason for the same position, or change its mind about something unrelated.

So this answers "how much of the current decision rests on this piece of
evidence", which is a sensitivity analysis, not "what would the room decide
without it", which would need another four minutes and five model calls. Every
surface that shows a flip says so, because the difference is exactly the kind of
thing a reader would otherwise assume the other way.

THE HONEST CASE
---------------
The most useful output is often the empty one. A decision no single piece of
evidence can flip is a robust decision, and saying so plainly is worth more than
manufacturing a flip by lowering the bar.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.api.core.schemas import Score
from services.api.crew.stages import Evidence, aggregate

Scores = dict[str, list[Score]]


@dataclass(frozen=True)
class Flip:
    """Removing this evidence changes which option wins."""

    evidence_id: str
    summary: str
    winner_before: str
    winner_after: str
    margin_before: float
    margin_after: float
    #: Seats whose scores were set aside — who was actually leaning on this.
    seats_affected: tuple[str, ...]


@dataclass(frozen=True)
class SeatSensitivity:
    seat: str
    #: Fraction of this seat's scored points that rest on evidence at all.
    grounded_share: float
    depends_on: tuple[str, ...]
    #: True when this seat scored without citing any evidence. Not an error —
    #: a seat may argue from its mandate alone — but the memo should say so.
    ungrounded: bool


def _without(scores: Scores, evidence_id: str) -> tuple[Scores, tuple[str, ...]]:
    """Drop every score that leaned on this evidence."""
    kept: Scores = {}
    affected: set[str] = set()
    for seat, seat_scores in scores.items():
        remaining = []
        for score in seat_scores:
            if evidence_id in score.depends_on:
                affected.add(seat)
            else:
                remaining.append(score)
        kept[seat] = remaining
    return kept, tuple(sorted(affected))


def _leader(scores: Scores) -> tuple[str | None, float]:
    ranked = aggregate(scores)
    if not ranked:
        return None, 0.0
    if len(ranked) == 1:
        return ranked[0].option, float(ranked[0].total)
    return ranked[0].option, float(ranked[0].total - ranked[1].total)


def flips(scores: Scores, evidence: list[Evidence]) -> list[Flip]:
    """Every single evidence item whose removal changes the winner.

    Single-item only, on purpose. Combinations grow exponentially and, more to
    the point, "these four things together would flip it" is not an actionable
    sentence for someone deciding what to go and find out.
    """
    before, margin_before = _leader(scores)
    if before is None:
        return []

    found: list[Flip] = []
    for item in evidence:
        reduced, affected = _without(scores, item.evidence_id)
        if not affected:
            continue
        after, margin_after = _leader(reduced)
        if after is not None and after != before:
            found.append(
                Flip(
                    evidence_id=item.evidence_id,
                    summary=item.summary,
                    winner_before=before,
                    winner_after=after,
                    margin_before=margin_before,
                    margin_after=margin_after,
                    seats_affected=affected,
                )
            )
    return sorted(found, key=lambda f: (f.margin_after, f.evidence_id))


def sensitivity(scores: Scores) -> list[SeatSensitivity]:
    """How much of each seat's position rests on evidence rather than mandate."""
    out = []
    for seat in sorted(scores):
        seat_scores = scores[seat]
        if not seat_scores:
            out.append(SeatSensitivity(seat, 0.0, (), ungrounded=True))
            continue
        grounded = sum(s.total for s in seat_scores if s.depends_on)
        total = sum(s.total for s in seat_scores)
        ids = sorted({e for s in seat_scores for e in s.depends_on})
        out.append(
            SeatSensitivity(
                seat=seat,
                grounded_share=round(grounded / total, 4) if total else 0.0,
                depends_on=tuple(ids),
                ungrounded=not ids,
            )
        )
    return out


@dataclass(frozen=True)
class Robustness:
    winner: str | None
    margin: float
    n_flips: int
    #: The plain-English answer, which is the thing a reader actually wants.
    verdict: str


def robustness(scores: Scores, evidence: list[Evidence]) -> Robustness:
    winner, margin_now = _leader(scores)
    found = flips(scores, evidence)
    if winner is None:
        verdict = "Nothing was scored, so there is no decision to test."
    elif not evidence:
        verdict = (
            "No evidence was recorded, so this decision rests entirely on the mandates' "
            "judgement. Nothing here can be tested by removing a source."
        )
    elif not found:
        verdict = (
            f"No single piece of evidence changes the outcome. The room's preference for "
            f"{winner} does not hang on any one source."
        )
    elif len(found) == 1:
        f = found[0]
        verdict = (
            f"The decision hangs on one thing: remove {f.evidence_id} ({f.summary}) and the "
            f"room prefers {f.winner_after} instead."
        )
    else:
        names = ", ".join(f.evidence_id for f in found)
        verdict = (
            f"{len(found)} separate pieces of evidence would each flip this on their own "
            f"({names}). The decision is not robust."
        )
    return Robustness(winner=winner, margin=margin_now, n_flips=len(found), verdict=verdict)
