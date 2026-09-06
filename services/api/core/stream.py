"""Server-sent events.

Phase C's debate has to arrive turn by turn — a boardroom you watch is a
different product from one that hands you a finished transcript, and the Chair
cannot interject into something that has already happened. That shape is
established here, in Phase A, so the streaming endpoints Phase C needs are an
addition rather than a rewrite of every response type.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterable
from typing import Any


def event(name: str, data: Any) -> dict[str, str]:
    """One SSE frame in the shape sse_starlette expects."""
    return {"event": name, "data": json.dumps(data, ensure_ascii=False, default=str)}


async def from_iterable(name: str, items: Iterable[Any]) -> AsyncIterator[dict[str, str]]:
    for item in items:
        yield event(name, item)
    yield event("done", {"ok": True})
