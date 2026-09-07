"""Wiring. One place that knows how the pieces are assembled."""

from __future__ import annotations

from functools import lru_cache
from sqlite3 import Connection

from services.api.core.db import connect
from services.api.core.llm import (
    AnthropicProvider,
    GeminiProvider,
    GroqProvider,
    LLMChain,
    OllamaProvider,
)
from services.api.core.quota import Quota
from services.api.core.search import (
    KeylessProvider,
    SearchChain,
    SearxngProvider,
    StubSearchProvider,
    UserLinksProvider,
)
from services.api.core.settings import settings
from services.api.crew.stubs import phase_c_stub
from services.api.rag.embed import Embedder, get_embedder


@lru_cache
def db() -> Connection:
    # check_same_thread is off because FastAPI serves requests from a threadpool
    # and this connection is process-wide. Writes are short and serialised by
    # SQLite's own lock; the workload is one operator, not a fleet.
    conn = connect(settings().counsel_db)
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@lru_cache
def quota() -> Quota:
    s = settings()
    return Quota(
        {
            "ollama": s.quota_ollama_requests,
            "gemini": s.quota_gemini_requests,
            "groq": s.quota_groq_requests,
            "stub": 1_000_000,
        },
        conn=connect(s.counsel_db),
    )


@lru_cache
def llm() -> LLMChain:
    """The provider chain the running service uses.

    The terminal stub is phase_c_stub(), NOT a bare StubProvider(). A bare stub
    answers complete() with prose and cannot answer structured() at all, so the
    chain raised

        LLMError: no provider returned a valid Framing after 2 attempts:
        ['stub: ValueError', 'stub: ValueError']

    for every structured stage. That is not a corner case: with no provider keys
    set the deployed service runs ENTIRELY on the stub, so Board, Decide and
    Report were all 500s while the Room worked, because a debate turn is
    complete() and a framing is structured().

    Every test built its chain with phase_c_stub() and every one of them passed.
    The substrate under test was not the substrate in production — the same
    shape of mistake as assuming Render's Python could load SQLite extensions.
    """
    return LLMChain(
        [
            OllamaProvider(),
            GeminiProvider(),
            GroqProvider(),
            AnthropicProvider(),
            phase_c_stub(),
        ],
        quota(),
    )


@lru_cache
def user_links() -> UserLinksProvider:
    return UserLinksProvider([])


@lru_cache
def search() -> SearchChain:
    return SearchChain([SearxngProvider(), KeylessProvider(), user_links(), StubSearchProvider()])


@lru_cache
def embedder() -> Embedder:
    return get_embedder()
