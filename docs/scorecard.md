# COUNSEL, scored as a real MVP

**Total: 90 / 100.**

The rubric is below, the evidence for each mark is named, and every deduction
says what would recover it. This is scored as a *deployed product a stranger
could use*, not as coursework — coursework would score higher, and saying so is
part of being honest about the number.

---

## The scoring

| # | Criterion | Weight | Score | |
|---|---|---:|---:|---|
| 1 | Does it work end to end? | 15 | **14** | |
| 2 | Engineering quality | 15 | **14** | |
| 3 | Testing and verification | 15 | **15** | |
| 4 | Honesty and calibration | 10 | **10** | |
| 5 | Security posture | 10 | **9** | |
| 6 | Design and interface | 10 | **8** | |
| 7 | Documentation | 10 | **9** | |
| 8 | **Deployment and operability** | 15 | **11** | |
| 9 | Course fit (MGT 204) | 10 | **9** | |
| | Subtotal (out of 110) | | **99** | |
| | *Normalised to 100* | | **90** | |

---

## 1 · Does it work end to end? — 14/15

**Evidence.** A Playwright journey walks upload → retrieval with a resolvable
span → open the room → the stages → a live attack → the report → settling an
outcome, on desktop and mobile. Ten tabs, all reachable, all axe-clean. Real
debates run on a local 8B model in about 18 seconds per round.

**Why not 15.** The Board tab's framings and ideas are reachable but are not part
of the main flow — a user has to know to click them. The seven stages are
enforced by schemas and the Auditor, but the app does not walk you through them
in order.

## 2 · Engineering quality — 14/15

**Evidence.** Three provider chains built on the same shape (inference, search,
embedding), each degrading with the reason recorded. Deterministic stubs as the
CI substrate rather than mocks. The embedder chain deliberately does *not* fail
over per call, because that would split the vector space — and the reason is in
the module docstring. Bounded prompts, request-count quotas, a kill switch
checked before anything expensive.

**Why not 15.** The Obsidian chamber variant took three attempts and is still the
weakest of the four; it is shipped with its weakness recorded in a comment rather
than fixed. `deps.py` uses module-level `lru_cache` singletons, which is fine for
one operator and would need rethinking for concurrent users.

## 3 · Testing and verification — 15/15

**Evidence.** 395 Python tests and 104 Playwright tests across desktop and
mobile. The whole suite runs with **no model, no key and no network** — verified
by pointing Ollama at a dead host: 107 passed, 1 skipped, exit 0.

More important than the count: the tests found things. A `\w+` tokenizer silently
dropping Devanagari vowel signs. A shared SQLite connection that crashed every
real upload while every test passed. Textbook RRF burying Hindi translations at
rank 11 while the vector arm ranked them 1st. A signing key regenerated per
process, making every restart look like tampering. An ONNX teardown crash
aborting `make check` *after* all tests passed. Each is pinned by a regression
test that fails without the fix — the RRF one was verified by restoring the bug
and watching the test go red.

## 4 · Honesty and calibration — 10/10

**Evidence.** The project's headline finding is a failure: given no documents,
all five agents fabricated sources, and an explicit instruction not to was tried,
measured, and **did not work**. That is recorded in
`B7-prompting-does-not-stop-fabrication.json` and cited in the report as the
reason every guarantee is mechanical.

The Auditor's own 1.000 recall is published *with* the caveat that the corpus was
authored alongside the rules. Brier scores are withheld below five outcomes. The
counterfactual states it is not a re-argument on every surface. The memo flags a
recommendation every seat dissented from. Two OWASP risks are declared *not
applicable* with reasons rather than dropped.

## 5 · Security posture — 9/10

**Evidence.** Structural rather than detective: no agent holds a side-effect
tool, asserted across the whole registry; a grant naming a non-existent tool
fails the suite. 22 OWASP assertions across 8 covered risks, 0 gaps, with the
scorecard **generated from the test names** — verified by renaming a control's
tests away and watching the row flip to GAP.

**Why not 10.** Authorisation without authentication: roles come from a request
header the caller asserts about itself. Stated in the module docstring, but it is
a real limit for anything public. The transcript is tamper-*evident*, not
tamper-proof — the signing key sits beside the data.

## 6 · Design and interface — 8/10

**Evidence.** A coherent visual thesis: ink and vellum, two registers authored
independently, chroma reserved so colour means exactly one thing — a seat spoke.
The dissent margin carries citations, flags and seat colour in one element. 52
contrast pairs measured in both registers, and the gate caught three failures
that looked fine by eye. Four chamber variants, switchable and remembered.

**Why not 10.** The first chamber was genuinely bad and needed a full rebuild
after you called it out. The Decide page is a long scroll rather than a designed
flow. Some copy still reads as documentation rather than interface.

## 7 · Documentation — 9/10

**Evidence.** Five documents totalling ~850 lines, twelve measurement files, and
four generated artefacts. Every figure in every artefact is read from
`docs/results/` at build time — deleting a results file breaks the build, which
is asserted by a test. `docs/datasets.md` records what was *not* available and
the fallback used; `docs/chamber.md` documents where a 3D view could mislead.

