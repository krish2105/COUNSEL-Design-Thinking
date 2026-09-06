"""The record has to be the thing that survives.

A memo, a dissent log and a calibration score are all downstream of the
transcript. If the transcript can be quietly adjusted, none of them means
anything — and the most likely adjustment is not an attacker, it is the owner
improving what the CFO said before showing it to someone.
"""

from __future__ import annotations

import dataclasses

import pytest

from services.api.crew.transcript import GENESIS, Transcript, canonical, sign


def build(n: int = 5) -> Transcript:
    t = Transcript(session_id="s1", key=b"test-key")
    for i in range(n):
        t.append(round_no=1, stage="Test", speaker=f"agent{i}", text=f"position {i}")
    return t


def test_a_clean_chain_verifies():
    assert build().verify() == []


def test_the_first_turn_chains_to_genesis():
    assert build(1).turns()[0].prev_sig == GENESIS


def test_editing_a_turn_breaks_that_turn_and_every_one_after_it():
    """The property a chain buys over independent signatures. An edit in the
    middle must not look like an isolated blemish."""
    t = build(5)
    turns = t.turns()
    turns[1] = dataclasses.replace(turns[1], text="a position the CFO never took")
    t.adopt(turns)

    broken = t.verify()
    assert broken == [x.turn_id for x in turns[1:]], (
        f"expected turns 1-4 broken, got {broken}. Independent signatures would "
        "have reported only turn 1."
    )


def test_deleting_a_turn_from_the_middle_is_detected():
    t = build(5)
    turns = t.turns()
    t.adopt(turns[:2] + turns[3:])
    assert t.verify(), "a removed turn leaves a gap the chain must notice"


def test_reordering_turns_is_detected():
    t = build(4)
    turns = t.turns()
    t.adopt([turns[0], turns[2], turns[1], turns[3]])
    assert t.verify()


def test_a_turn_forged_without_the_key_is_rejected():
    t = build(3)
    turns = t.turns()
    forged = dataclasses.replace(
        turns[-1],
        turn_id="s1:0003",
        text="and therefore the board approved option B",
        sig=sign({**turns[-1].payload(), "text": "forged"}, b"wrong-key"),
        prev_sig=turns[-1].sig,
    )
    t.adopt([*turns, forged])
    assert forged.turn_id in t.verify()


def test_appending_after_a_break_still_reports_the_break():
    """An attacker who edits an old turn and then continues the debate must not
    be able to re-establish a clean tail."""
    t = build(3)
    turns = t.turns()
    turns[0] = dataclasses.replace(turns[0], text="edited")
    t.adopt(turns)
    t.append(round_no=2, stage="Test", speaker="cfo", text="a later, honestly signed turn")
    assert len(t.verify()) >= 3


def test_citations_are_covered_by_the_signature():
    """A memo claim is only as good as the citation attached to it, so swapping
    a citation must break the seal exactly like swapping the text."""
    from services.api.rag.citations import Citation

    t = Transcript(session_id="s1", key=b"test-key")
    t.append(
        round_no=1,
        stage="Test",
        speaker="cfo",
        text="Payback is 26 months.",
        citations=(Citation("doc", 0, 10, "26 months"),),
    )
    turns = t.turns()
    turns[0] = dataclasses.replace(turns[0], citations=(Citation("doc", 0, 10, "8 months"),))
    t.adopt(turns)
    assert t.verify() == [turns[0].turn_id]


def test_canonicalisation_is_stable_across_equal_payloads():
    """If two serialisations of the same turn can differ, valid transcripts fail
    to verify intermittently and the failure looks like tampering."""
    a = {"b": 1, "a": "ünïcode", "c": [1, 2]}
    b = {"c": [1, 2], "a": "ünïcode", "b": 1}
    assert canonical(a) == canonical(b)
    assert "ünïcode".encode() in canonical(a), "non-ASCII must survive, not be escaped away"


@pytest.mark.parametrize("field", ["text", "speaker", "round_no", "stage", "created_at"])
def test_every_signed_field_is_actually_covered(field):
    t = build(2)
    turns = t.turns()
    original = getattr(turns[0], field)
    mutated = original + 1 if isinstance(original, int) else f"{original}-tampered"
    turns[0] = dataclasses.replace(turns[0], **{field: mutated})
    t.adopt(turns)
    assert turns[0].turn_id in t.verify(), f"{field} is not covered by the signature"
