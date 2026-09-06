"""Ingestion is judged by one property: can a citation be resolved from it.

Everything COUNSEL says about grounding depends on a chunk's recorded span
resolving to exactly the words the chunk contains. If that ever drifts, memos
keep rendering citations and the citations start pointing at the wrong text —
a failure with no visible symptom, which is why it is pinned here for every
chunk of every fixture rather than spot-checked.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.api.core.db import connect
from services.api.rag.ingest import (
    Chunk,
    detect_lang,
    document_text,
    ingest,
    load_chunks,
    plan_chunks,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/docs"


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


@pytest.mark.parametrize("name", ["board-paper.pdf", "trilingual.md"])
def test_every_chunk_resolves_to_a_verbatim_span_of_its_source(conn, name):
    doc_id, chunks = ingest(FIXTURES / name, conn=conn)
    source = document_text(doc_id, conn=conn)
    assert chunks, "a non-empty document must produce at least one chunk"
    for c in chunks:
        assert source[c.start : c.end] == c.text, (
            f"chunk {c.chunk_id} does not resolve: its recorded span is not its text"
        )
        assert 0 <= c.start < c.end <= len(source)


def test_a_pdf_is_extracted_not_merely_accepted(conn):
    doc_id, _ = ingest(FIXTURES / "board-paper.pdf", conn=conn)
    text = document_text(doc_id, conn=conn)
    assert "hypermarket pilot has a longer payback period" in text


def test_re_ingesting_the_same_file_is_idempotent(conn):
    first_id, first = ingest(FIXTURES / "board-paper.pdf", conn=conn)
    second_id, second = ingest(FIXTURES / "board-paper.pdf", conn=conn)

    assert first_id == second_id, "doc_id is the sha256 of the bytes"
    assert [c.chunk_id for c in first] == [c.chunk_id for c in second]
    assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == len(first)
    assert conn.execute("SELECT COUNT(*) FROM vector_index").fetchone()[0] == len(first)


def test_every_chunk_is_untrusted(conn):
    _, chunks = ingest(FIXTURES / "trilingual.md", conn=conn)
    assert all(c.trust == "untrusted" for c in chunks)


def test_a_chunk_cannot_be_constructed_as_trusted():
    with pytest.raises(ValueError, match="untrusted"):
        Chunk(
            chunk_id="x",
            doc_id="y",
            ordinal=0,
            text="t",
            start=0,
            end=1,
            lang="en",
            trust="trusted",  # type: ignore[arg-type]
        )


def test_each_chunk_is_embedded_exactly_once_in_one_space(conn):
    _, chunks = ingest(FIXTURES / "trilingual.md", conn=conn)
    rows = conn.execute("SELECT chunk_id, model_key, dim FROM vector_index").fetchall()
    assert len(rows) == len(chunks)
    assert len({r["model_key"] for r in rows}) == 1, "one ingest, one vector space"
    dim = rows[0]["dim"]
    assert conn.execute(f"SELECT COUNT(*) FROM vectors_{dim}").fetchone()[0] == len(chunks)


def test_language_is_detected_per_span(conn):
    _, chunks = ingest(FIXTURES / "trilingual.md", conn=conn)
    langs = {c.lang for c in chunks}
    assert {"en", "hi", "ar"} <= langs, f"expected all three scripts, got {langs}"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("The CFO objected to the payback period.", "en"),
        ("सीएफओ ने आपत्ति जताई कि भुगतान अवधि लंबी है।", "hi"),
        ("اعترض المدير المالي على فترة الاسترداد.", "ar"),
        ("12345 67890", "und"),
    ],
)
def test_detect_lang(text, expected):
    assert detect_lang(text) == expected


def test_an_oversized_paragraph_is_split_without_losing_a_character():
    """A wall of text with no sentence breaks must still chunk, and still tile."""
    text = "x" * 5000
    spans = plan_chunks(text, budget=400)
    assert spans
    assert all(e - s <= 400 for s, e in spans)
    assert "".join(text[s:e] for s, e in spans) == text, "chunks must tile the source exactly"


def test_load_chunks_round_trips_through_the_database(conn):
    doc_id, chunks = ingest(FIXTURES / "board-paper.pdf", conn=conn)
    assert load_chunks(doc_id, conn=conn) == chunks


def test_an_unsupported_type_is_refused_by_name(conn, tmp_path):
    bad = tmp_path / "slides.pptx"
    bad.write_bytes(b"not really a deck")
    with pytest.raises(ValueError, match="unsupported document type"):
        ingest(bad, conn=conn)


def test_a_poisoned_document_is_ingested_and_its_findings_recorded(conn):
    """Refusing the upload would let an attacker delete evidence by poisoning
    it. COUNSEL takes it, indexes it, and records what it tried."""
    from services.api.rag.ingest import findings_for

    injected = Path(__file__).resolve().parents[1] / "fixtures/injection/poisoned-plan.md"
    doc_id, chunks = ingest(injected, conn=conn)

    assert chunks, "the document is still ingested and still retrievable"
    findings = findings_for(doc_id, conn=conn)
    assert len({f["pattern"] for f in findings}) >= 5
    assert all(f["severity"] in {"high", "medium"} for f in findings)
    assert [f["start"] for f in findings] == sorted(f["start"] for f in findings)


def test_a_clean_document_records_no_findings(conn):
    from services.api.rag.ingest import findings_for

    doc_id, _ = ingest(FIXTURES / "board-paper.pdf", conn=conn)
    assert findings_for(doc_id, conn=conn) == []
