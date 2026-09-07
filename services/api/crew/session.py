"""A session is one decision, argued over rounds, with a record.

Stages come from the Design Thinking process (MGT 204). Each carries rules the
Auditor enforces — the "no critique" rule during Ideate is the one that matters,
because divergence collapses the moment someone starts evaluating.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from services.api.crew.transcript import Transcript


class Stage(StrEnum):
    EMPATHISE = "Empathise"
    DEFINE = "Define"
    IDEATE = "Ideate"
    PROTOTYPE = "Prototype"
    TEST = "Test"
    DECIDE = "Decide"
    LEARN = "Learn"


#: Rules in force per stage, given verbatim to every mandate and enforced by the
#: Auditor. These are the design-thinking process made executable rather than
#: described: a stage whose rule nothing checks is a heading, not a stage.
STAGE_RULES: dict[Stage, tuple[str, ...]] = {
    Stage.EMPATHISE: (
        "Describe what the people affected actually said or did. Do not propose solutions yet.",
        "Every claim about a person must cite a document span or be marked as an assumption.",
    ),
    Stage.DEFINE: (
        "Propose problem framings as 'How might we...' statements.",
        "Do not argue for a solution. The question is what problem is worth solving.",
    ),
    Stage.IDEATE: (
        "No critique of another seat's idea in this round. Divergence collapses the "
        "moment someone starts evaluating.",
        "Build on other seats' ideas rather than replacing them.",
    ),
    Stage.PROTOTYPE: (
        "Describe the smallest thing that would test the idea, not the finished product.",
        "State what the prototype would have to show to be judged a success.",
    ),
    Stage.TEST: (
        "Score on desirability, feasibility and viability, and say which you are weakest on.",
        "Critique is expected here. Attack arguments, never the seat making them.",
        # Added after measuring a real two-round debate: the seats produced five
        # parallel monologues and named each other exactly zero times. A round
        # where nobody answers anybody is not a debate, it is five position
        # papers filed at once. A chair asks "whose point are you answering?"
        # for the same reason.
        "Name the seat whose argument you are answering. A round where nobody "
        "answers anybody is five position papers, not a debate.",
    ),
    Stage.DECIDE: (
        "State a position and the evidence that would change it.",
        "Every number must cite a source.",
        "Where you disagree with another seat, name it and say what it got wrong.",
    ),
    Stage.LEARN: (
        "Compare what happened to what this room predicted.",
        "Name which seat was closest and which was furthest, including yourself.",
    ),
}


@dataclass
class Session:
    session_id: str
    question: str
    stage: Stage = Stage.DEFINE
    round_no: int = 0
    transcript: Transcript = field(init=False)
    closed: bool = False
    #: Set when a round ended early, with the reason — kill switch, budget, or
    #: a provider chain that could not serve. Never silently empty.
    ended_early: str | None = None

    #: Set by the store so the transcript signs with the installation key
    #: rather than a per-process one. See transcript.session_key.
    signing_key: bytes | None = None

    def __post_init__(self) -> None:
        self.transcript = (
            Transcript(session_id=self.session_id, key=self.signing_key)
            if self.signing_key
            else Transcript(session_id=self.session_id)
        )

    @property
    def rules(self) -> tuple[str, ...]:
        return STAGE_RULES[self.stage]
