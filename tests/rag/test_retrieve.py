"""Retrieval is tested on the property the A5 spike bought: cross-lingual recall.

If an English query stops finding its Hindi and Arabic counterparts, COUNSEL
does not fail loudly — it quietly answers in one language and cites it, which
looks exactly like working.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.api.core.db import connect
from services.api.rag.embed import FastEmbedEmbedder, OllamaEmbedder, get_embedder
from services.api.rag.ingest import ingest
from services.api.rag.retrieve import retrieve, tokenize

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/docs"


INJECTION = Path(__file__).resolve().parents[1] / "fixtures/injection"


@pytest.fixture
def corpus():
    conn = connect(":memory:")
    ingest(FIXTURES / "trilingual.md", conn=conn)
    ingest(FIXTURES / "board-paper.pdf", conn=conn)
    yield conn
    conn.close()


@pytest.fixture
def english_heavy_corpus():
    """The same three-language claim, buried under ten English passages.

    A small balanced corpus hides the fusion bug below: with few English chunks,
    the unrelated control also falls out of the BM25 list and the comparison
    proves nothing. English mass is what makes the test real.
    """
    conn = connect(":memory:")
    ingest(FIXTURES / "trilingual.md", conn=conn)
    ingest(FIXTURES / "board-paper.pdf", conn=conn)
    ingest(INJECTION / "poisoned-plan.md", conn=conn)
    yield conn
    conn.close()


def test_an_english_query_ranks_its_translations_above_an_unrelated_english_chunk(corpus):
    """The A5 spike, turned into a permanent regression.

    Asserting a fixed top-N would only measure how much English happens to be in
    the corpus. The property the spike actually bought is the ordering: the
    Hindi and Arabic statements of the CFO's objection must both outrank an
    English sentence about summer drinks. If that inverts, COUNSEL answers a
    trilingual corpus in one language and cites it, which looks like working.
    """
    result = retrieve("Why did the CFO object to the payback period?", conn=corpus, limit=10)
    order = {h.chunk.chunk_id: i for i, h in enumerate(result.hits)}
    ranks = {
        h.chunk.lang if h.chunk.lang != "en" else "control": order[h.chunk.chunk_id]
        for h in result.hits
        if h.chunk.lang in {"hi", "ar"} or "bright packaging" in h.chunk.text
    }
    assert "hi" in ranks and "ar" in ranks, f"translations not retrieved at all: {ranks}"
    assert "control" in ranks, (
        "the unrelated control chunk was not retrieved, so this proves nothing"
    )
    assert ranks["hi"] < ranks["control"], f"Hindi ranked below an unrelated English chunk: {ranks}"
    assert ranks["ar"] < ranks["control"], (
        f"Arabic ranked below an unrelated English chunk: {ranks}"
    )


def _embedders():
    """Both embedders, because COUNSEL runs a different one in each place.

    Local development uses bge-m3 over Ollama; the deployed instance uses
    MiniLM in-process (docs/models.md). Testing only whichever happens to be
    installed is how a regression reaches production unseen — the CI machine
    has no Ollama, so before this was parametrised, local runs tested bge-m3,
    CI tested MiniLM, and neither tested the other.
    """
    out = []
    ollama = OllamaEmbedder()
    out.append(
        pytest.param(
            ollama,
            id="bge-m3",
            marks=pytest.mark.skipif(
                not ollama.available(),
                reason="Ollama not reachable; bge-m3 is the local-only embedder",
            ),
        )
    )
    fast = FastEmbedEmbedder()
    out.append(
        pytest.param(
            fast,
            id="minilm",
            marks=pytest.mark.skipif(
                not fast.available(), reason="fastembed not installed; install the cloud extra"
            ),
        )
    )
    return out


@pytest.mark.parametrize("embedder", _embedders())
def test_fusion_does_not_bury_a_translation_under_english_mass(embedder):
    """The regression for the worst bug found in Phase A.

    Textbook RRF sums reciprocal ranks over both lists, which assumes both
    retrievers could rank any document. A Hindi chunk cannot appear in a BM25
    list for an English query at all — it shares no tokens — so it collected
    half the fused score of any English chunk BM25 ranked for any reason.

    Measured on this exact corpus with bge-m3 before the fix: the Hindi and
    Arabic statements of the CFO's objection ranked 1st and 2nd on the VECTOR
    arm and 11th and 12th after fusion, below a passage about summer drinks
    packaging. Nothing failed; COUNSEL just answered a trilingual corpus in
    English and cited it.

    The assertion is that both translations outrank an unrelated English
    passage — not that they hit a fixed position. A fixed position would only
    measure how much English is in the fixture, and the two embedders
    legitimately differ: bge-m3 puts Hindi 1st, MiniLM 4th (see
    docs/results/A7-fusion-crosslingual.json). Both are correct; burying them
    under the control is not.
    """
    conn = connect(":memory:")
    try:
        for name in ("docs/trilingual.md", "docs/board-paper.pdf", "injection/poisoned-plan.md"):
            ingest(FIXTURES.parent / name, conn=conn, embedder=embedder)

        result = retrieve(
            "Why did the CFO object to the payback period?",
            conn=conn,
            limit=16,
            embedder=embedder,
        )
        rank = {}
        for i, hit in enumerate(result.hits):
            if hit.chunk.lang in {"hi", "ar"}:
                rank.setdefault(hit.chunk.lang, i)
            elif "bright packaging" in hit.chunk.text:
                rank.setdefault("control", i)

        assert "hi" in rank and "ar" in rank, f"a translation was not retrieved at all: {rank}"
        assert "control" in rank, "the unrelated control was not retrieved, so this proves nothing"
        assert rank["hi"] < rank["control"], (
            f"Hindi ranked below an unrelated English passage: {rank}. "
            "Check the eligible-arm normalisation in retrieve()."
        )
        assert rank["ar"] < rank["control"], (
            f"Arabic ranked below an unrelated English passage: {rank}"
        )
    finally:
        conn.close()


def test_an_arm_that_could_not_rank_a_chunk_does_not_vote_against_it(english_heavy_corpus):
    """The principle behind the fix, stated as a test.

    A chunk sharing no query token is scored on the vector arm alone, so its
    score is a mean over one arm rather than a sum over two.
    """
    result = retrieve("payback period", conn=english_heavy_corpus, limit=16)
    cross_lingual = [h for h in result.hits if h.rank_bm25 is None and h.rank_vec is not None]
    assert cross_lingual, "expected at least one vector-only hit"
    for hit in cross_lingual:
        expected = 1.0 / (60 + hit.rank_vec + 1)
        assert hit.score == pytest.approx(expected, rel=1e-6), (
            "a vector-only hit must be scored as the mean over its one eligible arm"
        )


def test_both_arms_contribute(corpus):
    result = retrieve("hypermarket payback period", conn=corpus, limit=6)
    assert result.degraded == (), "both arms should run on a freshly ingested corpus"
    assert any(h.rank_bm25 is not None for h in result.hits), "lexical arm found nothing"
    assert any(h.rank_vec is not None for h in result.hits), "vector arm found nothing"


def test_lexical_search_finds_an_exact_string_embeddings_would_blur(corpus):
    result = retrieve("Greenlam quarterly downtime windows", conn=corpus, limit=5)
    assert any("downtime windows" in h.chunk.text for h in result.hits)


def test_vector_search_is_skipped_rather_than_mixing_spaces(corpus):
    """The corpus is embedded in one space. Querying in the other must not
    silently return neighbours from the wrong one."""
    active = get_embedder()
    other = FastEmbedEmbedder() if isinstance(active, OllamaEmbedder) else OllamaEmbedder()

    result = retrieve("payback period", conn=corpus, limit=5, embedder=other)
    assert result.degraded, "a space mismatch must be disclosed, not absorbed"
    assert "incompatible spaces" in result.degraded[0]
    assert all(h.rank_vec is None for h in result.hits), "no hit may come from the vector arm"
    assert result.hits, "retrieval degrades to lexical-only; it does not return nothing"


def test_an_empty_corpus_returns_nothing_without_raising():
    conn = connect(":memory:")
    try:
        assert retrieve("anything", conn=conn).hits == []
    finally:
        conn.close()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "The CFO's payback-period objection",
            ["the", "cfo", "s", "payback", "period", "objection"],
        ),
        ("भुगतान अवधि", ["भुगतान", "अवधि"]),
        ("فترة استرداد", ["فترة", "استرداد"]),
    ],
)
def test_tokenize_handles_all_three_scripts(text, expected):
    assert tokenize(text) == expected
