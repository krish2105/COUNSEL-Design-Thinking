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

Not yet deployed. Phase A ends with the first deploy; this section will carry the web and API
URLs and the commit sha behind them.

## Running it

```bash
uv sync --extra dev          # Python 3.13
cd apps/web && npm install
make check                   # the green bar: ruff, pytest, contrast, placeholders, typecheck
make api                     # FastAPI on :8000
make web                     # Next on :3000
```

## Documentation

- [docs/datasets.md](docs/datasets.md) — every data source, with licence and fallback
- [docs/models.md](docs/models.md) — model choices and the spikes that decided them
- [docs/results/](docs/results/) — every measured number the docs cite
