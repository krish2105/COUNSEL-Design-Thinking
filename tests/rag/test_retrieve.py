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


@pytest.fixture
def corpus():
    conn = connect(":memory:")
    ingest(FIXTURES / "trilingual.md", conn=conn)
    ingest(FIXTURES / "board-paper.pdf", conn=conn)
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
