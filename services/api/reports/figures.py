"""Every number the report is allowed to print.

WHY A REGISTRY AND NOT A TEMPLATE VARIABLE
------------------------------------------
The standing rule is that every figure in any generated document traces to
docs/results/. The weak way to honour that is to look up the numbers while
writing and paste them in — which is true on the day and quietly false a week
later, when a re-measurement moves a value and the document keeps the old one.

So a figure is DECLARED here with the file and the path inside it, and read at
build time. `Figure.value()` raises if the file is missing or the path is not
there, and the report build fails rather than emitting a stale or invented
number. Deleting a results file breaks the build. That is the intended
behaviour, and there is a test for it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RESULTS = Path(__file__).resolve().parents[3] / "docs/results"


class MissingFigure(RuntimeError):
    """A figure was requested that no results file supports."""


@dataclass(frozen=True)
class Figure:
    key: str
    file: str
    #: Dotted path into the JSON, with [n] for list indices.
    path: str
    unit: str = ""
    note: str = ""

    def value(self) -> Any:
        source = RESULTS / self.file
        if not source.exists():
            raise MissingFigure(
                f"figure {self.key!r} needs {self.file}, which does not exist. "
                "Regenerate it (see docs/README or the scripts/ directory) rather than "
                "typing the number in."
            )
        node: Any = json.loads(source.read_text())
        for part in self.path.split("."):
            if part.endswith("]") and "[" in part:
                name, index = part[:-1].split("[")
                if name:
                    node = node[name]
                node = node[int(index)]
            else:
                node = node[part]
        return node

    def rendered(self) -> str:
        v = self.value()
        if isinstance(v, float):
            v = f"{v:g}"
        return f"{v}{self.unit}"


FIGURES: tuple[Figure, ...] = (
    Figure(
        "embed.bge_en_hi",
        "A5-embedding-spike.json",
        "candidates[0].en_hi",
        note="bge-m3 English-Hindi cosine",
    ),
    Figure("embed.bge_en_ar", "A5-embedding-spike.json", "candidates[0].en_ar"),
    Figure("embed.bge_control", "A5-embedding-spike.json", "candidates[0].en_unrelated_control"),
    Figure("embed.nomic_en_hi", "A5-embedding-spike.json", "candidates[1].en_hi"),
    Figure("embed.nomic_control", "A5-embedding-spike.json", "candidates[1].en_unrelated_control"),
    Figure("auditor.recall", "B5-auditor-recall.json", "recall"),
    Figure("auditor.fpr", "B5-auditor-recall.json", "false_positive_rate"),
    Figure("auditor.n_cases", "B5-auditor-recall.json", "n_cases"),
    Figure("auditor.n_breaches", "B5-auditor-recall.json", "n_breaches"),
    Figure(
        "auditor.held_out_flagged",
        "B5-auditor-recall.json",
        "held_out_evaluation.seats_with_a_fabricated_source_flag",
    ),
    Figure("auditor.held_out_of", "B5-auditor-recall.json", "held_out_evaluation.of_seats"),
    Figure(
        "debate.before_total",
        "B4-debate-latency.json",
        "phase_d_remeasurement.measured_before.three_round_total_seconds",
        unit="s",
    ),
    Figure(
        "debate.after_total",
        "B4-debate-latency.json",
        "phase_d_remeasurement.measured_after.three_round_equivalent_seconds",
        unit="s",
    ),
    Figure("debate.target", "B4-debate-latency.json", "target_seconds", unit="s"),
    Figure("decision.margin", "C6-real-decision-run.json", "ranking.margin"),
    Figure("decision.hypermarket", "C6-real-decision-run.json", "ranking.hypermarket"),
    Figure("decision.plant", "C6-real-decision-run.json", "ranking.plant"),
    Figure("chamber.edges_before", "D1-chamber-edges.json", "before_any_facilitation_rule.edges"),
    Figure("chamber.edges_after", "D1-chamber-edges.json", "after_adding_the_rule.edges"),
    Figure("chamber.turns", "D1-chamber-edges.json", "after_adding_the_rule.turns"),
    Figure("owasp.covered", "E1-owasp-scorecard.json", "n_covered"),
    Figure("owasp.gaps", "E1-owasp-scorecard.json", "n_gaps"),
    Figure("owasp.assertions", "E1-owasp-scorecard.json", "n_assertions"),
)

BY_KEY = {f.key: f for f in FIGURES}


def figure(key: str) -> str:
    """The rendered value, or an exception. Never a placeholder."""
    if key not in BY_KEY:
        raise MissingFigure(f"no figure declared for {key!r}")
    return BY_KEY[key].rendered()


def all_figures() -> dict[str, str]:
    return {f.key: f.rendered() for f in FIGURES}
