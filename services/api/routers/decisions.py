"""The stages, the memo, the counterfactual and the ledger, over HTTP.

Nothing here acts on the world. The heaviest thing any of these endpoints does
is write a row to a local SQLite file, and the memo is returned as text for a
person to read — COUNSEL never sends it anywhere. Exporting is something the
user does, with the file, after reading it.
"""

from __future__ import annotations

import asyncio
import queue

import anyio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from services.api import deps
from services.api.core.rbac import Scope, require
from services.api.core.schemas import Score
from services.api.core.stream import event, sse
from services.api.crew import ledger as ledger_mod
from services.api.crew import store
from services.api.crew.counterfactual import flips, robustness, sensitivity
from services.api.crew.mandate import SEATING
from services.api.crew.memo import attach_dissents, build_memo, render_markdown
from services.api.crew.session import STAGE_RULES, Stage
from services.api.crew.stages import (
    Evidence,
    aggregate,
    collect_dissents,
    collect_framings,
    collect_ideas,
    collect_scores,
)

router = APIRouter(prefix="/sessions/{session_id}", tags=["decisions"])


class Progressive:
    """A blocking five-seat fan-out, iterated as it reports rather than after it finishes.

    Every fan-out here takes an `on_progress` callback that fires on the pool's
    worker threads, while the generator feeding the client runs on the event
    loop. This carries items across that boundary on a plain queue.Queue, which
    is the thread-safe primitive already in the standard library.

    WHY THIS EXISTS RATHER THAN A LIST
    ----------------------------------
    The obvious version collects into a list and emits it once the blocking call
    returns. Measured, that produced:

        0.04s  stage_open
        28.20s framing coo, cmo, cfo, ethics, devil
        28.20s done

    which fixes the timeout — a proxy only needs the first byte — while not
    actually streaming anything. With this:

        0.02s  stage_open
        4.74s  framing coo
        9.38s  framing cmo
        12.96s framing cfo
        16.97s framing devil
        23.08s framing ethics, done

    The seats finish nearly twenty seconds apart, which the batched version hid
    completely. Three endpoints claimed in their docstrings to show the room
    thinking; none of them did until this existed.

    `result` is the collector's own return value, read after iteration ends. It
    is in SEATING order, so what gets stored never depends on who was quickest —
    only what gets displayed does.
    """

    #: How often the loop looks for a finished seat. Short enough that a turn
    #: appears promptly, long enough that a mostly-idle wait is not a spin.
    POLL_SECONDS = 0.05

    def __init__(self, run) -> None:
        self._run = run
        self.result = None

    async def __aiter__(self):
        pending: queue.Queue = queue.Queue()
        finished = object()

        def work():
            try:
                return self._run(lambda *args: pending.put(args))
            finally:
                # In a finally, so a raising fan-out still releases the loop
                # below instead of hanging the request until the client gives up.
                pending.put(finished)

        task = asyncio.ensure_future(anyio.to_thread.run_sync(work))
        while True:
            try:
                item = pending.get_nowait()
            except queue.Empty:
                await anyio.sleep(self.POLL_SECONDS)
                continue
            if item is finished:
                break
            yield item

        # Awaited after the queue is drained, so a failure surfaces here with
        # every seat that did succeed already delivered.
        self.result = await task


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


def _stage_stream(
    session_id: str,
    *,
    stage: Stage,
    kind: str,
    collect,
    label: str,
) -> EventSourceResponse:
    """The streaming half of a one-shot stage: Define and Ideate.

    Both are the same five-seat fan-out as scoring and the memo, and measured on
    qwen3:8b they take 21.7s and 19.4s. That is under the 30-second ceiling every
    gateway between a browser and this process imposes — but only just, and the
    margin is the model's speed, not a property of the design. A larger model or
    a slower host puts them over it, and the failure mode is the one the memo
    already demonstrated: a 500 at exactly 30s from a proxy, while the endpoint
    itself completes fine and says so in the logs.

    Written once rather than twice because the two differ only in stage, artefact
    kind and collector. Two copies of a streaming generator would drift, and the
    thing that drifts first is which one remembers to save its artefacts.
    """
    session = _session(session_id)
    session.stage = stage
    conn = deps.db()

    async def frames():
        yield event("stage_open", {"stage": label, "kind": kind, "n_seats": len(SEATING)})

        fan = Progressive(lambda progress: collect(session, chain=deps.llm(), on_progress=progress))
        async for seat, obj in fan:
            # Arrival order, which is the honest order for a live view.
            yield event(kind, {"seat": seat, **obj.model_dump()})
        result = fan.result

        store.save_artefacts(session_id, kind, result, conn=conn)
        yield event(
            "done",
            {
                "stage": label,
                f"{kind}s": {k: v.model_dump() for k, v in result.items()},
            },
        )

    return sse(frames())


@router.post("/framings/stream", dependencies=[Depends(require(Scope.SESSION_WRITE))])
async def framings_stream(session_id: str) -> EventSourceResponse:
    return _stage_stream(
        session_id,
        stage=Stage.DEFINE,
        kind="framing",
        collect=collect_framings,
        label="Define",
    )


@router.post("/ideas/stream", dependencies=[Depends(require(Scope.SESSION_WRITE))])
async def ideas_stream(session_id: str) -> EventSourceResponse:
    return _stage_stream(
        session_id,
        stage=Stage.IDEATE,
        kind="idea",
        collect=collect_ideas,
        label="Ideate",
    )


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


