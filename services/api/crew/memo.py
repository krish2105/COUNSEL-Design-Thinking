"""The decision memo, and the gate every sentence in it has to pass.

WHAT THIS GUARANTEES
--------------------
Every factual sentence in the memo BODY resolves to a verbatim span of a
document the room actually holds. Not "the model was asked to cite" — the quote
is read back out of the database and compared.

WHAT IT DOES WITH WHAT FAILS
----------------------------
Not silence. A claim the room made but could not support is moved to an
`uncited` section and labelled, rather than dropped. Two reasons: dropping it
would let the memo imply the room was better evidenced than it was, and the
things a room asserts without evidence are exactly what a pre-mortem is for.

Phase B measured why this has to be mechanical: given no documents, all five
mandates invented sources fluently, and an explicit instruction not to did not
stop them (docs/results/B7-prompting-does-not-stop-fabrication.json). A mandate
told to cite will cite. Only a check that opens the citation knows.

THE SHAPE
---------
An Amazon-style one-pager: what we decided, why, who disagreed, what we think
could go wrong, and what would change our minds. The dissent log is not an
appendix — a decision memo without recorded disagreement is a memo that lost
information on the way to consensus.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from sqlite3 import Connection

from services.api.core.llm import LLMChain
from services.api.core.schemas import DissentDraft, MemoDraft
from services.api.crew.mandate import SEATING, load_mandates
from services.api.crew.session import Session
from services.api.crew.stages import Evidence, OptionResult, aggregate, margin
from services.api.rag.citations import Citation, UncitedClaim, require_citations
from services.api.rag.retrieve import retrieve


@dataclass(frozen=True)
class Claim:
    text: str
    citations: tuple[Citation, ...]


@dataclass(frozen=True)
class Dissent:
    seat: str
    title: str
    position: str
    would_change_my_mind: str


@dataclass
class Memo:
    session_id: str
    question: str
    recommendation: str
    ranked: list[OptionResult]
    margin: float
    context: list[Claim] = field(default_factory=list)
    reasoning: list[Claim] = field(default_factory=list)
    dissents: list[Dissent] = field(default_factory=list)
    premortem: list[str] = field(default_factory=list)
    would_change_our_mind: list[str] = field(default_factory=list)
    #: What the room asserted and could not support. Kept, labelled, and never
    #: presented as a finding.
    uncited: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    generated_at: str = ""
    #: True when the room reached this decision with no documents at all, which
    #: is a fact about the decision and belongs on its face.
    evidence_free: bool = False


def ground(text: str, *, conn: Connection, limit: int = 3) -> list[Citation]:
    """Find spans that actually support a claim.

    Retrieval-then-verify, deliberately in that order. Asking the model for a
    citation and checking it afterwards fails in the way Phase B measured; here
    the candidate spans come from the corpus, and only a verbatim overlap
    survives.
    """
    hits = retrieve(text, conn=conn, limit=limit).hits
    citations = []
    for hit in hits:
        # The claim must share a substantial phrase with the span, not merely
        # rank near it. Ranking near a span is what retrieval does for anything.
        overlap = _longest_shared_phrase(text, hit.chunk.text)
        if len(overlap) >= 24:
            citations.append(
                Citation(
                    doc_id=hit.chunk.doc_id,
                    start=hit.chunk.start,
                    end=hit.chunk.end,
                    quote=overlap,
                )
            )
    return citations


def _longest_shared_phrase(a: str, b: str, *, minimum: int = 24) -> str:
    """Longest run of words the two strings share.

    Word-level rather than character-level: a shared character run can cross a
    word boundary and produce a 'quote' that is not language.
    """
    aw, bw = a.split(), b.split()
    best = ""
    for i in range(len(aw)):
        for j in range(i + 1, len(aw) + 1):
            phrase = " ".join(aw[i:j])
            if len(phrase) <= len(best):
                continue
            if phrase in " ".join(bw):
                best = phrase
    return best if len(best) >= minimum else ""


def build_memo(
    session: Session,
    *,
    chain: LLMChain,
    conn: Connection,
    scores,
    evidence: list[Evidence],
) -> Memo:
    ranked = aggregate(scores)

    draft, _ = chain.structured(
        f"task: memo\n"
        f"You are the Facilitator writing the room's decision memo.\n"
        f"The decision: {session.question}\n"
        f"The room's ranking: {[(r.option, r.total) for r in ranked]}\n"
        "Write an Amazon-style one-pager. Every sentence in context and reasoning must be a "
        "single factual claim that could be checked against a document. Do not invent sources.",
        [_transcript_message(session)],
        model_cls=MemoDraft,
        max_tokens=900,
    )

    memo = Memo(
        session_id=session.session_id,
        question=session.question,
        recommendation=draft.recommendation,
        ranked=ranked,
        margin=margin(scores),
        premortem=list(draft.premortem),
        would_change_our_mind=list(draft.would_change_our_mind),
        evidence=list(evidence),
        generated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        evidence_free=not evidence,
    )

    for bucket, sentences in (("context", draft.context), ("reasoning", draft.reasoning)):
        for sentence in sentences:
            citations = ground(sentence, conn=conn)
            try:
                require_citations(sentence, citations, conn=conn)
            except UncitedClaim:
                memo.uncited.append(sentence)
                continue
            getattr(memo, bucket).append(Claim(text=sentence, citations=tuple(citations)))

    return memo


def attach_dissents(memo: Memo, drafts: dict[str, DissentDraft]) -> Memo:
    mandates = load_mandates()
    memo.dissents = [
        Dissent(
            seat=seat,
            title=mandates[seat].title,
            position=drafts[seat].position,
            would_change_my_mind=drafts[seat].would_change_my_mind,
        )
        for seat in SEATING
        if seat in drafts and not drafts[seat].agrees
    ]
    return memo


def _transcript_message(session: Session):
    from services.api.core.llm import Message

    lines = [
        f"[{t.speaker.upper()}] {t.text}"
        for t in session.transcript.turns()
        if t.speaker in SEATING or t.speaker == "chair"
    ]
    return Message("user", "\n\n".join(lines) or "The room has not spoken.")


def render_markdown(memo: Memo) -> str:
    """The memo as a document. Every body claim carries its span."""
    out = [
        "# Decision memo",
        "",
        f"**{memo.question}**",
        "",
        "## Recommendation",
        "",
        memo.recommendation,
        "",
    ]

    if memo.evidence_free:
        out += [
            "> **This decision was reached with no documents in the room.** Nothing below is "
            "grounded in a source the room holds, which is why the body is empty and every "
            "claim the room made appears under *Asserted without evidence*.",
            "",
        ]

    if memo.ranked:
        out += [
            "## How the room scored it",
            "",
            "| Option | Total | Mean confidence | Seats |",
            "|---|---:|---:|---|",
        ]
        out += [
            f"| {r.option} | {r.total} | {r.mean_confidence:.2f} | {', '.join(r.supporters)} |"
            for r in memo.ranked
        ]
        out += ["", f"Margin over the runner-up: **{memo.margin:.0f}**.", ""]

    for title, claims in (("Context", memo.context), ("Reasoning", memo.reasoning)):
        if not claims:
            continue
        out += [f"## {title}", ""]
        for claim in claims:
            spans = ", ".join(f"`{c.doc_id[:8]}[{c.start}:{c.end}]`" for c in claim.citations)
            out += [f"- {claim.text} — {spans}"]
        out += [""]

    if memo.dissents:
        out += ["## Dissent log", ""]
        for d in memo.dissents:
            out += [
                f"**{d.title}** dissents.",
                "",
                f"> {d.position}",
                "",
                f"*Would change their mind:* {d.would_change_my_mind}",
                "",
            ]

    if memo.premortem:
        out += [
            "## Pre-mortem",
            "",
            "*It is a year from now and this went badly. What happened?*",
            "",
        ]
        out += [f"- {p}" for p in memo.premortem] + [""]

    if memo.would_change_our_mind:
        out += ["## What would change our mind", ""]
        out += [f"- {w}" for w in memo.would_change_our_mind] + [""]

    if memo.uncited:
        out += [
            "## Asserted without evidence",
            "",
            "The room stated these and no document it holds supports them. They are recorded "
            "rather than removed: dropping them would make this memo look better evidenced "
            "than the decision actually was.",
            "",
        ]
        out += [f"- {u}" for u in memo.uncited] + [""]

    out += [
        "---",
        "",
        f"Session `{memo.session_id}` · generated {memo.generated_at} · "
        f"{len(memo.context) + len(memo.reasoning)} cited claims, {len(memo.uncited)} uncited.",
        "",
        "*COUNSEL is a decision-support tool. It is not financial, legal or professional "
        "advice, and the agents' expertise is prompt-defined.*",
    ]
    return "\n".join(out)
