"""The debate runtime, exercised entirely without a model.

Every test here runs on the deterministic stub. That is the point of having one:
the things worth asserting about a debate — that a round produces five turns,
that the record is sealed, that the kill switch stops it, that concurrency does
not reorder the transcript — are properties of the runtime, not of the model.
"""

from __future__ import annotations

import pytest

from services.api.core import killswitch
from services.api.core.llm import LLMChain, StubProvider
from services.api.core.quota import Quota
from services.api.crew.facilitator import Facilitator
from services.api.crew.mandate import SEATING
from services.api.crew.session import STAGE_RULES, Stage

QUESTION = "Should we pilot in a Dubai hypermarket or a Greenlam plant first?"


@pytest.fixture(autouse=True)
def _released():
    killswitch.release()
    yield
    killswitch.release()


@pytest.fixture
def facilitator():
    return Facilitator(LLMChain([StubProvider()], Quota({"stub": 10_000})))


def test_a_three_round_debate_produces_fifteen_mandate_turns(facilitator):
    session = facilitator.open("s1", QUESTION, stage=Stage.TEST)
    for _ in range(3):
        facilitator.run_round(session)
    facilitator.close(session)

    mandate_turns = [t for t in session.transcript.turns() if t.speaker in SEATING]
    assert len(mandate_turns) == 15
    assert session.transcript.verify() == [], "the record of a debate must be sealed"


def test_every_seat_speaks_exactly_once_per_round(facilitator):
    session = facilitator.open("s2", QUESTION)
    turns = facilitator.run_round(session)
    assert [t.speaker for t in turns] == list(SEATING)


def test_turn_order_is_seating_order_not_completion_order(facilitator):
    """Five seats speak concurrently. If the record were written in completion
    order, the same debate would produce a different hash chain each run and
    replay would be meaningless."""
    orders = []
    for i in range(3):
        session = facilitator.open(f"s-order-{i}", QUESTION)
        facilitator.run_round(session)
        orders.append([t.speaker for t in session.transcript.turns() if t.speaker in SEATING])
    assert orders[0] == orders[1] == orders[2] == list(SEATING)


def test_a_seat_argues_against_the_previous_round_not_the_current_one(facilitator):
    """What makes concurrent speaking equivalent to sequential speaking. If a
    seat could see another seat's turn from its own round, whoever ran last
    would have an advantage the round exists to remove."""
    session = facilitator.open("s3", QUESTION)
    facilitator.run_round(session)
    before = len(session.transcript.turns())

    captured: list[str] = []
    original = facilitator.llm.complete

    def spy(system, messages, **kw):
        captured.append(messages[0].content)
        return original(system, messages, **kw)

    facilitator.llm.complete = spy  # type: ignore[method-assign]
    facilitator.run_round(session)

    assert len(captured) == 5
    assert len(set(captured)) == 1, "all five seats must see an identical history"
    for history in captured:
        assert history.count("[round 1]") == before - 1  # minus the facilitator's opening turn
        assert "[round 2]" not in history


def test_the_opening_turn_records_the_question_and_the_rules_in_force(facilitator):
    session = facilitator.open("s4", QUESTION, stage=Stage.IDEATE)
    opening = session.transcript.turns()[0]
    assert opening.speaker == "facilitator"
    assert QUESTION in opening.text
    assert STAGE_RULES[Stage.IDEATE][0] in opening.text


def test_the_kill_switch_stops_a_debate_and_leaves_a_verifiable_record(facilitator):
    session = facilitator.open("s5", QUESTION)
    facilitator.run_round(session)
    killswitch.engage("owner stopped the session")

    with pytest.raises(killswitch.KillSwitchEngaged):
        facilitator.run_round(session)

    assert session.transcript.verify() == [], "a halted debate still has an intact record"
    assert len([t for t in session.transcript.turns() if t.speaker in SEATING]) == 5


def test_budget_exhaustion_degrades_rather_than_raising():
    """A room that runs out of budget mid-round must still produce a round.
    Losing the argument because the quota ran out would lose the record too."""
    thin = LLMChain([StubProvider(name="ollama", model="local")], Quota({"ollama": 2, "stub": 999}))
    session = Facilitator(thin).open("s6", QUESTION)
    turns = Facilitator(thin).run_round(session)
    assert len(turns) == 5
    providers = {t.provider for t in turns}
    assert providers == {"ollama", "stub"}, providers
    assert session.ended_early and "stub" in session.ended_early


def test_the_chair_can_interject_and_it_is_recorded_as_a_turn(facilitator):
    """The human is a participant in the record, not an editor of it."""
    session = facilitator.open("s7", QUESTION)
    facilitator.run_round(session)
    turn = facilitator.interject(session, "Assume the plant loses a shift in Q1. Re-argue.")

    assert turn.speaker == "chair"
    assert "loses a shift" in turn.text
    assert session.transcript.verify() == []
    assert session.transcript.turns()[-1].turn_id == turn.turn_id


def test_advancing_a_stage_changes_the_rules_the_seats_are_given(facilitator):
    session = facilitator.open("s8", QUESTION, stage=Stage.IDEATE)
    assert any("No critique" in r for r in session.rules)
    facilitator.advance(session, Stage.TEST)
    assert any("Critique is expected" in r for r in session.rules)
    assert not any("No critique" in r for r in session.rules)
    assert session.transcript.verify() == []


def test_a_closed_session_refuses_another_round(facilitator):
    session = facilitator.open("s9", QUESTION)
    facilitator.close(session)
    with pytest.raises(RuntimeError, match="closed"):
        facilitator.run_round(session)


def test_every_stage_declares_at_least_one_rule():
    """A stage whose rule nothing checks is a heading, not a stage."""
    for stage in Stage:
        assert STAGE_RULES[stage], stage