@router.get("/artefacts", dependencies=[Depends(require(Scope.READ))])
def artefacts(session_id: str) -> dict[str, object]:
    """Everything the room has produced, by stage.

    Read-only and keyed by kind, so the Board and Stages tabs render what
    actually happened rather than re-running anything to find out.
    """
    _session(session_id)
    conn = deps.db()
    return {
        "session_id": session_id,
        "artefacts": {
            kind: store.load_artefacts(session_id, kind, conn=conn)
            for kind in ("framing", "idea", "score", "dissent")
        },
        "evidence": [e.__dict__ for e in store.load_evidence(session_id, conn=conn)],
        "stage_rules": {str(stage): list(rules) for stage, rules in STAGE_RULES.items()},
    }


@router.post("/scores/stream", dependencies=[Depends(require(Scope.SESSION_WRITE))])
async def scores_stream(session_id: str, body: ScoreRequest) -> EventSourceResponse:
    """Scoring, streamed.

    Five seats across two options is roughly ninety seconds of model time, and a
    ninety-second synchronous response dies at every gateway between the browser
    and this process — measured: the Next.js dev rewrite returns 500 at exactly
    30 seconds while the API completes in 103. Streaming keeps the connection
    alive AND gives the person watching something to look at, which is the
    reason to prefer it over raising a timeout somewhere.

    The second half of that was untrue until Progressive existed: this collected
    every score and emitted them together at the end. See its docstring.
    """
    session = _session(session_id)
    session.stage = Stage.TEST
    conn = deps.db()
    evidence = store.load_evidence(session_id, conn=conn)

    async def frames():
        yield event(
            "scoring_open",
            {"options": body.options, "n_seats": 5, "evidence": [e.evidence_id for e in evidence]},
        )

        fan = Progressive(
            lambda progress: collect_scores(
                session, body.options, evidence, chain=deps.llm(), on_progress=progress
            )
        )
        async for option, seat, score in fan:
            yield event("scored", {"option": option, "seat": seat, **score.model_dump()})
        result = fan.result

        store.save_artefacts(session_id, "score", result, conn=conn)
        for seat, seat_scores in result.items():
            for score in seat_scores:
                ledger_mod.record_prediction(
                    session_id, seat, score.option, score.confidence, conn=conn
                )

        ranked = aggregate(result)
        yield event("ranked", {"ranked": [r.__dict__ for r in ranked]})
        yield event("done", {"n_scores": sum(len(v) for v in result.values())})

    return sse(frames())


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

    return _memo_payload(built)


def _memo_payload(built) -> dict[str, object]:
    return {
        "markdown": render_markdown(built),
        "recommendation": built.recommendation,
        "n_cited": len(built.context) + len(built.reasoning),
        "n_uncited": len(built.uncited),
        "ungrounded": built.ungrounded,
        "unanimous_dissent": built.unanimous_dissent,
        "dissents": [d.__dict__ for d in built.dissents],
        "margin": built.margin,
        "refused_provenance": [
            {"claim": claim, "patterns": patterns} for claim, patterns in built.refused_provenance
        ],
    }


@router.post("/memo/stream", dependencies=[Depends(require(Scope.SESSION_WRITE))])
async def memo_stream(session_id: str) -> EventSourceResponse:
    """The memo, streamed. Same reason as scores/stream, found the same way.

    Assembling a memo is two model phases — drafting the memo against the
    corpus, then asking all five seats whether they dissent — and measured on
    qwen3:8b it takes about 41 seconds. The synchronous POST /memo above
    completes in 40.5s directly and returns **500 at exactly 30.08s** through
    the Next.js rewrite, so the Report tab's one button was broken in a browser
    while the endpoint it calls was fine. That is the same 30-second gateway
    ceiling that scores/stream exists for; the memo path simply had not been
    driven through a browser on a session slow enough to cross it.

    Streaming also makes the wait legible: the recommendation appears as soon as
    it is drafted, and each seat's dissent lands as that seat answers — which
    became true only once Progressive replaced the collect-then-emit version.
    """
    session = _session(session_id)
    session.stage = Stage.DECIDE
    conn = deps.db()
    scores = _stored_scores(session_id)
    evidence = store.load_evidence(session_id, conn=conn)
    options = {score.option for seat_scores in scores.values() for score in seat_scores}

    async def frames():
        yield event("memo_open", {"n_evidence": len(evidence), "n_options": len(options)})

        built = await anyio.to_thread.run_sync(
            lambda: build_memo(
                session, chain=deps.llm(), conn=conn, scores=scores, evidence=evidence
            )
        )
        yield event(
            "drafted",
            {
                "recommendation": built.recommendation,
                "margin": built.margin,
                "n_cited": len(built.context) + len(built.reasoning),
                "n_uncited": len(built.uncited),
                "ungrounded": built.ungrounded,
            },
        )

        fan = Progressive(
            lambda progress: collect_dissents(
                session, built.recommendation, chain=deps.llm(), on_progress=progress
            )
        )
        async for seat, draft in fan:
            yield event("dissent", {"seat": seat, "agrees": draft.agrees})
        dissents = fan.result

        attach_dissents(built, dissents)
        store.save_artefacts(session_id, "dissent", dissents, conn=conn)
        yield event("done", _memo_payload(built))

    return sse(frames())


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
