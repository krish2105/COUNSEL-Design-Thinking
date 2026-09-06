"""Live web search, degrading rather than failing.

WHY A CHAIN AND NOT A CLIENT
----------------------------
The master plan specified SearXNG, self-hosted or public. On 2026-09-07 every
public instance tested — searx.be, searxng.site, priv.au, baresearch.org,
search.inetol.net — refused the JSON API with HTML, 403 or 429. Public SearXNG
is no longer an API; it is a website. A self-hosted instance still works and is
the best tier, but it depends on a Docker daemon the owner may not have running
during a viva, and a demo that dies because Docker is asleep is not a demo.

So search has the same shape as inference: ordered tiers, each recording why it
was passed over.

  SearxngProvider    local Docker, JSON enabled. Best breadth. Optional.
  KeylessProvider    Wikipedia Action API + DuckDuckGo Instant Answer. Both are
                     documented, keyless, licensed APIs — not scraped HTML —
                     which is why they are here and Mojeek/DDG-lite are not.
  UserLinksProvider  URLs the user pasted. Narrow, but it is exactly what a
                     board does when it says "read this before the meeting".
  StubSearchProvider fixtures. The CI tier, and the tier a recorded demo uses.

EVERY RESULT IS UNTRUSTED. A SearchResult cannot be constructed otherwise; see
__post_init__. That is deliberate: the alternative is a default that a call site
can override, and a boundary with an override is not a boundary.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol, runtime_checkable

import httpx

Trust = Literal["untrusted"]

# Wikimedia's robot policy refuses a generic client: httpx's default agent gets
# a 403 with a pointer to the policy (verified 2026-09-07). Identifying the
# project and giving a contact route is both the fix and the correct etiquette
# for any tool that reads someone else's server. The contact is the repository,
# deliberately not a personal address.
USER_AGENT = (
    "COUNSEL/0.1 (SP Jain MAIB Term 4 coursework; "
    "+https://github.com/krish2105/COUNSEL-Design-Thinking)"
)
HEADERS = {"User-Agent": USER_AGENT}


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class SearchResult:
    url: str
    title: str
    snippet: str
    retrieved_at: str
    provider: str
    trust: Trust = "untrusted"

    def __post_init__(self) -> None:
        # Enforced at runtime, not only in the type checker: the whole point is
        # that no call site anywhere can mint a trusted result.
        if self.trust != "untrusted":
            raise ValueError(
                f"a search result is always untrusted; got trust={self.trust!r}. "
                "Content fetched from the open web is data, never instruction."
            )


@runtime_checkable
class SearchProvider(Protocol):
    name: str

    def available(self) -> bool: ...

    def search(self, query: str, *, limit: int = 8) -> list[SearchResult]: ...


# ── Tier 1: self-hosted SearXNG ─────────────────────────────────────────────


class SearxngProvider:
    name = "searxng"

    def __init__(self, url: str | None = None, timeout: float = 12.0) -> None:
        self.url = (url or os.getenv("SEARXNG_URL") or "http://localhost:8888").rstrip("/")
        self.timeout = timeout

    def available(self) -> bool:
        try:
            r = httpx.get(f"{self.url}/healthz", timeout=2.0, headers=HEADERS)
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    def search(self, query, *, limit=8):
        r = httpx.get(
            f"{self.url}/search",
            params={"q": query, "format": "json", "safesearch": 1},
            timeout=self.timeout,
            headers=HEADERS,
        )
        r.raise_for_status()
        at = _now()
        return [
            SearchResult(
                url=item.get("url", ""),
                title=item.get("title", ""),
                snippet=item.get("content", ""),
                retrieved_at=at,
                provider=self.name,
            )
            for item in r.json().get("results", [])[:limit]
            if item.get("url")
        ]


# ── Tier 2: keyless, documented, licensed APIs ──────────────────────────────


class KeylessProvider:
    """OpenAlex (CC0) + Wikipedia Action API (CC BY-SA 4.0) + DuckDuckGo Instant Answer.

    All three are published APIs with stable contracts and no key. Deliberately
    NOT included: DuckDuckGo's HTML/lite endpoints and Mojeek, which would mean
    scraping a site's front end against its terms — a licence problem COUNSEL
    will not take on in a project whose entire claim is provenance.

    OpenAlex leads because of what this tier is for. Wikipedia answers "what is
    a hypermarket"; it returns nothing at all for "hypermarket footfall
    analytics pilot" (verified 2026-09-07). OpenAlex returns peer-reviewed work
    on exactly that, with a DOI — which is the kind of evidence a board paper
    can actually stand on. Sources are merged rather than raced, because their
    coverage barely overlaps.
    """

    name = "keyless"
    OPENALEX = "https://api.openalex.org/works"
    WIKI = "https://en.wikipedia.org/w/api.php"
    DDG = "https://api.duckduckgo.com/"

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout

    def available(self) -> bool:
        try:
            r = httpx.get(
                self.WIKI,
                params={"action": "query", "format": "json"},
                timeout=3.0,
                headers=HEADERS,
            )
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    def search(self, query, *, limit=8):
        at = _now()
        out: list[SearchResult] = []

        try:
            r = httpx.get(
                self.OPENALEX,
                params={"search": query, "per-page": limit},
                timeout=self.timeout,
                headers=HEADERS,
            )
            r.raise_for_status()
            for work in r.json().get("results", []):
                url = work.get("doi") or work.get("id")
                if not url:
                    continue
                year = work.get("publication_year")
                venue = (work.get("primary_location") or {}).get("source") or {}
                out.append(
                    SearchResult(
                        url=url,
                        title=work.get("display_name") or url,
                        snippet=_openalex_abstract(work)
                        or f"{venue.get('display_name', 'unknown venue')}, {year}. "
                        f"Cited {work.get('cited_by_count', 0)} times.",
                        retrieved_at=at,
                        provider=f"{self.name}:openalex",
                    )
                )
        except (httpx.HTTPError, KeyError, ValueError):
            pass

        try:
            r = httpx.get(
                self.WIKI,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": limit,
                    "format": "json",
                },
                timeout=self.timeout,
                headers=HEADERS,
            )
            r.raise_for_status()
            for hit in r.json().get("query", {}).get("search", [])[: max(1, limit // 2)]:
                title = hit["title"]
                out.append(
                    SearchResult(
                        url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                        title=title,
                        snippet=_strip_tags(hit.get("snippet", "")),
                        retrieved_at=at,
                        provider=f"{self.name}:wikipedia",
                    )
                )
        except (httpx.HTTPError, KeyError, ValueError):
            pass

        if len(out) < limit:
            try:
                r = httpx.get(
                    self.DDG,
                    params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
                    timeout=self.timeout,
                    headers=HEADERS,
                )
                r.raise_for_status()
                data = r.json()
                if data.get("AbstractURL") and data.get("AbstractText"):
                    out.append(
                        SearchResult(
                            url=data["AbstractURL"],
                            title=data.get("Heading") or query,
                            snippet=data["AbstractText"],
                            retrieved_at=at,
                            provider=f"{self.name}:duckduckgo",
                        )
                    )
            except (httpx.HTTPError, ValueError):
                pass

        seen: set[str] = set()
        deduped = [r for r in out if not (r.url in seen or seen.add(r.url))]
        return deduped[:limit]


def _openalex_abstract(work: dict) -> str:
    """Rebuild an abstract from OpenAlex's inverted index.

    OpenAlex ships abstracts as {token: [positions]} rather than as text, for
    copyright reasons. Reconstructing it is expected use, not a workaround.
    """
    index = work.get("abstract_inverted_index")
    if not index:
        return ""
    positions: list[tuple[int, str]] = [
        (pos, token) for token, spots in index.items() for pos in spots
    ]
    positions.sort()
    return " ".join(token for _, token in positions)[:900]


def _strip_tags(text: str) -> str:
    out, depth = [], 0
    for ch in text:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return "".join(out).strip()


# ── Tier 3: what the user put on the table ──────────────────────────────────


class UserLinksProvider:
    name = "user_links"

    def __init__(self, links: list[str] | None = None, timeout: float = 15.0) -> None:
        self._links = list(links or [])
        self.timeout = timeout

    def set_links(self, links: list[str]) -> None:
        self._links = list(links)

    def available(self) -> bool:
        return bool(self._links)

    def search(self, query, *, limit=8):
        at = _now()
        out: list[SearchResult] = []
        for url in self._links[:limit]:
            try:
                r = httpx.get(url, timeout=self.timeout, follow_redirects=True, headers=HEADERS)
                r.raise_for_status()
                body = _strip_tags(r.text)[:1200]
            except httpx.HTTPError as exc:
                body = f"could not be fetched: {type(exc).__name__}"
            out.append(
                SearchResult(url=url, title=url, snippet=body, retrieved_at=at, provider=self.name)
            )
        return out


# ── Tier 4: the CI substrate ────────────────────────────────────────────────


class StubSearchProvider:
    """Deterministic results derived from the query.

    Like StubProvider on the inference side, this is not canned text: the same
    query always yields the same synthetic corpus, so replay and citation tests
    mean something, and every snippet says plainly that it is stub output so it
    can never be mistaken for a real source in a transcript.
    """

    name = "stub"

    def available(self) -> bool:
        return True

    def search(self, query, *, limit=8):
        at = _now()
        digest = hashlib.sha256(query.encode()).hexdigest()
        return [
            SearchResult(
                url=f"https://stub.invalid/{digest[i * 8 : i * 8 + 8]}",
                title=f"Stub source {i + 1} for {query!r}",
                snippet=(
                    f"[stub:{digest[i * 8 : i * 8 + 8]}] Deterministic placeholder evidence for "
                    f"{query!r}. Generated offline by the stub search tier; it is not a real source "
                    "and must not be cited as one."
                ),
                retrieved_at=at,
                provider=self.name,
            )
            for i in range(min(limit, 4))
        ]


# ── The chain ───────────────────────────────────────────────────────────────


class SearchChain:
    def __init__(self, providers: list[SearchProvider]) -> None:
        if not providers or providers[-1].name != "stub":
            providers = [*providers, StubSearchProvider()]
        self.providers = providers
        self.last_degraded_from: tuple[str, ...] = ()

    def search(self, query: str, *, limit: int = 8) -> list[SearchResult]:
        skipped: list[str] = []
        for provider in self.providers:
            if not provider.available():
                skipped.append(f"{provider.name}(unreachable)")
                continue
            try:
                results = provider.search(query, limit=limit)
            except Exception as exc:  # noqa: BLE001 — degrade on anything a tier does
                skipped.append(f"{provider.name}({type(exc).__name__})")
                continue
            if not results:
                skipped.append(f"{provider.name}(no results)")
                continue
            self.last_degraded_from = tuple(skipped)
            return results[:limit]

        self.last_degraded_from = tuple(skipped)
        return []

    def health(self) -> list[dict[str, object]]:
        return [{"name": p.name, "available": p.available()} for p in self.providers]
