"""Authorisation, and the one thing that must work when nothing else does.

The RBAC tests are ordinary. The kill switch test is not: it asserts that once
the switch is engaged, the chain refuses BEFORE it consults availability, quota
or the network. A switch you have to route a request through in order to trip
is not a switch.
"""

from __future__ import annotations

import pytest

from services.api.core import killswitch
from services.api.core.llm import LLMChain, Message, StubProvider
from services.api.core.quota import Quota
from services.api.core.rbac import ROLE_SCOPES, Role, Scope, current_role, scopes_for


@pytest.fixture(autouse=True)
def _released():
    killswitch.release()
    yield
    killswitch.release()


def test_viewer_cannot_write():
    assert Scope.SESSION_WRITE not in scopes_for(Role.VIEWER)
    assert Scope.ADMIN_WRITE not in scopes_for(Role.VIEWER)


def test_analyst_can_run_sessions_but_not_pull_the_cord():
    assert Scope.SESSION_WRITE in scopes_for(Role.ANALYST)
    assert Scope.ADMIN_WRITE not in scopes_for(Role.ANALYST)


def test_admin_holds_every_scope():
    assert scopes_for(Role.ADMIN) == frozenset(Scope)


def test_scopes_are_monotone_up_the_roles():
    assert ROLE_SCOPES[Role.VIEWER] < ROLE_SCOPES[Role.ANALYST] < ROLE_SCOPES[Role.ADMIN]


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("admin", Role.ADMIN),
        ("ANALYST", Role.ANALYST),
        ("  viewer  ", Role.VIEWER),
        ("superuser", Role.VIEWER),
        ("", Role.VIEWER),
        (None, Role.VIEWER),
    ],
)
def test_an_unrecognised_role_falls_to_least_privilege(header, expected):
    assert current_role(header) is expected


def test_kill_switch_refuses_before_any_provider_is_consulted():
    class Tripwire(StubProvider):
        def __init__(self):
            super().__init__(name="tripwire", model="m")
            self.availability_checks = 0

        def available(self):
            self.availability_checks += 1
            return True

    tripwire = Tripwire()
    chain = LLMChain([tripwire, StubProvider()], Quota({"tripwire": 10, "stub": 10}))

    killswitch.engage("owner pulled the cord mid-debate")
    with pytest.raises(killswitch.KillSwitchEngaged, match="mid-debate"):
        chain.complete("s", [Message("user", "continue the debate")])

    assert tripwire.availability_checks == 0, (
        "the switch must refuse before availability is even checked"
    )


def test_releasing_the_switch_restores_service():
    chain = LLMChain([StubProvider()], Quota({"stub": 10}))
    killswitch.engage("test")
    killswitch.release()
    assert chain.complete("s", [Message("user", "x")]).provider == "stub"
