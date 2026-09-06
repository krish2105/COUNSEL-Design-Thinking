# COUNSEL Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (inline, no subagents — owner's instruction). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up COUNSEL's foundation — a scaffolded repo, a free-only `LLMProvider` chain, a degrading `SearchProvider` chain, and cited trilingual RAG over uploaded documents — so that Phase B's crew has a grounded, tested substrate to debate on.

**Architecture:** A FastAPI service (`services/api`) exposes provider-abstracted inference, search and retrieval to a Next 16 web shell (`apps/web`). Both provider chains follow the same shape: a `Protocol`, N concrete providers ordered by preference, and a deterministic stub as the terminal fallback and the CI substrate — so the entire test suite runs with no model and no network. Persistence is SQLite + sqlite-vec, one file, no server. Every piece of external text (uploaded document, search result) enters through one untrusted-content boundary and carries a `trust` tag for its whole life.

**Tech Stack:** Python 3.13 · uv · FastAPI · pydantic v2 · sqlite-vec · rank-bm25 · fastembed(ONNX) · Ollama(`bge-m3:567m`, `qwen3:8b`) · pytest · ruff — Next 16 · React 19 · Tailwind v4 · next-themes · Playwright · npm.

## Global Constraints

- **Zero paid inference.** Provider order is Ollama → Gemini(free) → Groq(free) → Anthropic(**present but hard-off**) → Stub. Anthropic must be unselectable even when `ANTHROPIC_API_KEY` is set; this is enforced by a test, not by config.
- **Quotas are request counts, not tokens.** Per provider, per session, persisted. Exhaustion degrades to the next provider; it never raises to the caller.
- **Only free, licensed data.** Every source recorded in `docs/datasets.md` with URL, retrieval date and licence. Inaccessible source ⇒ use the named fallback and say so in that file.
- **Every number in any document traces to `docs/results/`.** No figure is typed by hand.
- **No agent has side-effect tools.** Nothing is ever published or executed externally.
- **`trust` is not optional.** `SearchResult` and any chunk from an uploaded document cannot be constructed without `trust="untrusted"`.
- **Embedding model is `bge-m3:567m`, 1024-dim**, decided by the A5 spike and reproducible by script.
- **Tests green per task; one conventional commit per task** ending with:
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- **Placeholder scan must be empty** before any Term 4 artefact is generated.
- Contrast floors: text ≥ 4.5:1, UI borders ≥ 3:1, **in both colour registers**.

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `services/api/core/llm.py` | `LLMProvider` protocol, 5 providers, `LLMChain`, `LLMResponse` provenance |
| `services/api/core/search.py` | `SearchProvider` protocol, 4 providers, `SearchChain`, `SearchResult` |
| `services/api/core/quota.py` | Request-count budgets, persisted, shared by both chains |
| `services/api/core/killswitch.py` | Global refuse-all latch |
| `services/api/core/rbac.py` | `Role`, `Scope`, scope sets, `require()` |
| `services/api/core/db.py` | SQLite + sqlite-vec connection, schema, migrations |
| `services/api/rag/untrusted.py` | The one boundary: wrap + scan external text |
| `services/api/rag/ingest.py` | File → chunks with exact char spans → embeddings → DB |
| `services/api/rag/embed.py` | Ollama and fastembed backends behind one interface |
| `services/api/rag/retrieve.py` | BM25 + vector, RRF fusion |
| `services/api/rag/citations.py` | `Citation`, `require_citations()` verbatim gate |
| `services/api/main.py` | FastAPI app, routers, `/healthz` |
| `apps/web/styles/tokens.css` | Ink-and-vellum tokens, five mandate hues |
| `apps/web/scripts/check-contrast.mjs` | Contrast gate over the tokens |
| `scripts/spike_embeddings.py` | Regenerates the A5 model decision |
| `scripts/placeholder_scan.py` | Fails on TBD/TODO/lorem/XXX in docs + README |
| `docker-compose.searxng.yml` | Local SearXNG with JSON format enabled |

---

## Task A1: Repo scaffold and the green bar

