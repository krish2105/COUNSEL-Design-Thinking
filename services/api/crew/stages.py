"""Each stage, and what the room hands back from it.

THE SPLIT THAT MATTERS
----------------------
Generation is model-driven; assembly is not. The model proposes a framing,
sketches an idea, scores an option. Everything after that — collecting, ranking,
choosing a winner — is ordinary deterministic Python, so the same five scores
always produce the same decision and a replay is a replay.

This is why `aggregate` sorts on an explicit total-then-name key rather than
relying on dict order: five seats scoring concurrently arrive in whatever order
they finish, and a decision that depends on that is not a decision.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from services.api.core.llm import LLMChain, Message
from services.api.core.schemas import DissentDraft, Framing, Idea, Score
from services.api.crew.mandate import SEATING, load_mandates, system_prompt
from services.api.crew.session import Session, Stage

MAX_ARTEFACT_TOKENS = 700


@dataclass(frozen=True)
class Evidence:
    """One thing the room is allowed to lean on.

    Ids are what `Score.depends_on` refers to, and what the counterfactual
    removes one at a time.
    """

    evidence_id: str
    summary: str
    source: str
    #: True when this came from an uploaded document or a search result — which
    #: is to say, from outside. Kept so the memo can say where a decision's
    #: weight actually sits.
    external: bool = True


@dataclass(frozen=True)
class OptionResult:
    option: str
    total: int
    mean_confidence: float
    supporters: tuple[str, ...]
    per_seat: dict[str, int]


def _ask(chain: LLMChain, seat: str, session: Session, task: str, instruction: str, model_cls):
    mandate = load_mandates()[seat]
    system = f"task: {task}:{seat}\n" + system_prompt(
        mandate,
        stage=str(session.stage),
        rules=session.rules,
        question=session.question,
    )
    obj, response = chain.structured(
        system,
        [Message("user", instruction)],
        model_cls=model_cls,
        max_tokens=MAX_ARTEFACT_TOKENS,
        speaker=seat,
    )
    return seat, obj, response


def _fan_out(chain, session, task, instruction, model_cls, speakers=SEATING, on_progress=None):
    """Ask every seat at once, then return in seating order.

    Same reasoning as a debate round: the seats are answering the same question
    from the same state, so concurrency is not a shortcut, and fixed ordering on
    the way out keeps the result reproducible.
    """
    by_seat = {}
    with ThreadPoolExecutor(max_workers=len(speakers)) as pool:
        futures = {
            pool.submit(_ask, chain, seat, session, task, instruction, model_cls): seat
            for seat in speakers
        }
        for future in as_completed(futures):
            seat, obj, _ = future.result()
            by_seat[seat] = obj
            if on_progress is not None:
                on_progress(seat, obj)
    return {seat: by_seat[seat] for seat in speakers if seat in by_seat}


def collect_framings(session: Session, *, chain: LLMChain) -> dict[str, Framing]:
    """Define — each seat proposes the problem it thinks is worth solving."""
    return _fan_out(
        chain,
        session,
        "framing",
        "Propose ONE 'How might we...' framing of this decision from your mandate's point of "
        "view. Keep why_it_matters under 60 words. Do not propose a solution.",
        Framing,
    )


def collect_ideas(session: Session, *, chain: LLMChain) -> dict[str, Idea]:
    """Ideate — divergence, under the no-critique rule the Auditor enforces."""
    return _fan_out(
        chain,
        session,
        "idea",
        "Propose ONE idea. Do not critique anyone. If you are building on another seat's "
        "idea, name that seat in builds_on. Keep the sketch under 80 words.",
        Idea,
    )


def collect_scores(
    session: Session,
    options: list[str],
    evidence: list[Evidence],
    *,
    chain: LLMChain,
    on_progress=None,
) -> dict[str, list[Score]]:
    """Test — every seat scores every option on all three axes.

    `on_progress(option, seat, score)` fires as each seat finishes. Not a
    nicety: five seats scoring two options takes about ninety seconds, and a
    ninety-second synchronous HTTP response dies at every gateway between the
    browser and the process. Measured: the Next.js dev rewrite returns 500 at
    exactly 30 seconds while the API happily completes in 103.
    """
    catalogue = "; ".join(f"{e.evidence_id} ({e.summary})" for e in evidence) or "none supplied"
    scores: dict[str, list[Score]] = {seat: [] for seat in SEATING}
    for option in options:
        got = _fan_out(
            chain,
            session,
            "score",
            f"Score the option: {option}. Score desirability, feasibility and viability from 1 "
            "to 5, name the axis you are weakest on, and give a confidence between 0 and 1. "
            f"depends_on MUST list the evidence ids you relied on, from: {catalogue}. "
            "Keep the reason under 80 words.",
            Score,
            # `option` is bound as a default: a bare closure captures it by
            # reference, so every callback in the loop would report the LAST
            # option scored rather than its own.
            on_progress=(
                (lambda seat, obj, _option=option: on_progress(_option, seat, obj))
                if on_progress
                else None
            ),
        )
        for seat, score in got.items():
            # The model is asked for the option and sometimes restyles it; the
            # canonical string is the one the room is deciding between.
            scores[seat].append(score.model_copy(update={"option": option}))
    return scores


def collect_dissents(
    session: Session,
    recommendation: str,
    *,
    chain: LLMChain,
    on_progress: Callable[[str, DissentDraft], None] | None = None,
) -> dict[str, DissentDraft]:
    """Decide — who does not agree, and what it would take to move them.

    `on_progress(seat, draft)` fires as each seat answers, in completion order,
    so a caller streaming to a browser can show dissent arriving rather than
    holding the connection silent. The returned mapping is still in seating
    order, because the record must not depend on who finished first.
    """
    return _fan_out(
        chain,
        session,
        "dissent",
        f"The room is converging on: {recommendation}. State whether you agree, your position "
        "in under 80 words, and specifically what evidence would change your mind.",
        DissentDraft,
        on_progress=on_progress,
    )


def aggregate(scores: dict[str, list[Score]]) -> list[OptionResult]:
    """Rank the options. Deterministic and order-independent.

    Ties break on the option name, not on iteration order — five seats scoring
    concurrently arrive in whatever sequence they finish, and a decision that
    depends on that is not a decision.
    """
    by_option: dict[str, list[tuple[str, Score]]] = {}
    for seat, seat_scores in scores.items():
        for score in seat_scores:
            by_option.setdefault(score.option, []).append((seat, score))

    results = [
        OptionResult(
            option=option,
            total=sum(s.total for _, s in entries),
            mean_confidence=round(sum(s.confidence for _, s in entries) / len(entries), 4),
            supporters=tuple(sorted(seat for seat, _ in entries)),
            per_seat={seat: s.total for seat, s in entries},
        )
        for option, entries in by_option.items()
    ]
    return sorted(results, key=lambda r: (-r.total, -r.mean_confidence, r.option))


def winner(scores: dict[str, list[Score]]) -> OptionResult | None:
    ranked = aggregate(scores)
    return ranked[0] if ranked else None


def margin(scores: dict[str, list[Score]]) -> float:
    """How far ahead the leader is. Zero when the room is split."""
    ranked = aggregate(scores)
    if len(ranked) < 2:
        return float(ranked[0].total) if ranked else 0.0
    return float(ranked[0].total - ranked[1].total)


#: The stage a given artefact belongs to, so the UI and the memo can say where
#: something came from rather than presenting it as timeless.
ARTEFACT_STAGE = {
    "framing": Stage.DEFINE,
    "idea": Stage.IDEATE,
    "score": Stage.TEST,
    "dissent": Stage.DECIDE,
}
