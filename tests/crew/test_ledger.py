"""Calibration, and the gate that stops it lying.

The five mandates' expertise is prompt-defined. The ledger is the only thing
that can turn that into a measurable claim — but only over enough decisions. A
Brier score across two sessions is noise wearing a decimal point, so the
minimum-N gate is tested harder than the arithmetic.
"""

from __future__ import annotations

import pytest

from services.api.core.db import connect
from services.api.crew.ledger import (
    COIN_FLIP,
    MIN_OUTCOMES,
    brier,
    calibration,
    ledger,
    record_outcome,
    record_prediction,
)


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


_settled = 0


def settle(conn, seat, *, n, confidence, correct):
    """n fresh sessions in which `seat` backed an option with `confidence`."""
    global _settled
    for _ in range(n):
        _settled += 1
        sid = f"s{seat}{_settled}"
        conn.execute(
            "INSERT OR IGNORE INTO sessions(session_id, question, stage, round_no, closed, "
            "created_at) VALUES (?, 'q?', 'Decide', 1, 1, '2026-01-01T00:00:00Z')",
            (sid,),
        )
        backed = "plant" if correct else "hypermarket"
        record_prediction(sid, seat, backed, confidence, conn=conn)
        record_outcome(sid, chosen=backed, actual="plant", notes="", conn=conn)
    conn.commit()


def test_a_seat_below_the_minimum_returns_none_not_a_number():
    """The gate that matters more than the score. A caller that defaults None to
    0.0 would show a perfectly calibrated seat that has never been tested."""
    c = connect(":memory:")
    try:
        settle(c, "cfo", n=MIN_OUTCOMES - 1, confidence=0.9, correct=True)
        assert brier("cfo", conn=c) is None, "four outcomes is not a calibration record"
        settle(c, "cfo", n=1, confidence=0.9, correct=True)
        assert brier("cfo", conn=c) is not None, "the gate opens at exactly MIN_OUTCOMES"
    finally:
        c.close()


def test_a_perfectly_calibrated_seat_scores_near_zero(conn):
    settle(conn, "coo", n=8, confidence=1.0, correct=True)
    result = brier("coo", conn=conn)
    assert result and result.score == pytest.approx(0.0)
    assert result.hit_rate == 1.0
    assert "Well calibrated" in result.reading


def test_a_confidently_wrong_seat_scores_near_one(conn):
    settle(conn, "devil", n=8, confidence=1.0, correct=False)
    result = brier("devil", conn=conn)
    assert result and result.score == pytest.approx(1.0)
    assert result.hit_rate == 0.0
    assert "Worse than always saying 50%" in result.reading


def test_the_coin_flip_baseline_is_the_line_that_matters(conn):
    """A seat that always says 50% scores exactly 0.25 whatever happens. That is
    the number a reader should compare against, not zero."""
    settle(conn, "cmo", n=6, confidence=0.5, correct=True)
    result = brier("cmo", conn=conn)
    assert result and result.score == pytest.approx(COIN_FLIP)


def test_the_score_does_not_depend_on_the_order_outcomes_were_recorded(conn):
    settle(conn, "ethics", n=3, confidence=0.9, correct=True)
    settle(conn, "ethics", n=3, confidence=0.2, correct=True)
    first = brier("ethics", conn=conn)

    other = connect(":memory:")
    try:
        settle(other, "ethics", n=3, confidence=0.2, correct=True)
        settle(other, "ethics", n=3, confidence=0.9, correct=True)
        assert brier("ethics", conn=other).score == first.score
    finally:
        other.close()


def test_calibration_separates_scored_seats_from_pending_ones(conn):
    settle(conn, "cfo", n=6, confidence=0.8, correct=True)
    settle(conn, "cmo", n=2, confidence=0.8, correct=True)
    scored, pending = calibration(conn=conn)

    assert [b.seat for b in scored] == ["cfo"]
    by_seat = {p.seat: p for p in pending}
    assert by_seat["cmo"].n_outcomes == 2
    assert by_seat["cmo"].needs == MIN_OUTCOMES - 2
    assert by_seat["devil"].needs == MIN_OUTCOMES, "an untested seat needs the full minimum"


def test_scored_seats_are_ranked_best_first(conn):
    settle(conn, "coo", n=6, confidence=1.0, correct=True)
    settle(conn, "devil", n=6, confidence=1.0, correct=False)
    scored, _ = calibration(conn=conn)
    assert [b.seat for b in scored] == ["coo", "devil"]


def test_confidence_is_stored_at_prediction_time_and_not_rewritten(conn):
    """The entire point of a calibration record. If the outcome could revise the
    confidence, the score would measure nothing."""
    conn.execute(
        "INSERT INTO sessions(session_id, question, stage, round_no, closed, created_at) "
        "VALUES ('s1', 'q?', 'Decide', 1, 1, '2026-01-01T00:00:00Z')"
    )
    record_prediction("s1", "cfo", "plant", 0.9, conn=conn)
    record_outcome("s1", chosen="plant", actual="hypermarket", notes="the plant slipped", conn=conn)
    stored = conn.execute(
        "SELECT confidence FROM predictions WHERE session_id='s1' AND seat='cfo'"
    ).fetchone()["confidence"]
    assert stored == 0.9


def test_the_ledger_lists_outcomes_with_their_question(conn):
    conn.execute(
        "INSERT INTO sessions(session_id, question, stage, round_no, closed, created_at) "
        "VALUES ('s1', 'hypermarket or plant?', 'Learn', 3, 1, '2026-01-01T00:00:00Z')"
    )
    record_outcome("s1", chosen="plant", actual="plant", notes="ran Q2", conn=conn)
    [row] = ledger(conn=conn)
    assert row["question"] == "hypermarket or plant?" and row["notes"] == "ran Q2"


def test_an_empty_ledger_is_empty_rather_than_an_error(conn):
    scored, pending = calibration(conn=conn)
    assert scored == []
    assert len(pending) == 5 and all(p.needs == MIN_OUTCOMES for p in pending)
    assert ledger(conn=conn) == []