**Files:** Create `pyproject.toml`, `Makefile`, `.gitignore`, `.env.example`, `README.md`, `tests/test_smoke.py`, `apps/web/package.json`, `apps/web/tsconfig.json`.

**Interfaces:**
- Consumes: nothing.
- Produces: `make check` — the single green bar every later task must keep passing. Package root is `services`, importable as `services.api.*`. `pytest` runs from repo root with `pythonpath = ["services", "."]`.

- [ ] **Step 1:** Rename `master` → `main`; write `pyproject.toml` pinning `requires-python = ">=3.13,<3.14"` with deps `fastapi, uvicorn[standard], pydantic>=2.9, pydantic-settings, httpx, sse-starlette, sqlite-vec, rank-bm25, pypdf, python-docx, numpy, jinja2` and dev deps `pytest, pytest-asyncio, ruff`.
- [ ] **Step 2:** Write `tests/test_smoke.py::test_package_imports` asserting `import services.api` succeeds.
- [ ] **Step 3:** Run `uv run pytest -q` — expect FAIL (no package).
- [ ] **Step 4:** Create `services/api/__init__.py`; rerun — expect PASS.
- [ ] **Step 5:** Scaffold `apps/web` (Next 16, React 19, Tailwind v4, next-themes) and add `Makefile` target `check` = ruff + pytest + typecheck.
- [ ] **Step 6:** Commit `chore: scaffold repo, toolchain and green bar`.

**Verifiable check:** `make check` exits 0.

---

## Task A2: Ink-and-vellum tokens with a measured contrast gate

**Files:** Create `apps/web/styles/tokens.css`, `apps/web/scripts/check-contrast.mjs`, `docs/results/A2-contrast.json`.

**Interfaces:**
- Produces: CSS custom properties consumed by every later component — `--bg --surface --surface-raised --border --border-strong --text --text-muted --text-faint`, and the five mandate hues `--seat-cfo --seat-cmo --seat-coo --seat-ethics --seat-devil` plus `--seat-*-text` variants. Two registers selected by `:root[data-theme="dark"]` / `[data-theme="light"]`.

- [ ] **Step 1:** Author both registers in OKLCH. Dark = deep ink blue-black; light = cool bone/vellum. Mandate hues are the only chroma in the app.
- [ ] **Step 2:** Write `check-contrast.mjs`: parse the OKLCH values, convert to sRGB, compute WCAG contrast, assert text ≥ 4.5:1 and borders ≥ 3:1 **in both registers**, write every measured ratio to `docs/results/A2-contrast.json`.
- [ ] **Step 3:** Run it — expect FAIL on at least one value, then raise that value until measured, not guessed.
- [ ] **Step 4:** Rerun — expect PASS.
- [ ] **Step 5:** Commit `feat(web): ink-and-vellum tokens with measured contrast gate`.

**Verifiable check:** `node apps/web/scripts/check-contrast.mjs` exits 0 and `docs/results/A2-contrast.json` lists a ratio for every token pair.

---

## Task A3: The LLMProvider chain

**Files:** Create `services/api/core/llm.py`, `services/api/core/quota.py`, `tests/core/test_llm.py`, `tests/core/test_quota.py`.

**Interfaces:**
- Consumes: `Quota` from `quota.py`.
- Produces — later tasks import exactly these:

```python
Role = Literal["system", "user", "assistant"]

@dataclass(frozen=True)
class Message:
    role: Role
    content: str

@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str          # "ollama" | "gemini" | "groq" | "stub"
    model: str
    speaker: str | None    # mandate id; seam for per-agent voice
    latency_s: float
    degraded_from: tuple[str, ...]   # providers skipped, in order

class LLMProvider(Protocol):
    name: str
    model: str
    def available(self) -> bool: ...
    def complete(self, system: str, messages: list[Message], *,
                 max_tokens: int = 512, temperature: float = 0.0,
                 speaker: str | None = None) -> LLMResponse: ...

class LLMChain:
    def __init__(self, providers: list[LLMProvider], quota: Quota) -> None: ...
    def complete(self, ...) -> LLMResponse: ...   # never raises on provider failure
```

