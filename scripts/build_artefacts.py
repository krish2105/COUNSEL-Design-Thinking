"""Deck, viva and demo script — from the same figure registry as the report.

One registry means the deck cannot quote a number the report contradicts. If a
measurement changes, everything that cites it changes together or the build
fails; there is no path by which a slide keeps a figure the results no longer
support.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.api.reports.figures import MissingFigure, figure  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs/artefacts"
PLACEHOLDER = re.compile(r"\{\{([a-z0-9_.]+)\}\}")

DECK = """
# COUNSEL — slide outline

*MGT 204 Design Thinking · 12 slides · Krishna Mathur*

Each slide names the one thing it must land. Figures come from docs/results/.

---

**1 · The gap**
Design thinking asks you to diverge before you converge. A solo founder has
nobody to diverge with.
*Land:* the problem is structural, not motivational.

**2 · The room**
Five mandates — CFO, CMO, COO, Ethics Officer, Devil's Advocate — plus a
Facilitator and an Auditor. Each mandate is a file you can open.
*Land:* these are not five voices of one model; the difference is legible.

**3 · Blind spots are the substance**
Every mandate declares at least two things it under-weights. The loader raises
if one claims none.
*Land:* divergence only works if the biases are on the table.
*Show:* the Crew tab.

**4 · The chamber**
A round table computed entirely from the signed transcript. Scrub the replay.
*Land:* the picture cannot disagree with the record because it has no state.

**5 · The finding**
Given no documents, all five seats invented sources — a Q3 report, a Chamber
statistic, a policy clause, a customer quote. An explicit instruction not to
was tried and **did not stop it**.
*Land:* this is why every guarantee here is mechanical, not prompted.

**6 · The Auditor**
Recall {{auditor.recall}}, false-positive rate {{auditor.fpr}} on
{{auditor.n_cases}} seeded cases — and {{auditor.held_out_flagged}} of
{{auditor.held_out_of}} on held-out real model turns.
*Land:* the held-out number is the one that counts.

**7 · The memo**
Every body claim resolves to a verbatim span. What fails is quarantined under
*Asserted without evidence*, never dropped.
*Land:* dropping it would make the memo look better evidenced than the decision.

**8 · Too close to call**
Hypermarket {{decision.hypermarket}} to plant's {{decision.plant}} — a margin of
{{decision.margin}}. Every seat then dissented from the recommendation those
scores produced.
*Land:* the memo says so above the table instead of publishing it quietly.

**9 · What would change our mind**
Two separate pieces of evidence would each flip it alone. Sensitivity analysis,
not a re-argument, and labelled as such.
*Land:* the honest output is often "this is not robust".

**10 · Security**
{{owasp.covered}} OWASP risks covered by {{owasp.assertions}} assertions,
{{owasp.gaps}} gaps, scorecard generated from the tests.
*Show:* the live attack on the Security tab.
*Land:* no agent holds a tool that can act.

**11 · Performance and constraint**
{{debate.before_total}} to {{debate.after_total}} for three rounds against a
{{debate.target}} target. Zero paid inference throughout.
*Land:* the free-tier constraint forced better engineering, not worse.

**12 · Limits**
Prompt-defined expertise. Calibration needs volume. The citation gate rewards
copying. Five agents barely argue unless a chair makes them
({{chamber.edges_before}} cross-references in ten turns, {{chamber.edges_after}}
after a facilitation rule).
*Land:* I know what this does not do.
"""

VIVA = """
# COUNSEL — 15 viva questions, with answers

Answers are grounded in what was measured, including the failures. Where a
number appears it is read from docs/results/.

---

**1. Why bounded, side-effect-free agents?**
Because prompting cannot keep that promise. "Do not post anything" is a request,
and an injected instruction is a competing request. COUNSEL keeps it by there
being nothing to call: every tool declares `side_effects` and a test asserts
`False` across the whole registry. The live attack asks for `publish_memo`; that
tool does not exist.

**2. How are citations enforced?**
Retrieval-then-verify. Candidate spans come from the corpus, and a claim only
survives if it shares a verbatim phrase of 24+ characters with the span it
cites. The quote is read back out of the database and compared. A test asserts
that a sentence about penguins does not acquire a citation merely by ranking
near one.

**3. What does the Auditor actually catch?**
Four mechanical rules: fabricated source, unsupported number, ad-hominem, and
stage-rule breach. Recall {{auditor.recall}} with a {{auditor.fpr}}
false-positive rate on {{auditor.n_cases}} seeded cases, and
{{auditor.held_out_flagged}} of {{auditor.held_out_of}} on held-out turns.

**4. That seeded number looks too good. Is it?**
Yes, and the script says so. I wrote the corpus and the rules together, so it
measures internal consistency more than generalisation. The held-out run against
real model turns is the honest one — and it found a bug the seeded corpus never
would: hedging was judged per turn, so "If conversion drops below 12%…"
immunised a later "the plant has a proven 15% conversion rate".

**5. What does the Auditor miss?**
A confident, well-hedged, entirely wrong argument with no numbers in it. It
checks the *form* of an argument — sourcing, target, stage discipline — not its
truth. Truth is the room's job and the ledger's.

**6. Where could the 3D view mislead?**
Three ways, all closed. Glow is recency, not importance, so a seat that spoke a
lot earlier fades. Every edge is drawn identically, so there is no thickness
channel to misread as intensity. And an edge means one seat *named* another —
not that it agreed — which the caption says under the picture.

