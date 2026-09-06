"""Who was right, and how sure they were when they said it.

WHY THIS EXISTS
---------------
The five mandates' "expertise" is prompt-defined. That is stated everywhere in
this project, and it is the honest limitation. The outcome ledger is the only
thing that can turn it into a measurable claim: over enough decisions, a seat
that is confidently wrong will score differently from one that is calibrated,
and neither the prompt nor anybody's opinion decides that.

THE MEASURE
-----------
Brier score, on each seat's confidence in the option it backed:

    (confidence - outcome)^2      outcome = 1 if that option proved right, else 0

Lower is better. 0.0 is perfect. 0.25 is what you get by always saying 50%, which
makes it the line worth looking at: a seat above 0.25 is worse than a coin that
admits it does not know.

THE GATE THAT MATTERS MORE THAN THE SCORE
-----------------------------------------
A Brier score over two decisions is noise wearing a decimal point. `brier()`
returns None below MIN_OUTCOMES and every caller must handle it — the API omits
the seat, and the UI is required to say how many more outcomes are needed rather
than drawing a chart of nothing. This is the difference between a calibration
record and a number that flatters whoever ran the fewest sessions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from sqlite3 import Connection

from services.api.core.db import WRITE_LOCK

#: Below this, a Brier score is noise. Chosen because five is the smallest
#: number at which a single lucky call cannot dominate the mean, and it is
#: stated in the UI rather than hidden.
MIN_OUTCOMES = 5

#: Always-50% baseline. A seat above this is worse than a coin that admits it.
COIN_FLIP = 0.25


@dataclass(frozen=True)
class BrierScore:
    seat: str
    score: float
    n_outcomes: int
    mean_confidence: float
    #: How often the seat backed the option that turned out right.
    hit_rate: float
    #: Plain English, because a decimal alone tells a reader nothing.
    reading: str


@dataclass(frozen=True)
class Pending:
    """A seat that has not been scored yet, and how far off it is."""

    seat: str
    n_outcomes: int
    needs: int


def record_prediction(
    session_id: str, seat: str, option: str, confidence: float, *, conn: Connection
) -> None:
    """Store what a seat backed, at the moment it backed it."""
    with WRITE_LOCK:
        conn.execute(
            "INSERT INTO predictions(session_id, seat, option, confidence) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(session_id, seat, option) DO UPDATE SET confidence = excluded.confidence",
            (session_id, seat, option, float(confidence)),
        )
        conn.commit()


def record_outcome(
    session_id: str, *, chosen: str, actual: str, notes: str, conn: Connection
) -> None:
    """What actually happened. The Learn stage, months later."""
    with WRITE_LOCK:
        conn.execute(
            "INSERT INTO outcomes(session_id, chosen, actual, notes, recorded_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(session_id) DO UPDATE SET "
            "chosen=excluded.chosen, actual=excluded.actual, notes=excluded.notes, "
            "recorded_at=excluded.recorded_at",
            (
                session_id,
                chosen,
                actual,
                notes,
                datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
        conn.commit()


def _scored_rows(seat: str, *, conn: Connection) -> list[tuple[float, int]]:
    """(confidence, was_right) for every settled prediction by this seat.

    One row per SESSION, not per prediction. A seat scores every option on the
    table, so it holds several confidences per session; the one that counts for
    calibration is the option it actually backed, which is the one it was most
    confident in. Keying this by anything other than the session — the outcome,
    say — collapses every session into one row and makes the whole score a lie.
    """
    rows = conn.execute(
        "SELECT p.session_id, p.confidence, p.option, o.actual FROM predictions p "
        "JOIN outcomes o ON o.session_id = p.session_id WHERE p.seat = ? "
        "ORDER BY p.session_id, p.option",
        (seat,),
    ).fetchall()

    backed: dict[str, tuple[float, int]] = {}
    for row in rows:
        session_id = row["session_id"]
        confidence = float(row["confidence"])
        current = backed.get(session_id)
        if current is None or confidence > current[0]:
            backed[session_id] = (confidence, 1 if row["option"] == row["actual"] else 0)
    return [backed[sid] for sid in sorted(backed)]


def _reading(score: float, n: int) -> str:
    if score <= 0.10:
        return f"Well calibrated over {n} outcomes: confident when right, hesitant when not."
    if score <= COIN_FLIP:
        return f"Better than always saying 50%, over {n} outcomes."
    return (
        f"Worse than always saying 50%, over {n} outcomes. This seat is confident in the "
        "wrong direction often enough to matter."
    )


def brier(seat: str, *, conn: Connection) -> BrierScore | None:
    """None below MIN_OUTCOMES. Callers must handle that rather than default to 0."""
    rows = _scored_rows(seat, conn=conn)
    if len(rows) < MIN_OUTCOMES:
        return None
    score = sum((c - o) ** 2 for c, o in rows) / len(rows)
    return BrierScore(
        seat=seat,
        score=round(score, 4),
        n_outcomes=len(rows),
        mean_confidence=round(sum(c for c, _ in rows) / len(rows), 4),
        hit_rate=round(sum(o for _, o in rows) / len(rows), 4),
        reading=_reading(score, len(rows)),
    )


def calibration(*, conn: Connection) -> tuple[list[BrierScore], list[Pending]]:
    """Every seat, split into those that can be scored and those that cannot."""
    from services.api.crew.mandate import SEATING

    scored, pending = [], []
    for seat in SEATING:
        result = brier(seat, conn=conn)
        if result is not None:
            scored.append(result)
        else:
            n = len(_scored_rows(seat, conn=conn))
            pending.append(Pending(seat=seat, n_outcomes=n, needs=MIN_OUTCOMES - n))
    return sorted(scored, key=lambda b: b.score), pending


def ledger(*, conn: Connection) -> list[dict[str, object]]:
    return [
        dict(r)
        for r in conn.execute(
            "SELECT o.*, s.question FROM outcomes o JOIN sessions s "
            "ON s.session_id = o.session_id ORDER BY o.recorded_at DESC"
        ).fetchall()
    ]
