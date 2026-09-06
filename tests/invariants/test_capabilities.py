"""LLM06 / LLM08 — excessive agency, prevented structurally.

COUNSEL promises that a boardroom of agents can argue without any of them being
able to act. Prompting cannot keep that promise: "do not post anything" is a
request, and an injected instruction is a competing request. These tests assert
the promise is kept by there being nothing to call.
"""

from __future__ import annotations

import pytest

from services.api.crew.mandate import SEATING
from services.api.crew.tools import (
    GRANTS,
    REGISTRY,
    CapabilityError,
    catalogue,
    granted,
    invoke,
)


def test_no_registered_tool_has_side_effects():
    """The whole promise, in one assertion over the whole registry."""
    offenders = [name for name, tool in REGISTRY.items() if tool.side_effects]
    assert offenders == [], (
        f"tools with side effects were registered: {offenders}. COUNSEL's claim is "
        "that no agent can act on the outside world; adding one is a design change."
    )


def test_no_tool_name_suggests_an_outward_action():
    forbidden = {"post", "publish", "send", "email", "deploy", "write", "delete", "execute", "buy"}
    offenders = {n for n in REGISTRY for f in forbidden if f in n.lower()}
    assert offenders == set(), offenders


def test_every_grant_names_a_tool_that_exists():
    """A grant for a tool that does not exist is a silent hole: it looks like a
    capability and fails only when something reaches for it."""
    for agent, tools in GRANTS.items():
        missing = tools - set(REGISTRY)
        assert missing == set(), f"{agent} is granted non-existent tools: {missing}"


def test_every_registered_tool_is_granted_to_someone():
    """An ungranted tool is dead code in a security-relevant registry."""
    reachable = set().union(*GRANTS.values())
    assert set(REGISTRY) - reachable == set()


@pytest.mark.parametrize("mandate", SEATING)
def test_a_debating_mandate_holds_research_tools_and_nothing_else(mandate):
    assert granted(mandate) == frozenset({"search", "ask"})


@pytest.mark.parametrize("mandate", SEATING)
def test_a_debating_mandate_cannot_control_the_room(mandate):
    """A room where any seat can close the round is a room where the loudest
    seat decides when the argument is over."""
    for control in ("start_round", "close_round"):
        with pytest.raises(CapabilityError, match="not granted"):
            invoke(mandate, control, session_id="s", round_no=1)


def test_the_auditor_cannot_research_and_the_facilitator_cannot_flag():
    with pytest.raises(CapabilityError):
        invoke("auditor", "search", query="anything")
    with pytest.raises(CapabilityError):
        invoke("facilitator", "flag", turn_id="t", rule="r", why="w")


def test_an_unknown_tool_is_refused_before_any_grant_is_consulted():
    with pytest.raises(CapabilityError, match="no such tool"):
        invoke("cfo", "publish_memo", anything="goes")


def test_an_unknown_agent_holds_nothing():
    assert granted("shadow_cfo") == frozenset()
    with pytest.raises(CapabilityError):
        invoke("shadow_cfo", "search", query="x")


def test_the_facilitator_can_actually_run_a_round():
    assert invoke("facilitator", "start_round", session_id="s", round_no=1)["opened"] is True
    assert invoke("facilitator", "close_round", session_id="s", round_no=1)["closed"] is True


def test_a_catalogue_only_shows_what_the_agent_holds():
    names = {t["name"] for t in catalogue("cfo")}
    assert names == {"ask", "search"}
    assert all(t["side_effects"] is False for t in catalogue("cfo"))
