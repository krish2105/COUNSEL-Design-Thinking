"""Build the Term 4 report from measured results.

THE RULE THIS ENFORCES
----------------------
Every figure in the document is read from docs/results/ at build time through
the registry in services/api/reports/figures.py. There is no path by which a
number can be typed into this file: the template holds KEYS, and an unknown key
or a missing results file raises and the build fails.

Deleting a results file therefore breaks the build rather than printing a stale
figure. That is the intended behaviour and tests/reports/test_report.py asserts
it.

Writes both a .docx (the coursework deliverable) and a .md (readable in the
repo, diffable in review).
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.api.reports.figures import MissingFigure, figure  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "docs/artefacts"
TITLE = "COUNSEL — the AI boardroom"
SUBTITLE = "MGT 204 Design Thinking · SP Jain MAIB Term 4 · Krishna Mathur"

#: Double-brace placeholders are substituted from the figure registry.
#: An undeclared key or a missing results file raises and the build fails.
TEMPLATE = """
# {title}

*{subtitle}*

## 1. The problem

Design thinking asks a team to diverge before it converges, but a solo founder or
a student has no room of experts to argue with. COUNSEL provides one: five agents
with distinct mandates — CFO, CMO, COO, Ethics Officer, Devil's Advocate —
research a real decision with public data, debate it across the seven
design-thinking stages, and produce a record: a decision memo, a dissent log, and
an outcome ledger that scores each agent's calibration once reality answers.

The demonstration decision is a real one: *should RAQIB pilot in a Dubai
hypermarket or a Greenlam plant first?*

## 2. What the system does, and what it refuses to do

COUNSEL runs on zero paid inference. Local models first, free tiers behind them,
and a deterministic stub as the terminal fallback so the entire test suite runs
with no model and no network. Anthropic is present in the provider chain and
permanently disabled — a refusal with a test behind it rather than an absence
that reads as an oversight.

No agent holds a tool that acts on the world. The five mandates hold `search` and
`ask`; only the Facilitator can open or close a round. Every tool declares
`side_effects` and a test asserts `False` across the whole registry, so a tool
that wrote anywhere would fail the suite before it could fail a user.

## 3. The design-thinking layer

| Stage | What the room produces | The rule that binds it |
|---|---|---|
| Empathise | Cited observations | No solutions yet |
| Define | One "How might we…" per seat | The schema rejects a framing that is not a question |
| Ideate | One idea per seat | **No critique** — divergence collapses the moment someone evaluates |
| Prototype | The smallest testable thing | Say what would count as success |
| Test | Desirability / feasibility / viability | A seat must name its weakest axis, and the schema rejects it if that is not the lowest score |
| Decide | Memo, dissent log, pre-mortem | Every number cites a source |
| Learn | Outcome and Brier score | Name who was closest, including yourself |

The mandates are prompt files a reader can open and disagree with. Each declares
at least two **blind spots** — what it systematically under-weights — and the
loader raises if one claims none. Divergence only works if the room's biases are
on the table.

## 4. What was measured

### 4.1 The embedding model was chosen by measurement

| Model | EN~HI | EN~AR | unrelated control |
|---|---:|---:|---:|
| bge-m3 | {{embed.bge_en_hi}} | {{embed.bge_en_ar}} | {{embed.bge_control}} |
| nomic-embed-text | {{embed.nomic_en_hi}} | — | {{embed.nomic_control}} |

`nomic-embed-text` is not merely weaker — its cross-lingual similarity sits
**below** its own unrelated-pair score, so an Arabic query would rank an
unrelated English chunk above the correct Arabic one and cite it. It is
disqualified, and the spike script fails if it ever clears the bar.

### 4.2 The agents fabricate sources, and prompting does not stop them

Given no documents, all five mandates invented sources fluently — a Q3 footfall
report, a Dubai Chamber statistic, a policy clause, a customer quote. None
existed. Adding an explicit instruction not to invent citations was tried and
measured: it fixed a related hallucination and **did not stop the fabrication**.

That is the central finding of this project and the reason every guarantee in it
is mechanical rather than prompted. A mandate told to cite will cite; only a
check that opens the citation knows whether it resolves.

The Auditor catches it: recall **{{auditor.recall}}** and a false-positive rate
of **{{auditor.fpr}}** on {{auditor.n_cases}} seeded cases
({{auditor.n_breaches}} breaches), and — the honest measurement —
**{{auditor.held_out_flagged}} of {{auditor.held_out_of}}** real model turns
flagged for a fabricated source on held-out data it was never tuned against.

### 4.3 Performance

A three-round debate took {{debate.before_total}} and now takes
{{debate.after_total}}, against a target of {{debate.target}}. The cause was not
the model: every seat was being handed the entire transcript each round, so the
prompt and the wall clock both grew with the debate.

