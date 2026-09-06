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
from typing import Literal, Protocol, TypeVar, runtime_checkable

import httpx
from pydantic import BaseModel, ValidationError

from services.api.core import killswitch
from services.api.core.quota import Quota

Role = Literal["system", "user", "assistant"]
T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """Raised when the chain cannot produce a valid structured result."""


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
    #: True when the model stopped because it ran out of token budget rather
    #: than because it had finished. Under schema-constrained decoding this is
    #: the dangerous case: the grammar forces the object closed, so the result
    #: PARSES and VALIDATES while carrying a sentence cut in half and its tail
    #: spilled into the next field. Nothing downstream can detect that from the
    #: value alone, so it is caught here.
    truncated: bool = False
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
        schema: dict | None = None,
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

    def complete(
        self, system, messages, *, max_tokens=512, temperature=0.0, speaker=None, schema=None
    ):
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


def _gemini_schema(schema: dict) -> dict:
    """Strip the JSON Schema keywords Gemini's responseSchema rejects.

    Gemini takes a subset of OpenAPI rather than full JSON Schema: it has no
    $defs/$ref, and chokes on additionalProperties and several annotations that
    pydantic emits by default. Rather than hand-writing a second schema per
    model and letting the two drift, the pydantic one is flattened here.
    """
    defs = schema.get("$defs", {})

    def walk(node):
        if isinstance(node, list):
            return [walk(n) for n in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            name = node["$ref"].rsplit("/", 1)[-1]
            return walk(defs.get(name, {"type": "string"}))
        return {
            k: walk(v)
            for k, v in node.items()
            if k
            not in {
                "$defs",
                "additionalProperties",
                "title",
                "default",
                "exclusiveMinimum",
                "exclusiveMaximum",
                "minLength",
                "maxLength",
                "minimum",
                "maximum",
                "minItems",
                "maxItems",
            }
        }

    return walk({k: v for k, v in schema.items() if k != "$defs"})


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

    def complete(
        self, system, messages, *, max_tokens=512, temperature=0.0, speaker=None, schema=None
    ):
        t0 = time.perf_counter()
        body = {}
        if schema is not None:
            # Ollama accepts a JSON Schema directly and constrains decoding to it,
            # which is stronger than asking for JSON in the prompt and hoping.
            body["format"] = schema
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
                **body,
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        payload = r.json()
        return LLMResponse(
            text=payload["message"]["content"],
            provider=self.name,
            model=self.model,
            speaker=speaker,
            latency_s=time.perf_counter() - t0,
            truncated=payload.get("done_reason") == "length",
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

    def complete(
        self, system, messages, *, max_tokens=512, temperature=0.0, speaker=None, schema=None
    ):
        t0 = time.perf_counter()
        generation: dict[str, object] = {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        }
        if schema is not None:
            generation["responseMimeType"] = "application/json"
            generation["responseSchema"] = _gemini_schema(schema)
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
                "generationConfig": generation,
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        candidate = r.json()["candidates"][0]
        parts = candidate["content"]["parts"]
        return LLMResponse(
            text="".join(p.get("text", "") for p in parts),
            provider=self.name,
            model=self.model,
            speaker=speaker,
            latency_s=time.perf_counter() - t0,
            truncated=candidate.get("finishReason") == "MAX_TOKENS",
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

    def complete(
        self, system, messages, *, max_tokens=512, temperature=0.0, speaker=None, schema=None
    ):
        t0 = time.perf_counter()
        extra: dict[str, object] = {}
        if schema is not None:
            # Groq's OpenAI-compatible endpoint offers json_object, not a schema,
            # so the schema is also stated in the prompt and validated on return.
            extra["response_format"] = {"type": "json_object"}
        r = httpx.post(
            self.ENDPOINT,
            headers={"Authorization": f"Bearer {self._key}"},
            json={
                "model": self.model,
                "messages": [{"role": "system", "content": system}]
                + [{"role": m.role, "content": m.content} for m in messages],
                "max_tokens": max_tokens,
                "temperature": temperature,
                **extra,
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        choice = r.json()["choices"][0]
        return LLMResponse(
            text=choice["message"]["content"],
            provider=self.name,
            model=self.model,
            speaker=speaker,
            latency_s=time.perf_counter() - t0,
            truncated=choice.get("finish_reason") == "length",
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

    def complete(
        self, system, messages, *, max_tokens=512, temperature=0.0, speaker=None, schema=None
    ):
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
        schema: dict | None = None,
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
                    schema=schema,
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
                truncated=response.truncated,
                degraded_from=tuple(skipped),
            )

        # Unreachable in practice: the stub is always present and always available.
        raise RuntimeError(f"no provider could serve the request; tried {skipped}")

    def structured(
        self,
        system: str,
        messages: list[Message],
        *,
        model_cls: type[T],
        max_tokens: int = 700,
        temperature: float = 0.0,
        speaker: str | None = None,
        retries: int = 1,
    ) -> tuple[T, LLMResponse]:
        """Return a validated object, or raise after exhausting the chain.

        Unlike `complete`, this CAN fail, and deliberately so. A turn that comes
        back as prose instead of a Score is not a degraded answer that a caller
        can render anyway — it is an absence, and the stage that asked for it
        has to know. What the chain does absorb is a single malformed reply per
        provider: the validation error is fed back once, which is enough for a
        small local model to correct a missing field, and cheap.
        """
        schema = model_cls.model_json_schema()
        attempts: list[str] = []
        conversation = list(messages)

        for attempt in range(retries + 1):
            response = self.complete(
                system,
                conversation,
                max_tokens=max_tokens,
                temperature=temperature,
                speaker=speaker,
                schema=schema,
            )
            try:
                if response.truncated:
                    raise ValueError(
                        "the model ran out of token budget mid-object. Under constrained "
                        "decoding the grammar closes the object anyway, so this validates "
                        "while carrying a half-finished sentence."
                    )
                return model_cls.model_validate_json(_json_slice(response.text)), response
            except (ValidationError, ValueError) as exc:
                attempts.append(f"{response.provider}: {type(exc).__name__}")
                if attempt == retries:
                    break
                conversation = [
                    *messages,
                    Message("assistant", response.text[:1500]),
                    Message(
                        "user",
                        "That did not validate against the required schema. Return ONLY a JSON "
                        f"object matching it, correcting this: {str(exc)[:400]}",
                    ),
                ]

        raise LLMError(
            f"no provider returned a valid {model_cls.__name__} after {retries + 1} attempts: "
            f"{attempts}"
        )

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


def _json_slice(text: str) -> str:
    """Pull the JSON object out of a reply that may be wrapped in prose or fences.

    Schema-constrained decoding makes this unnecessary on Ollama and Gemini, but
    Groq's JSON mode and any model answering without schema support will happily
    wrap the object in ```json fences or a sentence of explanation.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("```")[1]
        if stripped.startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.strip()
    start, end = stripped.find("{"), stripped.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"no JSON object in reply: {text[:120]!r}")
    return stripped[start : end + 1]
