"""The memo, and the one thing it must never do.

Phase B measured all five mandates inventing sources fluently, and an explicit
instruction not to did not stop them. So the guarantee here is not that the
model behaved — it is that a claim whose quote does not resolve cannot reach the
body, whatever the model did.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.api.core.db import connect
from services.api.core.llm import LLMChain
from services.api.core.quota import Quota
from services.api.core.schemas import DissentDraft, Score
from services.api.crew.facilitator import Facilitator
from services.api.crew.memo import (
    Memo,
    _longest_shared_phrase,
    attach_dissents,
    build_memo,
    ground,
    render_markdown,
)
from services.api.crew.session import Stage
from services.api.crew.stages import Evidence
from services.api.crew.stubs import phase_c_stub
from services.api.rag.citations import Citation
from services.api.rag.ingest import ingest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/docs"
QUESTION = "Should RAQIB pilot in a Dubai hypermarket or a Greenlam plant first?"
EVIDENCE = [Evidence("e1", "board paper", "board-paper.pdf")]


@pytest.fixture
def chain():
    return LLMChain([phase_c_stub()], Quota({"stub": 100_000}))


@pytest.fixture
def conn():
    c = connect(":memory:")
    ingest(FIXTURES / "board-paper.pdf", conn=c)
    yield c
    c.close()


@pytest.fixture
def session(chain):
    return Facilitator(chain).open("s-memo", QUESTION, stage=Stage.DECIDE)


def score(option, total_each=4):
    return Score(
        option=option,
        desirability=total_each,
        feasibility=total_each,
        viability=total_each,
        weakest_on="desirability",
        confidence=0.6,
        depends_on=["e1"],
        reason="r" * 20,
    )


SCORES = {
    "cfo": [score("plant", 5), score("hypermarket", 2)],
    "cmo": [score("plant", 3), score("hypermarket", 4)],
}


def test_a_claim_whose_quote_does_not_resolve_never_reaches_the_body(session, chain, conn):
    """The guarantee. Not 'the model was asked to cite' — the quote is read back
    out of the database and compared."""
    memo = build_memo(session, chain=chain, conn=conn, scores=SCORES, evidence=EVIDENCE)

    for claim in memo.context + memo.reasoning:
        assert claim.citations, "a body claim with no citation is exactly what must not happen"
        for citation in claim.citations:
            stored = conn.execute(
                "SELECT text FROM documents WHERE doc_id = ?", (citation.doc_id,)
            ).fetchone()["text"]
            assert citation.quote in stored[citation.start : citation.end]


def test_what_fails_the_gate_is_recorded_not_dropped(session, chain, conn):
    """Dropping it would make the memo look better evidenced than the decision
    was, and what a room asserts without evidence is what a pre-mortem is for."""
    memo = build_memo(session, chain=chain, conn=conn, scores=SCORES, evidence=EVIDENCE)
    total_sentences = len(memo.context) + len(memo.reasoning) + len(memo.uncited)
    assert total_sentences > 0
    assert memo.uncited, "the stub memo asserts things the fixture cannot support"
    rendered = render_markdown(memo)
    assert "Asserted without evidence" in rendered
    for sentence in memo.uncited:
        assert sentence in rendered


def test_a_forged_quote_cannot_be_smuggled_into_the_body(conn):
    """Constructed directly, bypassing the model, to prove the gate is the
    thing doing the work."""
    from services.api.rag.citations import UncitedClaim, require_citations

    doc_id = conn.execute("SELECT doc_id FROM documents").fetchone()["doc_id"]
    with pytest.raises(UncitedClaim):
        require_citations(
            "The board approved the hypermarket.",
            [Citation(doc_id, 0, 60, "The board approved the hypermarket")],
            conn=conn,
        )


def test_a_room_with_no_documents_says_so_on_the_face_of_the_memo(session, chain):
    empty = connect(":memory:")
    try:
        memo = build_memo(session, chain=chain, conn=empty, scores=SCORES, evidence=[])
        assert memo.ungrounded is True
        assert memo.context == [] and memo.reasoning == []
        rendered = render_markdown(memo)
        assert "no documents in the room" in rendered
        assert "Asserted without evidence" in rendered
    finally:
        empty.close()


def test_the_ranking_and_margin_appear_in_the_memo(session, chain, conn):
    memo = build_memo(session, chain=chain, conn=conn, scores=SCORES, evidence=EVIDENCE)
    assert memo.ranked[0].option == "plant"
    assert memo.margin == 6.0
    rendered = render_markdown(memo)
    assert "How the room scored it" in rendered and "plant" in rendered


def test_dissent_records_the_seat_and_what_would_move_it(session, chain, conn):
    memo = build_memo(session, chain=chain, conn=conn, scores=SCORES, evidence=EVIDENCE)
    drafts = {
        "cfo": DissentDraft(agrees=False, position="p" * 20, would_change_my_mind="w" * 20),
        "cmo": DissentDraft(agrees=True, position="p" * 20, would_change_my_mind="w" * 20),
    }
    attach_dissents(memo, drafts)
    assert [d.seat for d in memo.dissents] == ["cfo"], "only disagreement is a dissent"
    assert memo.dissents[0].title == "Chief Financial Officer"
    assert "Dissent log" in render_markdown(memo)


def test_a_unanimous_room_has_no_dissent_section(session, chain, conn):
    memo = build_memo(session, chain=chain, conn=conn, scores=SCORES, evidence=EVIDENCE)
    attach_dissents(
        memo,
        {
            s: DissentDraft(agrees=True, position="p" * 20, would_change_my_mind="w" * 20)
            for s in ("cfo", "cmo")
        },
    )
    assert memo.dissents == []
    assert "Dissent log" not in render_markdown(memo)


def test_the_memo_always_carries_its_not_advice_boundary(session, chain, conn):
    memo = build_memo(session, chain=chain, conn=conn, scores=SCORES, evidence=EVIDENCE)
    rendered = render_markdown(memo)
    assert "not financial, legal or professional" in rendered
    assert "prompt-defined" in rendered


def test_grounding_requires_a_shared_phrase_not_merely_a_near_ranking(conn):
    """Retrieval ranks anything near anything. A citation needs overlap."""
    real = ground(
        "The CFO objected that the hypermarket pilot has a longer payback period.", conn=conn
    )
    assert real, "a sentence lifted from the document must ground"

    unrelated = ground("Penguins migrate across the Antarctic shelf each spring.", conn=conn)
    assert unrelated == [], "an unrelated sentence must not acquire a citation by ranking near one"


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (
            "the hypermarket pilot has a longer payback",
            "x the hypermarket pilot has a longer payback y",
            "the hypermarket pilot has a longer payback",
        ),
        ("completely different words here", "nothing shared at all", ""),
        ("short", "short", ""),
    ],
)
def test_longest_shared_phrase(a, b, expected):
    assert _longest_shared_phrase(a, b) == expected


def test_an_empty_memo_still_renders():
    memo = Memo(session_id="s", question="q?", recommendation="none", ranked=[], margin=0.0)
    rendered = render_markdown(memo)
    assert "# Decision memo" in rendered and "q?" in rendered


def test_a_recommendation_the_whole_room_rejects_is_flagged_on_its_face(session, chain, conn):
    """Measured on a real run: the scores gave hypermarket 55 to plant's 51, so
    the memo recommended the hypermarket — and all five seats then said they
    disagreed and preferred the plant. A four-point margin across five seats and
    three axes is inside the noise. Presenting that as the room's decision would
    be the most misleading thing this memo could do."""
    memo = build_memo(session, chain=chain, conn=conn, scores=SCORES, evidence=EVIDENCE)
    attach_dissents(
        memo,
        {
            seat: DissentDraft(agrees=False, position="p" * 20, would_change_my_mind="w" * 20)
            for seat in ("cfo", "cmo", "coo", "ethics", "devil")
        },
    )

    assert memo.unanimous_dissent is True
    rendered = render_markdown(memo)
    assert "Every seat in the room disagreed" in rendered
    assert "too close to call" in rendered


def test_a_partly_split_room_is_not_flagged_as_unanimous(session, chain, conn):
    memo = build_memo(session, chain=chain, conn=conn, scores=SCORES, evidence=EVIDENCE)
    attach_dissents(
        memo,
        {
            "cfo": DissentDraft(agrees=False, position="p" * 20, would_change_my_mind="w" * 20),
            "cmo": DissentDraft(agrees=True, position="p" * 20, would_change_my_mind="w" * 20),
        },
    )
    assert memo.unanimous_dissent is False
    assert "Every seat in the room disagreed" not in render_markdown(memo)


def test_the_memo_is_shown_the_corpus_not_just_the_transcript(session, chain, conn):
    """Measured: given only the transcript and the ranking, the model wrote
    claims about the SCORING — 'the hypermarket received a higher score of 55' —
    every one of which failed the citation gate, because nothing about a score
    can ground in a board paper. It scored 0 cited with a document sitting in
    the corpus unread. A model cannot cite what it was never shown."""
    from services.api.crew.memo import _corpus_extract

    extract = _corpus_extract("Why did the CFO object to the payback period?", conn=conn)
    assert "untrusted_content" in extract, "corpus passages are fenced as what they are"
    assert "payback period" in extract

    empty = connect(":memory:")
    try:
        assert "No documents are in the room" in _corpus_extract("anything", conn=empty)
    finally:
        empty.close()


def test_a_duplicated_claim_appears_once(session, chain, conn, monkeypatch):
    """A verbatim-overlap gate pushes the model toward copying, and a copied
    sentence is easy to copy twice. Duplicates are pure noise; relevance is left
    to the reader, because a mechanical relevance filter would put one more
    model judgement between the reader and the source."""
    from services.api.core.schemas import MemoDraft

    repeated = "The CFO objected that the hypermarket pilot has a longer payback period."

    def fake_structured(*args, **kwargs):
        return (
            MemoDraft(
                recommendation="r" * 20,
                context=[repeated, repeated],
                reasoning=[
                    repeated,
                    "The COO noted plant downtime windows are scheduled quarterly.",
                ],
            ),
            type("R", (), {"provider": "stub", "model": "m", "truncated": False})(),
        )

    monkeypatch.setattr(chain, "structured", fake_structured)
    memo = build_memo(session, chain=chain, conn=conn, scores=SCORES, evidence=EVIDENCE)

    texts = [c.text for c in memo.context + memo.reasoning] + memo.uncited
    assert texts.count(repeated) == 1, f"the same sentence appeared {texts.count(repeated)} times"
