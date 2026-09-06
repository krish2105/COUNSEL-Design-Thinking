"""A citation that does not resolve is a lie with a footnote.

COUNSEL's whole claim is that every factual sentence in a generated memo points
at something real. The weak version of that is a model emitting a plausible
quote next to a plausible source id. The strong version — the one implemented
here — is a gate that reads the cited span out of the stored document and
refuses the claim unless the quote is verbatim inside it.

This is deliberately mechanical. It cannot be satisfied by a well-behaved model,
only by a correct one, and it fails closed.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from sqlite3 import Connection

from services.api.rag.ingest import document_text


@dataclass(frozen=True)
class Citation:
    doc_id: str
    start: int
    end: int
    quote: str

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError(f"citation span is empty or inverted: [{self.start}, {self.end})")
        if not self.quote.strip():
            raise ValueError("a citation must quote something")


class UncitedClaim(ValueError):
    """Raised when a claim has no citation, or a citation that does not resolve."""


_WS = re.compile(r"\s+")


def _normalise(text: str) -> str:
    """Fold whitespace and Unicode form, and nothing else.

    PDF extraction inserts line breaks mid-sentence and Arabic text arrives in
    several equivalent normalisation forms, so a byte-exact comparison would
    reject correct quotes. Folding stops there on purpose: case, punctuation and
    digits are left alone, because those are precisely what a board argues over
    and a quote that changes them is not the same quote.
    """
    return _WS.sub(" ", unicodedata.normalize("NFC", text)).strip()


def resolve(citation: Citation, *, conn: Connection) -> str:
    """Return the stored text of the cited span."""
    source = document_text(citation.doc_id, conn=conn)
    if citation.end > len(source):
        raise UncitedClaim(
            f"citation span [{citation.start}, {citation.end}) runs past the end of "
            f"document {citation.doc_id[:12]} ({len(source)} chars)"
        )
    return source[citation.start : citation.end]


def verify(citation: Citation, *, conn: Connection) -> bool:
    try:
        return _normalise(citation.quote) in _normalise(resolve(citation, conn=conn))
    except (KeyError, UncitedClaim):
        return False


def require_citations(claim: str, citations: list[Citation], *, conn: Connection) -> None:
    """Raise UncitedClaim unless every citation resolves verbatim. Fails closed."""
    if not citations:
        raise UncitedClaim(f"claim has no citation: {claim[:120]!r}")

    for citation in citations:
        try:
            span = resolve(citation, conn=conn)
        except KeyError as exc:
            raise UncitedClaim(
                f"claim cites unknown document {citation.doc_id[:12]}: {claim[:120]!r}"
            ) from exc
        if _normalise(citation.quote) not in _normalise(span):
            raise UncitedClaim(
                f"quote is not present in the cited span. "
                f"Claim: {claim[:100]!r}. Quoted: {citation.quote[:80]!r}. "
                f"Span [{citation.start}, {citation.end}) actually reads: {span[:80]!r}"
            )
