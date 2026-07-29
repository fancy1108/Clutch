"""Regression: closed WebSocket / ASGI send-after-close must not leak into Chat."""

from __future__ import annotations

import pytest
from fastapi import WebSocketDisconnect

from src.chat_runner import _is_ws_transport_error, _try_ws_notify


def test_is_ws_transport_error_detects_asgi_send_after_close() -> None:
    exc = RuntimeError(
        "Unexpected ASGI message 'websocket.send', after sending 'websocket.close' "
        "or response already completed."
    )
    assert _is_ws_transport_error(exc)
    assert _is_ws_transport_error(WebSocketDisconnect())
    assert not _is_ws_transport_error(RuntimeError("LLM API error 529"))


@pytest.mark.asyncio
async def test_try_ws_notify_swallows_asgi_runtime_error() -> None:
    async def boom() -> None:
        raise RuntimeError(
            "Unexpected ASGI message 'websocket.send', after sending 'websocket.close' "
            "or response already completed."
        )

    await _try_ws_notify(boom(), run_id="run_test", what="state_patch")
