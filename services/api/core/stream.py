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

from sse_starlette.sse import EventSourceResponse

#: Headers every SSE response here carries.
#:
#: `Content-Encoding: identity` is the load-bearing one and it was found the
#: hard way. The Next.js rewrite compresses proxied responses when the client
#: asks for it, and a browser ALWAYS asks — so the dev proxy answered
#: text/event-stream with `Content-Encoding: gzip`, and gzip buffers. Measured
#: in a real browser: response headers at 0.01s, then the entire body, every
#: frame of it, at 33.60s. The same request under curl (which does not request
#: gzip by default) streamed frame by frame, which is why every hand test
#: looked fine.
#:
#: The effect was total: no stream in this application had ever actually
#: streamed to a browser. Declaring the encoding upstream leaves the proxy
#: nothing to negotiate, so it forwards the bytes as they arrive.
#:
#: `x-accel-buffering: no` is the nginx equivalent and does nothing here; it is
#: kept because it costs nothing and Render's edge is not this codebase's to
#: assume about.
SSE_HEADERS = {
    "Content-Encoding": "identity",
    "Cache-Control": "no-store",
    "X-Accel-Buffering": "no",
}


def sse(frames) -> EventSourceResponse:
    """An SSE response that survives a compressing proxy. Use this, not the
    EventSourceResponse constructor — see SSE_HEADERS for what goes wrong."""
    return EventSourceResponse(frames, headers=SSE_HEADERS)


def event(name: str, data: Any) -> dict[str, str]:
    """One SSE frame in the shape sse_starlette expects."""
    return {"event": name, "data": json.dumps(data, ensure_ascii=False, default=str)}


async def from_iterable(name: str, items: Iterable[Any]) -> AsyncIterator[dict[str, str]]:
    for item in items:
        yield event(name, item)
    yield event("done", {"ok": True})
