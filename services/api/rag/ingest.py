"""Files in, chunks out, with an offset that survives the round trip.

THE ONE INVARIANT
-----------------
For every chunk, `document_text(doc_id)[chunk.start:chunk.end] == chunk.text`.

Everything COUNSEL claims about citation rests on it. A memo says "the CFO's
objection is grounded in the business plan" and points at a span; if that span
does not resolve to the exact words quoted, the citation is decoration. So
chunk text is never normalised, stripped or re-joined after slicing — it IS the
slice, and `tests/rag/test_ingest.py` asserts it for every chunk of every
fixture.

Chunk size is asked of the embedder rather than fixed, because the local model
takes 8192 tokens and the deployed one takes 128 (docs/models.md).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from sqlite3 import Connection
from typing import Literal

from services.api.core.db import WRITE_LOCK, ensure_vector_table
from services.api.rag.embed import Embedder, get_embedder, model_key
from services.api.rag.untrusted import scan

Trust = Literal["untrusted"]

#: Even with an 8192-token model, a chunk that large retrieves badly — the
#: citation ends up pointing at a page instead of a sentence.
MAX_CHUNK_CHARS = 1800
CHARS_PER_TOKEN = 3


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    ordinal: int
    text: str
    start: int
    end: int
    lang: str
    trust: Trust = "untrusted"

    def __post_init__(self) -> None:
        if self.trust != "untrusted":
            raise ValueError("an uploaded document is always untrusted content")


# ── extraction ──────────────────────────────────────────────────────────────


def extract_text(path: Path) -> tuple[str, str]:
    """Return (text, media_type). The text returned here is what offsets index into."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        pages = [p.extract_text() or "" for p in PdfReader(str(path)).pages]
        return "\n\n".join(pages), "application/pdf"
    if suffix == ".docx":
        import docx

        paras = [p.text for p in docx.Document(str(path)).paragraphs]
        return "\n\n".join(paras), (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    if suffix in {".txt", ".md", ".markdown"}:
        return path.read_text(encoding="utf-8"), (
            "text/markdown" if suffix != ".txt" else "text/plain"
        )
    raise ValueError(f"unsupported document type: {suffix or path.name}")


# ── language ────────────────────────────────────────────────────────────────


def detect_lang(text: str) -> str:
    """Script-range detection. Deliberately not a dependency.

    COUNSEL needs to know which of three scripts a span is in so the record can
    render it correctly and the citation can resolve. It does not need to tell
    Portuguese from Spanish, so a 15-line function beats a model.
    """
    devanagari = sum(1 for c in text if "ऀ" <= c <= "ॿ")
    arabic = sum(1 for c in text if "؀" <= c <= "ۿ" or "ݐ" <= c <= "ݿ")
    latin = sum(1 for c in text if c.isascii() and c.isalpha())
    total = devanagari + arabic + latin
    if total == 0:
        return "und"
    if devanagari / total > 0.30:
        return "hi"
    if arabic / total > 0.30:
        return "ar"
    return "en"


# ── chunking ────────────────────────────────────────────────────────────────

_PARA = re.compile(r"\n\s*\n")
_SENT = re.compile(r"(?<=[.!?۔।])\s+")


def _budget(embedder: Embedder | None) -> int:
    #: With no embedder there is no context window to respect, so the chunk
    #: size is the retrieval-granularity cap alone.
    if embedder is None:
        return MAX_CHUNK_CHARS
    return max(200, min(MAX_CHUNK_CHARS, embedder.max_tokens * CHARS_PER_TOKEN))


def _spans(text: str, pattern: re.Pattern[str]) -> list[tuple[int, int]]:
    """Split into [start, end) spans without ever touching the substrings."""
    spans, cursor = [], 0
    for m in pattern.finditer(text):
        if m.start() > cursor:
            spans.append((cursor, m.start()))
        cursor = m.end()
    if cursor < len(text):
        spans.append((cursor, len(text)))
    return spans


def plan_chunks(text: str, budget: int) -> list[tuple[int, int]]:
    """Contiguous [start, end) spans, each within budget where the text allows."""
    out: list[tuple[int, int]] = []
    for p_start, p_end in _spans(text, _PARA):
        if p_end - p_start <= budget:
            out.append((p_start, p_end))
            continue
        # Too big: fall back to sentences, then to a hard cut for text with no
        # sentence boundaries at all (a minified table, a wall of CJK).
        para = text[p_start:p_end]
        acc_start = p_start
        acc_end = p_start
        for s_start, s_end in _spans(para, _SENT):
            abs_start, abs_end = p_start + s_start, p_start + s_end
            if abs_end - acc_start > budget and acc_end > acc_start:
                out.append((acc_start, acc_end))
                acc_start = abs_start
            acc_end = abs_end
            while acc_end - acc_start > budget:
                out.append((acc_start, acc_start + budget))
                acc_start += budget
        if acc_end > acc_start:
            out.append((acc_start, acc_end))
    return out


# ── ingestion ───────────────────────────────────────────────────────────────


def ingest(
    path: Path, *, conn: Connection, embedder: Embedder | None = None
) -> tuple[str, list[Chunk]]:
    """Ingest a file. Idempotent: doc_id is the sha256 of the bytes.

    Extraction, chunking and embedding all happen OUTSIDE the write lock —
    embedding a long document takes seconds and there is no reason for it to
    block a concurrent read of the record. The lock covers only the writes, so
    a document is never half-ingested.
    """
    embedder = embedder or get_embedder()
    raw = path.read_bytes()
    doc_id = hashlib.sha256(raw).hexdigest()

    if conn.execute("SELECT 1 FROM documents WHERE doc_id = ?", (doc_id,)).fetchone():
        return doc_id, load_chunks(doc_id, conn=conn)

    text, media_type = extract_text(path)
    chunks = [
        Chunk(
            chunk_id=f"{doc_id[:16]}:{ordinal:04d}",
            doc_id=doc_id,
            ordinal=ordinal,
            # Never normalised. This slice IS the chunk, which is what makes the
            # round-trip invariant hold.
            text=text[start:end],
            start=start,
            end=end,
            lang=detect_lang(text[start:end]),
        )
        for ordinal, (start, end) in enumerate(plan_chunks(text, _budget(embedder)))
    ]
    # No embedder is a supported state: the deployed free tier cannot fit one
    # in memory. The document is still ingested, chunked and searchable — it
    # simply has no vectors, and retrieval says so rather than failing.
    vectors = (
        embedder.embed([c.text for c in chunks], kind="passage")
        if chunks and embedder is not None
        else []
    )
    findings = scan(text)

    with WRITE_LOCK:
        # Re-check inside the lock: two uploads of the same file can race here.
        if conn.execute("SELECT 1 FROM documents WHERE doc_id = ?", (doc_id,)).fetchone():
            return doc_id, load_chunks(doc_id, conn=conn)

        conn.execute(
            "INSERT INTO documents(doc_id, filename, media_type, text, n_chars, ingested_at, trust) "
            "VALUES (?, ?, ?, ?, ?, ?, 'untrusted')",
            (
                doc_id,
                path.name,
                media_type,
                text,
                len(text),
                datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )

        # Scanned once, at the boundary, and recorded. A document that tries to
        # instruct the model is still ingested and still retrievable — refusing
        # it would let an attacker delete evidence by poisoning it — but every
        # agent and the Documents tab can see what it tried.
        conn.executemany(
            "INSERT OR IGNORE INTO doc_findings(doc_id, pattern, severity, start, end, excerpt) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [(doc_id, f.pattern, f.severity, f.span[0], f.span[1], f.excerpt) for f in findings],
        )

        conn.executemany(
            "INSERT INTO chunks(chunk_id, doc_id, ordinal, text, start, end, lang, trust) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'untrusted')",
            [(c.chunk_id, c.doc_id, c.ordinal, c.text, c.start, c.end, c.lang) for c in chunks],
        )

        if chunks and embedder is not None and vectors:
            table = ensure_vector_table(conn, embedder.dim)
            key = model_key(embedder)
            for chunk, vector in zip(chunks, vectors, strict=True):
                cur = conn.execute(f"INSERT INTO {table}(embedding) VALUES (?)", (_pack(vector),))
                conn.execute(
                    "INSERT INTO vector_index(chunk_id, model_key, dim, vec_rowid) "
                    "VALUES (?, ?, ?, ?)",
                    (chunk.chunk_id, key, embedder.dim, cur.lastrowid),
                )

        conn.commit()

    return doc_id, chunks


def _pack(vector: list[float]) -> bytes:
    import struct

    return struct.pack(f"{len(vector)}f", *vector)


def findings_for(doc_id: str, *, conn: Connection) -> list[dict[str, object]]:
    """What the scanner found in this document, in document order."""
    return [
        dict(r)
        for r in conn.execute(
            "SELECT pattern, severity, start, end, excerpt FROM doc_findings "
            "WHERE doc_id = ? ORDER BY start",
            (doc_id,),
        ).fetchall()
    ]


def document_text(doc_id: str, *, conn: Connection) -> str:
    row = conn.execute("SELECT text FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
    if row is None:
        raise KeyError(f"no such document: {doc_id}")
    return row["text"]


def load_chunks(doc_id: str, *, conn: Connection) -> list[Chunk]:
    rows = conn.execute(
        "SELECT chunk_id, doc_id, ordinal, text, start, end, lang FROM chunks "
        "WHERE doc_id = ? ORDER BY ordinal",
        (doc_id,),
    ).fetchall()
    return [Chunk(**dict(r)) for r in rows]
