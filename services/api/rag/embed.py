"""Embeddings, with the model recorded on every vector.

THREE BACKENDS, BECAUSE THE DEPLOYMENT FORCED IT
-------------------------------------------------
Locally, Ollama serves bge-m3 — a proper retrieval model, 1024-dim, 8192-token
context. The deployed instance has no Ollama and 512 MB of RAM on Render's free
tier, which rules out every large multilingual model regardless of how well it
scores (multilingual-e5-large is 2.24 GB). So deployed COUNSEL embeds in-process
with paraphrase-multilingual-MiniLM-L12-v2: 384-dim, 0.22 GB, Apache-2.0.

Both were measured, not assumed — see docs/models.md and
docs/results/A5-embedding-spike.json.

THE CONSEQUENCE, HANDLED EXPLICITLY
-----------------------------------
Two models means two vector spaces, and cosine similarity between them is
noise that looks like a score. So `model_key` travels with every stored vector
and retrieval refuses to compare across spaces (see rag/retrieve.py). Nothing
here silently mixes them.

`max_tokens` also differs by an order of magnitude — 8192 against 128 — so the
chunker asks the active embedder how big a chunk may be rather than hard-coding
a size that only works on a laptop.

WHY THIS CHAIN RESOLVES ONCE AND THEN REFUSES TO FAIL OVER
-----------------------------------------------------------
The LLM and search chains fail over per request, because a turn served by Groq
instead of Ollama is still a turn. An embedder cannot work that way. Falling
back mid-corpus would leave half the documents in one vector space and half in
another, and every later query would silently retrieve from whichever half
matched its own space — losing the other half with no error.

So `EmbedderChain` picks the first available backend once and keeps it. A
runtime failure raises rather than switching. Changing backends is a
re-ingestion, not a fallback.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Literal, Protocol, runtime_checkable

Kind = Literal["query", "passage"]


@runtime_checkable
class Embedder(Protocol):
    name: str
    model: str
    dim: int
    max_tokens: int

    def available(self) -> bool: ...

    def embed(self, texts: list[str], *, kind: Kind = "passage") -> list[list[float]]: ...


def model_key(embedder: Embedder) -> str:
    """The identity a stored vector is tagged with. Space, not just weights."""
    return f"{embedder.name}:{embedder.model}:{embedder.dim}"


class OllamaEmbedder:
    """bge-m3 over local Ollama. Preferred wherever Ollama is reachable."""

    name = "ollama"

    def __init__(self, model: str | None = None, host: str | None = None) -> None:
        self.model = model or os.getenv("OLLAMA_EMBED_MODEL") or "bge-m3:567m"
        self.host = (host or os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        self.dim = 1024
        self.max_tokens = 8192

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=2) as r:
                tags = json.load(r)
            return any(m["name"] == self.model for m in tags.get("models", []))
        except Exception:  # noqa: BLE001 — unreachable is a normal state, not an error
            return False

    def embed(self, texts, *, kind: Kind = "passage"):
        if not texts:
            return []
        req = urllib.request.Request(
            f"{self.host}/api/embed",
            data=json.dumps({"model": self.model, "input": texts}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            return [list(map(float, v)) for v in json.load(resp)["embeddings"]]


class GeminiEmbedder:
    """Google's free embedding tier. The deployed instance's first choice.

    Preferred over running a model in-process because Render's free instance has
    512 MB of RAM and no persistent disk: an in-process model costs a fifth of
    that budget plus a fresh download on every cold start, which happens after
    each 15-minute idle spin-down.

    `kind` maps onto Gemini's task types, which is not cosmetic — asymmetric
    embedding models place a question and the passage that answers it in
    deliberately different regions, and using the document task type for a query
    measurably degrades retrieval.

    UNVERIFIED AT TIME OF WRITING: no GEMINI_API_KEY was available when this was
    built, so the free-tier limits and the output dimensionality are taken from
    the documented contract rather than measured. scripts/spike_embeddings.py
    records the real numbers the first time a key is present, and until it has,
    docs/models.md says so.
    """

    name = "gemini"
    ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
    TASK = {"query": "RETRIEVAL_QUERY", "passage": "RETRIEVAL_DOCUMENT"}

    def __init__(
        self, api_key: str | None = None, model: str | None = None, dim: int = 768
    ) -> None:
        self._key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_EMBED_MODEL") or "gemini-embedding-001"
        self.dim = dim
        self.max_tokens = 2048

    def available(self) -> bool:
        return bool(self._key)

    def embed(self, texts, *, kind: Kind = "passage"):
        if not texts:
            return []
        import httpx

        # Batched so a 40-chunk document is one request against the request-count
        # quota rather than forty.
        r = httpx.post(
            f"{self.ENDPOINT}/{self.model}:batchEmbedContents",
            params={"key": self._key},
            json={
                "requests": [
                    {
                        "model": f"models/{self.model}",
                        "content": {"parts": [{"text": t}]},
                        "taskType": self.TASK[kind],
                        "outputDimensionality": self.dim,
                    }
                    for t in texts
                ]
            },
            timeout=120.0,
        )
        r.raise_for_status()
        return [[float(x) for x in e["values"]] for e in r.json()["embeddings"]]


class FastEmbedEmbedder:
    """ONNX in-process. What the deployed instance actually runs."""

    name = "fastembed"
    DEFAULT = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("FASTEMBED_MODEL") or self.DEFAULT
        self.dim = 384
        # The reason chunk size is a property of the embedder and not a constant.
        self.max_tokens = 128
        self._impl = None

    def available(self) -> bool:
        try:
            import fastembed  # noqa: F401

            return True
        except ImportError:
            return False

    def _load(self):
        if self._impl is None:
            from fastembed import TextEmbedding

            self._impl = TextEmbedding(model_name=self.model)
        return self._impl

    def embed(self, texts, *, kind: Kind = "passage"):
        if not texts:
            return []
        return [[float(x) for x in v] for v in self._load().embed(texts)]


class EmbedderChain:
    """Ollama → Gemini → fastembed, resolved once.

    Resolution order is by quality where it is free: bge-m3 locally, then
    Gemini's hosted model, then the small in-process ONNX model that fits a
    512 MB instance. See the module docstring for why this does not fail over
    per call the way the LLM and search chains do.
    """

    def __init__(self, candidates: list[Embedder] | None = None) -> None:
        self.candidates = candidates or [OllamaEmbedder(), GeminiEmbedder(), FastEmbedEmbedder()]
        self._resolved: Embedder | None = None

    def resolve(self) -> Embedder:
        if self._resolved is None:
            for candidate in self.candidates:
                if candidate.available():
                    self._resolved = candidate
                    break
            else:
                raise RuntimeError(
                    "no embedder available. Start Ollama and `ollama pull bge-m3:567m`, "
                    "set GEMINI_API_KEY, or install the cloud extra with "
                    "`uv sync --extra cloud`."
                )
        return self._resolved

    def health(self) -> list[dict[str, object]]:
        return [
            {"name": c.name, "model": c.model, "dim": c.dim, "available": c.available()}
            for c in self.candidates
        ]


def get_embedder() -> Embedder:
    """The active embedder. Never mixes spaces; see EmbedderChain."""
    return EmbedderChain().resolve()
