"""The embedder is the one place a wrong answer looks like a right one.

A retrieval that returns the wrong chunk still returns a chunk, with a citation
attached, and nothing downstream can tell. So these tests pin the property the
A5 spike measured, and they pin the thing that would silently break it: two
models with different vector spaces being compared to each other.
"""

from __future__ import annotations

import math

import pytest

from services.api.rag.embed import (
    FastEmbedEmbedder,
    OllamaEmbedder,
    get_embedder,
    model_key,
)

EN = "The CFO objected that the hypermarket pilot has a longer payback period."
HI = "सीएफओ ने आपत्ति जताई कि हाइपरमार्केट पायलट की भुगतान अवधि लंबी है।"
CONTROL = "The marketing team prefers bright packaging for summer drinks."


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(x * x for x in b)))


def test_an_embedder_is_always_available_in_this_environment():
    e = get_embedder()
    assert e.available()
    assert e.dim > 0 and e.max_tokens > 0


def test_vectors_have_the_declared_width():
    e = get_embedder()
    [v] = e.embed([EN])
    assert len(v) == e.dim, "a declared dim that does not match the vector corrupts the index"


def test_embedding_is_deterministic():
    e = get_embedder()
    a, b = e.embed([EN])[0], e.embed([EN])[0]
    assert cosine(a, b) > 0.9999


def test_the_active_embedder_still_clears_the_trilingual_margin():
    """The A5 spike, frozen as a regression.

    If someone swaps the model and this drops, retrieval starts ranking an
    unrelated English chunk above the correct Hindi one — and answers it with
    a citation, which is worse than failing.
    """
    e = get_embedder()
    en, hi, control = e.embed([EN, HI, CONTROL])
    assert cosine(en, hi) - cosine(en, control) >= 0.25


def test_model_key_distinguishes_incompatible_spaces():
    assert model_key(OllamaEmbedder()) != model_key(FastEmbedEmbedder())
    assert "1024" in model_key(OllamaEmbedder())
    assert "384" in model_key(FastEmbedEmbedder())


def test_empty_input_does_not_call_the_model():
    assert get_embedder().embed([]) == []


@pytest.mark.parametrize("kind", ["query", "passage"])
def test_both_kinds_are_accepted(kind):
    assert len(get_embedder().embed([EN], kind=kind)) == 1


def test_gemini_is_unavailable_without_a_key(monkeypatch):
    from services.api.rag.embed import GeminiEmbedder

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert GeminiEmbedder(api_key="").available() is False
    assert GeminiEmbedder(api_key="a-key").available() is True


def test_the_chain_prefers_ollama_then_gemini_then_fastembed():
    from services.api.rag.embed import EmbedderChain, GeminiEmbedder

    class Absent:
        name, model, dim, max_tokens = "absent", "none", 1, 1

        def available(self):
            return False

        def embed(self, texts, *, kind="passage"):
            raise AssertionError("an unavailable embedder must never be called")

    gemini = GeminiEmbedder(api_key="present")
    assert EmbedderChain([Absent(), gemini, FastEmbedEmbedder()]).resolve() is gemini
    assert isinstance(
        EmbedderChain([Absent(), GeminiEmbedder(api_key=""), FastEmbedEmbedder()]).resolve(),
        FastEmbedEmbedder,
    )


def test_the_chain_resolves_once_and_does_not_drift():
    """Failing over mid-corpus would split the vector space, leaving half the
    documents unreachable from any query with no error anywhere."""
    from services.api.rag.embed import EmbedderChain

    chain = EmbedderChain()
    first = chain.resolve()
    assert chain.resolve() is first, "the resolved embedder must be stable for the process"


def test_the_chain_names_every_candidate_for_healthz():
    from services.api.rag.embed import EmbedderChain

    names = {row["name"] for row in EmbedderChain().health()}
    assert names == {"ollama", "gemini", "fastembed"}


def test_no_embedder_resolves_to_none_rather_than_raising():
    """None is a supported state, not an error. Measured on Render's free tier:
    the in-process ONNX model does not fit in 512 MB and there is no other
    option without a key, so the deployed instance has no embedder at all.
    Raising would have made every upload a 502."""
    from services.api.rag.embed import EmbedderChain

    class Absent:
        name, model, dim, max_tokens = "absent", "none", 1, 1

        def available(self):
            return False

        def embed(self, texts, *, kind="passage"):
            raise AssertionError("an unavailable embedder must never be called")

    assert EmbedderChain([Absent()]).resolve() is None


def test_require_embedder_still_raises_with_instructions():
    """For the callers that genuinely cannot proceed without one."""
    from services.api.rag import embed as embed_mod

    original = embed_mod.get_embedder
    try:
        embed_mod.get_embedder = lambda: None
        with pytest.raises(RuntimeError, match="ollama pull bge-m3"):
            embed_mod.require_embedder()
    finally:
        embed_mod.get_embedder = original
