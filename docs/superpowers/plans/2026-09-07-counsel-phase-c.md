# COUNSEL Phase C Implementation Plan — stages, memo, ledger

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans, inline, no subagents. One conventional commit per task with the Claude co-author trailer.

**Goal:** Turn a debate into a decision that survives contact with reality — the seven design-thinking stages as executable artefacts, an Amazon-style memo where every factual sentence resolves to a span, a counterfactual engine that says which single piece of evidence would flip the call, and an outcome ledger that scores each seat's calibration once the world answers.

**Architecture:** Phase B's turns are *speech*. Phase C adds *artefacts* — structured, validated objects the room produces at each stage, which the memo is assembled from. The generation is model-driven; the assembly, the citation gate, the counterfactual arithmetic and the Brier scoring are all deterministic Python. Nothing a model emits reaches the memo without passing `require_citations`.

**Tech Stack:** Phase A/B, plus pydantic models as output schemas (Ollama `format`, Gemini `responseSchema`, Groq JSON mode, registered stub handlers).

## Global Constraints

Everything from Phases A and B still holds. Additionally:

- **Every factual sentence in the memo body cites a span that resolves.** A claim that fails `require_citations` never appears as an assertion; it is moved to a clearly-labelled section recording what the room believed but could not support.
- **The counterfactual is arithmetic over recorded positions, not a re-run of the argument.** Labelled as such wherever it appears.
- **Brier scores are meaningless below a stated minimum number of outcomes.** The UI must refuse to draw a calibration claim until then.
- **No agent gains a tool.** The registry assertion from B3 still passes.
- The demo decision throughout: *"Should RAQIB pilot in a Dubai hypermarket or a Greenlam plant first?"*

---

## Task C1: Structured output through the provider chain

**Files:** `services/api/core/llm.py`, `services/api/core/schemas.py`, `tests/core/test_structured.py`.

**Interfaces:**
```python
class LLMChain:
    def structured(self, system: str, messages: list[Message], *,
                   model_cls: type[BaseModel], max_tokens: int = 400,
                   temperature: float = 0.0, speaker: str | None = None,
                   retries: int = 1) -> tuple[BaseModel, LLMResponse]
```
Each provider passes the JSON schema natively where it can (Ollama `format`, Gemini `responseSchema`, Groq `response_format`). Validation failure retries once with the pydantic error appended, then degrades to the next provider. `StubProvider.register(task, handler)` supplies schema-valid deterministic objects so the whole of Phase C runs in CI with no model.

- [ ] **Step 1:** Tests — a valid object round-trips; a provider returning prose degrades rather than raising; the stub returns schema-valid objects for every Phase C task; retry appends the validation error.
- [ ] **Step 2:** Implement. **Step 3:** Commit `feat(api): schema-validated structured output across the provider chain`.

**Verifiable check:** every Phase C schema round-trips through the stub with no model running.

---

## Task C2: Stage artefacts — framings, ideas, scores

**Files:** `services/api/crew/stages.py`, `services/api/core/schemas.py`, `tests/crew/test_stages.py`.

**Interfaces:**
```python
class Framing(BaseModel):     # Define
    hmw: str                  # "How might we ..."
    why_it_matters: str
    whose_problem: str

class Idea(BaseModel):        # Ideate
    title: str
    sketch: str
    builds_on: str | None     # another seat's idea, per the stage rule

class Score(BaseModel):       # Test
    option: str
    desirability: int         # 1-5
    feasibility: int
    viability: int
    weakest_on: Literal["desirability", "feasibility", "viability"]
    confidence: float         # 0-1, used later for Brier
    depends_on: list[str]     # evidence ids this score rests on

def collect_framings(session, *, chain) -> dict[str, Framing]
def collect_ideas(session, *, chain) -> dict[str, Idea]
def collect_scores(session, options, *, chain) -> dict[str, list[Score]]
def aggregate(scores) -> list[OptionResult]   # deterministic
```

- [ ] **Step 1:** Tests — aggregation is deterministic and order-independent; a seat scoring outside 1–5 is rejected by the schema; `weakest_on` must match the lowest of the three; every score carries a confidence.
- [ ] **Step 2:** Implement. **Step 3:** Commit `feat(crew): stage artefacts for Define, Ideate and Test`.