- [ ] **Step 1:** Write `tests/core/test_llm.py` with five failing tests: (a) chain falls through Ollama→Gemini→Groq on injected failure and records `degraded_from`; (b) `AnthropicProvider.available()` is `False` even with `ANTHROPIC_API_KEY` set; (c) quota exhaustion on a provider skips it rather than raising; (d) `StubProvider` returns byte-identical text for identical input across two constructions; (e) every response carries a non-empty `provider` and `model`.
- [ ] **Step 2:** Run — expect FAIL (module missing).
- [ ] **Step 3:** Implement `quota.py` (`Quota.consume(provider) -> bool`, request counts, persisted to SQLite) then `llm.py` with all five providers. `StubProvider` derives output deterministically from a sha256 of `(system, messages)` — schema-valid, never canned.
- [ ] **Step 4:** Run — expect PASS.
- [ ] **Step 5:** Commit `feat(api): free-only LLM provider chain with request quotas`.

**Verifiable check:** `uv run pytest tests/core/test_llm.py -q` green, including the Anthropic-never-selected test.

---

## Task A4: The SearchProvider chain

**Files:** Create `services/api/core/search.py`, `docker-compose.searxng.yml`, `searxng/settings.yml`, `tests/core/test_search.py`, `tests/fixtures/search/*.json`, `scripts/search_smoke.py`.

**Interfaces:**
- Produces:

```python
@dataclass(frozen=True)
class SearchResult:
    url: str
    title: str
    snippet: str
    retrieved_at: str            # ISO 8601 UTC
    provider: str
    trust: Literal["untrusted"]  # only legal value; no default that can be overridden

class SearchProvider(Protocol):
    name: str
    def available(self) -> bool: ...
    def search(self, query: str, *, limit: int = 8) -> list[SearchResult]: ...

class SearchChain:
    def __init__(self, providers: list[SearchProvider]) -> None: ...
    def search(self, query: str, *, limit: int = 8) -> list[SearchResult]: ...
```

Providers in order: `SearxngProvider` (local `:8888`, `format=json`), `KeylessProvider` (Wikipedia Action API + DuckDuckGo Instant Answer — both verified 200 on 2026-09-07), `UserLinksProvider` (fetches URLs the user pasted), `StubSearchProvider` (fixtures).

- [ ] **Step 1:** Write `tests/core/test_search.py`: (a) chain degrades SearXNG→keyless→links→stub in that order under injected unavailability; (b) `SearchResult(trust="trusted")` raises `ValueError`; (c) every result from every provider has `retrieved_at` and a resolvable `url`; (d) fixtures replay identically.
- [ ] **Step 2:** Run — expect FAIL.
- [ ] **Step 3:** Implement `search.py`; write `docker-compose.searxng.yml` with `search.formats: [html, json]` and a generated `secret_key`.
- [ ] **Step 4:** Run — expect PASS.
- [ ] **Step 5:** Run `uv run python scripts/search_smoke.py`, writing `docs/results/A4-search-smoke.json` recording which tier actually served each query today.
- [ ] **Step 6:** Commit `feat(api): degrading search provider chain, SearXNG first`.

**Verifiable check:** `uv run pytest tests/core/test_search.py -q` green **and** `docs/results/A4-search-smoke.json` names the serving tier per query.

---

## Task A5: Embedding decision, made reproducible

**Files:** Create `scripts/spike_embeddings.py`, `services/api/rag/embed.py`, `docs/models.md`, `docs/results/A5-embedding-spike.json`, `tests/rag/test_embed.py`.

**Interfaces:**
```python
class Embedder(Protocol):
    model: str
    dim: int
    def embed(self, texts: list[str]) -> list[list[float]]: ...

class OllamaEmbedder(Embedder): ...   # local dev, http://localhost:11434/api/embed
class FastEmbedEmbedder(Embedder): ...# deployed, ONNX, no Ollama needed
def get_embedder() -> Embedder: ...   # Ollama if reachable, else fastembed
```

