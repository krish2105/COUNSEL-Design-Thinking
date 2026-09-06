# COUNSEL Phase B Implementation Plan — the crew

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans, inline, no subagents. Checkbox syntax; every task green; one conventional commit per task with the Claude co-author trailer.

**Goal:** Five mandates, a Facilitator and an Auditor that can hold a real multi-round debate on Phase A's grounded substrate — with a tamper-evident transcript, capability bounds no agent can exceed, and an Auditor that catches stage-rule breaches.

**Architecture:** A mandate is a **prompt file**, not a class: its values, blind spots and evidence standards are data a human can read and argue with, because "the CFO is biased toward payback period" is a claim the user must be able to check. The runtime is deterministic — the Facilitator decides who speaks and when, in Python; the model only produces what a speaker says. Capability is granted declaratively per agent and the registry is asserted to contain nothing with side effects.

**Tech Stack:** Phase A's `LLMChain`, `SearchChain` and retrieval, plus `hmac`/`hashlib` for the transcript chain and a `ThreadPoolExecutor` for intra-round concurrency.

## Global Constraints

Everything from Phase A still holds. Additionally:

- **No agent has a side-effect tool.** Debating mandates get `search` and `ask`. The Facilitator gets `start_round` and `close_round`. The Auditor gets `flag`. Nothing else exists, and a test enumerates the whole registry to prove it.
- **Every turn is signed into a hash chain.** Altering any message breaks every signature after it.
- **A three-round debate must finish in under 4 minutes** on `qwen3:8b` (§3.8). Measured, recorded in `docs/results/`, and asserted.
- **The Auditor must catch ≥ 90% of seeded stage-rule breaches** (§3.8). Measured against a labelled corpus, not asserted.
- Turns are capped at 180 tokens and run with `think: false`; the five mandates speak **concurrently within a round** against the previous round's transcript.

---

## Task B1: Mandates as prompt files

**Files:** Create `services/api/crew/mandates/{cfo,cmo,coo,ethics,devil}.md`, `services/api/crew/mandate.py`, `tests/crew/test_mandates.py`.

**Interfaces:**
```python
@dataclass(frozen=True)
class Mandate:
    id: str            # "cfo" | "cmo" | "coo" | "ethics" | "devil"
    title: str
    seat: str          # matches the --seat-* CSS tokens
    accountable_for: str
    values: tuple[str, ...]
    blind_spots: tuple[str, ...]     # what this mandate systematically under-weights
    evidence_standards: tuple[str, ...]
    body: str          # the prompt itself

def load_mandates() -> dict[str, Mandate]
def system_prompt(m: Mandate, *, stage: str, rules: tuple[str, ...]) -> str
```

- [ ] **Step 1:** Write the five files with YAML frontmatter and a prose body. Every mandate must declare at least two blind spots — a mandate that claims none is the bug.
- [ ] **Step 2:** Write `tests/crew/test_mandates.py` asserting all five load, ids match the seat tokens in `tokens.css`, each declares ≥ 2 blind spots and ≥ 2 values, and no two mandates share a value set.
- [ ] **Step 3:** Run — expect FAIL. Implement `mandate.py`. Run — expect PASS.
- [ ] **Step 4:** Commit `feat(crew): five mandates as readable prompt files with declared blind spots`.

**Verifiable check:** all five load, and the blind-spot assertion passes for every one.

---

## Task B2: Signed transcripts

**Files:** Create `services/api/crew/transcript.py`, `tests/invariants/test_transcript.py`.

**Interfaces:**
```python
@dataclass(frozen=True)
class Turn:
    turn_id: str
    session_id: str
    round_no: int
    stage: str
    speaker: str          # mandate id, "facilitator", "auditor", or "chair"
    text: str
    provider: str
    model: str
    citations: tuple[Citation, ...]
    created_at: str
    prev_sig: str
    sig: str

class Transcript:
    def append(self, ...) -> Turn
    def verify(self) -> list[str]      # empty when the chain is intact
    def turns(self) -> list[Turn]
```
Each signature is HMAC-SHA256 over a canonical JSON of the turn **including `prev_sig`**, so the transcript is a hash chain, not a set of independent signatures.

- [ ] **Step 1:** Write the tests: a clean chain verifies; editing any turn's text breaks that turn and every one after it; reordering breaks it; deleting a middle turn breaks it; a forged turn appended without the key is rejected.
- [ ] **Step 2:** Run — FAIL. Implement. Run — PASS.
- [ ] **Step 3:** Commit `feat(crew): tamper-evident transcript as a hash chain`.

**Verifiable check:** editing turn 2 of 5 reports turns 2, 3, 4 and 5 as broken — not just turn 2.

---

## Task B3: Capability registry

**Files:** Create `services/api/crew/tools.py`, `tests/invariants/test_capabilities.py`.

