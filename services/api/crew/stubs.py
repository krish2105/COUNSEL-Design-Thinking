"""Deterministic, schema-valid artefacts for every Phase C task.

WHY THIS IS NOT A MOCK
----------------------
A mock returns a canned object and tests nothing but the plumbing around it.
These handlers derive their output from a hash of the actual prompt, so two
different seats asked the same question produce different — but stable —
artefacts. That makes the properties Phase C actually claims testable without a
model: that aggregation is order-independent, that the citation gate rejects
what it should, that a counterfactual identifies the right flip, that Brier
scoring separates a calibrated seat from an overconfident one.

It is also what lets the whole of Phase C run in CI, where there is no Ollama
and no key.
"""

from __future__ import annotations

import json

from services.api.core.llm import StubProvider

AXES = ("desirability", "feasibility", "viability")


def _seat_of(system: str) -> str:
    first = system.strip().splitlines()[0] if system.strip() else ""
    return first.rsplit(":", 1)[-1].strip() if ":" in first else "seat"


def _n(digest: str, offset: int, lo: int, hi: int) -> int:
    return lo + int(digest[offset : offset + 2], 16) % (hi - lo + 1)


def framing(system, messages, digest):
    seat = _seat_of(system)
    return json.dumps(
        {
            "hmw": f"How might we test the {seat} case before committing capital?",
            "why_it_matters": (
                f"The {seat} mandate carries the cost of being wrong here, and the room has "
                "not yet agreed what evidence would settle it."
            ),
            "whose_problem": f"the {seat} function and the team that would run the pilot",
        }
    )


def idea(system, messages, digest):
    seat = _seat_of(system)
    return json.dumps(
        {
            "title": f"Shadow pilot, {seat} framing",
            "sketch": (
                f"Run the smallest version of the decision the {seat} mandate can learn from, "
                "on data that already exists, before anyone commits a site. Stub output."
            ),
            "builds_on": None,
        }
    )


def score(system, messages, digest):
    """A stable but seat-dependent score, with an honest weakest axis."""
    seat = _seat_of(system)
    prompt = "\n".join(m.content for m in messages)
    option = "hypermarket" if "hypermarket" in prompt.lower() else "plant"
    values = {
        "desirability": _n(digest, 0, 1, 5),
        "feasibility": _n(digest, 4, 1, 5),
        "viability": _n(digest, 8, 1, 5),
    }
    weakest = min(AXES, key=lambda a: (values[a], a))
    return json.dumps(
        {
            "option": option,
            **values,
            "weakest_on": weakest,
            "confidence": round(0.4 + (int(digest[12:14], 16) % 50) / 100, 2),
            "depends_on": [f"e{int(digest[16:18], 16) % 3 + 1}"],
            "reason": f"Stub reasoning for the {seat} mandate on the {option} option.",
        }
    )


def memo(system, messages, digest):
    return json.dumps(
        {
            "recommendation": "Pilot in the plant first, on the stub provider's deterministic reading.",
            "context": ["The room considered two sites.", "No documents were supplied."],
            "reasoning": ["The plant option scored higher on feasibility."],
            "premortem": ["The pilot ran but taught the room nothing it did not already believe."],
            "would_change_our_mind": ["Comparable conversion data from both sites."],
        }
    )


def dissent(system, messages, digest):
    return json.dumps(
        {
            "agrees": int(digest[:2], 16) % 2 == 0,
            "position": f"Stub position for {_seat_of(system)}, derived from the prompt hash.",
            "would_change_my_mind": "Evidence on the axis this mandate says it is weakest on.",
        }
    )


HANDLERS = {
    "framing": framing,
    "idea": idea,
    "score": score,
    "memo": memo,
    "dissent": dissent,
}


def register_all(stub: StubProvider) -> StubProvider:
    """Wire every Phase C task onto a stub provider."""
    for task, handler in HANDLERS.items():
        stub.register(task, handler)
        # Debate turns carry the seat on the task id ("debate_turn:cfo"), and the
        # stage tasks do the same so a handler can tell the seats apart.
        for seat in ("cfo", "cmo", "coo", "ethics", "devil"):
            stub.register(f"{task}:{seat}", handler)
    return stub


def phase_c_stub() -> StubProvider:
    return register_all(StubProvider())
