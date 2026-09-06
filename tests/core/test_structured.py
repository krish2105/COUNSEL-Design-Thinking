"""Structured output, and what happens when a model does not cooperate.

`complete` is total: a provider failure degrades to the next one. `structured`
deliberately is not. A turn that comes back as prose instead of a Score is not a
degraded answer a caller can render anyway — it is an absence, and the stage
that asked for it has to know.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from services.api.core.llm import (
    LLMChain,
    LLMError,
    Message,
    StubProvider,
    _gemini_schema,
    _json_slice,
)
from services.api.core.quota import Quota
from services.api.core.schemas import TASKS, Framing, Score
from services.api.crew.stubs import phase_c_stub


@pytest.fixture
def chain():
    return LLMChain([phase_c_stub()], Quota({"stub": 10_000}))


@pytest.mark.parametrize("task", sorted(TASKS))
def test_every_phase_c_task_round_trips_with_no_model(task, chain):
    """The whole of Phase C must be testable in CI, where there is no Ollama."""
    obj, response = chain.structured(
        f"task: {task}:cfo\nYou are the CFO.",
        [Message("user", "hypermarket or plant?")],
        model_cls=TASKS[task],
    )
    assert isinstance(obj, TASKS[task])
    assert response.provider == "stub"


def test_the_stub_is_deterministic_but_seat_dependent(chain):
    a, _ = chain.structured("task: score:cfo\nCFO", [Message("user", "q")], model_cls=Score)
    b, _ = chain.structured("task: score:cfo\nCFO", [Message("user", "q")], model_cls=Score)
    c, _ = chain.structured("task: score:cmo\nCMO", [Message("user", "q")], model_cls=Score)
    assert a == b, "identical input must give identical output, or replay means nothing"
    assert a != c, "a canned object would make every seat agree; this is not a mock"


def test_prose_instead_of_json_raises_rather_than_degrading():
    class Chatty(StubProvider):
        def __init__(self):
            super().__init__(name="chatty", model="prose")

        def complete(self, system, messages, **kw):
            return super().complete(system, messages, **kw)

    chatty = Chatty()  # no handler registered, so it returns prose
    chain = LLMChain([chatty], Quota({"chatty": 10, "stub": 10}))
    with pytest.raises(LLMError, match="no provider returned a valid Score"):
        chain.structured("task: unknown\nx", [Message("user", "q")], model_cls=Score)


def test_a_malformed_first_reply_is_retried_once_with_the_error():
    """Enough for a small local model to add a field it forgot, and cheap."""
    calls: list[str] = []

    class FlakyOnce(StubProvider):
        name = "flaky"

        def complete(self, system, messages, **kw):
            calls.append(messages[-1].content)
            if len(calls) == 1:
                return super().complete("task: nothing\n", messages, **kw)
            return super().complete("task: score:cfo\nCFO", messages, **kw)

    provider = FlakyOnce(name="flaky", model="m")
    from services.api.crew.stubs import register_all

    register_all(provider)
    chain = LLMChain([provider], Quota({"flaky": 10, "stub": 10}))

    obj, _ = chain.structured("task: score:cfo\nCFO", [Message("user", "q")], model_cls=Score)
    assert isinstance(obj, Score)
    assert len(calls) == 2
    assert "did not validate" in calls[1], "the retry must carry the validation error"


def test_a_schema_violation_is_caught_by_the_model_not_the_prompt():
    with pytest.raises(ValidationError):
        Score(
            option="plant",
            desirability=5,
            feasibility=2,
            viability=4,
            weakest_on="desirability",
            confidence=0.7,
            reason="x" * 20,
        )
    with pytest.raises(ValidationError):
        Framing(hmw="We should build a loyalty tier", why_it_matters="x" * 20, whose_problem="y")


def test_the_gemini_schema_drops_what_gemini_rejects():
    """Gemini takes a subset of OpenAPI, not JSON Schema. Hand-writing a second
    schema per model would let the two drift, so the pydantic one is flattened."""
    flat = _gemini_schema(Score.model_json_schema())
    rendered = str(flat)
    for rejected in ("$defs", "$ref", "additionalProperties", "exclusiveMinimum"):
        assert rejected not in rendered
    assert "properties" in flat and "option" in flat["properties"]


@pytest.mark.parametrize(
    "reply",
    [
        '{"a": 1}',
        'Here you go:\n```json\n{"a": 1}\n```',
        '```\n{"a": 1}\n```',
        'Certainly. {"a": 1} Hope that helps.',
    ],
)
def test_json_is_recovered_from_a_chatty_reply(reply):
    """Schema-constrained decoding makes this unnecessary on Ollama and Gemini,
    but Groq's JSON mode will still wrap an object in fences or a sentence."""
    assert _json_slice(reply) == '{"a": 1}'


def test_a_reply_with_no_json_at_all_is_refused():
    with pytest.raises(ValueError, match="no JSON object"):
        _json_slice("I would rather explain it in words.")
