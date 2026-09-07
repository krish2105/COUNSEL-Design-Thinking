"""Retrieval and web search — the evidence side of the boardroom.

Both endpoints return content that someone else wrote, so both label it. The
streaming variant exists to establish the shape Phase C's debate needs, not
because searching four sources is slow.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from services.api import deps
from services.api.core.rbac import Scope, require
from services.api.core.stream import from_iterable, sse
from services.api.rag.retrieve import retrieve

router = APIRouter(tags=["research"])


class Query(BaseModel):
    q: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=8, ge=1, le=50)


@router.post("/retrieve", dependencies=[Depends(require(Scope.READ))])
def retrieve_endpoint(query: Query) -> dict[str, object]:
    result = retrieve(query.q, conn=deps.db(), limit=query.limit, embedder=deps.embedder())
    return {
        "query": query.q,
        "degraded": list(result.degraded),
        "hits": [
            {
                "chunk_id": h.chunk.chunk_id,
                "doc_id": h.chunk.doc_id,
                "text": h.chunk.text,
                "start": h.chunk.start,
                "end": h.chunk.end,
                "lang": h.chunk.lang,
                "score": round(h.score, 6),
                "rank_bm25": h.rank_bm25,
                "rank_vec": h.rank_vec,
                "trust": "untrusted",
            }
            for h in result.hits
        ],
    }


@router.post("/search", dependencies=[Depends(require(Scope.SESSION_WRITE))])
def search_endpoint(query: Query) -> dict[str, object]:
    chain = deps.search()
    results = chain.search(query.q, limit=query.limit)
    return {
        "query": query.q,
        "served_by": results[0].provider if results else None,
        "degraded_from": list(chain.last_degraded_from),
        "results": [
            {
                "url": r.url,
                "title": r.title,
                "snippet": r.snippet,
                "retrieved_at": r.retrieved_at,
                "provider": r.provider,
                "trust": r.trust,
            }
            for r in results
        ],
    }


@router.post("/search/stream", dependencies=[Depends(require(Scope.SESSION_WRITE))])
async def search_stream(query: Query) -> EventSourceResponse:
    """The SSE seam. Phase C's debate streams turns through this same shape."""
    chain = deps.search()
    results = chain.search(query.q, limit=query.limit)
    return sse(
        from_iterable(
            "result",
            [
                {"url": r.url, "title": r.title, "provider": r.provider, "trust": r.trust}
                for r in results
            ],
        )
    )
