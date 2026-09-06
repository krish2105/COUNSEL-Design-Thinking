"""The full arc over HTTP: evidence in, scores, counterfactual, memo, outcome."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api import deps
from services.api.core import killswitch
from services.api.core.db import connect
from services.api.core.llm import LLMChain
from services.api.core.quota import Quota
from services.api.core.rbac import ROLE_HEADER
from services.api.crew.ledger import MIN_OUTCOMES
from services.api.crew.stubs import phase_c_stub

QUESTION = "Should RAQIB pilot in a Dubai hypermarket or a Greenlam plant first?"
OPTIONS = ["hypermarket", "plant"]
EVIDENCE = [
    {"evidence_id": "e1", "summary": "footfall estimate", "source": "estate report"},
    {"evidence_id": "e2", "summary": "payback model", "source": "treasury"},
    {"evidence_id": "e3", "summary": "plant capacity audit", "source": "operations"},
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "decisions.db"
    for cached in (deps.db, deps.quota, deps.llm, deps.search, deps.embedder, deps.user_links):
        cached.cache_clear()
    conn = connect(db_path)
    monkeypatch.setattr(deps, "db", lambda: conn)
    monkeypatch.setattr(deps, "llm", lambda: LLMChain([phase_c_stub()], Quota({"stub": 1_000_000})))
    killswitch.release()
    from services.api.main import app

    with TestClient(app) as c:
        yield c
    killswitch.release()
    for cached in (deps.quota, deps.search, deps.embedder, deps.user_links):
        cached.cache_clear()


def as_(role):
    return {ROLE_HEADER: role}


@pytest.fixture
def session(client):
    sid = client.post(
        "/sessions", json={"question": QUESTION, "stage": "Test"}, headers=as_("analyst")
    ).json()["session_id"]
    client.post(f"/sessions/{sid}/evidence", json=EVIDENCE, headers=as_("analyst"))
    return sid


def test_a_viewer_cannot_score_or_write_a_memo(client, session):
    assert (
        client.post(
            f"/sessions/{session}/scores", json={"options": OPTIONS}, headers=as_("viewer")
        ).status_code
        == 403
    )
    assert client.post(f"/sessions/{session}/memo", headers=as_("viewer")).status_code == 403


def test_the_room_scores_every_option_and_ranks_them(client, session):
    body = client.post(
        f"/sessions/{session}/scores", json={"options": OPTIONS}, headers=as_("analyst")
    ).json()
    assert {r["option"] for r in body["ranked"]} == set(OPTIONS)
    assert len(body["scores"]) == 5
    for seat_scores in body["scores"].values():
        assert all(s["depends_on"] for s in seat_scores)


def test_the_counterfactual_refuses_before_the_room_has_scored(client, session):
    r = client.get(f"/sessions/{session}/counterfactual", headers=as_("viewer"))
    assert r.status_code == 409
    assert "has not scored" in r.json()["detail"]


def test_the_counterfactual_always_states_that_it_is_not_a_re_run(client, session):
    """The difference a reader would otherwise assume the other way."""
    client.post(f"/sessions/{session}/scores", json={"options": OPTIONS}, headers=as_("analyst"))
    body = client.get(f"/sessions/{session}/counterfactual", headers=as_("viewer")).json()
    assert "not a re-run of the argument" in body["method"]
    assert body["verdict"]
    assert len(body["sensitivity"]) == 5


def test_the_memo_reports_how_much_of_it_is_actually_cited(client, session):
    client.post(f"/sessions/{session}/scores", json={"options": OPTIONS}, headers=as_("analyst"))
    body = client.post(f"/sessions/{session}/memo", headers=as_("analyst")).json()
    assert "# Decision memo" in body["markdown"]
    assert body["n_cited"] + body["n_uncited"] > 0
    assert "not financial, legal or professional" in body["markdown"]


def test_a_memo_written_with_no_documents_says_so(client, session):
    """No documents in the corpus means nothing CAN be cited, however well the
    room argued. That is different from having no evidence ids — this session
    has three — and the memo must say the right one on its face."""
    client.post(f"/sessions/{session}/scores", json={"options": OPTIONS}, headers=as_("analyst"))
    body = client.post(f"/sessions/{session}/memo", headers=as_("analyst")).json()
    assert body["n_cited"] == 0, "no documents were uploaded, so nothing can be cited"
    assert "no documents in the room" in body["markdown"]
    assert "Asserted without evidence" in body["markdown"]


def test_the_ledger_refuses_to_score_a_seat_below_the_minimum(client, session):
    client.post(f"/sessions/{session}/scores", json={"options": OPTIONS}, headers=as_("analyst"))
    client.post(
        f"/sessions/{session}/outcome",
        json={"chosen": "plant", "actual": "plant", "notes": "ran in Q2"},
        headers=as_("analyst"),
    )
    body = client.get("/ledger", headers=as_("viewer")).json()

    assert body["minimum_outcomes"] == MIN_OUTCOMES
    assert body["scored"] == [], "one outcome is not a calibration record"
    assert len(body["pending"]) == 5
    assert all(p["needs"] == MIN_OUTCOMES - 1 for p in body["pending"])
    assert len(body["outcomes"]) == 1


def test_framings_must_be_questions(client, session):
    body = client.post(f"/sessions/{session}/framings", headers=as_("analyst")).json()
    assert len(body["framings"]) == 5
    assert all(f["hmw"].lower().startswith("how might we") for f in body["framings"].values())


def test_ideas_are_collected_without_critique(client, session):
    body = client.post(f"/sessions/{session}/ideas", headers=as_("analyst")).json()
    assert len(body["ideas"]) == 5
    assert all(len(i["sketch"]) >= 20 for i in body["ideas"].values())


def test_an_unknown_session_is_a_404(client):
    assert client.post("/sessions/nope/framings", headers=as_("analyst")).status_code == 404