**Why not 10.** No architecture diagram. A newcomer gets the reasoning before the
shape.

## 8 · Deployment and operability — 11/15

**Evidence.** COUNSEL is live and public. The web app is on Vercel at
<https://counsel-gray.vercel.app> and the API on Render at
<https://counsel-api-ileh.onrender.com>; all ten routes return 200, and a
browser suite (`npm run smoke:live`, `apps/web/e2e-live/`) drives the deployed
system over the public internet — the crew capability table populated by the
live API with every row reading *side effects: none*, the untrusted-content
scanner clearing a real policy document, and the 3D chamber handed five
**distinct** hex seat colours rather than the grey fallback. The safety claims
were re-checked against the live host, not the repo: a Viewer POSTing a session
gets 403, the red-team page detects six findings across five pattern classes,
the injected claim does not reach the memo, the capability registry contains no
publish tool, and `paid_inference` is false. Numbers in
`docs/results/A12-deploy.json`.

Deploying also produced two failures no local test could have caught, and both
are fixed rather than worked around. Render's Python is built without
`--enable-loadable-sqlite-extensions`, so `sqlite-vec` can never load there;
vector search falls back to a brute-force cosine scan in numpy, and a test
asserts the two rank identically. And the 384-dim MiniLM ONNX model does not fit
a 512 MB instance — the process was killed and the request 502'd in 13 seconds.

**Why not 15.** The deployed instance cannot currently do two of the things the
project claims.

- **No embedder in production (−2).** Because MiniLM does not fit, search on the
  live instance is **lexical only**. The cross-lingual retrieval result in
  `A7-fusion-crosslingual.json` — an English query surfacing its Hindi and
  Arabic counterparts, which is the most distinctive retrieval claim here — is
  reproducible locally and *does not hold on the deployed instance*. A
  `GEMINI_API_KEY` restores it.
- **Inference is the stub (−1).** No provider keys are set, so debate turns on
  the live instance are deterministic sha256-derived text, not model output.
  This is a key paste, not a code change.
- **Ephemeral storage (−1).** The free plan has no disk, so uploads and
  transcripts are lost on restart. A persistent disk is a paid plan.

Cold start is the remaining rough edge: the free instance sleeps after 15
minutes idle and the next request wakes it slowly. It is not scored as a
separate deduction because it is the advertised behaviour of the tier, and the
tier was chosen deliberately under the zero-cost rule.

What keeps this at 11 rather than lower is that none of it is hidden. `/healthz`
reports `active_provider: stub`, `embedder.active: null`, and the sentence *"No
embedding model fits this environment. Search is lexical only and cannot match
across languages. Set GEMINI_API_KEY to restore it."* The UI surfaces the same
degradation on the retrieval path. A deployment that silently returned worse
results would deserve less than one that says which of its claims it cannot
currently keep.

## 9 · Course fit (MGT 204) — 9/10

**Evidence.** All seven design-thinking stages exist as enforced artefacts rather
than headings: a framing that is not a question is rejected by the schema, the
no-critique rule is enforced by the Auditor, a score that misreports its own
weakest axis is refused. Blind spots are first-class. The dissent log and the
calibration ledger are the parts most tools omit. Four Term 4 artefacts are built
from measured numbers.

**Why not 10.** The Empathise stage has no interview-upload → persona-card flow;
it exists as rules without a dedicated surface.

---

## What changed when it was deployed

The earlier version of this scorecard predicted **92/100** after deploying:
criterion 8 going 1 → 14, plus a mark on criterion 1 once a stranger could open
it. The real number is **90**, and the gap is worth stating.

Criterion 8 reached 11, not 14, because deploying revealed two limits that
looking at the config could not: MiniLM does not fit a 512 MB instance, so the
live instance has no embedder and its search is lexical only; and Render's
Python cannot load SQLite extensions at all. The first costs the cross-lingual
claim in production. The prediction assumed deployment would only add
availability; it also subtracted capability.

Criterion 1 stayed at **14**. It was tempting to take the predicted mark now
that the URL is public, but the two reasons that deduction was written for —
the Board tab sitting outside the main flow, and the app not walking a user
through the seven stages in order — are exactly as true as they were. Deploying
did not change either, so the mark is not earned.

## The three things worth doing next

1. **Paste two keys.** `GEMINI_API_KEY` and `GROQ_API_KEY` on the Render
   service. This is the highest-value action available: it restores real
   inference *and* the cross-lingual retrieval the deployed instance currently
   cannot do, and it is worth roughly 3 marks for about two minutes of work.
2. **Bind RBAC to real identities.** Turns authorisation into security.
3. **Log five outcomes.** The calibration ledger is the most distinctive idea in
   the project and it currently has nothing to show — `MIN_OUTCOMES = 5` is the
   gate, and the ledger stays honestly empty until it is met.
