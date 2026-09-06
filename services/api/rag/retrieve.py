"""Hybrid retrieval: lexical and semantic, fused by rank.

WHY BOTH
--------
COUNSEL retrieves across English, Hindi and Arabic. Vector search is what makes
that possible at all — BM25 cannot match an English query to an Arabic sentence,
because they share no tokens. But BM25 is what makes exact things findable: a
figure, a clause number, a name spelled the way the document spells it, which
is exactly what a board paper argues over and exactly where embeddings are
vague.

They are fused with Reciprocal Rank Fusion rather than by blending scores. BM25
scores and cosine distances live on different, unnormalised scales; any weighted
sum of them is a number with no meaning that happens to sort. RRF only uses
rank, so it cannot be fooled by scale.

REFUSING TO MIX SPACES
----------------------
Vectors carry the model that produced them. If the active embedder is not the
one the corpus was embedded with, the vector arm is skipped entirely and
retrieval runs lexical-only, with `degraded` set so the caller can say so.
Returning neighbours from the wrong space would produce confident nonsense with
a citation attached, which is the single worst failure this system can have.
"""

from __future__ import annotations

import struct
import unicodedata
from dataclasses import dataclass
from sqlite3 import Connection

from services.api.core.db import vector_table
from services.api.rag.embed import Embedder, get_embedder, model_key
from services.api.rag.ingest import Chunk

RRF_K = 60


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float
    rank_bm25: int | None
    rank_vec: int | None


@dataclass(frozen=True)
class Retrieval:
    hits: list[Hit]
    #: Empty when both arms ran. Otherwise says which arm was skipped and why,
    #: so a report can disclose that it answered on lexical search alone.
    degraded: tuple[str, ...] = ()


#: Zero-width joiners are part of a word in Indic scripts, not separators.
_JOINERS = {"\u200c", "\u200d"}


def tokenize(text: str) -> list[str]:
    r"""Split into words across Latin, Devanagari and Arabic.

    `\w+` is wrong here and fails silently. Devanagari vowel signs are Unicode
    combining marks (Mn/Mc), which `\w` excludes, so `\w+` splits भुगतान into
    ['भ', 'गत', 'न'] — dropping the vowels and leaving BM25 matching fragments
    that mean nothing. Arabic diacritics have the same problem. So a token is a
    run of alphanumerics, combining marks and joiners.
    """
    tokens: list[str] = []
    current: list[str] = []
    for ch in text:
        if ch.isalnum() or unicodedata.category(ch)[0] == "M" or ch in _JOINERS:
            current.append(ch)
        elif current:
            tokens.append("".join(current).lower())
            current = []
    if current:
        tokens.append("".join(current).lower())
    return tokens


def _all_chunks(conn: Connection) -> list[Chunk]:
    rows = conn.execute(
        "SELECT chunk_id, doc_id, ordinal, text, start, end, lang FROM chunks ORDER BY rowid"
    ).fetchall()
    return [Chunk(**dict(r)) for r in rows]


def _bm25_ranking(query: str, chunks: list[Chunk], limit: int) -> list[str]:
    if not chunks:
        return []
    from rank_bm25 import BM25Okapi

    tokens = tokenize(query)
    if not tokens:
        return []
    scores = BM25Okapi([tokenize(c.text) for c in chunks]).get_scores(tokens)
    ordered = sorted(zip(chunks, scores, strict=True), key=lambda p: -p[1])
    return [c.chunk_id for c, s in ordered[:limit] if s > 0]


def _vector_ranking(
    query: str, *, conn: Connection, embedder: Embedder, limit: int
) -> tuple[list[str], str | None]:
    key = model_key(embedder)
    stored = {
        r["model_key"]
        for r in conn.execute("SELECT DISTINCT model_key FROM vector_index").fetchall()
    }
    if not stored:
        return [], "no vectors stored"
    if key not in stored:
        return [], (
            f"corpus was embedded with {sorted(stored)} but the active embedder is {key}; "
            "vector search skipped rather than comparing incompatible spaces"
        )

    table = vector_table(embedder.dim)
    [vector] = embedder.embed([query], kind="query")
    rows = conn.execute(
        f"SELECT rowid, distance FROM {table} WHERE embedding MATCH ? AND k = ? ORDER BY distance",
        (struct.pack(f"{len(vector)}f", *vector), limit),
    ).fetchall()
    if not rows:
        return [], None

    by_rowid = {
        r["vec_rowid"]: r["chunk_id"]
        for r in conn.execute(
            "SELECT vec_rowid, chunk_id FROM vector_index WHERE model_key = ?", (key,)
        ).fetchall()
    }
    return [by_rowid[r["rowid"]] for r in rows if r["rowid"] in by_rowid], None


def retrieve(
    query: str, *, conn: Connection, limit: int = 8, embedder: Embedder | None = None
) -> Retrieval:
    embedder = embedder or get_embedder()
    chunks = _all_chunks(conn)
    by_id = {c.chunk_id: c for c in chunks}
    pool = max(limit * 4, 20)

    lexical = _bm25_ranking(query, chunks, pool)
    semantic, why_skipped = _vector_ranking(query, conn=conn, embedder=embedder, limit=pool)

    lex_rank = {cid: i for i, cid in enumerate(lexical)}
    vec_rank = {cid: i for i, cid in enumerate(semantic)}

    fused: dict[str, float] = {}
    for ranking in (lex_rank, vec_rank):
        for cid, rank in ranking.items():
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)

    hits = [
        Hit(
            chunk=by_id[cid],
            score=score,
            rank_bm25=lex_rank.get(cid),
            rank_vec=vec_rank.get(cid),
        )
        for cid, score in sorted(fused.items(), key=lambda p: -p[1])
        if cid in by_id
    ][:limit]

    degraded = (f"vector({why_skipped})",) if why_skipped else ()
    return Retrieval(hits=hits, degraded=degraded)
