"""The boardroom over HTTP, driven end to end on the deterministic stub."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from services.api import deps
from services.api.core import killswitch
from services.api.core.db import connect
from services.api.core.llm import LLMChain, StubProvider
from services.api.core.quota import Quota
from services.api.core.rbac import ROLE_HEADER

QUESTION = "Should we pilot in a Dubai hypermarket or a Greenlam plant first?"


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "sessions.db"
    for cached in (deps.db, deps.quota, deps.llm, deps.search, deps.embedder, deps.user_links):
        cached.cache_clear()
    monkeypatch.setattr(deps, "db", lambda: connect(db_path))
    # The suite must exercise the RUNTIME, not the model. Without this the tests
    # reach the developer's local Ollama and a 13-test file takes three minutes
    # to assert things that have nothing to do with inference — and it would
    # then behave differently in CI, where no model exists.
    monkeypatch.setattr(deps, "llm", lambda: LLMChain([StubProvider()], Quota({"stub": 10_000})))
    killswitch.release()
    from services.api.main import app

    with TestClient(app) as c:
        yield c
    killswitch.release()
    # deps.llm is monkeypatched to a plain lambda here, so it has no cache to
    # clear; monkeypatch restores the real lru_cache-wrapped function itself.
    for cached in (deps.quota, deps.search, deps.embedder, deps.user_links):
        cached.cache_clear()


def as_(role):
    return {ROLE_HEADER: role}


def open_session(client, stage="Test"):
    r = client.post(
        "/sessions", json={"question": QUESTION, "stage": stage}, headers=as_("analyst")
    )
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


def sse(client, session_id):
    with client.stream(
        "POST", f"/sessions/{session_id}/rounds/stream", headers=as_("analyst")
    ) as r:
        assert r.status_code == 200
        body = "".join(r.iter_text())
    frames = []
    name = None
    for line in body.splitlines():
        if line.startswith("event: "):
            name = line[7:].strip()
        elif line.startswith("data: ") and name:
            frames.append((name, json.loads(line[6:])))
    return frames


def test_a_viewer_cannot_open_a_session(client):
    r = client.post("/sessions", json={"question": QUESTION}, headers=as_("viewer"))
    assert r.status_code == 403


def test_opening_a_session_records_the_question_and_the_rules(client):
    r = client.post(
        "/sessions", json={"question": QUESTION, "stage": "Ideate"}, headers=as_("analyst")
    )
    body = r.json()
    assert body["stage"] == "Ideate"
    assert any("No critique" in rule for rule in body["rules"])
    assert body["chain_intact"] is True
    assert body["n_turns"] == 1, "the facilitator's opening turn is part of the record"


def test_a_streamed_round_emits_a_signed_turn_for_every_seat(client):
    sid = open_session(client)
    frames = sse(client, sid)
    kinds = [name for name, _ in frames]

    assert kinds[0] == "round_open"
    assert kinds[-1] == "done"
    turns = [d for n, d in frames if n == "turn"]
    assert len(turns) == 5
    assert all(t["signed"] is True for t in turns)
    assert [t["speaker"] for t in turns] == ["cfo", "cmo", "coo", "ethics", "devil"]


def test_liveness_frames_are_marked_as_not_the_record(client):
    """A viewer sees a seat's words as it finishes, in completion order. Those
    frames are explicitly unsigned so nothing downstream mistakes them for the
    transcript."""
    sid = open_session(client)
    frames = sse(client, sid)
    speaking = [d for n, d in frames if n == "speaking"]
    assert len(speaking) == 5
    assert all(s["signed"] is False for s in speaking)


def test_the_round_reports_its_own_chain_state(client):
    sid = open_session(client)
    done = [d for n, d in sse(client, sid) if n == "done"][0]
    assert done["chain_intact"] is True
    assert done["n_turns"] == 5


def test_the_transcript_survives_a_round_trip_through_the_database(client):
    sid = open_session(client)
    sse(client, sid)
    body = client.get(f"/sessions/{sid}/transcript", headers=as_("viewer")).json()
    assert body["verified"] is True
    assert len(body["turns"]) == 6  # opening + five seats
    assert body["turns"][0]["speaker"] == "facilitator"


def test_verify_reads_the_stored_rows_and_catches_a_tampered_turn(client):
    """The check that matters. An edit made outside the application — straight
    into the database — is exactly what tamper-evidence is for."""
    sid = open_session(client)
    sse(client, sid)
    assert client.get(f"/sessions/{sid}/verify", headers=as_("viewer")).json()["intact"] is True

    conn = deps.db()
    conn.execute(
        "UPDATE turns SET text = ? WHERE session_id = ? AND ordinal = 2",
        ("A position the CFO never took.", sid),
    )
    conn.commit()

    after = client.get(f"/sessions/{sid}/verify", headers=as_("viewer")).json()
    assert after["intact"] is False
    assert len(after["broken_turns"]) >= 4, "the edit must break every turn after it too"


def test_the_chair_can_interject_and_it_joins_the_chain(client):
    sid = open_session(client)
    sse(client, sid)
    r = client.post(
        f"/sessions/{sid}/interject",
        json={"text": "Assume the plant loses a shift in Q1. Re-argue."},
        headers=as_("analyst"),
    )
    assert r.status_code == 200 and r.json()["speaker"] == "chair"
    assert client.get(f"/sessions/{sid}/verify", headers=as_("viewer")).json()["intact"] is True


def test_a_viewer_cannot_interject(client):
    sid = open_session(client)
    r = client.post(f"/sessions/{sid}/interject", json={"text": "x"}, headers=as_("viewer"))
    assert r.status_code == 403


def test_advancing_the_stage_changes_the_rules_in_force(client):
    sid = open_session(client, stage="Ideate")
    r = client.post(f"/sessions/{sid}/stage", json={"stage": "Test"}, headers=as_("analyst"))
    assert any("Critique is expected" in rule for rule in r.json()["rules"])


def test_a_closed_session_refuses_another_round(client):
    sid = open_session(client)
    client.post(f"/sessions/{sid}/close", headers=as_("analyst"))
    with client.stream("POST", f"/sessions/{sid}/rounds/stream", headers=as_("analyst")) as r:
        assert r.status_code == 409


def test_the_seats_endpoint_publishes_the_blind_spots(client):
    """The blind spots are the point: a reader must be able to see what a
    mandate admits it under-weights before weighing what it argued."""
    seats = client.get("/sessions/seats", headers=as_("viewer")).json()
    assert [s["id"] for s in seats] == ["cfo", "cmo", "coo", "ethics", "devil"]
    for seat in seats:
        assert len(seat["blind_spots"]) >= 2
        assert set(seat["tools"]) == {"ask", "search"}, "no seat may hold a control tool"


def test_an_unknown_session_is_a_404(client):
    assert client.get("/sessions/nope", headers=as_("viewer")).status_code == 404
