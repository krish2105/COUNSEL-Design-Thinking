"""What the room is allowed to hand back.

Phase B's turns are speech: a paragraph, signed, flagged if it misbehaves.
Phase C needs artefacts — objects the memo can be assembled from and the
counterfactual can do arithmetic over. Prose cannot carry a confidence or a
dependency link, so from here the model returns validated structures and the
assembly stays in Python.

Every field that a later stage depends on is required. `depends_on` in
particular is not optional: a score with no stated dependencies cannot be
included in a sensitivity analysis, and silently treating it as depending on
nothing would understate how fragile a decision is.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Axis = Literal["desirability", "feasibility", "viability"]


class Framing(BaseModel):
    """Define — a problem worth solving, stated as a question."""

    hmw: str = Field(min_length=10, max_length=240)
    why_it_matters: str = Field(min_length=10, max_length=500)
    whose_problem: str = Field(min_length=3, max_length=300)

    @model_validator(mode="after")
    def _must_be_a_question(self):
        text = self.hmw.strip().lower()
        if not text.startswith("how might we"):
            raise ValueError(
                "a framing must be a 'How might we...' question. The stage exists to "
                f"keep the room on the problem rather than the answer; got: {self.hmw[:60]!r}"
            )
        return self


class Idea(BaseModel):
    """Ideate — divergence, under the no-critique rule."""

    title: str = Field(min_length=3, max_length=120)
    sketch: str = Field(min_length=20, max_length=900)
    #: The seat whose idea this builds on. The stage rule asks seats to build
    #: rather than replace, so this records whether they actually did.
    builds_on: str | None = Field(default=None, max_length=40)


class Score(BaseModel):
    """Test — desirability, feasibility, viability, and what it rests on."""

    option: str = Field(min_length=1, max_length=160)
    desirability: int = Field(ge=1, le=5)
    feasibility: int = Field(ge=1, le=5)
    viability: int = Field(ge=1, le=5)
    weakest_on: Axis
    #: Used for Brier calibration once the outcome is known. A seat that will
    #: not commit to a number cannot be scored, so this is required.
    confidence: float = Field(ge=0.0, le=1.0)
    #: Evidence ids this score rests on. At least one, enforced — the module
    #: docstring says this is not optional and the schema now says so too.
    #: Measured: given three evidence ids in the prompt and all three cited in
    #: its own prose, a real model still returned depends_on: []. A score that
    #: claims to rest on nothing is excluded from the sensitivity analysis,
    #: which understates how fragile the decision is — silently.
    depends_on: list[str] = Field(min_length=1)
    reason: str = Field(min_length=10, max_length=900)

    @model_validator(mode="after")
    def _weakest_must_be_weakest(self):
        axes = {
            "desirability": self.desirability,
            "feasibility": self.feasibility,
            "viability": self.viability,
        }
        if axes[self.weakest_on] != min(axes.values()):
            raise ValueError(
                f"weakest_on={self.weakest_on} scores {axes[self.weakest_on]} but the "
                f"lowest axis is {min(axes, key=axes.get)} at {min(axes.values())}. "
                "A seat that misreports its own weakest axis cannot be scored honestly."
            )
        return self

    @property
    def total(self) -> int:
        return self.desirability + self.feasibility + self.viability


class MemoDraft(BaseModel):
    """Decide — the raw material of the memo, before the citation gate."""

    recommendation: str = Field(min_length=10, max_length=600)
    context: list[str] = Field(default_factory=list, max_length=8)
    reasoning: list[str] = Field(default_factory=list, max_length=10)
    premortem: list[str] = Field(default_factory=list, max_length=8)
    would_change_our_mind: list[str] = Field(default_factory=list, max_length=8)


class DissentDraft(BaseModel):
    """A seat that does not agree, and what it would take."""

    agrees: bool
    position: str = Field(min_length=10, max_length=900)
    would_change_my_mind: str = Field(min_length=10, max_length=600)


#: Task ids on the first line of a system prompt. StubProvider reads these to
#: choose a deterministic handler, which is what lets all of Phase C run in CI.
TASKS = {
    "framing": Framing,
    "idea": Idea,
    "score": Score,
    "memo": MemoDraft,
    "dissent": DissentDraft,
}
