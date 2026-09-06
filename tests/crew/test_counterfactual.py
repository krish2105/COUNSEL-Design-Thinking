"""What would change our mind, as arithmetic.

The memo has promised this sentence since Phase A. These tests are what make it
executable rather than rhetorical — and they pin the honest cases as hard as the
dramatic ones, because a decision nothing can flip is a real answer and
manufacturing a flip by lowering the bar would be worse than saying nothing.
"""

from __future__ import annotations

import pytest

from services.api.core.schemas import Score
from services.api.crew.counterfactual import flips, robustness, sensitivity
from services.api.crew.stages import Evidence

E1 = Evidence("e1", "footfall estimate", "estate report")
E2 = Evidence("e2", "payback model", "treasury")
E3 = Evidence("e3", "plant capacity audit", "operations")
ALL = [E1, E2, E3]


def s(option, each, *, depends, conf=0.6):
    return Score(
        option=option,
        desirability=each,
        feasibility=each,
        viability=each,
        weakest_on="desirability",
        confidence=conf,
        depends_on=list(depends),
        reason="r" * 20,
    )


def test_a_decision_resting_on_one_item_names_exactly_that_item():
    """The dramatic case, and the one the memo promises."""
    scores = {
        # The plant lead comes entirely from one seat leaning on e3.
        "coo": [s("plant", 5, depends=["e3"])],
        "cfo": [s("hypermarket", 4, depends=["e1"])],
    }
    found = flips(scores, ALL)
    assert [f.evidence_id for f in found] == ["e3"]
    assert found[0].winner_before == "plant"
    assert found[0].winner_after == "hypermarket"
    assert found[0].seats_affected == ("coo",)


def test_a_robust_decision_reports_no_flips_rather_than_inventing_one():
    """The most useful output is often the empty one."""
    scores = {
        "cfo": [s("plant", 5, depends=["e1"]), s("hypermarket", 1, depends=["e1"])],
        "cmo": [s("plant", 5, depends=["e2"]), s("hypermarket", 1, depends=["e2"])],
        "coo": [s("plant", 5, depends=["e3"]), s("hypermarket", 1, depends=["e3"])],
    }
    assert flips(scores, ALL) == []
    verdict = robustness(scores, ALL)
    assert verdict.n_flips == 0
    assert "does not hang on any one source" in verdict.verdict


def test_removing_evidence_nothing_depends_on_changes_nothing():
    scores = {"cfo": [s("plant", 4, depends=["e1"]), s("hypermarket", 2, depends=["e1"])]}
    assert flips(scores, [E2, E3]) == []


def test_several_independent_flips_are_all_reported():
    scores = {
        "cfo": [s("plant", 5, depends=["e1"])],
        "cmo": [s("plant", 5, depends=["e2"])],
        "coo": [s("hypermarket", 5, depends=["e3"]), s("hypermarket", 4, depends=["e3"])],
    }
    found = flips(scores, ALL)
    assert len(found) >= 2
    verdict = robustness(scores, ALL)
    assert "not robust" in verdict.verdict


def test_the_analysis_is_deterministic():
    scores = {
        "coo": [s("plant", 5, depends=["e3"])],
        "cfo": [s("hypermarket", 4, depends=["e1"])],
    }
    assert flips(scores, ALL) == flips(scores, ALL)
    assert flips(scores, list(reversed(ALL))) == flips(scores, ALL)


def test_a_room_with_no_evidence_says_so_instead_of_claiming_robustness():
    """The trap this avoids: zero flips because nothing was cited would
    otherwise render as 'no single source changes the outcome', which reads as
    strength and is the opposite."""
    scores = {"cfo": [s("plant", 4, depends=["e1"])]}
    verdict = robustness(scores, [])
    assert verdict.n_flips == 0
    assert "rests entirely on the mandates' judgement" in verdict.verdict
    assert "does not hang on any one source" not in verdict.verdict


def test_nothing_scored_is_reported_as_no_decision():
    assert robustness({}, ALL).verdict.startswith("Nothing was scored")


def test_a_score_cannot_be_built_without_naming_what_it_rests_on():
    """The schema guard from C1, asserted from the consumer's side.

    Measured in C1: given three evidence ids and citing all three in its own
    prose, a real model still returned depends_on: []. A score that rests on
    nothing is invisible to this analysis, which UNDERSTATES fragility.
    """
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="at least 1 item"):
        s("plant", 4, depends=[])


def test_sensitivity_reports_which_evidence_each_seat_leaned_on():
    scores = {
        "cfo": [s("plant", 4, depends=["e1", "e2"])],
        "coo": [s("plant", 4, depends=["e3"])],
    }
    by_seat = {r.seat: r for r in sensitivity(scores)}
    assert by_seat["cfo"].depends_on == ("e1", "e2")
    assert by_seat["coo"].depends_on == ("e3",)
    assert all(r.grounded_share == 1.0 for r in by_seat.values())


def test_a_seat_that_scored_nothing_is_marked_ungrounded():
    result = {r.seat: r for r in sensitivity({"cfo": [s("plant", 4, depends=["e1"])], "devil": []})}
    assert result["cfo"].grounded_share == 1.0
    assert result["cfo"].depends_on == ("e1",)
    assert result["devil"].ungrounded is True
    assert result["devil"].grounded_share == 0.0


def test_flips_are_ordered_so_the_closest_call_comes_first():
    scores = {
        "cfo": [s("plant", 5, depends=["e1"])],
        "cmo": [s("plant", 3, depends=["e2"])],
        "coo": [s("hypermarket", 5, depends=["e3"])],
    }
    found = flips(scores, ALL)
    assert found == sorted(found, key=lambda f: (f.margin_after, f.evidence_id))
