# Models

Every model COUNSEL uses, why it was chosen, and the measurement behind the
choice. No number on this page was typed by hand — each one comes from a script
in `scripts/` that writes to `docs/results/`, and each is reproducible on a
laptop with no paid account.

**Standing constraint:** zero paid inference. Every model below is either local
(Ollama, on the owner's machine) or a documented free tier.

---

## Embeddings

**Decision: `bge-m3:567m` locally, `paraphrase-multilingual-MiniLM-L12-v2` when deployed.**

Measured by `scripts/spike_embeddings.py` on 2026-09-07 →
[`docs/results/A5-embedding-spike.json`](results/A5-embedding-spike.json).

### The test

One claim in three languages, plus an unrelated English control:

- **EN** — "The CFO objected that the hypermarket pilot has a longer payback period."
- **HI** — "सीएफओ ने आपत्ति जताई कि हाइपरमार्केट पायलट की भुगतान अवधि लंबी है।"
- **AR** — "اعترض المدير المالي على أن تجربة الهايبرماركت لها فترة استرداد أطول."
- **Control** — "The marketing team prefers bright packaging for summer drinks."

A similarity score in isolation means nothing. What matters is the **margin over
the control**: how much closer a model puts the translation than it puts an
unrelated sentence. The bar is 0.25 on both cross-lingual pairs.

### Results

| Model | Backend | dim | EN~HI | EN~AR | control | margin (HI / AR) | Usable |
|---|---|---:|---:|---:|---:|---:|:--:|
| **bge-m3:567m** | Ollama | 1024 | 0.830 | 0.779 | 0.463 | **+0.367 / +0.316** | yes |
| nomic-embed-text | Ollama | 768 | 0.336 | 0.365 | 0.436 | −0.100 / −0.071 | **no** |
| **paraphrase-multilingual-MiniLM-L12-v2** | fastembed (ONNX) | 384 | 0.773 | 0.741 | 0.079 | **+0.694 / +0.662** | yes |

### What the numbers mean

**`nomic-embed-text` is not merely weaker — it is wrong for this application.**
Its cross-lingual scores sit *below* its own unrelated-pair score. An Arabic
query would rank an unrelated English chunk above the correct Arabic
translation, and COUNSEL would answer it with a citation attached. A confidently
wrong answer with provenance is worse than no answer, so this model is
disqualified rather than deprioritised. `scripts/spike_embeddings.py` fails if it
ever clears the bar, which would mean this page needs revisiting.

**MiniLM's margin is the larger one, and that is not a reason to prefer it
everywhere.** Its context window is 128 tokens against bge-m3's 8192. On a
four-sentence probe that costs nothing; on a page of a business plan it means
chunks an order of magnitude smaller and far more of them. bge-m3 stays the
local model because local is where documents are actually read.

### The spike margin did not predict retrieval quality

Worth recording, because it is the kind of thing a table like the one above
invites you to get wrong. MiniLM has the *larger* margin on the probe, and is
the *weaker* model in actual retrieval. Measured on a 16-chunk corpus for the
query "Why did the CFO object to the payback period?", after the fusion fix:

| Embedder | Hindi | Arabic | unrelated control |
|---|---:|---:|---:|
| bge-m3:567m (local) | **1** | 2 | 9 |
| MiniLM (deployed) | **4** | 1 | 10 |

MiniLM still places both translations well above the control, so it is usable —
but a single sentence pair is not a retrieval benchmark, and the difference only
appeared once both models were run against a real corpus. See
[`docs/results/A7-fusion-crosslingual.json`](results/A7-fusion-crosslingual.json).

`tests/rag/test_retrieve.py` is parametrised over both embedders for this
reason. Before it was, the CI machine had no Ollama, so local runs tested
bge-m3, CI tested MiniLM, and neither tested the other.

### Why there are two at all

The deployed API has no Ollama, so it must embed in-process. Render's free tier
gives **512 MB of RAM**, which rules out `multilingual-e5-large` (1024-dim, MIT,
and a good model) at 2.24 GB, and rules out every other large multilingual
option. MiniLM at 0.22 GB fits. The deployment constraint chose the model, not a
leaderboard.

### The consequence, and how it is contained

Two models means two vector spaces. Cosine similarity between them is noise that
looks like a score. So:

- every stored vector is tagged with `model_key = backend:model:dim`;
- retrieval refuses to compare vectors across spaces and degrades to BM25-only
  rather than returning plausible neighbours from the wrong space;
- chunk size is read from the active embedder's `max_tokens`, not hard-coded.

Checked by `tests/rag/test_embed.py::test_model_key_distinguishes_incompatible_spaces`
and `::test_the_active_embedder_still_clears_the_trilingual_margin`.

---

## Inference

Ordered free-first by `services/api/core/llm.py`. Each skip is recorded on the
response, so a transcript can always show which model produced a turn.

| Order | Provider | Model | Cost | Role |
|---|---|---|---|---|
| 1 | Ollama | `qwen3:8b` | free, local | Debate turns during development and demos |
| 2 | Gemini | `gemini-2.0-flash` | free tier | What the deployed instance thinks with |
| 3 | Groq | `llama-3.3-70b-versatile` | free tier | Second cloud opinion, and fast |
| 4 | Anthropic | — | metered | **Present and permanently disabled** |
| 5 | Stub | `deterministic-v1` | free | CI substrate and terminal fallback |

`qwen3:8b` runs with `think: false`. Qwen3 reasons by default; a boardroom turn
is a position, not a scratchpad, and the thinking tokens roughly triple wall
clock for output the transcript then has to hide.

### Anthropic is in the chain, and refuses

`AnthropicProvider.available()` returns `False` even when `ANTHROPIC_API_KEY` is
set, and `tests/core/test_llm.py::test_anthropic_is_never_selected_even_with_a_key`
sets the key and asserts it stays off. The class is deliberately not deleted: an
absence reads as an oversight and invites a well-meaning contributor to fill it,
whereas a refusal with a test behind it is a stated position. Enabling it is a
budget decision for the owner, not a code change.

### Measured throughput

`qwen3:8b`, `think: false`, on the owner's machine, 2026-09-07: **22.5 tokens/s**
(168 tokens in 7.5 s, plus 5.1 s cold load).

A three-round debate is 15 mandate turns plus facilitator and auditor overhead —
roughly 20 generations. Run sequentially at 200 tokens each that is about 180 s,
inside the 4-minute target with almost no headroom. Phase C therefore caps turns
at 180 tokens and runs the five mandates **concurrently within a round**: they
argue against the previous round's transcript, so intra-round parallelism is
semantically correct rather than a shortcut. `qwen3:4b-instruct` is the speed
fallback if a machine cannot hold the 8B.

---

## Reproducing any number on this page

```bash
uv run python scripts/spike_embeddings.py   # the embedding table
uv run python scripts/search_smoke.py       # which search tier served what
node apps/web/scripts/check-contrast.mjs    # every contrast ratio
```
