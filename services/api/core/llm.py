"""Provider-agnostic inference, ordered free-first.

WHY AN ABSTRACTION AND NOT AN SDK CALL
--------------------------------------
COUNSEL has a hard constraint — zero paid inference — and a soft one: it must
run identically on the owner's Mac (where Ollama is a local process) and on a
free Render dyno (where it is not). Which vendor serves a debate turn is an
operational detail. Binding the crew to one SDK would make that detail
structural, and would make the zero-cost promise a matter of discipline rather
than of architecture.

Five providers, one interface, tried in this order:

  OllamaProvider     local, free, no key, no egress. Preferred everywhere it exists.
  GeminiProvider     free tier. What the deployed instance actually thinks with.
  GroqProvider       free tier. Second cloud opinion, and fast.
  AnthropicProvider  PRESENT AND PERMANENTLY DISABLED. It exists so that the
                     refusal is visible in the code and testable, rather than
                     being an absence a future contributor might "fix".
  StubProvider       deterministic, dependency-free, always last. Not a mock:
                     it derives schema-shaped output from a hash of its input,
                     so the crew runtime, budgets, citation gates and audit
                     rules are all genuinely exercised with no model at all.

The stub being terminal is what makes `complete()` total: a provider failure is
degradation with a recorded reason, never an exception the caller must handle.
The one thing that DOES raise is the kill switch, checked first.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

import httpx

from services.api.core import killswitch
from services.api.core.quota import Quota

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    speaker: str | None = None
    latency_s: float = 0.0
    #: Providers passed over, in order, each carrying its reason:
    #: e.g. ("ollama(unreachable)", "gemini(quota exhausted)").
    degraded_from: tuple[str, ...] = field(default_factory=tuple)


@runtime_checkable
class LLMProvider(Protocol):
    name: str
    model: str

    def available(self) -> bool: ...

    def complete(
        self,
        system: str,
        messages: list[Message],
        *,
        max_tokens: int = 512,
        temperature: float = 0.0,
        speaker: str | None = None,
    ) -> LLMResponse: ...


# ── The CI substrate ────────────────────────────────────────────────────────


class StubProvider:
    """Deterministic, free, always available.

    Given identical input it returns identical output, which is what makes the
    determinism and replay tests meaningful rather than circular. Phase C
    registers per-task handlers so the stub returns schema-valid structures for
    debate turns; until then it returns readable prose derived from the input,
    clearly marked as stub output so it can never be mistaken for a model's
    reasoning in a transcript.
    """

    def __init__(self, name: str = "stub", model: str = "deterministic-v1") -> None:
        self.name = name
        self.model = model
        self._handlers: dict[str, object] = {}

    def register(self, task: str, handler) -> None:
        """Phase C hook: bind a task id to a deterministic structured generator."""
        self._handlers[task] = handler

    def available(self) -> bool:
        return True

    def complete(self, system, messages, *, max_tokens=512, temperature=0.0, speaker=None):
        t0 = time.perf_counter()
        digest = hashlib.sha256(
            json.dumps(
                [system, [(m.role, m.content) for m in messages]], ensure_ascii=False
            ).encode()
        ).hexdigest()
        handler = self._handlers.get(_task_of(system))
        text = (
            handler(system, messages, digest)
            if handler
            else f"[stub:{digest[:12]}] Position recorded without a model. "
            f"This response is deterministic output from the stub provider, not reasoning."
        )
        return LLMResponse(
            text=text,
            provider=self.name,
            model=self.model,
            speaker=speaker,
            latency_s=time.perf_counter() - t0,
        )


def _task_of(system: str) -> str:
    """Task id conventionally declared as `task: <id>` on the system prompt's first line."""
    first = system.strip().splitlines()[0] if system.strip() else ""
    return first.split("task:", 1)[1].strip() if "task:" in first else "unknown"


# ── Local ───────────────────────────────────────────────────────────────────


