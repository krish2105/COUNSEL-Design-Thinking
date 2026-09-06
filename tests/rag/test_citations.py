"""The citation gate is mechanical on purpose.

A model that means well can satisfy a prompt that asks for citations. Only a
model that is correct can satisfy a gate that reads the cited span out of the
database and looks for the quote in it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.api.core.db import connect
from services.api.rag.citations import (
    Citation,
    UncitedClaim,
    require_citations,
    resolve,
    verify,
)
from services.api.rag.ingest import document_text, ingest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/docs"
QUOTE = "hypermarket pilot has a longer payback period"


@pytest.fixture
def corpus():
    conn = connect(":memory:")
    doc_id, _ = ingest(FIXTURES / "board-paper.pdf", conn=conn)
    yield conn, doc_id
    conn.close()


def _span_of(conn, doc_id, needle):
    text = document_text(doc_id, conn=conn)
    start = text.index(needle)
    return start, start + len(needle)


def test_a_truthful_citation_passes(corpus):
    conn, doc_id = corpus
    start, end = _span_of(conn, doc_id, QUOTE)
    require_citations("The CFO raised payback.", [Citation(doc_id, start, end, QUOTE)], conn=conn)


def test_a_doctored_quote_is_rejected(corpus):
    """The failure this whole file exists for: a plausible quote, a real span,
    and words the document never contained."""
    conn, doc_id = corpus
    start, end = _span_of(conn, doc_id, QUOTE)
    forged = Citation(doc_id, start, end, "hypermarket pilot has a shorter payback period")

    with pytest.raises(UncitedClaim, match="not present in the cited span"):
        require_citations("The CFO endorsed the pilot.", [forged], conn=conn)
    assert verify(forged, conn=conn) is False


def test_a_quote_that_exists_elsewhere_but_not_in_the_cited_span_is_rejected(corpus):
    """Right document, real sentence, wrong span. A citation names a location,
    not just a source."""
    conn, doc_id = corpus
    wrong_start, wrong_end = _span_of(conn, doc_id, "Override requires written approval")
    with pytest.raises(UncitedClaim, match="not present in the cited span"):
        require_citations("x", [Citation(doc_id, wrong_start, wrong_end, QUOTE)], conn=conn)


def test_an_uncited_claim_is_rejected(corpus):
    conn, _ = corpus
    with pytest.raises(UncitedClaim, match="no citation"):
        require_citations("Footfall will rise 20 percent.", [], conn=conn)


def test_an_unknown_document_is_rejected(corpus):
    conn, _ = corpus
    with pytest.raises(UncitedClaim, match="unknown document"):
        require_citations("x", [Citation("0" * 64, 0, 5, "COUNS")], conn=conn)


def test_a_span_past_the_end_of_the_document_is_rejected(corpus):
    conn, doc_id = corpus
    n = len(document_text(doc_id, conn=conn))
    with pytest.raises(UncitedClaim, match="runs past the end"):
        require_citations("x", [Citation(doc_id, n - 5, n + 500, "COUNS")], conn=conn)


def test_whitespace_folding_accepts_a_quote_broken_across_a_pdf_line(corpus):
    """PDF extraction inserts breaks mid-sentence; a correct quote must survive
    that, while still being the same words."""
    conn, doc_id = corpus
    start, end = _span_of(conn, doc_id, QUOTE)
    rewrapped = QUOTE.replace(" ", "\n   ")
    require_citations("x", [Citation(doc_id, start, end, rewrapped)], conn=conn)


def test_folding_does_not_extend_to_meaning(corpus):
    """Whitespace is folded. Digits are not — a board argues over those."""
    conn, doc_id = corpus
    start, end = _span_of(conn, doc_id, "board of directors")
    with pytest.raises(UncitedClaim):
        require_citations("x", [Citation(doc_id, start, end, "board of 3 directors")], conn=conn)


def test_resolve_returns_the_stored_span(corpus):
    conn, doc_id = corpus
    start, end = _span_of(conn, doc_id, QUOTE)
    assert resolve(Citation(doc_id, start, end, QUOTE), conn=conn) == QUOTE


@pytest.mark.parametrize(
    ("start", "end", "quote"),
    [(10, 10, "x"), (10, 5, "x"), (0, 5, "   ")],
)
def test_a_malformed_citation_cannot_be_constructed(start, end, quote):
    with pytest.raises(ValueError):
        Citation("d", start, end, quote)
