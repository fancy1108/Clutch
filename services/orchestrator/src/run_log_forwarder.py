"""Per-run log forwarding: persist ClutchState and push to WebSocket sinks."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable
from typing import Any

PersistFn = Callable[[str, str], None]
WsEmitFn = Callable[[str, str], Awaitable[None]]
WsStatePatchFn = Callable[[dict[str, Any], str], Awaitable[None]]

_lock = threading.Lock()
_forwarders: dict[str, RunLogForwarder] = {}


class RunLogForwarder:
    __slots__ = ("run_id", "_loop", "_persist", "_ws_emit", "_ws_state_emit")

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._loop: asyncio.AbstractEventLoop | None = None
        self._persist: PersistFn | None = None
        self._ws_emit: WsEmitFn | None = None
        self._ws_state_emit: WsStatePatchFn | None = None

    def set_persist(self, callback: PersistFn | None) -> None:
        self._persist = callback

    def attach_ws(
        self,
        loop: asyncio.AbstractEventLoop,
        emit: WsEmitFn,
        state_patch_emit: WsStatePatchFn | None = None,
    ) -> None:
        self._loop = loop
        self._ws_emit = emit
        self._ws_state_emit = state_patch_emit

    def detach_ws(self) -> None:
        self._loop = None
        self._ws_emit = None
        self._ws_state_emit = None

    def emit(self, line: str, *, node_id: str = "") -> None:
        if not line:
            return
        if self._persist is not None:
            self._persist(line, node_id)
        if self._ws_emit is not None and self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._ws_emit(line, node_id), self._loop)

    def emit_state_patch(self, patch: dict[str, Any], status: str) -> None:
        if self._ws_state_emit is not None and self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._ws_state_emit(patch, status), self._loop)


def get_forwarder(run_id: str) -> RunLogForwarder:
    with _lock:
        forwarder = _forwarders.get(run_id)
        if forwarder is None:
            forwarder = RunLogForwarder(run_id)
            _forwarders[run_id] = forwarder
        return forwarder


def clear_forwarder(run_id: str) -> None:
    with _lock:
        _forwarders.pop(run_id, None)
