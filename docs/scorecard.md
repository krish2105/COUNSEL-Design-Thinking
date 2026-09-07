# COUNSEL, scored as a real MVP

**Total: 78 / 100.**

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
| 8 | **Deployment and operability** | 15 | **1** | |
| 9 | Course fit (MGT 204) | 10 | **9** | |
| | Subtotal (out of 110) | | **89** | |
| | *Normalised to 100* | | **78** | |

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

## 8 · Deployment and operability — 1/15

**This is the honest deduction, and it is the big one.**

COUNSEL runs on `localhost`. It has never been deployed. `render.yaml`,
`vercel.json`, a CI workflow and `docs/deploy.md` are written and the config
parses — that is the one mark. But nothing has been built on a real host, no URL
exists, cold-start behaviour is untested, the fastembed path has never run inside
512 MB, and the Gemini embedder is marked ⚠ UNVERIFIED because no key was ever
available to measure it.

A product a stranger cannot open is not a product. **Recovering this is worth 14
marks and about thirty minutes** — the steps are in `docs/deploy.md` and they
need your accounts.

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

## What the score would be after deploying

**92 / 100** — deployment goes 1 → 14, and criterion 1 gains a mark once a
stranger can actually open it. Nothing else changes.

## The three things worth doing next

1. **Deploy.** Largest single gain in the rubric, ~30 minutes, needs your accounts.
2. **Bind RBAC to real identities.** Turns authorisation into security.
3. **Log five outcomes.** The calibration ledger is the most distinctive idea in
   the project and it currently has nothing to show.