**7. Why do so few edges appear?**
Because the seats barely engage. Ten turns produced {{chamber.edges_before}}
cross-references; the only seat names were self-references. A facilitation rule
moved it to {{chamber.edges_after}}. I stopped tuning there: making the picture
busier would have been optimising the visualisation rather than the debate.

**8. What did the free-tier constraint force you to do better?**
Four things. A provider abstraction rather than an SDK call, so which vendor
serves a turn is not structural. A deterministic stub that is the CI substrate,
so the entire suite runs with no model. Request-count quotas, because a token
budget I cannot verify is theatre. And a bounded prompt — the thing that took a
three-round debate from {{debate.before_total}} to {{debate.after_total}}.

**9. Why is Anthropic in the chain if it is disabled?**
Because an absence reads as an oversight and invites someone to fill it. A
refusal with a test behind it is a stated position: the test sets the API key and
asserts the provider stays unselectable.

**10. Your embedding choice — defend it.**
Measured, not chosen from a leaderboard. bge-m3 puts a Hindi translation at
{{embed.bge_en_hi}} against an unrelated control at {{embed.bge_control}}.
nomic-embed-text puts it at {{embed.nomic_en_hi}} against
{{embed.nomic_control}} — *below* its own control, so it would rank an unrelated
English chunk above the correct Arabic one and cite it. Disqualified, not
deprioritised.

**11. Your memo recommended something every agent disagreed with. Explain.**
The scores gave hypermarket {{decision.hypermarket}} to plant's
{{decision.plant}} — a margin of {{decision.margin}} across five seats and three
axes, inside the noise. The prose round said what 1–5 integer scoring was too
coarse to express. The memo now carries that contradiction above the ranking
table; a recommendation nobody supports should not be published under an
authoritative-looking number.

**12. Is the transcript really tamper-proof?**
No — tamper-*evident*. The signing key sits beside the data, so anyone who can
edit the database can re-sign a forged chain. It catches corruption, partial
writes, and any edit made through or around the application, which is what a
hash chain buys. Resisting a determined operator needs the key held where the
application cannot read it, and that is a deployment decision.

**13. What is the counterfactual actually doing?**
Arithmetic over recorded positions. Remove an evidence id, drop the scores that
cited it, re-aggregate. It answers *how much of this decision rests on that
source*, not *what would the room decide without it* — a real re-debate might
land elsewhere. Every surface that shows a flip says so.

**14. When does the Brier score mean anything?**
Not yet. It is withheld below five outcomes and the seats show as pending with
how many more they need. A score across two sessions is noise wearing a decimal
point, and a caller that defaulted it to zero would show a perfectly calibrated
seat that has never been tested.

**15. What would this need to become a product?**
Real identities behind the RBAC roles; the signing key held outside the
application; durable storage for the ledger; and enough logged outcomes for
calibration to mean anything. None of those change the architecture — they move
where the trust boundary sits.
"""

DEMO = """
# COUNSEL — 3-minute demo script

Exactly what to click, and the sentence to say while it loads. Timings assume a
warm model.

---

**0:00 — The Room** · `/room`
> "Five agents with different mandates argue a real decision. This one is mine:
> should RAQIB pilot in a Dubai hypermarket or a Greenlam plant first?"

Click **Open the room**, then **Run a round**.

**0:15 — while it runs (~18s)** · scroll to *What each seat admits it gets wrong*
> "Every mandate declares its own blind spots. The CFO admits it prices profit
> and never option value. That is the design-thinking substance: divergence only
> works if the biases are on the table."

**0:40 — the turns land**
> "Five seats, each signed into a hash chain. Edit one and every turn after it
> breaks."

Point at the CFO's turn.
> "It concedes its blind spot — and it fabricates a source in the same
> paragraph. There is no Q3 footfall report. The Auditor caught it underneath."

**1:10 — the chamber** · drag the replay slider
> "The table is computed from the transcript. An edge means one seat named
> another — nothing about agreement. Watch the argument build."

**1:30 — Decide** · `/decide` → **Score the options**
> "While that scores: this is where 'what would change our mind' stops being a
> sentence and becomes arithmetic."

**2:00 — the counterfactual**
> "Margin of {{decision.margin}}. Two separate pieces of evidence would each
> flip it alone. It says the decision is not robust — and every seat dissented
> from the recommendation the scores produced, which the memo puts above the
> table."

**2:30 — Security** · `/security` → **Run the attack**
> "A poisoned document goes into the live corpus. It is taken, not refused —
> refusing would let an attacker delete evidence. Flagged. The tool it demands
> does not exist. And its claim cannot reach the memo."

**2:50 — close** · `/crew`
> "{{owasp.covered}} OWASP risks covered by {{owasp.assertions}} assertions,
> {{owasp.gaps}} gaps, scorecard generated from the tests. Zero paid inference
> throughout. And every number I have said is in docs/results/."

---

**If the model is cold**, run one round before the audience arrives; the first
round pays a model load the rest do not.

**If nothing works**, `/crew` and `/security` need no model at all and carry the
whole safety story.
"""


def build(name: str, template: str) -> Path:
    rendered = PLACEHOLDER.sub(lambda m: figure(m.group(1)), template)
    path = OUT / name
    path.write_text(rendered)
    return path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        for name, template in (
            ("MGT204_deck_outline.md", DECK),
            ("MGT204_viva_15.md", VIVA),
            ("MGT204_demo_3min.md", DEMO),
        ):
            path = build(name, template)
            print(f"  {path.relative_to(REPO)}")
    except MissingFigure as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
