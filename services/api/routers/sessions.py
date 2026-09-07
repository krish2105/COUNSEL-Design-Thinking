"""The boardroom, over HTTP.

Every round is streamed. A debate you watch is a different product from one that
hands you a finished transcript — and the Chair cannot interject into something
that has already happened, which is the whole reason the streaming shape was
built in Phase A rather than retrofitted here.

Frames, in order:
  round_open   who is about to speak
  speaking     a seat has finished, in completion order — for liveness only,
               unsigned, and explicitly not the record
  turn         the signed turn, in seating order — this IS the record
  flag         what the Auditor found
  done         round complete, with the chain's verification state
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import anyio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from services.api import deps
from services.api.core.rbac import Scope, require
from services.api.core.stream import event, sse
from services.api.crew import store
from services.api.crew.auditor import audit
from services.api.crew.facilitator import Facilitator
from services.api.crew.mandate import SEATING, load_mandates
from services.api.crew.session import STAGE_RULES, Stage
from services.api.crew.tools import granted
from services.api.crew.transcript import session_key

router = APIRouter(prefix="/sessions", tags=["sessions"])


class OpenSession(BaseModel):
    question: str = Field(min_length=10, max_length=500)
    stage: Stage = Stage.DEFINE


class Interjection(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class Advance(BaseModel):
    stage: Stage


def _facilitator() -> Facilitator:
    return Facilitator(deps.llm())


def _load_or_404(session_id: str):
    session = store.load_session(session_id, conn=deps.db())
    if session is None:
        raise HTTPException(404, f"no such session: {session_id}")
    return session


@router.post("", dependencies=[Depends(require(Scope.SESSION_WRITE))])
def open_session(body: OpenSession) -> dict[str, object]:
    conn = deps.db()
    session = _facilitator().open(
        uuid.uuid4().hex[:12], body.question, stage=body.stage, signing_key=session_key(conn)
    )
    store.save_session(session, conn=conn)
    store.save_turns(session.transcript.turns(), conn=conn, start_ordinal=0)
    return _describe(session)


@router.get("", dependencies=[Depends(require(Scope.READ))])
def list_sessions() -> list[dict[str, object]]:
    return store.list_sessions(conn=deps.db())


@router.get("/seats", dependencies=[Depends(require(Scope.READ))])
def seats() -> list[dict[str, object]]:
    """The room, with each seat's declared blind spots.

    Exposed because the blind spots are the point: a user must be able to read
    what each mandate admits it under-weights before deciding how much to trust
    what it just argued.
    """
    mandates = load_mandates()
    return [
        {
            "id": seat,
            "title": mandates[seat].title,
            "accountable_for": mandates[seat].accountable_for,
            "values": list(mandates[seat].values),
            "blind_spots": list(mandates[seat].blind_spots),
            "evidence_standards": list(mandates[seat].evidence_standards),
            "tools": sorted(granted(seat)),
        }
        for seat in SEATING
    ]


@router.get("/{session_id}", dependencies=[Depends(require(Scope.READ))])
def get_session(session_id: str) -> dict[str, object]:
    return _describe(_load_or_404(session_id))


@router.get("/{session_id}/transcript", dependencies=[Depends(require(Scope.READ))])
def transcript(session_id: str) -> dict[str, object]:
    session = _load_or_404(session_id)
    flags = store.flags_for(session_id, conn=deps.db())
    return {
        "session_id": session_id,
        "verified": session.transcript.verify() == [],
        "broken_turns": session.transcript.verify(),
        "turns": [
            {
                "turn_id": t.turn_id,
                "round_no": t.round_no,
                "stage": t.stage,
                "speaker": t.speaker,
                "text": t.text,
                "provider": t.provider,
                "model": t.model,
                "created_at": t.created_at,
                "sig": t.sig[:16],
                "flags": flags.get(t.turn_id, []),
            }
            for t in session.transcript.turns()
        ],
    }


@router.get("/{session_id}/chamber", dependencies=[Depends(require(Scope.READ))])
def chamber(session_id: str) -> dict[str, object]:
    """Everything the round table draws, derived from the signed transcript.

    Nothing here is stored. A chamber loaded from its own saved state could
    drift from the record it claims to show; this one has no state of its own.
    """
    from services.api.crew.chamber import chamber_state

    _load_or_404(session_id)
    return chamber_state(session_id, conn=deps.db())


@router.get("/{session_id}/verify", dependencies=[Depends(require(Scope.READ))])
def verify(session_id: str) -> dict[str, object]:
    """Re-read the stored rows and check the chain.

    Deliberately reads from the database rather than from memory: an edit made
    outside the application is exactly what this is for.
    """
    session = _load_or_404(session_id)
    broken = session.transcript.verify()
    return {
        "session_id": session_id,
        "intact": broken == [],
        "broken_turns": broken,
        "n_turns": len(session.transcript.turns()),
        "note": (
            "Tamper-evidence, not tamper-proofing: the signing key sits beside the data. "
            "This detects corruption and any edit made through or around the application."
        ),
    }


@router.post("/{session_id}/interject", dependencies=[Depends(require(Scope.SESSION_WRITE))])
def interject(session_id: str, body: Interjection) -> dict[str, object]:
    """The human, speaking as Chair. Recorded as a signed turn like any other."""
    session = _load_or_404(session_id)
    conn = deps.db()
    ordinal = store.turn_count(session_id, conn=conn)
    turn = _facilitator().interject(session, body.text)
    store.save_turns([turn], conn=conn, start_ordinal=ordinal)
    return {"turn_id": turn.turn_id, "speaker": turn.speaker, "text": turn.text}


@router.post("/{session_id}/stage", dependencies=[Depends(require(Scope.SESSION_WRITE))])
def advance(session_id: str, body: Advance) -> dict[str, object]:
    session = _load_or_404(session_id)
    conn = deps.db()
    ordinal = store.turn_count(session_id, conn=conn)
    _facilitator().advance(session, body.stage)
    store.save_turns(session.transcript.turns()[ordinal:], conn=conn, start_ordinal=ordinal)
    store.save_session(session, conn=conn)
    return _describe(session)


@router.post("/{session_id}/close", dependencies=[Depends(require(Scope.SESSION_WRITE))])
def close(session_id: str) -> dict[str, object]:
    session = _load_or_404(session_id)
    conn = deps.db()
    ordinal = store.turn_count(session_id, conn=conn)
    _facilitator().close(session)
    store.save_turns(session.transcript.turns()[ordinal:], conn=conn, start_ordinal=ordinal)
    store.save_session(session, conn=conn)
    return _describe(session)


@router.post("/{session_id}/rounds/stream", dependencies=[Depends(require(Scope.SESSION_WRITE))])
async def run_round_stream(session_id: str) -> EventSourceResponse:
    session = _load_or_404(session_id)
    if session.closed:
        raise HTTPException(409, "session is closed")

    conn = deps.db()
    facilitator = _facilitator()
    ordinal = store.turn_count(session_id, conn=conn)
    progress: list[tuple[str, str]] = []

    async def frames() -> AsyncIterator[dict[str, str]]:
        yield event(
            "round_open",
            {
                "round_no": session.round_no + 1,
                "speakers": list(SEATING),
                "stage": str(session.stage),
                "rules": list(session.rules),
            },
        )

        turns = await anyio.to_thread.run_sync(
            lambda: facilitator.run_round(
                session, on_progress=lambda seat, text: progress.append((seat, text))
            )
        )

        for seat, text in progress:
            yield event(
                "speaking",
                {
                    "seat": seat,
                    "text": text,
                    "signed": False,
                    "note": "liveness only; the signed turn follows",
                },
            )

        store.save_turns(turns, conn=conn, start_ordinal=ordinal)
        store.save_session(session, conn=conn)

        all_flags = []
        for turn in turns:
            yield event(
                "turn",
                {
                    "turn_id": turn.turn_id,
                    "round_no": turn.round_no,
                    "speaker": turn.speaker,
                    "text": turn.text,
                    "provider": turn.provider,
                    "model": turn.model,
                    "sig": turn.sig[:16],
                    "signed": True,
                },
            )
            flags = audit(turn, stage=str(session.stage))
            all_flags.extend(flags)
            for flag in flags:
                yield event(
                    "flag",
                    {
                        "turn_id": flag.turn_id,
                        "rule": flag.rule,
                        "severity": flag.severity,
                        "excerpt": flag.excerpt,
                        "why": flag.why,
                    },
                )
        store.save_flags(all_flags, conn=conn)

        yield event(
            "done",
            {
                "round_no": session.round_no,
                "n_turns": len(turns),
                "n_flags": len(all_flags),
                "chain_intact": session.transcript.verify() == [],
                "ended_early": session.ended_early,
            },
        )

    return sse(frames())


def _describe(session) -> dict[str, object]:
    return {
        "session_id": session.session_id,
        "question": session.question,
        "stage": str(session.stage),
        "rules": list(STAGE_RULES[session.stage]),
        "round_no": session.round_no,
        "closed": session.closed,
        "ended_early": session.ended_early,
        "n_turns": len(session.transcript.turns()),
        "chain_intact": session.transcript.verify() == [],
    }