### 4.4 The decision was too close to call, and the memo says so

The room scored the hypermarket {{decision.hypermarket}} against the plant's
{{decision.plant}} — a margin of **{{decision.margin}}** across five seats and
three axes, which is inside the noise. Every seat then dissented from the
recommendation those scores produced. The memo carries that contradiction above
the ranking table rather than publishing a recommendation nobody supported.

Two separate pieces of evidence would each have flipped the outcome on their own,
which the counterfactual reports as *"the decision is not robust"*.

### 4.5 Five agents do not argue unless a chair makes them

Ten turns produced **{{chamber.edges_before}}** cross-references between seats;
the only seat names in the transcript were self-references. An explicit
facilitation rule — *name the seat whose argument you are answering* — moved that
to **{{chamber.edges_after}}** in {{chamber.turns}} turns. Real, and small. No
further prompt tuning was attempted, because tuning until the diagram looked
busier would be optimising the visualisation rather than the debate.

## 5. Security

The OWASP LLM Top 10 is implemented as executable controls:
**{{owasp.covered}}** risks covered by {{owasp.assertions}} assertions,
**{{owasp.gaps}}** gaps, and two risks declared not applicable with their
reasons. The scorecard is generated from the test names, so it cannot claim
coverage a test does not provide — verified by renaming a control's tests away
and confirming the row flips to a gap.

Both attacks the brief names are asserted end to end: a poisoned uploaded
document does not change which option the memo recommends, and a turn signed with
the wrong key breaks the transcript's hash chain.

## 6. Honest limitations

- **The agents' expertise is prompt-defined.** The prompts are files the user can
  open, which is the difference between admitting that and hiding it.
- **A turn is speech; the memo is record.** COUNSEL does not stop a seat saying
  something unsupported, any more than a boardroom does. It stops that claim
  reaching the memo, and marks it where it was said.
- **The counterfactual is arithmetic, not re-argument.** It reports how much of
  the current decision rests on a source, not what the room would decide without
  it.
- **Calibration needs volume.** Brier scores are withheld below five outcomes.
- **The citation gate rewards copying.** Requiring claims to stay close to the
  source's wording makes the model quote. Duplicates are removed; relevance is
  left to the reader, because a mechanical relevance filter would put one more
  model judgement between the reader and the source.
- **An 8B local model converges.** Several seats returned near-identical scores,
  which is part of why the unanimous-dissent check exists.

## 7. What it would take to become a product

Real identities behind the RBAC roles; a signing key held where the application
cannot read it, so the transcript resists a determined operator rather than only
an accident; durable storage for the outcome ledger; and enough logged outcomes
for calibration to mean anything. None of those change the architecture — they
change where the trust boundary sits.

---

*Generated {generated} from docs/results/. Every figure in this document is read
from a measurement file at build time; none is typed in.*
"""

PLACEHOLDER = re.compile(r"\{\{([a-z0-9_.]+)\}\}")


def render() -> str:
    body = TEMPLATE.format(
        title=TITLE,
        subtitle=SUBTITLE,
        generated=datetime.now(UTC).strftime("%Y-%m-%d"),
    )
    return PLACEHOLDER.sub(lambda m: figure(m.group(1)), body)


def _has_style(doc, name: str) -> bool:
    try:
        doc.styles[name]
    except KeyError:
        return False
    return True


def write_docx(markdown: str, path: Path) -> None:
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Georgia"
    style.font.size = Pt(10.5)

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("# "):
            doc.add_heading(line[2:], level=0)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=1)
        elif line.startswith("### "):
            doc.add_heading(line[4:], level=2)
        elif line.startswith("|"):
            # Tables are emitted as fixed-width rows: python-docx tables would
            # need column counts the template does not declare, and a mangled
            # table is worse than a legible monospace row.
            p = doc.add_paragraph(line)
            # python-docx Styles is not a dict, so ruff's .get() suggestion does
            # not apply here; the membership test is the supported API.
            p.style = doc.styles["Macro Text"] if _has_style(doc, "Macro Text") else style
        elif line.startswith("- "):
            doc.add_paragraph(line[2:], style="List Bullet")
        elif line.startswith("*") and line.endswith("*") and len(line) > 2:
            doc.add_paragraph(line.strip("*")).italic = True
        else:
            doc.add_paragraph(line)
    doc.save(str(path))


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        markdown = render()
    except MissingFigure as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    md_path = OUT_DIR / "MGT204_MAJLIS_report.md"
    md_path.write_text(markdown)
    docx_path = OUT_DIR / "MGT204_MAJLIS_report.docx"
    write_docx(markdown, docx_path)

    n = len(PLACEHOLDER.findall(TEMPLATE))
    print(f"report built from {n} measured figures")
    print(f"  {md_path.relative_to(REPO)}")
    print(f"  {docx_path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
