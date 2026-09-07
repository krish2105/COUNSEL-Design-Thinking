"""The chain the SERVICE builds, not the one the tests build.

Every other test constructs its LLMChain from phase_c_stub(). deps.llm() built
a bare StubProvider(), which answers complete() with prose and cannot answer
structured() at all. With no provider keys the deployed service runs entirely
on that terminal stub, so on the live site every framing, idea, score and memo
returned 500 —

    LLMError: no provider returned a valid Framing after 2 attempts:
    ['stub: ValueError', 'stub: ValueError']

— while the Room worked, because a debate turn is complete() and a framing is
structured(). 403 tests were green throughout.

The lesson is the one Render's SQLite already taught: a test that substitutes a
better substrate than production ships tests the product for a machine nobody
runs. These tests use deps.llm() itself.
"""

from __future__ import annotations

import pytest

from services.api import deps
from services.api.core.llm import Message
from services.api.core.schemas import TASKS
from services.api.crew.mandate import SEATING


@pytest.fixture
def production_chain(tmp_path, monkeypatch):
    """deps.llm() with no keys and no Ollama, which is the deployed configuration."""
    monkeypatch.setenv("COUNSEL_DB", str(tmp_path / "chain.db"))
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:1")
    for name in ("GEMINI_API_KEY", "GROQ_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    for cached in (deps.llm, deps.quota, deps.db):
        cached.cache_clear()
    from services.api.core.settings import settings

    settings.cache_clear()
    yield deps.llm()
    for cached in (deps.llm, deps.quota, deps.db):
        cached.cache_clear()
    settings.cache_clear()


@pytest.mark.parametrize("task", sorted(TASKS))
def test_the_deployed_chain_answers_every_structured_task(production_chain, task):
    """A stage that cannot produce its artefact is a 500 on a public URL."""
    model_cls = TASKS[task]
    obj, response = production_chain.structured(
        f"task: {task}\nYou are a seat on a board.",
        [Message("user", "Should RAQIB pilot in a Dubai hypermarket or a Greenlam plant first?")],
        model_cls=model_cls,
    )
    assert isinstance(obj, model_cls), f"{task} did not validate as {model_cls.__name__}"
    assert response.provider == "stub", "with no keys the chain must land on the stub"


@pytest.mark.parametrize("task", sorted(TASKS))
def test_the_deployed_chain_answers_per_seat_task_ids(production_chain, task):
    """Stage tasks carry the seat ("score:cfo"), so every seat variant must resolve.

    register_all() binds both the bare id and one per seat. A chain wired with
    only the bare ids would pass the test above and still 500 in the product.
    """
    model_cls = TASKS[task]
    for seat in SEATING:
        obj, _ = production_chain.structured(
            f"task: {task}:{seat}\nYou are the {seat}.",
            [Message("user", "hypermarket or plant?")],
            model_cls=model_cls,
        )
        assert isinstance(obj, model_cls), f"{task}:{seat} did not validate"


def test_the_deployed_chain_still_refuses_to_pay(production_chain, monkeypatch):
    """The terminal stub changed; the money boundary must not have."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-this-would-cost-money")
    assert all(p.name != "anthropic" or not p.available() for p in production_chain.providers), (
        "Anthropic became selectable when the terminal stub was swapped"
    )
