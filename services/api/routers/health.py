"""What is actually running, right now.

A health endpoint that returns {"ok": true} tells you the process is up, which
was never in doubt. This one answers the questions that matter for a system
whose whole claim is free-tier operation: which provider is serving, how much
budget is left, which embedding space the corpus is in, and whether the kill
switch is out.
"""

from __future__ import annotations

from fastapi import APIRouter

from services.api import __version__, deps
from services.api.core import killswitch
from services.api.rag.embed import EmbedderChain, model_key

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, object]:
    chain = deps.llm()
    active = next((p for p in chain.providers if p.available()), None)
    embed = deps.embedder()
    conn = deps.db()
    spaces = [
        r["model_key"]
        for r in conn.execute("SELECT DISTINCT model_key FROM vector_index").fetchall()
    ]
    return {
        "version": __version__,
        "providers": chain.health(),
        "active_provider": active.name if active else None,
        "search_tiers": deps.search().health(),
        "embedder": {
            "active": model_key(embed),
            "dim": embed.dim,
            "max_tokens": embed.max_tokens,
            # The whole chain, not just the winner: which embedders were
            # available is what explains why the corpus is in the space it is in.
            "chain": EmbedderChain().health(),
        },
        "corpus_spaces": spaces,
        "documents": conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
        "chunks": conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0],
        "killswitch": {"engaged": killswitch.engaged(), "reason": killswitch.reason()},
        "paid_inference": False,
    }
