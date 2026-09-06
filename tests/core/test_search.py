"""Search is where untrusted text enters COUNSEL.

Every result is something a stranger wrote, and it is about to be put in front
of five agents that will reason over it. So the type itself refuses to be
trusted: there is no code path that produces a SearchResult without the
untrusted tag, which is what lets Phase E's harness reason about the boundary
instead of auditing every call site.
"""

from __future__ import annotations

import pytest

from services.api.core.search import (
    SearchChain,
    SearchResult,
    StubSearchProvider,
    UserLinksProvider,
)


class DeadProvider:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0

    def available(self) -> bool:
        return False

    def search(self, query, *, limit=8):
        self.calls += 1
        return []


class EmptyProvider:
    """Available, reachable, and returns nothing — a real and common case."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0

    def available(self) -> bool:
        return True

    def search(self, query, *, limit=8):
        self.calls += 1
        return []


def test_a_result_cannot_be_constructed_as_trusted():
    with pytest.raises(ValueError, match="untrusted"):
        SearchResult(
            url="https://example.invalid/a",
            title="t",
            snippet="s",
            retrieved_at="2026-09-07T00:00:00Z",
            provider="searxng",
            trust="trusted",  # type: ignore[arg-type]
        )


def test_the_chain_degrades_in_the_declared_order():
    searxng = DeadProvider("searxng")
    keyless = EmptyProvider("keyless")
    links = DeadProvider("user_links")
    stub = StubSearchProvider()

    chain = SearchChain([searxng, keyless, links, stub])
    results = chain.search("dubai hypermarket footfall")

    assert results, "the stub tier always answers"
    assert all(r.provider == "stub" for r in results)
    assert keyless.calls == 1, "an available provider is called even if it returns nothing"
    assert searxng.calls == 0 and links.calls == 0, "unavailable providers are skipped, not called"
    assert [d.split("(")[0] for d in chain.last_degraded_from] == [
        "searxng",
        "keyless",
        "user_links",
    ]
    assert "unreachable" in chain.last_degraded_from[0]
    assert "no results" in chain.last_degraded_from[1]


def test_every_result_carries_provenance_and_the_untrusted_tag():
    results = SearchChain([StubSearchProvider()]).search("design thinking")
    assert results
    for r in results:
        assert r.trust == "untrusted"
        assert r.url.startswith("http")
        assert r.retrieved_at.endswith("Z"), "retrieval time is recorded in UTC, for the citation"
        assert r.provider


def test_the_stub_replays_identically():
    a = SearchChain([StubSearchProvider()]).search("hypermarket vs plant")
    b = SearchChain([StubSearchProvider()]).search("hypermarket vs plant")
    assert [r.url for r in a] == [r.url for r in b]
    assert [r.snippet for r in a] == [r.snippet for r in b]


def test_user_links_are_unavailable_until_the_user_supplies_some():
    provider = UserLinksProvider([])
    assert provider.available() is False

    provider.set_links(["https://example.invalid/business-plan"])
    assert provider.available() is True


def test_limit_is_respected_by_every_tier():
    results = SearchChain([StubSearchProvider()]).search("q", limit=2)
    assert len(results) <= 2
