# COUNSEL Phase E Implementation Plan — the harness and the artefacts

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans, inline, no subagents. One conventional commit per task with the Claude co-author trailer.

**Goal:** Turn every safety claim COUNSEL makes into an executable attack that either fails or is recorded as a gap, publish the scorecard, and produce the four Term 4 artefacts from measured numbers rather than prose.

**Architecture:** The scorecard is generated FROM the tests, not written alongside them. A control listed as covered must name the test that covers it, and a control with no test is printed as a gap rather than omitted — an unenforced control that looks enforced is worse than an admitted one.

## Global Constraints

Everything from Phases A–D holds. Additionally:

- **Every number in every artefact traces to `docs/results/`.** The report builder reads those files; it does not accept a figure typed by hand.
- **No attack in the harness is a technique anyone could reuse offensively.** These are defensive tests against COUNSEL's own boundary, and the payloads are the ones already in the fixtures.
- **Gaps are printed, not hidden.** The scorecard shows uncovered risks as uncovered.
- Placeholder scan must be clean before any artefact is generated.

---

## Task E1: OWASP LLM Top 10 harness

**Files:** `tests/invariants/test_owasp.py`, `services/api/security/scorecard.py`.

Each test id carries the risk it covers, so a reviewer can walk the table and find the proof.

| Risk | COUNSEL's control |
|---|---|
| LLM01 Prompt injection | Untrusted-content boundary; poisoned document cannot change the memo |
| LLM02 Insecure output handling | Memo claims pass `require_citations`; no output is executed |
| LLM03 Training-data poisoning | Not applicable — no training. Declared, not silently omitted |
| LLM04 Model denial of service | Request-count quotas; turn-token caps; bounded history |
| LLM05 Supply chain | Pinned lockfiles; model provenance in `docs/models.md` |
| LLM06 Sensitive information disclosure | Prompt-exfiltration pattern; no secrets in prompts; RBAC |
| LLM07 Insecure plugin design | The capability registry: every tool read-only, asserted |
| LLM08 Excessive agency | No side-effect tools; only the Facilitator controls rounds |
| LLM09 Overreliance | Uncited claims quarantined; unanimous-dissent warning; Brier gate |
| LLM10 Model theft | Not applicable — no proprietary weights. Declared |

- [ ] **Step 1:** Write the tests, one per risk, each asserting the control rather than describing it.
- [ ] **Step 2:** `scorecard.py` builds the table by reading the test ids, so a control cannot claim coverage without one.
- [ ] **Step 3:** `scripts/owasp_scorecard.py` writes `docs/results/E1-owasp-scorecard.json`.
- [ ] **Step 4:** Commit `test(security): OWASP LLM Top 10 as executable controls`.

**Verifiable check:** the scorecard lists every risk, names a test for each covered one, and prints gaps as gaps.

---

## Task E2: Goal-hijack and impersonation, as the master plan names them

**Files:** `tests/invariants/test_owasp.py` (extended).

The master plan §3.7 names two attacks specifically:
1. A poisoned uploaded document must not change the memo.
2. An unsigned message must be rejected as agent impersonation.

- [ ] Both asserted end to end, not in isolation.
- [ ] Commit `test(security): goal hijack and agent impersonation`.

**Verifiable check:** a memo built over a poisoned corpus carries the same recommendation as one built without it.

---

## Task E3: The Term 4 report

**Files:** `services/api/reports/`, `scripts/build_report.py`.

`MGT204_MAJLIS_report.docx` — built from `docs/results/`, every figure read from a file, every claim traceable.

- [ ] **Step 1:** A builder that REFUSES to emit a figure that has no results file behind it.
- [ ] **Step 2:** Commit `feat(reports): the Term 4 report, built from measured results`.

**Verifiable check:** deleting a results file makes the build fail rather than print a stale number.

---

## Task E4: Deck, viva and demo script

**Files:** `docs/artefacts/`.

- [ ] Slide deck outline with the same figures.
- [ ] 15 viva questions with answers grounded in what was measured, including the failures.
- [ ] A 3-minute demo script naming exactly what to click.
- [ ] Commit `docs: deck, viva and demo script`.

**Verifiable check:** placeholder scan clean; every figure appears in `docs/results/`.

---

## Task E5: Deploy and score

- [ ] Deploy prep, then STOP for the owner's accounts and keys.
- [ ] Score out of 100 against a stated rubric, with the evidence for each mark.
- [ ] Commit `docs: deployment and the honest score`.
