"""What each agent can do, declared in one table.

THE PROMISE THIS FILE KEEPS
---------------------------
COUNSEL's central safety claim is that a boardroom of agents can argue without
any of them being able to act. That is not enforced by prompting — "do not post
anything" is a request, and an injected instruction is a competing request. It
is enforced by there being nothing to call.

So the registry is exhaustive: an agent can invoke exactly what appears in
GRANTS, every entry in GRANTS must exist in REGISTRY, and every tool in REGISTRY
declares `side_effects` which a test asserts is False for all of them. Adding a
tool that writes to the outside world would fail the suite before it could fail
a user.

WHY THE FACILITATOR HOLDS THE ONLY CONTROL TOOLS
------------------------------------------------
Turn-taking and round limits are the Facilitator's, and no debating mandate can
reach them. A room where any participant can close the round is a room where the
loudest seat decides when the argument is over.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class CapabilityError(PermissionError):
    """Raised when an agent reaches for a tool it was not granted."""


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    #: Must be False for every registered tool. A True here is a design change
    #: that has to be argued for, not a flag that can be flipped.
    side_effects: bool
    run: Callable[..., Any]


def _make_registry() -> dict[str, Tool]:
    # Imported lazily so the registry can be inspected in tests without standing
    # up a database or a search chain.
    from services.api import deps
    from services.api.rag.retrieve import retrieve

    def search(query: str, limit: int = 5) -> list[dict[str, object]]:
        """Public web search. Read-only, and everything it returns is untrusted."""
        chain = deps.search()
        return [
            {
                "url": r.url,
                "title": r.title,
                "snippet": r.snippet,
                "provider": r.provider,
                "retrieved_at": r.retrieved_at,
                "trust": r.trust,
            }
            for r in chain.search(query, limit=limit)
        ]

    def ask(query: str, limit: int = 5) -> list[dict[str, object]]:
        """Retrieve from the room's own documents, with spans so a claim can cite."""
        result = retrieve(query, conn=deps.db(), limit=limit, embedder=deps.embedder())
        return [
            {
                "doc_id": h.chunk.doc_id,
                "text": h.chunk.text,
                "start": h.chunk.start,
                "end": h.chunk.end,
                "lang": h.chunk.lang,
                "trust": h.chunk.trust,
            }
            for h in result.hits
        ]

    def start_round(session_id: str, round_no: int) -> dict[str, object]:
        """Open a round. Facilitator only — a room where any seat can start the
        next round is a room with no chair."""
        return {"session_id": session_id, "round_no": round_no, "opened": True}

    def close_round(session_id: str, round_no: int) -> dict[str, object]:
        """Close a round. Facilitator only, for the same reason."""
        return {"session_id": session_id, "round_no": round_no, "closed": True}

    def flag(turn_id: str, rule: str, why: str) -> dict[str, object]:
        """Record an audit finding against a turn. Writes to the record only."""
        return {"turn_id": turn_id, "rule": rule, "why": why}

    tools = [
        Tool("search", search.__doc__ or "", False, search),
        Tool("ask", ask.__doc__ or "", False, ask),
        Tool("start_round", start_round.__doc__ or "", False, start_round),
        Tool("close_round", close_round.__doc__ or "", False, close_round),
        Tool("flag", flag.__doc__ or "", False, flag),
    ]
    return {t.name: t for t in tools}


REGISTRY: dict[str, Tool] = _make_registry()

#: Who may call what. The five debating mandates get research and nothing else.
GRANTS: dict[str, frozenset[str]] = {
    "cfo": frozenset({"search", "ask"}),
    "cmo": frozenset({"search", "ask"}),
    "coo": frozenset({"search", "ask"}),
    "ethics": frozenset({"search", "ask"}),
    "devil": frozenset({"search", "ask"}),
    "facilitator": frozenset({"start_round", "close_round"}),
    "auditor": frozenset({"flag"}),
    #: The human, when they interject as Chair. Read-only like everyone else.
    "chair": frozenset({"search", "ask"}),
}


def granted(agent: str) -> frozenset[str]:
    return GRANTS.get(agent, frozenset())


def invoke(agent: str, tool: str, **kwargs: Any) -> Any:
    if tool not in REGISTRY:
        raise CapabilityError(f"no such tool: {tool!r}")
    if tool not in granted(agent):
        raise CapabilityError(
            f"agent {agent!r} is not granted {tool!r}; it holds {sorted(granted(agent))}"
        )
    return REGISTRY[tool].run(**kwargs)


def catalogue(agent: str) -> list[dict[str, object]]:
    """What this agent may call, for its prompt and for /healthz."""
    return [
        {"name": t.name, "description": t.description.strip(), "side_effects": t.side_effects}
        for name, t in sorted(REGISTRY.items())
        if name in granted(agent)
    ]
