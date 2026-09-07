"""The chamber's geometry, which must never say more than the transcript does.

A 3D view is where an invented measurement would be least questioned — it looks
like data because it looks like a diagram. So the derivation is tested for what
it refuses to claim as much as for what it draws.
"""

from __future__ import annotations

import pytest

from services.api.core.db import connect
from services.api.crew.chamber import addressees, chamber_state, edges
from services.api.crew.transcript import Transcript


def test_naming_a_seat_creates_an_edge_to_it():
    assert addressees("The COO's throughput figure is from the line.", speaker="cfo") == ("coo",)
    assert addressees("The Chief Marketing Officer overstates demand.", speaker="cfo") == ("cmo",)


def test_a_seat_naming_itself_creates_no_edge():
    """A self-edge on a round table is a circle nobody can read, and it is not
    an argument between two people."""
    assert addressees("As CFO I anchored on the first number.", speaker="cfo") == ()


def test_naming_nobody_creates_no_edge():
    assert addressees("Payback lands at 26 months on the current model.", speaker="cfo") == ()


def test_several_seats_named_in_one_turn_all_get_edges():
    got = addressees(
        "The COO and the Ethics Officer are both right that this slips.", speaker="devil"
    )
    assert got == ("coo", "ethics")


def test_edges_are_returned_in_seating_order_not_mention_order():
    """So the same transcript draws the same picture every time."""
    a = addressees("The Devil's Advocate, then the CFO, then the COO.", speaker="cmo")
    b = addressees("The COO, the CFO, and the Devil's Advocate.", speaker="cmo")
    assert a == b == ("cfo", "coo", "devil")


@pytest.mark.parametrize(
    "text",
    [
        "The chief financial officers of our competitors disagree.",
        "Coordinating with the cooperative is a separate question.",
    ],
)
def test_a_word_containing_a_seat_name_is_not_a_mention(text):
    """'coo' inside 'cooperative' must not seat someone at the table."""
    assert addressees(text, speaker="devil") == ()


def test_the_derivation_is_deterministic():
    text = "The COO and the CFO disagree about the shift."
    assert addressees(text, speaker="cmo") == addressees(text, speaker="cmo")


def test_edges_carry_the_turn_they_came_from():
    t = Transcript(session_id="s", key=b"k")
    turn = t.append(
        round_no=1, stage="Test", speaker="cfo", text="The COO is right about capacity."
    )
    [edge] = edges(t.turns())
    assert edge.from_seat == "cfo" and edge.to_seat == "coo"
    assert edge.turn_id == turn.turn_id and edge.round_no == 1


def test_non_seat_turns_produce_no_edges():
    """The Facilitator's opening turn names the room; it is not an argument."""
    t = Transcript(session_id="s", key=b"k")
    t.append(round_no=0, stage="Test", speaker="facilitator", text="The CFO and COO will speak.")
    assert edges(t.turns()) == []


def test_chamber_state_says_what_it_shows_and_what_it_does_not():
    conn = connect(":memory:")
    try:
        conn.execute(
            "INSERT INTO sessions(session_id, question, stage, round_no, closed, created_at) "
            "VALUES ('s1','q?','Test',1,0,'2026-01-01T00:00:00Z')"
        )
        conn.commit()
        state = chamber_state("s1", conn=conn)
        assert [s["id"] for s in state["seats"]] == ["cfo", "cmo", "coo", "ethics", "devil"]
        assert "not that it agreed" in state["shows"]
        assert state["turns"] == [] and state["edges"] == []
    finally:
        conn.close()