- [ ] **Step 1:** Write `scripts/spike_embeddings.py` to embed one sentence in EN/HI/AR plus an unrelated English control under both `bge-m3:567m` and `nomic-embed-text`, and **assert** bge-m3 beats its control by ≥ 0.25 on both cross-lingual pairs while nomic-embed-text fails that bar.
- [ ] **Step 2:** Run it; write measured values to `docs/results/A5-embedding-spike.json`.
- [ ] **Step 3:** Write `docs/models.md` recording the decision, the numbers, the date, and *why* nomic-embed-text is disqualified (its cross-lingual similarity is below its own unrelated-pair score).
- [ ] **Step 4:** Implement `embed.py` with both backends; test that both report `dim == 1024` and agree within tolerance on a fixed sentence.
- [ ] **Step 5:** Commit `feat(rag): choose bge-m3 for trilingual retrieval, with reproducible spike`.

**Verifiable check:** `uv run python scripts/spike_embeddings.py` exits 0 and regenerates the JSON.

---

## Task A6: Document ingestion with exact spans

**Files:** Create `services/api/rag/ingest.py`, `services/api/core/db.py`, `tests/rag/test_ingest.py`, `tests/fixtures/docs/*`.

**Interfaces:**
```python
@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    start: int          # char offset into the document's extracted text
    end: int
    lang: str           # "en" | "hi" | "ar" | "und"
    trust: Literal["untrusted"]

def ingest(path: Path, *, conn) -> tuple[str, list[Chunk]]:  # (doc_id, chunks)
def document_text(doc_id: str, *, conn) -> str
```
`doc_id` is the sha256 of the file bytes, which is what makes re-ingest idempotent.

- [ ] **Step 1:** Write `tests/rag/test_ingest.py`: (a) a fixture PDF ingests to ≥ 1 chunk; (b) **for every chunk, `document_text(doc_id)[c.start:c.end] == c.text`**; (c) ingesting the same file twice yields the same `doc_id` and does not duplicate rows; (d) every chunk has `trust == "untrusted"`.
- [ ] **Step 2:** Run — expect FAIL.
- [ ] **Step 3:** Implement `db.py` (schema: `documents`, `chunks`, `embeddings` via `vec0`, `quotas`) and `ingest.py` for PDF/DOCX/TXT/MD. Chunking is offset-preserving: split on paragraph boundaries with overlap, tracking offsets, never re-joining normalised text.
- [ ] **Step 4:** Run — expect PASS.
- [ ] **Step 5:** Commit `feat(rag): offset-preserving ingestion into sqlite-vec`.

**Verifiable check:** the span round-trip test — every chunk resolves to a verbatim slice of its source.

---

## Task A7: Hybrid retrieval and the citation contract

**Files:** Create `services/api/rag/retrieve.py`, `services/api/rag/citations.py`, `tests/rag/test_retrieve.py`, `tests/rag/test_citations.py`.

**Interfaces:**
```python
@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float
    rank_bm25: int | None
    rank_vec: int | None

def retrieve(query: str, *, conn, limit: int = 8) -> list[Hit]   # RRF fusion, k=60

@dataclass(frozen=True)
class Citation:
    doc_id: str
    start: int
    end: int
    quote: str

class UncitedClaim(ValueError): ...
def require_citations(claim: str, citations: list[Citation], *, conn) -> None
```
`require_citations` raises `UncitedClaim` if the list is empty **or** if any `quote` is not a verbatim substring of `document_text(doc_id)[start:end]`.

- [ ] **Step 1:** Write both test files. The retrieval test ingests the same sentence in EN, HI and AR as three documents and asserts an English query returns the Hindi and Arabic chunks in the top 3 — the A5 spike numbers turned into a permanent regression. The citation test asserts a doctored quote raises `UncitedClaim`.
- [ ] **Step 2:** Run — expect FAIL.
- [ ] **Step 3:** Implement BM25 (`rank_bm25`) + vector search, fuse with Reciprocal Rank Fusion, then `citations.py`.
- [ ] **Step 4:** Run — expect PASS.
- [ ] **Step 5:** Commit `feat(rag): hybrid retrieval with a verbatim citation gate`.

