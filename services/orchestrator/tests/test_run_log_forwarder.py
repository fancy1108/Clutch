"""Tests for per-run workflow log forwarding."""

from __future__ import annotations

import asyncio

from src.run_log_forwarder import clear_forwarder, get_forwarder
from src.terminal_logs import TAG_WORKFLOW, tagged


def test_forwarder_persist_and_ws() -> None:
    clear_forwarder("run_fwd_test")
    forwarder = get_forwarder("run_fwd_test")
    persisted: list[tuple[str, str]] = []
    streamed: list[tuple[str, str]] = []

    forwarder.set_persist(lambda line, node_id: persisted.append((line, node_id)))

    loop = asyncio.new_event_loop()

    async def ws_emit(line: str, node_id: str) -> None:
        streamed.append((line, node_id))

    forwarder.attach_ws(loop, ws_emit)
    forwarder.emit(tagged(TAG_WORKFLOW, "hello"), node_id="n1")
    loop.run_until_complete(asyncio.sleep(0))
    forwarder.detach_ws()
    loop.close()
    clear_forwarder("run_fwd_test")

    assert persisted == [(tagged(TAG_WORKFLOW, "hello"), "n1")]
    assert streamed == [(tagged(TAG_WORKFLOW, "hello"), "n1")]


def test_get_forwarder_returns_singleton_per_run() -> None:
    clear_forwarder("run_singleton")
    first = get_forwarder("run_singleton")
    second = get_forwarder("run_singleton")
    assert first is second
    clear_forwarder("run_singleton")
