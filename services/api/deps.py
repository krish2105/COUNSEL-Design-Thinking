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
    StubProvider,
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
    return LLMChain(
        [
            OllamaProvider(),
            GeminiProvider(),
            GroqProvider(),
            AnthropicProvider(),
            StubProvider(),
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