**Verifiable check:** `aggregate` returns identical results for shuffled input, and the winner is reproducible.

---

## Task C3: The decision memo, dissent log and pre-mortem

**Files:** `services/api/crew/memo.py`, `tests/crew/test_memo.py`.

**Interfaces:**
```python
class Claim(BaseModel):
    text: str
    citations: list[Citation]

class Memo(BaseModel):
    question: str; recommendation: str; context: list[Claim]
    reasoning: list[Claim]; dissents: list[Dissent]
    premortem: list[str]; would_change_our_mind: list[str]
    uncited: list[str]        # what the room asserted but could not support
    generated_at: str; session_id: str

def build_memo(session, *, chain, conn) -> Memo
def render_markdown(memo) -> str
```
`build_memo` runs every claim through `require_citations`. Failures move to `uncited`, never into the body.

- [ ] **Step 1:** Tests — a claim with a forged quote never reaches `reasoning`; a memo with zero resolvable citations still renders, with an empty body and a populated `uncited`; every dissent names a seat and its reason; the rendered markdown contains no claim absent from the model.
- [ ] **Step 2:** Implement. **Step 3:** Commit `feat(crew): citation-gated decision memo with a dissent log`.

**Verifiable check:** a forged citation cannot appear in the memo body — asserted directly.

---

## Task C4: "What would change our mind"

**Files:** `services/api/crew/counterfactual.py`, `tests/crew/test_counterfactual.py`.

**Interfaces:**
```python
class Flip(BaseModel):
    evidence_id: str; removing_it_changes_winner_to: str
    margin_before: float; margin_after: float

def sensitivity(scores, evidence) -> list[SeatSensitivity]
def flips(scores, evidence) -> list[Flip]     # minimal single-item flips
```
Deterministic arithmetic over recorded `depends_on` links. Not a re-run of the debate, and labelled so everywhere.

- [ ] **Step 1:** Tests — a decision resting on one evidence item reports exactly that item as a flip; a decision no single item can flip reports none; sensitivity per seat sums correctly; removing evidence nothing depends on changes nothing.
- [ ] **Step 2:** Implement. **Step 3:** Commit `feat(crew): counterfactual engine for what would change our mind`.

**Verifiable check:** a synthetic decision hinging on one item yields exactly one flip.

---

## Task C5: Outcome ledger and Brier calibration

**Files:** `services/api/crew/ledger.py`, `services/api/core/db.py`, `tests/crew/test_ledger.py`.

**Interfaces:**
```python
def record_outcome(session_id, *, chosen: str, actual: str, notes: str, conn) -> None
def brier(seat, *, conn) -> BrierScore | None      # None below MIN_OUTCOMES
MIN_OUTCOMES = 5
def calibration(*, conn) -> list[BrierScore]
```

- [ ] **Step 1:** Tests — a seat with fewer than `MIN_OUTCOMES` returns `None` rather than a number; a perfectly calibrated seat scores 0.0; a confidently wrong seat scores near 1.0; the score is order-independent.
- [ ] **Step 2:** Implement. **Step 3:** Commit `feat(crew): outcome ledger with Brier calibration and a minimum-N gate`.

**Verifiable check:** `brier()` returns `None` at 4 outcomes and a number at 5.

---

## Task C6: Web — Stages, Board, Memo, Ledger

**Files:** `apps/web/app/{stages,memo,ledger}/page.tsx`, components, `apps/web/e2e/memo.spec.ts`.

- [ ] **Step 1:** Playwright — the memo renders with every body claim showing a resolvable span; the `uncited` section is visibly separated; a flip is shown with its margins; the ledger refuses to draw calibration below `MIN_OUTCOMES`.
- [ ] **Step 2:** Implement. **Step 3:** Commit `feat(web): stages, memo with the dissent margin, and the ledger`.

**Verifiable check:** e2e green on desktop and mobile, axe clean.

---

## Task C7: Phase C documentation and results

- [ ] `docs/decisions.md` — the stages, what the memo guarantees, what the counterfactual is and is not, and what Brier scores need to mean anything.
- [ ] README updated; `make check` and `make e2e` green; placeholder scan clean.
- [ ] Commit `docs: the decision record, its guarantees and its limits`.