**Verifiable check:** the trilingual top-3 test and the doctored-quote rejection both pass.

---

## Task A8: The untrusted-content boundary

**Files:** Create `services/api/rag/untrusted.py`, `tests/invariants/test_injection.py`, `tests/fixtures/injection/*.txt`.

**Interfaces:**
```python
@dataclass(frozen=True)
class Finding:
    pattern: str
    span: tuple[int, int]
    severity: Literal["high", "medium"]

def scan(text: str) -> list[Finding]      # public seam — Phase E attacks this directly
def wrap(text: str, *, source: str) -> str  # fences content in <untrusted_content source=...>
```

- [ ] **Step 1:** Write `tests/invariants/test_injection.py`: five seeded payloads (instruction override, role reassignment, fence escape, system-prompt exfiltration, tool-invocation attempt) must all produce a `high` finding; **and** a legitimate governance document containing the sentence "Override requires written approval from the board." must produce **no** finding.
- [ ] **Step 2:** Run — expect FAIL.
- [ ] **Step 3:** Implement `scan` with intent-shaped patterns (imperative + directed-at-the-model), not bare keyword matching — that is what makes the false-positive test passable.
- [ ] **Step 4:** Run — expect PASS.
- [ ] **Step 5:** Wire `ingest` and `SearchChain` to call `wrap`/`scan` so no external text reaches a prompt unfenced. Commit `feat(security): single untrusted-content boundary with injection scan`.

**Verifiable check:** 5/5 payloads flagged, 0 false positives on the "override" document.

---

## Task A9: FastAPI skeleton, RBAC, budgets, kill switch

**Files:** Create `services/api/main.py`, `services/api/core/rbac.py`, `services/api/core/killswitch.py`, `services/api/routers/{health,documents,search}.py`, `tests/invariants/test_rbac.py`, `tests/api/test_health.py`.

**Interfaces:**
```python
class Role(StrEnum): VIEWER; ANALYST; ADMIN
class Scope(StrEnum): READ; SESSION_WRITE; ADMIN_WRITE
ROLE_SCOPES: dict[Role, frozenset[Scope]]
def require(scope: Scope): ...            # FastAPI dependency

def engaged() -> bool
def engage(reason: str) -> None
class KillSwitchEngaged(RuntimeError): ...
```
`GET /healthz` returns `{providers: [{name, available, quota_remaining}], embedder, killswitch, db}`.
Responses stream as SSE where a Phase C debate will stream — the shape is set now so the Chair-interjection feature is not a rewrite.

- [ ] **Step 1:** Write the RBAC and health tests: Viewer gets 403 on `POST /sessions`; Analyst succeeds; **kill switch engaged ⇒ the very next `LLMChain.complete` raises `KillSwitchEngaged` before any provider is touched**; `/healthz` names the active provider and remaining quota.
- [ ] **Step 2:** Run — expect FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run — expect PASS.
- [ ] **Step 5:** Commit `feat(api): RBAC, session budgets and kill switch`.

**Verifiable check:** `uv run pytest tests/invariants tests/api -q` green.

---

## Task A10: The web shell — Chamber and Record

**Files:** Create `apps/web/app/{layout.tsx,page.tsx}`, `apps/web/app/(record)/{documents,ask}/page.tsx`, `apps/web/components/{Rail.tsx,ThemeToggle.tsx,LangToggle.tsx,Upload.tsx}`, `apps/web/lib/i18n.ts`, `apps/web/e2e/shell.spec.ts`.

**Interfaces:**
- Consumes: `GET /healthz`, `POST /documents`, `GET /documents`, `POST /search` from A4/A6/A9.
- Produces: the tab shell and the **dissent margin** rail component (`Rail.tsx`) that Phase D's memo and transcript both render into.