class OllamaProvider:
    name = "ollama"

    def __init__(self, host: str | None = None, model: str | None = None, timeout: float = 120.0):
        self.host = (host or os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        self.model = model or os.getenv("OLLAMA_CHAT_MODEL") or "qwen3:8b"
        self.timeout = timeout

    def available(self) -> bool:
        try:
            r = httpx.get(f"{self.host}/api/tags", timeout=2.0)
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    def complete(self, system, messages, *, max_tokens=512, temperature=0.0, speaker=None):
        t0 = time.perf_counter()
        r = httpx.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "messages": [{"role": "system", "content": system}]
                + [{"role": m.role, "content": m.content} for m in messages],
                "stream": False,
                # qwen3 reasons by default. A boardroom turn is a position, not a
                # scratchpad, and thinking tokens triple the wall clock for output
                # the transcript then has to hide.
                "think": False,
                "options": {"num_predict": max_tokens, "temperature": temperature},
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return LLMResponse(
            text=r.json()["message"]["content"],
            provider=self.name,
            model=self.model,
            speaker=speaker,
            latency_s=time.perf_counter() - t0,
        )


# ── Free cloud ──────────────────────────────────────────────────────────────


class GeminiProvider:
    name = "gemini"
    ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: float = 60.0):
        self._key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL") or "gemini-2.0-flash"
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self._key)

    def complete(self, system, messages, *, max_tokens=512, temperature=0.0, speaker=None):
        t0 = time.perf_counter()
        r = httpx.post(
            f"{self.ENDPOINT}/{self.model}:generateContent",
            params={"key": self._key},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [
                    {
                        "role": "model" if m.role == "assistant" else "user",
                        "parts": [{"text": m.content}],
                    }
                    for m in messages
                ],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": temperature,
                },
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        parts = r.json()["candidates"][0]["content"]["parts"]
        return LLMResponse(
            text="".join(p.get("text", "") for p in parts),
            provider=self.name,
            model=self.model,
            speaker=speaker,
            latency_s=time.perf_counter() - t0,
        )


class GroqProvider:
    name = "groq"
    ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: float = 60.0):
        self._key = api_key if api_key is not None else os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile"
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self._key)

    def complete(self, system, messages, *, max_tokens=512, temperature=0.0, speaker=None):
        t0 = time.perf_counter()
        r = httpx.post(
            self.ENDPOINT,
            headers={"Authorization": f"Bearer {self._key}"},
            json={
                "model": self.model,
                "messages": [{"role": "system", "content": system}]
                + [{"role": m.role, "content": m.content} for m in messages],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return LLMResponse(
            text=r.json()["choices"][0]["message"]["content"],
            provider=self.name,
            model=self.model,
            speaker=speaker,
            latency_s=time.perf_counter() - t0,
        )


# ── Present, and permanently off ────────────────────────────────────────────


class AnthropicProvider:
    """Wired into the chain and unable to serve a single request.

    This class is deliberately not deleted. COUNSEL's constraint is zero paid
    inference, and the honest way to hold that line is to show the paid option
    sitting in the chain, refusing — with the refusal covered by a test — rather
    than to leave a gap that reads as an oversight and invites a well-meaning
    contributor to fill it.
    """

    name = "anthropic"
    why_disabled = (
        "Zero paid inference is a project constraint, not a default. "
        "Anthropic is metered, so this provider refuses even when a key is present. "
        "Removing this refusal is a budget decision for the owner, not a code change."
    )

    def __init__(self, model: str = "claude-opus-5") -> None:
        self.model = model

    def available(self) -> bool:
        return False

    def complete(self, system, messages, *, max_tokens=512, temperature=0.0, speaker=None):
        raise RuntimeError(self.why_disabled)


# ── The chain ───────────────────────────────────────────────────────────────


class LLMChain:
    """Tries providers in order and records why each one was passed over.

    `complete()` is total with respect to provider failure: the stub is appended
    if the caller did not supply one, so there is always something able to
    answer. The kill switch is the sole exception and is checked first, before
    availability, quota, or any network call.
    """

    def __init__(self, providers: list[LLMProvider], quota: Quota) -> None:
        if not providers or providers[-1].name != "stub":
            providers = [*providers, StubProvider()]
        self.providers = providers
        self.quota = quota

    def complete(
        self,
        system: str,
        messages: list[Message],
        *,
        max_tokens: int = 512,
        temperature: float = 0.0,
        speaker: str | None = None,
    ) -> LLMResponse:
        killswitch.check()

        skipped: list[str] = []
        for provider in self.providers:
            if not provider.available():
                skipped.append(f"{provider.name}(unreachable)")
                continue
            if not self.quota.consume(provider.name):
                skipped.append(f"{provider.name}(quota exhausted)")
                continue
            try:
                response = provider.complete(
                    system,
                    messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    speaker=speaker,
                )
            except Exception as exc:  # noqa: BLE001 — degrade on anything a provider does
                skipped.append(f"{provider.name}({type(exc).__name__})")
                continue
            return LLMResponse(
                text=response.text,
                provider=response.provider,
                model=response.model,
                speaker=speaker,
                latency_s=response.latency_s,
                degraded_from=tuple(skipped),
            )

        # Unreachable in practice: the stub is always present and always available.
        raise RuntimeError(f"no provider could serve the request; tried {skipped}")

    def health(self) -> list[dict[str, object]]:
        return [
            {
                "name": p.name,
                "model": p.model,
                "available": p.available(),
                "quota_remaining": self.quota.remaining(p.name),
            }
            for p in self.providers
        ]
