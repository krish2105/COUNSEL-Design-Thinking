# Data sources

Every source COUNSEL can read, with the URL, the date it was last verified, its
licence, and — where a source turned out to be unusable — the fallback actually
in use and why.

**Standing rule:** only free, licensed sources. Nothing behind a paywall, a
request form, or a signup. Where a licence requires attribution or a specific
client identity, COUNSEL complies rather than working around it.

**Everything here was verified by running it on 2026-09-07**, not by reading
documentation. Re-verify with `uv run python scripts/search_smoke.py`, which
writes [`docs/results/A4-search-smoke.json`](results/A4-search-smoke.json).

---

## Live web search

COUNSEL searches through an ordered chain of tiers, exactly like its inference
chain. Each tier records why it was passed over, so a session can always show
where its evidence came from.

### Tier 1 — SearXNG, self-hosted · optional

| | |
|---|---|
| Endpoint | `http://localhost:8888/search?format=json` |
| Licence | SearXNG is AGPL-3.0; results carry the licences of the engines behind them |
| Verified | 2026-09-07 — configuration written; requires a running Docker daemon |
| Start it | `export SEARXNG_SECRET=$(openssl rand -hex 32)` then `docker compose -f docker-compose.searxng.yml up -d` |

Best breadth of any tier, and optional by design. See the next section for why
it is not simply required.

### ⚠ Public SearXNG instances — NOT USABLE

The master plan allowed a public SearXNG instance as an alternative to
self-hosting. Tested 2026-09-07, all with `&format=json`:

| Instance | Result |
|---|---|
| `searx.be` | HTTP 200, **HTML** — the JSON format is disabled |
| `searxng.site` | HTTP 403 |
| `priv.au` | HTTP 429 |
| `baresearch.org` | HTTP 200, **HTML** |
| `search.inetol.net` | HTTP 429 |
| `search.bus-hit.me` | no route to host |

**Not one public instance serves the JSON API.** Public SearXNG is a website
now, not an API. **Fallback in use:** self-hosted SearXNG (Tier 1) when Docker
is running, and Tier 2 below whenever it is not — a demo that dies because
Docker is asleep is not a demo.

### Tier 2 — keyless, documented APIs · always available

These are the spine of COUNSEL's research when Docker is not running, and they
are all published APIs with stable contracts. None is scraped.

| Source | Endpoint | Licence | Verified |
|---|---|---|---|
| **OpenAlex** | `https://api.openalex.org/works` | **CC0** | 2026-09-07 — 200, relevant peer-reviewed work with DOIs |
| **Wikipedia Action API** | `https://en.wikipedia.org/w/api.php` | CC BY-SA 4.0 | 2026-09-07 — 200 |
| **DuckDuckGo Instant Answer** | `https://api.duckduckgo.com/` | free, documented, keyless | 2026-09-07 — 200 |

**OpenAlex leads this tier**, which is a change from the master plan and worth
the sentence. Wikipedia answers *what a hypermarket is*; it returns literally
nothing for *"hypermarket footfall analytics pilot"*. OpenAlex returns
peer-reviewed work on exactly that, with a DOI — the kind of evidence a board
paper can stand on. Wikipedia is capped at half the result slots so it cannot
crowd OpenAlex out, and the three are merged rather than raced, because their
coverage barely overlaps.

**Wikimedia's robot policy is complied with, not worked around.** The default
`httpx` user agent receives a 403 with a pointer to the policy. Every outbound
request COUNSEL makes now identifies the project and gives the repository as a
contact route — deliberately not a personal address.

### Deliberately excluded

| Source | Why not |
|---|---|
| DuckDuckGo `lite`/`html` endpoints | Scraping a front end against its terms. Reachable (HTTP 200), and still not used. |
| Mojeek | HTTP 403 to a plain client, and scraping it would be the same problem. |
| Bing / Google / Brave APIs | Require a key, a card, or both. |

A project whose entire claim is provenance does not fund itself by scraping.

### Tier 3 — links the user supplies

URLs pasted into a session, fetched directly. Narrow, and exactly what a board
does when it says "read this before the meeting". Licence is whatever the linked
page carries; COUNSEL records the URL and retrieval time and quotes rather than
republishes.

### Tier 4 — deterministic fixtures

Offline stub results derived from the query hash. This is the CI tier. Every
snippet says in its own text that it is stub output and must not be cited as a
real source, so it cannot be mistaken for evidence in a transcript.

---

## Weather

| | |
|---|---|
| Source | Open-Meteo — `https://api.open-meteo.com/v1/forecast` and `https://archive-api.open-meteo.com/v1/archive` |
| Licence | CC BY 4.0, free for non-commercial use, **no API key** |
| Verified | 2026-09-07 — both returned 200 with valid JSON for Dubai (25.20, 55.27), forecast and historical daily series |

Available to the boardroom as context for any decision with a seasonal or
site-specific dimension.

## Reference and statistical sources

| Source | Endpoint | Licence | Verified |
|---|---|---|---|
| World Bank Indicators | `https://api.worldbank.org/v2/` | CC BY 4.0 | 2026-09-07 — 200, UAE GDP series |
| EUR-Lex (EU AI Act, CELEX 32024R1689) | `https://eur-lex.europa.eu/` | © EU, reuse permitted with attribution | 2026-09-07 — 200 |
| Bayanat.ae — UAE open data | `https://bayanat.ae/` | per-dataset, recorded when a dataset is used | 2026-09-07 — 200 |

## Portals checked and not currently usable

| Portal | Result on 2026-09-07 | Consequence |
|---|---|---|
| Dubai Pulse | no route to host | Not used. No Dubai-specific open dataset is claimed anywhere in COUNSEL. |
| `uaestat.fcsc.gov.ae` | HTTP 403 to a plain client | Not used. |

---

## Documents the user uploads

The main corpus. PDF, DOCX, Markdown and plain text; a business plan, interview
transcripts, a policy. These are the user's own files and carry no external
licence, and COUNSEL never sends them anywhere: ingestion, embedding and
retrieval all happen in the process, and the only network calls the app makes
are to the search tiers above and to whichever inference provider is serving.

**Every uploaded document is treated as untrusted.** It cannot be stored
otherwise — `Chunk` raises on construction if its trust tag is anything but
`untrusted` — and it is scanned at ingest for content that tries to instruct the
model rather than inform it. A document that fails that scan is still ingested
and still retrievable, with its findings recorded: refusing it would let an
attacker delete evidence by poisoning it.

---

## House data from sibling projects — NOT AVAILABLE

The master plan (§3.2) offered "DLD/AQAR and RAQIB exports as optional house
data". **No repository by those names exists** under `~/Desktop/MAIB-Term4/`
(checked 2026-09-07; the siblings present are `MISAR-AI-OPERATIONS`, `dhawq`,
`bidaya`, `hisbah`, `masar`, `rasid` and `spine`).

**Fallback in use:** house data is treated as absent. The seeded demo session
runs on uploaded documents plus live search. No Dubai Land Department extract,
footfall series or property dataset is fabricated to fill the gap, and no claim
anywhere in COUNSEL depends on one.
