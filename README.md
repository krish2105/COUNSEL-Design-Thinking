# COUNSEL

**The AI boardroom.** Five agents with distinct mandates — CFO, CMO, COO, Ethics Officer,
Devil's Advocate — research a real decision with live public data, debate it across the seven
design-thinking stages, and converge on a record: a decision memo, a dissent log, and an
outcome ledger that scores each agent's calibration once reality arrives.

Built for SP Jain MAIB Term 4, MGT 204 Design Thinking. Owner: Krishna Mathur.

## Standing constraints

- **Zero paid inference.** Ollama → Gemini (free) → Groq (free) → deterministic stub.
  Anthropic is wired but hard-off, enforced by a test.
- **Only free, licensed data.** Every source is recorded in [docs/datasets.md](docs/datasets.md)
  with URL, retrieval date and licence.
- **Every number traces to [docs/results/](docs/results/).** No figure is typed by hand.
- **No agent has side-effect tools.** Nothing is published or executed externally. Ever.

## Live

Not yet deployed. Phase A's last task is the first deploy — Vercel for the web app, Render for
the API, SQLite on a Render disk — and this section will then carry both URLs and the commit sha
behind them.

Running locally right now: web on `:3000`, API on `:8000`, inference on local Ollama
(`qwen3:8b`), embeddings on `bge-m3:567m`.

## Running it

```bash
uv sync --extra dev          # Python 3.13
cd apps/web && npm install
make check                   # the green bar: ruff, pytest, contrast, placeholders, typecheck
make api                     # FastAPI on :8000
make web                     # Next on :3000
```

## What is built

Phase A: the substrate the boardroom will run on.

| | |
|---|---|
| **Inference** | Ollama → Gemini (free) → Groq (free) → Anthropic (present, hard-off) → deterministic stub. Each skip recorded with its reason. |
| **Search** | Self-hosted SearXNG → OpenAlex + Wikipedia + DuckDuckGo (keyless) → your links → fixtures. |
| **Retrieval** | BM25 + `bge-m3` vectors, fused by rank, normalised so a translation is not buried under English. |
| **Citations** | A claim is refused unless its quote is verbatim inside the span it cites. |
| **Security** | One untrusted-content boundary. Catches five injection families; clears a real governance policy. |
| **Web** | Trilingual EN/HI/AR with RTL, two colour registers, the dissent-margin rail. |

Phases B–E add the crew, the seven design-thinking stages, the memo and dissent log, the 3D
round table, the outcome ledger, and the OWASP harness.

## Documentation

- [docs/datasets.md](docs/datasets.md) — every source, with licence, verification date and fallback
- [docs/models.md](docs/models.md) — model choices and the spikes that decided them
- [docs/results/](docs/results/) — every measured number the docs cite
- [docs/superpowers/plans/](docs/superpowers/plans/) — the master plan and the Phase A task plan

## Testing

```bash
make check   # ruff, 105 pytest, contrast gate, placeholder scan, typecheck
make e2e     # 8 Playwright tests on desktop and mobile (needs `make api` and `make web`)
```
