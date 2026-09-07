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

WHY THE FUSION IS NORMALISED BY ELIGIBLE ARMS
---------------------------------------------
Textbook RRF sums reciprocal ranks across both lists, which silently assumes
both retrievers COULD rank any document. On a multilingual corpus that
assumption is false, and the consequence is severe. Measured on the real corpus
before this was fixed: for the query "Why did the CFO object to the payback
period?", the Hindi and Arabic statements of exactly that objection ranked 1st
and 2nd on the vector arm — the best semantic matches in the corpus after the
literal English sentence — and came 11th and 12th after fusion, below "The
marketing team prefers bright packaging for summer drinks".

They could never appear in the BM25 list at all, because they share no tokens
with an English query, so they collected roughly half the fused score of any
English chunk BM25 ranked for any reason. The cross-lingual retrieval the whole
embedding spike was run to buy was being destroyed by the fusion step, and
nothing failed: COUNSEL simply answered a trilingual corpus in one language and
cited it.

So the score is the MEAN reciprocal rank over the arms that were eligible to
rank that chunk, not the sum over all arms. A chunk sharing no token with the
query is not BM25-eligible, and an arm that structurally cannot express an
opinion about a document does not get counted as having voted against it.
Eligibility is decided by token overlap, which is exact and needs no language
detection.

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

from services.api.core.db import vec_available, vector_table
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
    positive = [c.chunk_id for c, s in ordered[:limit] if s > 0]
    if positive:
        return positive

    # BM25's IDF goes non-positive when a term appears in every document, which
    # on a ONE-document corpus is every term in it. Filtering on score > 0 then
    # returns nothing for a query that plainly matches — measured on the
    # deployed instance, where a user who uploads one document and searches it
    # got zero results. Falling back to token overlap keeps small corpora
    # searchable without disturbing the ranking anywhere else.
    wanted = set(tokens)
    overlap = [(c.chunk_id, len(wanted & set(tokenize(c.text)))) for c in chunks]
    return [cid for cid, n in sorted(overlap, key=lambda p: -p[1])[:limit] if n > 0]


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
    by_rowid = {
        r["vec_rowid"]: r["chunk_id"]
        for r in conn.execute(
            "SELECT vec_rowid, chunk_id FROM vector_index WHERE model_key = ?", (key,)
        ).fetchall()
    }

    if vec_available(conn):
        rows = conn.execute(
            f"SELECT rowid, distance FROM {table} WHERE embedding MATCH ? AND k = ? "
            "ORDER BY distance",
            (struct.pack(f"{len(vector)}f", *vector), limit),
        ).fetchall()
        ordered = [r["rowid"] for r in rows]
    else:
        ordered = _brute_force(conn, table, vector, limit)

    return [by_rowid[rid] for rid in ordered if rid in by_rowid], None


def _brute_force(conn: Connection, table: str, query: list[float], limit: int) -> list[int]:
    """Cosine similarity over every stored vector, in numpy.

    The fallback for interpreters with no loadable-extension support — Render's
    Python is one, which is how this was found. It is a full scan, and that is
    fine at this scale: COUNSEL's corpus is the documents one person uploaded
    before a meeting, so a few thousand vectors at most. Measured at that size
    the scan is well under a millisecond, and it keeps semantic retrieval —
    the whole cross-lingual claim — working where sqlite-vec cannot load.
    """
    import numpy as np

    rows = conn.execute(f"SELECT rowid, embedding FROM {table}").fetchall()
    if not rows:
        return []

    matrix = np.frombuffer(b"".join(r["embedding"] for r in rows), dtype=np.float32)
    matrix = matrix.reshape(len(rows), -1)
    q = np.asarray(query, dtype=np.float32)

    norms = np.linalg.norm(matrix, axis=1) * np.linalg.norm(q)
    # A zero-norm vector cannot be scored; leaving it as -inf keeps it out of
    # the ranking rather than making it the best match by accident.
    scores = np.where(norms > 0, matrix @ q / np.where(norms > 0, norms, 1), -np.inf)

    best = np.argsort(-scores)[:limit]
    return [rows[int(i)]["rowid"] for i in best if scores[int(i)] > -np.inf]


def retrieve(
    query: str, *, conn: Connection, limit: int = 8, embedder: Embedder | None = None
) -> Retrieval:
    embedder = embedder or get_embedder()
    chunks = _all_chunks(conn)
    by_id = {c.chunk_id: c for c in chunks}
    pool = max(limit * 4, 20)

    lexical = _bm25_ranking(query, chunks, pool)
    if embedder is None:
        semantic, why_skipped = (
            [],
            (
                "no embedding model can run in this environment, so search is lexical only "
                "and cannot match across languages"
            ),
        )
    else:
        semantic, why_skipped = _vector_ranking(query, conn=conn, embedder=embedder, limit=pool)

    lex_rank = {cid: i for i, cid in enumerate(lexical)}
    vec_rank = {cid: i for i, cid in enumerate(semantic)}

    query_tokens = set(tokenize(query))
    vector_ran = bool(semantic) or why_skipped is None

    fused: dict[str, float] = {}
    for cid in set(lex_rank) | set(vec_rank):
        chunk = by_id.get(cid)
        if chunk is None:
            continue
        contributions = 0.0
        eligible = 0

        # BM25 can only rank a chunk that shares a token with the query. If it
        # shares none, BM25's silence is not evidence — it is inability.
        if query_tokens & set(tokenize(chunk.text)):
            eligible += 1
            if cid in lex_rank:
                contributions += 1.0 / (RRF_K + lex_rank[cid] + 1)

        if vector_ran:
            eligible += 1
            if cid in vec_rank:
                contributions += 1.0 / (RRF_K + vec_rank[cid] + 1)

        fused[cid] = contributions / eligible if eligible else 0.0

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
