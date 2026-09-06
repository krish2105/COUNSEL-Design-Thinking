# The crew

Five mandates, a Facilitator and an Auditor. This page describes what each can
do, what each admits it gets wrong, and what the Auditor does and does not
catch. Every figure here comes from a file in [`docs/results/`](results/).

---

## The room

The five seats are **prompt files**, not classes:
[`services/api/crew/mandates/`](../services/api/crew/mandates/). That is
deliberate. COUNSEL's claim is that these agents hold genuinely different
positions rather than paraphrasing one model, and that claim is only checkable
if the difference is legible enough to argue with. Open the files and disagree
with them.

| Seat | Accountable for | Admits it under-weights |
|---|---|---|
| **CFO** | Whether the company can afford this, and what it costs to be wrong | Option value; anything it cannot quantify, which it treats as worth zero rather than unmeasured; the first number on the table, including its own |
| **CMO** | Whether anyone outside the room wants it, at a price that works | What photographs well over what works; interest mistaken for intent; the operational load of what it promises |
| **COO** | Whether it can be done, by the people and equipment that exist | Upside — it is built to find what breaks, so it prices the risk of acting and not of standing still; constraints it has not retested |
| **Ethics Officer** | Who carries the downside, and whether they agreed to | The identifiable harm over the statistical one; the ethical cost of delay, which is a decision with victims too |
| **Devil's Advocate** | Attacking the position the room is drifting toward | Contrarianism mistaken for rigour — it is rewarded for disagreeing, so it will disagree when the room is right |

**The blind spots are the substance, not decoration.** Divergence before
convergence only works if the room's biases are on the table, and an agent
claiming none is the most dangerous one present. Every mandate declares at least
two, the loader raises if one does not, and each is instructed to say out loud
when the argument has moved onto its own weak ground.

That is not aspirational. In the measured sample
([`B4-mandate-differentiation.json`](results/B4-mandate-differentiation.json))
the CFO volunteered, unprompted: *"I underweight the option value of a Greenlam
pilot — it could reveal operational risks we haven't measured."*

### Two boundaries, in the prompts and in the tests

- The **Ethics Officer does not give legal advice.** It identifies where legal or
  regulatory review is needed and says what question a lawyer should be asked.
- The **Devil's Advocate attacks arguments, never people.** The Auditor flags it
  if it slips.

---

## What each agent can do

Capability is granted declaratively in
[`services/api/crew/tools.py`](../services/api/crew/tools.py) and there is
nothing else to call.

| Agent | Tools | Side effects |
|---|---|---|
| CFO · CMO · COO · Ethics · Devil | `search`, `ask` | none |
| Facilitator | `start_round`, `close_round` | none |
| Auditor | `flag` | none |
| Chair (the human) | `search`, `ask` | none |

**No tool in COUNSEL has side effects**, and that is asserted over the whole
registry rather than reviewed by eye. Prompting could not keep this promise:
"do not post anything" is a request, and an injected instruction is a competing
request. It is kept by there being nothing to call. Three tests hold the line —
no registered tool declares side effects, no tool NAME contains post/publish/
send/email/deploy/delete/execute, and every grant names a tool that actually
exists (a grant for a missing tool looks like a capability and fails only when
something reaches for it).

Only the Facilitator can start or close a round. A room where any seat can close
the round is a room where the loudest seat decides when the argument is over.

---

## How a round works

Who speaks, in what order, for how many rounds, and when the argument ends are
decided in ordinary Python. The model produces only what a seat says on its
turn. A debate whose control flow is model-generated cannot be replayed,
bounded or audited.

**The five seats speak concurrently within a round.** This is not a shortcut: a
round already means every seat argues against the transcript as it stood at the
*end of the previous round*, so no seat can hear another's current-round turn
even in principle. Running them sequentially would hand a hidden advantage to
whoever spoke last — the exact bias a facilitated round exists to remove. Turns
are then written in fixed seating order, so the record and its hash chain are
identical every run whatever order the models finished in.

### Measured

[`B4-debate-latency.json`](results/B4-debate-latency.json) — a real 3-round
debate on `qwen3:8b`, `think: false`, 180-token turns:

| | |
|---|---|
| Total | **126.5 s** against a 240 s target |
| Per round | 45.3 s, 42.8 s, 38.3 s |
| Mandate turns | 15 |
| Transcript intact | yes |

---

## The record

Every turn is signed into a **hash chain**: each signature covers the turn *and
the previous signature*. Editing turn 2 of 5 invalidates 2, 3, 4 and 5; removing
a turn from the middle breaks everything after the gap; reordering breaks it.
Independent per-turn signatures would catch the edit and miss the deletion.

Citations are inside the signed payload, because a memo claim is only as good as
the citation attached to it.