- [ ] **Step 1:** Write `e2e/shell.spec.ts`: upload a fixture document and assert its chunk count renders; switch to Arabic and assert `document.documentElement.dir === "rtl"` **and `scrollWidth <= clientWidth`** (no horizontal overflow); assert axe reports zero critical violations.
- [ ] **Step 2:** Run — expect FAIL.
- [ ] **Step 3:** Build the shell. Fraunces (display, WONK raised at display sizes) / Newsreader (body) / IBM Plex Mono (utility), with Noto Naskh Arabic and Noto Serif Devanagari. Theme toggle via next-themes; `prefers-reduced-motion` honoured globally.
- [ ] **Step 4:** Run — expect PASS.
- [ ] **Step 5:** Commit `feat(web): trilingual shell with the dissent-margin rail`.

**Verifiable check:** `npx playwright test` green including the RTL-overflow and axe assertions.

---

## Task A11: Documentation discipline

**Files:** Create `docs/datasets.md`, `docs/models.md` (extend), `scripts/placeholder_scan.py`, `README.md` (Live section), `tests/test_placeholders.py`.

- [ ] **Step 1:** Write `scripts/placeholder_scan.py` scanning `docs/`, `README.md` and `services/api/reports/` for `TBD|TODO|FIXME|lorem|XXX|<placeholder>|\.\.\.$`, exiting non-zero with file:line on any hit.
- [ ] **Step 2:** Run — expect FAIL on the current tree; fix every hit.
- [ ] **Step 3:** Write `docs/datasets.md` with every source verified on 2026-09-07 — URL, date, licence — **and** an explicit "unavailable / fallback used" section for public SearXNG JSON and the absent RAQIB/AQAR house-data exports.
- [ ] **Step 4:** Add `test_placeholders.py` so the scan runs inside `make check`.
- [ ] **Step 5:** Commit `docs: dataset provenance, model decisions and placeholder gate`.

**Verifiable check:** `uv run python scripts/placeholder_scan.py` exits 0.

---

## Task A12: Phase A deploy — **STOP GATE**

**Files:** Create `render.yaml`, `apps/web/vercel.json`, `.github/workflows/check.yml`.

- [ ] **Step 1:** Write `render.yaml` (Python web service, persistent disk mounted at `/data` for the SQLite file, `fastembed` embedder in cloud mode) and `vercel.json`.
- [ ] **Step 2:** Verify `make check` green on a clean clone.
- [ ] **Step 3:** **STOP.** Hand the owner: the exact Render and Vercel clicks, where to paste `GEMINI_API_KEY` and `GROQ_API_KEY`, and the `gh repo create` command. Take no account action unattended.
- [ ] **Step 4:** After the owner confirms, update the README **Live** section with both URLs and write `docs/results/A12-deploy.json` recording the deployed commit sha and the `/healthz` payload.
- [ ] **Step 5:** Commit `chore: phase A deploy configuration and live links`.

**Verifiable check:** the live URL renders the shell in all three languages and `/healthz` names a live provider.

---

## Self-Review

**Spec coverage.** Master plan §3.7 Phase A is "Scaffold, `LLMProvider`, search backend, document upload + RAG" — covered by A1/A3/A4/A6+A7. The shared header adds: EN/HI/AR + RTL (A10), theme toggle (A2/A10), responsive (A10), RBAC (A9), `docs/results/` traceability (A2/A4/A5/A11/A12), embedding spike in `docs/models.md` (A5), placeholder scan (A11). The 3D centrepiece, OWASP harness and Term 4 artefacts are Phases D/E by the master plan's own sequencing; A8 and A9 lay their seams deliberately.

**Placeholder scan.** No TBD/TODO/"similar to Task N" in this plan; every interface block gives concrete names and types.

**Type consistency.** `Chunk` is defined once in A6 and consumed unchanged by A7's `Hit`. `trust: Literal["untrusted"]` is identical in `SearchResult` (A4) and `Chunk` (A6). `document_text(doc_id, *, conn)` is defined in A6 and used by A7's `require_citations`. `Embedder.dim == 1024` in A5 matches the `vec0` column width in A6's schema.
