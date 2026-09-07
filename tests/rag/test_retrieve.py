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


def test_retrieval_works_without_the_sqlite_extension(monkeypatch):
    """Render's Python is built without loadable-extension support, so
    sqlite-vec cannot load there at all. The suite was green and the first
    request to the live API was a 500 — every Python on the dev machine has the
    flag.

    Vectors now fall back to a brute-force cosine scan. This asserts the
    fallback returns the SAME ordering as sqlite-vec, not merely that it returns
    something: a fallback that silently reranks would be worse than an error.
    """
    from services.api.core import db as db_mod

    with_extension = connect(":memory:")
    try:
        assert db_mod.vec_available(with_extension) is True
        for name in ("docs/trilingual.md", "docs/board-paper.pdf"):
            ingest(FIXTURES.parent / name, conn=with_extension)
        expected = [
            h.chunk.text for h in retrieve("payback period", conn=with_extension, limit=5).hits
        ]
    finally:
        with_extension.close()

    def refuses_to_load(_conn):
        raise AttributeError("'sqlite3.Connection' object has no attribute ...")

    monkeypatch.setattr(db_mod.sqlite_vec, "load", refuses_to_load)
    without = db_mod.connect(":memory:")
    try:
        assert db_mod.vec_available(without) is False
        for name in ("docs/trilingual.md", "docs/board-paper.pdf"):
            ingest(FIXTURES.parent / name, conn=without)
        got = [h.chunk.text for h in retrieve("payback period", conn=without, limit=5).hits]
    finally:
        without.close()

    assert got == expected, "the numpy fallback must rank identically to sqlite-vec"


def test_the_fallback_creates_a_plain_table_not_a_virtual_one(monkeypatch):
    from services.api.core import db as db_mod

    monkeypatch.setattr(
        db_mod.sqlite_vec, "load", lambda _c: (_ for _ in ()).throw(AttributeError())
    )
    conn = db_mod.connect(":memory:")
    try:
        db_mod.ensure_vector_table(conn, 384)
        sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'vectors_384'").fetchone()[
            "sql"
        ]
        assert "VIRTUAL TABLE" not in sql.upper()
        assert "BLOB" in sql.upper()
    finally:
        conn.close()


def test_a_single_document_corpus_is_still_searchable():
    """BM25's IDF goes non-positive when a term appears in every document, which
    on a one-document corpus is every term in it. Filtering on score > 0 then
    returned NOTHING for a query that plainly matches — measured on the deployed
    instance, where uploading one document and searching it gave zero results.
    """
    conn = connect(":memory:")
    try:
        ingest(FIXTURES / "board-paper.pdf", conn=conn)
        result = retrieve("payback period", conn=conn, limit=5)
        assert result.hits, "a one-document corpus must still be searchable"
        assert any("payback period" in h.chunk.text for h in result.hits)
    finally:
        conn.close()


def test_retrieval_works_with_no_embedder_at_all(monkeypatch):
    """The deployed free tier cannot fit an embedding model in 512 MB, so there
    is no embedder there. That is a supported state: the corpus is stored
    without vectors, search runs lexical-only, and the reason is reported rather
    than the request failing."""
    from services.api.rag import embed as embed_mod

    monkeypatch.setenv("COUNSEL_DISABLE_FASTEMBED", "1")
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:1")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert embed_mod.EmbedderChain().resolve() is None

    conn = connect(":memory:")
    try:
        _, chunks = ingest(FIXTURES / "board-paper.pdf", conn=conn, embedder=None)
        assert chunks, "the document is still ingested"
        assert conn.execute("SELECT COUNT(*) FROM vector_index").fetchone()[0] == 0

        result = retrieve("payback period", conn=conn, limit=5, embedder=None)
        assert result.hits, "lexical search must still work"
        assert result.degraded and "lexical only" in result.degraded[0]
        assert "cannot match across languages" in result.degraded[0]
    finally:
        conn.close()