`GET /sessions/{id}/verify` re-reads the stored rows rather than the in-memory
transcript, so an edit made outside the application is exactly what it detects.

**What this does not defend against, plainly:** the signing key sits beside the
data, so anyone who can edit the database can also read the key and re-sign a
forged chain. This is tamper-**evidence**, not tamper-proofing. It catches
corruption, partial writes, and any edit made through or around the application.
Resisting a determined operator needs the key held somewhere COUNSEL cannot
reach, which is a deployment decision rather than a code one.

---

## The Auditor

Four mechanical rules, run on every turn. Deterministic, no model.

| Rule | What it catches |
|---|---|
| `fabricated-source` | A citation-shaped attribution with no resolvable citation behind it |
| `unsupported-number` | A hard figure with no source and no hedge |
| `ad-hominem` | An attack on a seat rather than on its argument |
| `stage-rule` | Critique during Ideate; a solution proposed during Empathise or Define |

### Why `fabricated-source` exists

Phase B measured five mandates arguing a real decision, and **every source in
the sample was invented** — a Q3 2024 footfall report, a Dubai Chamber
statistic, a Q2 store audit with a page number, Clause 4.2 of a Global
Operations Policy, a customer quote. None of them exist. The room had been given
no documents and, rather than saying so, all five seats produced exactly the
citation-shaped evidence their mandates ask for. The CFO's prompt says *"a number
needs a source and a date"* — so the model supplied a source and a date.

That is the strongest available argument for a mechanical gate, and why
prompting was never going to be enough. **A mandate told to cite will cite. Only
a check that opens the citation knows whether it resolves.**

### This was tested, not assumed

The obvious objection is that a firmer instruction would fix it. It was tried
and measured
([`B7-prompting-does-not-stop-fabrication.json`](results/B7-prompting-does-not-stop-fabrication.json)).
The prompt now says, when the room has no documents: *"Do not invent a report, a
statistic or a citation."*

It **did** fix one thing. An unconditional mention of `<untrusted_content>` had
been producing turns that argued about *"the untrusted_content cites a 2022
study"* — a document that never existed. Naming a container was enough for the
model to invent something to put in it, so the fence instruction is now emitted
only when there is fenced material. An instruction about evidence that does not
exist is not a safeguard; it is a prompt for a hallucination.

It did **not** fix fabrication. The very next measured turn produced *"a 22%
higher operational expense ratio than the Greenlam average (Q3 2024 report)"* —
and, in the same breath, correctly volunteered its declared blind spot. The
mandate is being followed. The fabrication is not disobedience, and no wording
was going to remove it. The Auditor flagged both.

### Measured

[`B5-auditor-recall.json`](results/B5-auditor-recall.json):

| Corpus | Recall | False-positive rate |
|---|---:|---:|
| Seeded, 42 cases (24 breaches, 18 clean) | **1.000** | **0.000** |

That number is worth less than it looks, and the script says so: the corpus was
authored alongside the rules, so it measures internal consistency more than
generalisation. It is still built to be hard — the 18 clean cases deliberately
reuse the breaches' vocabulary, because recall bought with false positives is
worthless. *"The CFO is short-sighted"* must be flagged and *"the CFO's payback
calculation is short-sighted about the downside"* must not, or the Auditor gets
switched off and then protects nothing.

**The honest measurement is held-out**: the five real `qwen3:8b` turns from the
B4 run, authored by the model before the Auditor existed. **5 of 5 seats are
flagged for a fabricated source.**

That held-out run also found the one real bug. Hedging had been judged per
*turn*, so a turn opening *"If conversion drops below 12%…"* immunised its own
later assertion that *"the plant has a proven 15% conversion rate"*. A hedge now
covers the sentence it is attached to and no other. Neither the seeded corpus
nor any hand-written test would have found that.

### What the Auditor does not catch

A confident, well-hedged, entirely **wrong** argument with no numbers in it
passes cleanly. The Auditor checks the *form* of an argument — sourcing, target,
stage discipline — not its truth. Truth is the room's job, and the outcome
ledger's.

---

## Honest limitations

- **These agents' expertise is prompt-defined.** Putting the prompts in files
  the user can open is the difference between admitting that and hiding it.
- **A turn is speech, not record.** COUNSEL does not stop a seat saying something
  unsupported in a round, any more than a boardroom does. It stops that claim
  reaching the memo, and marks it where it was said.
- **The Auditor is rules, not judgement.** It will miss a novel phrasing. Every
  rule it has was added because something got past it.

## Reproducing anything on this page

```bash
uv run python scripts/audit_recall.py    # the Auditor's recall and held-out run
uv run pytest tests/crew tests/invariants -q
```
