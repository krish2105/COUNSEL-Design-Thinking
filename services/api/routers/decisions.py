"""The stages, the memo, the counterfactual and the ledger, over HTTP.

Nothing here acts on the world. The heaviest thing any of these endpoints does
is write a row to a local SQLite file, and the memo is returned as text for a
person to read — COUNSEL never sends it anywhere. Exporting is something the
user does, with the file, after reading it.
"""

from __future__ import annotations

import anyio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from services.api import deps
from services.api.core.rbac import Scope, require
from services.api.core.schemas import Score
from services.api.core.stream import event
from services.api.crew import ledger as ledger_mod
from services.api.crew import store
from services.api.crew.counterfactual import flips, robustness, sensitivity
from services.api.crew.memo import attach_dissents, build_memo, render_markdown
from services.api.crew.session import Stage
from services.api.crew.stages import (
    Evidence,
    aggregate,
    collect_dissents,
    collect_framings,
    collect_ideas,
    collect_scores,
)

router = APIRouter(prefix="/sessions/{session_id}", tags=["decisions"])


class EvidenceIn(BaseModel):
    evidence_id: str = Field(min_length=1, max_length=32)
    summary: str = Field(min_length=3, max_length=240)
    source: str = Field(min_length=1, max_length=240)


class ScoreRequest(BaseModel):
    options: list[str] = Field(min_length=2, max_length=6)


class OutcomeIn(BaseModel):
    chosen: str = Field(min_length=1, max_length=160)
    actual: str = Field(min_length=1, max_length=160)
    notes: str = Field(default="", max_length=2000)


def _session(session_id: str):
    session = store.load_session(session_id, conn=deps.db())
    if session is None:
        raise HTTPException(404, f"no such session: {session_id}")
    return session


@router.post("/evidence", dependencies=[Depends(require(Scope.SESSION_WRITE))])
def add_evidence(session_id: str, items: list[EvidenceIn]) -> list[dict[str, object]]:
    _session(session_id)
    evidence = [Evidence(i.evidence_id, i.summary, i.source) for i in items]
    store.save_evidence(session_id, evidence, conn=deps.db())
    return [e.__dict__ for e in store.load_evidence(session_id, conn=deps.db())]


@router.post("/framings", dependencies=[Depends(require(Scope.SESSION_WRITE))])
def framings(session_id: str) -> dict[str, object]:
    session = _session(session_id)
    session.stage = Stage.DEFINE
    result = collect_framings(session, chain=deps.llm())
    store.save_artefacts(session_id, "framing", result, conn=deps.db())
    return {"stage": "Define", "framings": {k: v.model_dump() for k, v in result.items()}}


@router.post("/ideas", dependencies=[Depends(require(Scope.SESSION_WRITE))])
def ideas(session_id: str) -> dict[str, object]:
    session = _session(session_id)
    session.stage = Stage.IDEATE
    result = collect_ideas(session, chain=deps.llm())
    store.save_artefacts(session_id, "idea", result, conn=deps.db())
    return {"stage": "Ideate", "ideas": {k: v.model_dump() for k, v in result.items()}}


@router.post("/scores", dependencies=[Depends(require(Scope.SESSION_WRITE))])
def scores(session_id: str, body: ScoreRequest) -> dict[str, object]:
    session = _session(session_id)
    session.stage = Stage.TEST
    conn = deps.db()
    evidence = store.load_evidence(session_id, conn=conn)
    result = collect_scores(session, body.options, evidence, chain=deps.llm())
    store.save_artefacts(session_id, "score", result, conn=conn)

    # Each seat's strongest call is its prediction, recorded now so the ledger
    # can score it later against what actually happened.
    for seat, seat_scores in result.items():
        for score in seat_scores:
            ledger_mod.record_prediction(
                session_id, seat, score.option, score.confidence, conn=conn
            )

    ranked = aggregate(result)
    return {
        "stage": "Test",
        "ranked": [r.__dict__ for r in ranked],
        "scores": {k: [s.model_dump() for s in v] for k, v in result.items()},
    }


def _stored_scores(session_id: str) -> dict[str, list[Score]]:
    payload = store.load_artefacts(session_id, "score", conn=deps.db())
    if not payload:
        raise HTTPException(409, "the room has not scored the options yet — run /scores first")
    return {seat: [Score(**s) for s in items] for seat, items in payload.items()}


