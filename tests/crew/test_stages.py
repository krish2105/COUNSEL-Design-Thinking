"""The stages, and the one property the decision rests on: determinism.

Generation is model-driven. Everything after it is not. Five seats score
concurrently and arrive in whatever order they finish, so if the winner
depended on that order the decision would not be a decision.
"""

from __future__ import annotations

import random

import pytest

from services.api.core.llm import LLMChain
from services.api.core.quota import Quota
from services.api.core.schemas import Score
from services.api.crew.facilitator import Facilitator
from services.api.crew.mandate import SEATING
from services.api.crew.session import Stage
from services.api.crew.stages import (
    Evidence,
    aggregate,
    collect_framings,
    collect_ideas,
    collect_scores,
    margin,
    winner,
)
from services.api.crew.stubs import phase_c_stub

QUESTION = "Should RAQIB pilot in a Dubai hypermarket or a Greenlam plant first?"
OPTIONS = ["hypermarket", "plant"]
EVIDENCE = [
    Evidence("e1", "footfall estimate", "estate report"),
    Evidence("e2", "payback model", "treasury"),
    Evidence("e3", "plant capacity audit", "operations"),
]


@pytest.fixture
def chain():
    return LLMChain([phase_c_stub()], Quota({"stub": 100_000}))


@pytest.fixture
def session(chain):
    return Facilitator(chain).open("s-stage", QUESTION, stage=Stage.TEST)


def score(option, d, f, v, conf=0.5, seat_reason="r" * 20, depends=("e1",)):
    axes = {"desirability": d, "feasibility": f, "viability": v}
    weakest = min(axes, key=lambda a: (axes[a], a))
    return Score(
        option=option,
        desirability=d,
        feasibility=f,
        viability=v,
        weakest_on=weakest,
        confidence=conf,
        depends_on=list(depends),
        reason=seat_reason,
    )


def test_every_seat_produces_a_framing(session, chain):
    framings = collect_framings(session, chain=chain)
    assert list(framings) == list(SEATING)
    assert all(f.hmw.lower().startswith("how might we") for f in framings.values())


def test_every_seat_produces_an_idea(session, chain):
    ideas = collect_ideas(session, chain=chain)
    assert list(ideas) == list(SEATING)
    assert all(len(i.sketch) >= 20 for i in ideas.values())


def test_every_seat_scores_every_option_and_names_its_dependencies(session, chain):
    scores = collect_scores(session, OPTIONS, EVIDENCE, chain=chain)
    assert set(scores) == set(SEATING)
    for seat_scores in scores.values():
        assert [s.option for s in seat_scores] == OPTIONS
        for s in seat_scores:
            assert s.depends_on, "a score resting on nothing cannot enter the sensitivity analysis"
            assert 0.0 <= s.confidence <= 1.0


def test_aggregation_is_independent_of_the_order_seats_finish_in():
    """The property the whole decision rests on."""
    base = {
        "cfo": [score("plant", 4, 5, 4), score("hypermarket", 3, 2, 3)],
        "cmo": [score("plant", 2, 4, 3), score("hypermarket", 5, 3, 4)],
        "coo": [score("plant", 5, 5, 4), score("hypermarket", 2, 2, 3)],
        "ethics": [score("plant", 3, 4, 4), score("hypermarket", 3, 3, 3)],
        "devil": [score("plant", 3, 3, 3), score("hypermarket", 4, 3, 3)],
    }
    reference = aggregate(base)
    rng = random.Random(7)
    for _ in range(10):
        seats = list(base)
        rng.shuffle(seats)
        shuffled = {seat: list(reversed(base[seat])) for seat in seats}
        assert aggregate(shuffled) == reference


def test_a_tie_breaks_on_the_option_name_not_on_iteration_order():
    tied = {
        "cfo": [score("alpha", 3, 3, 3), score("beta", 3, 3, 3)],
        "cmo": [score("beta", 3, 3, 3), score("alpha", 3, 3, 3)],
    }
    ranked = aggregate(tied)
    assert ranked[0].total == ranked[1].total
    assert ranked[0].option == "alpha", "a tie must resolve the same way every run"


def test_the_winner_is_the_highest_total():
    scores = {
        "cfo": [score("plant", 5, 5, 5), score("hypermarket", 1, 1, 1)],
        "cmo": [score("plant", 4, 4, 4), score("hypermarket", 2, 2, 2)],
    }
    top = winner(scores)
    assert top and top.option == "plant"
    assert top.total == 27
    assert top.supporters == ("cfo", "cmo")
    assert margin(scores) == 27 - 9


def test_a_split_room_shows_a_small_margin():
    scores = {
        "cfo": [score("plant", 5, 5, 5), score("hypermarket", 1, 1, 1)],
        "cmo": [score("plant", 1, 1, 1), score("hypermarket", 5, 5, 5)],
    }
    assert margin(scores) == 0.0, "a room split down the middle has no lead"


def test_aggregation_of_nothing_is_nothing():
    assert aggregate({}) == []
    assert winner({}) is None
    assert margin({}) == 0.0


def test_per_seat_totals_are_reported_so_a_reader_can_see_who_carried_it():
    scores = {"cfo": [score("plant", 5, 5, 5)], "cmo": [score("plant", 1, 1, 1)]}
    [result] = aggregate(scores)
    assert result.per_seat == {"cfo": 15, "cmo": 3}


def test_a_score_cannot_misreport_its_own_weakest_axis():
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="lowest axis"):
        Score(
            option="plant",
            desirability=5,
            feasibility=1,
            viability=4,
            weakest_on="viability",
            confidence=0.5,
            depends_on=["e1"],
            reason="r" * 20,
        )
