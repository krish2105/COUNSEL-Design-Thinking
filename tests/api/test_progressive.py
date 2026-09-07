"""Streaming that only looks like streaming.

The first version of the stage stream collected every seat into a list and
emitted the list once the blocking fan-out returned. Measured against a real
model it produced

    0.04s  stage_open
    28.20s framing coo, cmo, cfo, ethics, devil
    28.20s done

That still fixes the 30-second gateway timeout, because a proxy only needs the
first byte — so every test passed, the endpoint worked, and nothing streamed.
Three endpoints said in their docstrings that they show the room thinking.

Timing assertions would be flaky here (the stub answers instantly), so these
tests use a collector that BLOCKS until the consumer has received an earlier
item. Under the batched implementation the consumer never receives it, the
collector never unblocks, and the test fails on its own timeout rather than on
a stopwatch.
"""

from __future__ import annotations

import threading

import pytest

from services.api.routers.decisions import Progressive

RELEASE_TIMEOUT = 5.0


async def test_an_item_reaches_the_consumer_before_the_fanout_returns():
    """The property the batched version silently lacked."""
    first_seen = threading.Event()

    def run(progress):
        progress("cfo", "first")
        # If the consumer is not iterating yet, this waits the full timeout and
        # the assertion below fails — which is exactly the batched behaviour.
        released = first_seen.wait(timeout=RELEASE_TIMEOUT)
        assert released, "the consumer never saw the first item before the fan-out finished"
        progress("cmo", "second")
        return {"cfo": "first", "cmo": "second"}

    fan = Progressive(run)
    seen = []
    async for seat, obj in fan:
        seen.append((seat, obj))
        first_seen.set()

    assert seen == [("cfo", "first"), ("cmo", "second")]


async def test_the_result_is_the_collectors_own_return_value():
    """Display order is arrival order; stored order is whatever the collector says."""

    def run(progress):
        for seat in ("coo", "cfo"):
            progress(seat, seat.upper())
        return {"cfo": "CFO", "coo": "COO"}  # seating order, not arrival order

    fan = Progressive(run)
    arrived = [seat async for seat, _ in fan]

    assert arrived == ["coo", "cfo"], "the live view shows who answered first"
    assert list(fan.result) == ["cfo", "coo"], "the stored artefact keeps seating order"


async def test_a_failing_fanout_raises_after_delivering_what_succeeded():
    """A seat that answered should not be lost because a later one raised."""

    def run(progress):
        progress("cfo", "answered")
        raise RuntimeError("the model fell over")

    fan = Progressive(run)
    delivered = []
    with pytest.raises(RuntimeError, match="fell over"):
        async for seat, _obj in fan:
            delivered.append(seat)

    assert delivered == ["cfo"], "the successful seat must still have been yielded"


async def test_a_fanout_that_reports_nothing_still_completes():
    """An empty room ends the stream rather than hanging the request."""

    def run(progress):
        return {}

    fan = Progressive(run)
    assert [item async for item in fan] == []
    assert fan.result == {}
