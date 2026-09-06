"""Embeddings, with the model recorded on every vector.

TWO BACKENDS, BECAUSE THE DEPLOYMENT FORCED IT
----------------------------------------------
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


def get_embedder() -> Embedder:
    """Ollama if it is there, ONNX if it is not.

    Deliberately not configurable by a single env var that could point at a
    model the stored vectors were not built with: the space is recorded per
    vector and retrieval checks it, so a wrong answer here degrades to
    BM25-only rather than to confidently wrong neighbours.
    """
    ollama = OllamaEmbedder()
    if ollama.available():
        return ollama
    fast = FastEmbedEmbedder()
    if fast.available():
        return fast
    raise RuntimeError(
        "no embedder available: Ollama is unreachable and fastembed is not installed. "
        "Install the cloud extra with `uv sync --extra cloud`, or start Ollama and "
        "`ollama pull bge-m3:567m`."
    )