@router.post("/scores/stream", dependencies=[Depends(require(Scope.SESSION_WRITE))])
async def scores_stream(session_id: str, body: ScoreRequest) -> EventSourceResponse:
    """Scoring, streamed.

    Five seats across two options is roughly ninety seconds of model time, and a
    ninety-second synchronous response dies at every gateway between the browser
    and this process — measured: the Next.js dev rewrite returns 500 at exactly
    30 seconds while the API completes in 103. Streaming keeps the connection
    alive AND gives the person watching something to look at, which is the
    reason to prefer it over raising a timeout somewhere.
    """
    session = _session(session_id)
    session.stage = Stage.TEST
    conn = deps.db()
    evidence = store.load_evidence(session_id, conn=conn)
    seen: list[tuple[str, str, Score]] = []

    async def frames():
        yield event(
            "scoring_open",
            {"options": body.options, "n_seats": 5, "evidence": [e.evidence_id for e in evidence]},
        )

        result = await anyio.to_thread.run_sync(
            lambda: collect_scores(
                session,
                body.options,
                evidence,
                chain=deps.llm(),
                on_progress=lambda option, seat, score: seen.append((option, seat, score)),
            )
        )

        for option, seat, score in seen:
            yield event("scored", {"option": option, "seat": seat, **score.model_dump()})

        store.save_artefacts(session_id, "score", result, conn=conn)
        for seat, seat_scores in result.items():
            for score in seat_scores:
                ledger_mod.record_prediction(
                    session_id, seat, score.option, score.confidence, conn=conn
                )

        ranked = aggregate(result)
        yield event("ranked", {"ranked": [r.__dict__ for r in ranked]})
        yield event("done", {"n_scores": sum(len(v) for v in result.values())})

    return EventSourceResponse(frames())


@router.get("/counterfactual", dependencies=[Depends(require(Scope.READ))])
def counterfactual(session_id: str) -> dict[str, object]:
    """Which single piece of evidence would flip this."""
    _session(session_id)
    scores = _stored_scores(session_id)
    evidence = store.load_evidence(session_id, conn=deps.db())
    verdict = robustness(scores, evidence)
    return {
        "verdict": verdict.verdict,
        "winner": verdict.winner,
        "margin": verdict.margin,
        "flips": [f.__dict__ for f in flips(scores, evidence)],
        "sensitivity": [s.__dict__ for s in sensitivity(scores)],
        "method": (
            "Sensitivity analysis over recorded positions, not a re-run of the argument. "
            "Removing evidence sets aside the scores that cited it; the room is not asked "
            "to reconsider without it, and a real re-debate could land elsewhere."
        ),
    }


@router.post("/memo", dependencies=[Depends(require(Scope.SESSION_WRITE))])
def memo(session_id: str) -> dict[str, object]:
    session = _session(session_id)
    session.stage = Stage.DECIDE
    conn = deps.db()
    scores = _stored_scores(session_id)
    evidence = store.load_evidence(session_id, conn=conn)

    built = build_memo(session, chain=deps.llm(), conn=conn, scores=scores, evidence=evidence)
    dissents = collect_dissents(session, built.recommendation, chain=deps.llm())
    attach_dissents(built, dissents)
    store.save_artefacts(session_id, "dissent", dissents, conn=conn)

    return {
        "markdown": render_markdown(built),
        "recommendation": built.recommendation,
        "n_cited": len(built.context) + len(built.reasoning),
        "n_uncited": len(built.uncited),
        "ungrounded": built.ungrounded,
        "unanimous_dissent": built.unanimous_dissent,
        "dissents": [d.__dict__ for d in built.dissents],
        "margin": built.margin,
    }


@router.post("/outcome", dependencies=[Depends(require(Scope.SESSION_WRITE))])
def outcome(session_id: str, body: OutcomeIn) -> dict[str, object]:
    """The Learn stage. What actually happened, months later."""
    _session(session_id)
    ledger_mod.record_outcome(
        session_id, chosen=body.chosen, actual=body.actual, notes=body.notes, conn=deps.db()
    )
    return {"session_id": session_id, "recorded": True}


ledger_router = APIRouter(prefix="/ledger", tags=["ledger"])


@ledger_router.get("", dependencies=[Depends(require(Scope.READ))])
def calibration() -> dict[str, object]:
    conn = deps.db()
    scored, pending = ledger_mod.calibration(conn=conn)
    return {
        "minimum_outcomes": ledger_mod.MIN_OUTCOMES,
        "coin_flip_baseline": ledger_mod.COIN_FLIP,
        "scored": [b.__dict__ for b in scored],
        "pending": [p.__dict__ for p in pending],
        "outcomes": ledger_mod.ledger(conn=conn),
        "note": (
            f"A Brier score below {ledger_mod.MIN_OUTCOMES} outcomes is noise. Seats under "
            "that threshold are listed as pending with no score rather than shown at zero."
        ),
    }