**Interfaces:**
```python
@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    side_effects: bool          # must be False for every registered tool
    run: Callable[..., object]

REGISTRY: dict[str, Tool]
GRANTS: dict[str, frozenset[str]]     # agent id -> tool names
def invoke(agent: str, tool: str, **kwargs) -> object   # raises CapabilityError
```

- [ ] **Step 1:** Tests: every tool in `REGISTRY` declares `side_effects is False`; a debating mandate invoking `start_round` raises `CapabilityError`; the Auditor cannot `search`; an unknown tool name raises; **every name in every grant exists in the registry** (a grant for a tool that does not exist is a silent hole).
- [ ] **Step 2:** Run — FAIL. Implement `search` and `ask` over Phase A's chains, `start_round`/`close_round`, `flag`. Run — PASS.
- [ ] **Step 3:** Commit `feat(crew): declarative capability grants with no side-effect tools`.

**Verifiable check:** the registry-wide `side_effects is False` assertion, plus a mandate being refused `start_round`.

---

## Task B4: The Facilitator and the debate runtime

**Files:** Create `services/api/crew/session.py`, `services/api/crew/facilitator.py`, `tests/crew/test_debate.py`.

**Interfaces:**
```python
@dataclass
class Session:
    session_id: str
    question: str
    stage: str
    round_no: int
    budget: Quota
    transcript: Transcript

class Facilitator:
    def open(self, question: str, *, stage: str) -> Session
    def run_round(self, session: Session, *, rules: tuple[str, ...]) -> list[Turn]
    def close(self, session: Session) -> Session
```
The five mandates speak concurrently within a round against the **previous** round's transcript, which is what makes intra-round parallelism correct rather than a shortcut.

- [ ] **Step 1:** Tests on the stub provider: a 3-round debate produces exactly 15 mandate turns; every turn is signed and the chain verifies; the kill switch mid-round stops the debate and leaves a verifiable transcript; budget exhaustion ends the round cleanly rather than raising; turn order within a round is deterministic under a seed despite concurrency.
- [ ] **Step 2:** Run — FAIL. Implement. Run — PASS.
- [ ] **Step 3:** Measure a real 3-round debate on `qwen3:8b` and write `docs/results/B4-debate-latency.json`.
- [ ] **Step 4:** Commit `feat(crew): facilitator, rounds and concurrent mandate turns`.

**Verifiable check:** 15 turns, chain verifies, and the measured wall clock for a real 3-round debate is recorded and under 240 s.

---

## Task B5: The Auditor

**Files:** Create `services/api/crew/auditor.py`, `tests/fixtures/audit/breaches.jsonl`, `tests/crew/test_auditor.py`, `scripts/audit_recall.py`.

**Interfaces:**
```python
@dataclass(frozen=True)
class Flag:
    turn_id: str
    rule: str        # "ad-hominem" | "unsupported-number" | "stage-rule" | "uncited-claim"
    severity: str
    excerpt: str
    why: str

def audit(turn: Turn, *, session: Session, conn) -> list[Flag]
```

- [ ] **Step 1:** Build a labelled corpus of ≥ 30 turns — breaches and clean turns that use the same vocabulary, so recall is not bought with false positives.
- [ ] **Step 2:** Write the tests and `scripts/audit_recall.py`, which writes `docs/results/B5-auditor-recall.json` and **fails below 0.90 recall or above 0.15 false-positive rate**.
- [ ] **Step 3:** Run — FAIL. Implement. Run — PASS.
- [ ] **Step 4:** Commit `feat(crew): auditor with measured recall on a labelled breach corpus`.

**Verifiable check:** `uv run python scripts/audit_recall.py` exits 0 with recall ≥ 0.90.

---

## Task B6: Session API with streamed turns

**Files:** Create `services/api/routers/sessions.py`, `tests/api/test_sessions.py`.

Endpoints: `POST /sessions` (Analyst), `GET /sessions/{id}`, `GET /sessions/{id}/transcript`, `POST /sessions/{id}/rounds/stream` (SSE, one frame per turn), `GET /sessions/{id}/verify`.

- [ ] **Step 1:** Tests: a Viewer cannot open a session; the SSE stream emits one `turn` frame per mandate plus `done`; `/verify` reports an intact chain; tampering with a stored turn makes `/verify` report it.
- [ ] **Step 2:** Run — FAIL. Implement. Run — PASS.
- [ ] **Step 3:** Commit `feat(api): session endpoints with per-turn SSE`.

**Verifiable check:** the SSE stream emits five `turn` frames for a five-mandate round, and `/verify` catches a tampered turn.

---

## Task B7: Phase B documentation and results

- [ ] **Step 1:** `docs/crew.md` — the mandates, their declared blind spots, the capability table, and what the Auditor does and does not catch.
- [ ] **Step 2:** README updated; placeholder scan clean; `make check` green.
- [ ] **Step 3:** Commit `docs: the crew, its capability bounds and the auditor's measured limits`.

**Verifiable check:** `make check` exits 0 and every figure in `docs/crew.md` has a file in `docs/results/`.
