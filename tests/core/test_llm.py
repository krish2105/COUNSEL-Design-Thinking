"""The provider chain is the load-bearing promise of this project.

COUNSEL claims zero paid inference. That claim is only worth anything if it is
enforced somewhere an accident cannot get past — so it is enforced here, in
tests, rather than in a config file a future edit could flip.
"""

from __future__ import annotations

import pytest

from services.api.core import killswitch
from services.api.core.llm import (
    AnthropicProvider,
    LLMChain,
    Message,
    StubProvider,
)
from services.api.core.quota import Quota


class FlakyProvider:
    """A provider that is configured but fails when actually called."""

    def __init__(self, name: str, *, reachable: bool = True) -> None:
        self.name = name
        self.model = f"{name}-test"
        self._reachable = reachable
        self.calls = 0

    def available(self) -> bool:
        return self._reachable

    def complete(self, system, messages, **kw):
        self.calls += 1
        raise RuntimeError(f"{self.name} exploded")


@pytest.fixture(autouse=True)
def _released():
    killswitch.release()
    yield
    killswitch.release()


@pytest.fixture
def quota():
    return Quota({"ollama": 100, "gemini": 100, "groq": 100, "stub": 10_000})


def _msgs():
    return [Message("user", "Should we pilot in a hypermarket or a plant first?")]


def test_chain_falls_through_to_the_next_free_provider(quota):
    ollama = FlakyProvider("ollama")
    gemini = FlakyProvider("gemini")
    groq = FlakyProvider("groq", reachable=False)
    stub = StubProvider()

    chain = LLMChain([ollama, gemini, groq, stub], quota)
    r = chain.complete("You are the CFO.", _msgs())

    assert r.provider == "stub"
    assert ollama.calls == 1, "ollama should have been tried first"
    assert gemini.calls == 1, "gemini should have been tried after ollama failed"
    assert groq.calls == 0, "an unavailable provider is skipped, not called"
    assert [d.split("(")[0] for d in r.degraded_from] == ["ollama", "gemini", "groq"]
    assert "unreachable" in r.degraded_from[2], "the reason for each skip is recorded"


def test_anthropic_is_never_selected_even_with_a_key(monkeypatch, quota):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-this-would-cost-money")
    anthropic = AnthropicProvider()

    assert anthropic.available() is False
    assert "zero paid inference" in anthropic.why_disabled.lower()

    chain = LLMChain([anthropic, StubProvider()], quota)
    r = chain.complete("You are the CFO.", _msgs())
    assert r.provider == "stub"
    assert r.degraded_from[0].startswith("anthropic")


def test_exhausted_quota_skips_a_provider_rather_than_raising():
    quota = Quota({"ollama": 1, "stub": 10})
    ollama = StubProvider(name="ollama", model="pretend-local")
    chain = LLMChain([ollama, StubProvider()], quota)

    first = chain.complete("s", _msgs())
    assert first.provider == "ollama"
    assert quota.remaining("ollama") == 0

    second = chain.complete("s", _msgs())
    assert second.provider == "stub", "exhaustion degrades; it does not raise"
    assert "quota" in second.degraded_from[0]


def test_quotas_are_counted_as_requests_not_tokens():
    quota = Quota({"stub": 3})
    chain = LLMChain([StubProvider()], quota)
    for _ in range(3):
        chain.complete("s", [Message("user", "x" * 5000)])
    assert quota.remaining("stub") == 0, "a 5000-char prompt costs exactly one request"


def test_the_stub_is_deterministic_across_constructions():
    a = StubProvider().complete("You are the CFO.", _msgs())
    b = StubProvider().complete("You are the CFO.", _msgs())
    assert a.text == b.text and a.text != ""

    c = StubProvider().complete("You are the CMO.", _msgs())
    assert c.text != a.text, "a different mandate must produce different output"


def test_every_response_carries_its_own_provenance(quota):
    r = LLMChain([StubProvider()], quota).complete("s", _msgs(), speaker="cfo")
    assert r.provider and r.model
    assert r.speaker == "cfo", "the speaker seam exists from Phase A for per-agent voice"
    assert r.latency_s >= 0


def test_the_chain_never_raises_when_every_provider_fails(quota):
    chain = LLMChain([FlakyProvider("ollama"), FlakyProvider("gemini")], quota)
    r = chain.complete("s", _msgs())
    assert r.provider == "stub", "the stub is the terminal fallback, always appended"


def test_kill_switch_refuses_before_any_provider_is_touched(quota):
    ollama = FlakyProvider("ollama")
    chain = LLMChain([ollama, StubProvider()], quota)
    killswitch.engage("owner pulled the cord")

    with pytest.raises(killswitch.KillSwitchEngaged) as exc:
        chain.complete("s", _msgs())
    assert "owner pulled the cord" in str(exc.value)
    assert ollama.calls == 0, "nothing is called once the switch is engaged"
