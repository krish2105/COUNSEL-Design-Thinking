"""The full arc over HTTP: evidence in, scores, counterfactual, memo, outcome."""

from __future__ import annotations

import json

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


def sse(response) -> list[tuple[str, dict]]:
    """Parse an SSE body into (event, data) pairs.

    TestClient buffers the whole stream, which is fine here: what is being
    checked is the FRAME SEQUENCE, not the timing. The timing is the part a
    test cannot assert — see test_every_slow_write_has_a_streaming_sibling.
    """
    frames, name = [], None
    for line in response.text.splitlines():
        if line.startswith("event: "):
            name = line[7:].strip()
        elif line.startswith("data: ") and name:
            frames.append((name, json.loads(line[6:])))
            name = None
    return frames


def test_the_memo_streams_its_two_phases_and_ends_with_the_whole_memo(client, session):
    """The Report tab's one button, over the wire.

    POST /memo takes ~41s against a real model and returned 500 at exactly 30s
    through the Next rewrite, so the button was broken in a browser while the
    endpoint it called was healthy. The stream is the fix; this pins its shape.
    """
    client.post(f"/sessions/{session}/scores", json={"options": OPTIONS}, headers=as_("analyst"))
    r = client.post(f"/sessions/{session}/memo/stream", headers=as_("analyst"))
    assert r.status_code == 200

    frames = sse(r)
    kinds = [name for name, _ in frames]
    assert kinds[0] == "memo_open", kinds
    assert kinds[-1] == "done", kinds
    assert "drafted" in kinds

    # A recommendation must be readable BEFORE the dissents are collected —
    # that is the whole point of splitting the phases rather than streaming
    # one frame at the end.
    drafted = next(data for name, data in frames if name == "drafted")
    assert drafted["recommendation"]
    assert kinds.index("drafted") < kinds.index("done")

    # Every seat is asked, and the terminal frame carries the same payload the
    # synchronous route returns, so the two cannot drift.
    dissent_frames = [data for name, data in frames if name == "dissent"]
    assert len(dissent_frames) == 5
    done = frames[-1][1]
    assert "# Decision memo" in done["markdown"]
    assert done["recommendation"] == drafted["recommendation"]

    # The dissent LOG holds dissenters, not attendees: a seat that agrees is
    # not a dissent. So the memo's list must match exactly the seats whose
    # streamed frame said they did not agree.
    disagreed = {d["seat"] for d in dissent_frames if not d["agrees"]}
    assert {d["seat"] for d in done["dissents"]} == disagreed
    assert done["unanimous_dissent"] == (len(disagreed) == 5)


def test_a_viewer_cannot_stream_a_memo_either(client, session):
    """The stream is a second door to the same room, so it needs the same lock."""
    r = client.post(f"/sessions/{session}/memo/stream", headers=as_("viewer"))
    assert r.status_code == 403


def test_every_slow_write_has_a_streaming_sibling():
    """The invariant that would have caught this without a browser.

    Any endpoint that fans a request out to all five seats, or runs more than
    one model phase, will eventually exceed the 30-second ceiling that every
    proxy between a browser and this process imposes. Measured twice now:
    scoring at 103s and the memo at 41s, both returning 500 at exactly 30s
    through the Next rewrite while completing fine when called directly.

    So a slow endpoint without a /stream sibling is a button that works in
    curl and not in the product. Adding one here without its stream fails.
    """
    from services.api.main import app

    # The OpenAPI schema, not app.routes. This FastAPI version wraps included
    # routers in _IncludedRouter objects that carry no .path, so enumerating
    # app.routes yields only /docs and /openapi.json — the first version of
    # this test did exactly that, matched nothing, and passed cleanly against a
    # deliberately deleted stream. A test that cannot fail is worse than none.
    paths = set(app.openapi()["paths"])

    slow = {
        "/sessions/{session_id}/scores",  # five seats x two options, ~103s measured
        "/sessions/{session_id}/memo",  # draft + five dissents, ~41s measured
    }
    # /framings and /ideas are the same five-seat fan-out shape and are NOT in
    # that set, because measured on qwen3:8b they are 21.7s and 19.4s — under
    # the ceiling, but not by much. A slower host or a larger model puts them
    # over it, and the failure would look exactly like the memo's did. Recorded
    # here rather than left as an assumption someone has to rediscover.
    # Asserted to EXIST before being checked, so renaming one cannot quietly
    # turn this back into a tautology.
    assert slow <= paths, f"these endpoints moved; update this list: {sorted(slow - paths)}"

    missing = {p for p in slow if f"{p}/stream" not in paths}
    assert not missing, (
        f"these run multi-seat model work with no streaming sibling: {sorted(missing)}. "
        "A synchronous response longer than 30s returns 500 through the Next rewrite, "
        "so the button that calls it is broken in a browser while curl says it is fine."
    )
