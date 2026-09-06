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

Phase B: the crew.

| | |
|---|---|
| **The room** | Five mandates as [readable prompt files](docs/crew.md), each declaring at least two blind spots it under-weights. The loader refuses a mandate that claims none. |
| **Capability** | Declarative grants, and **no tool in COUNSEL has side effects** — asserted over the whole registry, not reviewed by eye. |
| **Rounds** | Deterministic turn-taking in Python; the five seats speak concurrently against the previous round's transcript. A real 3-round debate on `qwen3:8b` takes **126.5 s** against a 240 s target. |
| **The record** | Every turn signed into a hash chain. Editing turn 2 of 5 breaks 2, 3, 4 and 5. `/verify` re-reads the stored rows. |
| **The Auditor** | Four mechanical rules. **5 of 5** real model turns caught fabricating a source. |
| **The Room** | A live tab: open a session, run a round, watch five seats argue, and interject as Chair. Each seat's dissent thickens the margin rule in its own colour; the Auditor's findings sit in the margin beside the words that caused them. |

Phase C: the decision.

| | |
|---|---|
| **Stages** | The seven design-thinking stages as validated artefacts — a framing that must be a question, a score that cannot misreport its own weakest axis. |
| **The memo** | Every body claim resolves to a verbatim span. What fails is recorded under *Asserted without evidence*, never dropped. |
| **What would change our mind** | Executable. Remove one piece of evidence, re-aggregate, report the flip — as arithmetic, and labelled as sensitivity analysis rather than a re-argument. |
| **The ledger** | Brier calibration per seat, refusing to show a score below five outcomes. |

Phases D–E add the 3D round table with replay, the OWASP harness and the Term 4 artefacts.

## Two things a real run changed

**All five seats dissented from the memo's own recommendation.** The scores gave
hypermarket 55 to plant's 51, so the memo recommended the hypermarket — then every seat,
asked individually, disagreed. A 4-point margin across five seats and three axes is inside
the noise. The memo now says so above the ranking table.

**A ~100-second request dies at every gateway.** The same scoring call returns 500 at exactly
30 seconds through a proxy and 200 after 103 seconds direct. Everything long is streamed.

## The finding that shaped Phase B

Given no documents, all five mandates invented sources fluently — a Q3 footfall report, a
Dubai Chamber statistic, a policy clause, a customer quote. None exist. Adding an explicit
*"do not invent a report, a statistic or a citation"* to the prompt was
[measured](docs/results/B7-prompting-does-not-stop-fabrication.json) and did not stop it.

That is why every guarantee in COUNSEL is mechanical rather than prompted. A mandate told to
cite will cite. Only a check that opens the citation knows whether it resolves.

## Documentation

- [docs/datasets.md](docs/datasets.md) — every source, with licence, verification date and fallback
- [docs/models.md](docs/models.md) — model choices and the spikes that decided them
- [docs/crew.md](docs/crew.md) — the mandates, their blind spots, and the Auditor's measured limits
- [docs/decisions.md](docs/decisions.md) — the stages, what the memo guarantees, and what it does not
- [docs/results/](docs/results/) — every measured number the docs cite
- [docs/superpowers/plans/](docs/superpowers/plans/) — the master plan and the Phase A task plan

## Testing

```bash
make check   # ruff, 304 pytest, contrast gate, placeholder scan, typecheck
make e2e     # 40 Playwright tests on desktop and mobile (needs `make api` and `make web`)
```
