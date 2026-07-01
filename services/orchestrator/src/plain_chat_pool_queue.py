"""Global FIFO wait queue when Hybrid shell pool is full (cross-session)."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)

ResumeHandler = Callable[["PoolQueuedTurn", "WebSocket | None"], Awaitable[None]]
RefreshHandler = Callable[[], Awaitable[None]]

_main_loop: asyncio.AbstractEventLoop | None = None
_resume_handler: ResumeHandler | None = None
_refresh_handler: RefreshHandler | None = None
_ws_by_run_id: dict[str, WebSocket] = {}
_queue: deque[PoolQueuedTurn] = deque()
_drain_lock = asyncio.Lock()
_drain_task: asyncio.Task[None] | None = None
_drain_retry_task: asyncio.Task[None] | None = None


@dataclass(frozen=True)
class PoolQueuedTurn:
    run_id: str
    text: str
    agent_id: str
    session_model_id: str | None
    client_message_id: str | None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def set_resume_handler(handler: ResumeHandler) -> None:
    global _resume_handler
    _resume_handler = handler


def set_refresh_handler(handler: RefreshHandler) -> None:
    global _refresh_handler
    _refresh_handler = handler


def register_plain_chat_ws(run_id: str, websocket: WebSocket) -> None:
    _ws_by_run_id[run_id] = websocket


def unregister_plain_chat_ws(run_id: str) -> None:
    _ws_by_run_id.pop(run_id, None)


def get_plain_chat_ws(run_id: str) -> WebSocket | None:
    return _ws_by_run_id.get(run_id)


def iter_queued_run_ids() -> list[str]:
    return [item.run_id for item in _queue]


def pool_queue_depth() -> int:
    return len(_queue)


def queue_position_for(run_id: str) -> int | None:
    for index, item in enumerate(_queue):
        if item.run_id == run_id:
            return index + 1
    return None


def _pool_blocker_snapshots() -> list[dict[str, str]]:
    from src.run_history import list_runs
    from src.run_state_store import sync_run_state_from_disk
    from src.shell_session import get_shell_session_manager
    from src.state import initial_state

    manager = get_shell_session_manager()
    history_by_run = {str(record.get("run_id", "")): record for record in list_runs()}
    snapshots: list[dict[str, str]] = []
    for run_id in manager.busy_shell_run_ids():
        record = history_by_run.get(run_id, {})
        title = str(record.get("title") or "").strip() or run_id
        state = sync_run_state_from_disk(run_id, initial_state(run_id))
        agent_name = str(state.get("active_agent") or "").strip()
        snapshots.append(
            {
                "run_id": run_id,
                "title": title,
                "agent_name": agent_name,
            }
        )
    return snapshots


def pool_queue_state_patch(for_run_id: str) -> dict[str, object]:
    position = queue_position_for(for_run_id)
    blockers = _pool_blocker_snapshots()
    return {
        "shell_pool_blocker_run_ids": [item["run_id"] for item in blockers],
        "shell_pool_blockers": blockers,
        "shell_pool_queue_position": position if position is not None else 0,
        "shell_pool_queue_depth": pool_queue_depth(),
    }


def clear_pool_queue_state_patch() -> dict[str, object]:
    return {
        "shell_pool_blocker_run_ids": [],
        "shell_pool_blockers": [],
        "shell_pool_queue_position": 0,
        "shell_pool_queue_depth": 0,
    }


def enqueue_turn(item: PoolQueuedTurn) -> int:
    for existing in _queue:
        if existing.run_id == item.run_id:
            return len(_queue)
    _queue.append(item)
    return len(_queue)


def notify_pool_slot_from_thread() -> None:
    loop = _main_loop
    if loop is None or loop.is_closed():
        return
    try:
        asyncio.run_coroutine_threadsafe(_notify_slot_and_drain(), loop)
    except RuntimeError:
        logger.debug("pool queue drain notify skipped (event loop unavailable)")


async def _notify_slot_and_drain() -> None:
    await _refresh_queued_run_states()
    await schedule_pool_drain()


async def schedule_pool_drain() -> None:
    global _drain_task, _main_loop
    running = asyncio.get_running_loop()
    if _main_loop is None:
        _main_loop = running
    if _drain_task is not None and not _drain_task.done():
        return
    _drain_task = asyncio.create_task(_drain_pool_queue())


def _schedule_drain_retry(delay_s: float = 1.0) -> None:
    global _drain_retry_task, _main_loop
    loop = _main_loop
    if loop is None or loop.is_closed():
        return
    if _drain_retry_task is not None and not _drain_retry_task.done():
        return

    async def _retry() -> None:
        await asyncio.sleep(delay_s)
        await schedule_pool_drain()

    _drain_retry_task = loop.create_task(_retry())


async def _refresh_queued_run_states() -> None:
    handler = _refresh_handler
    if handler is None:
        return
    try:
        await handler()
    except Exception:
        logger.exception("pool queue state refresh failed")


def _ensure_resume_handler() -> ResumeHandler | None:
    global _resume_handler
    if _resume_handler is not None:
        return _resume_handler
    try:
        from src.main import _resume_pool_queued_turn
    except ImportError:
        return None
    _resume_handler = _resume_pool_queued_turn
    return _resume_handler


async def _drain_pool_queue() -> None:
    from src.shell_session import get_shell_session_manager

    handler = _ensure_resume_handler()
    if handler is None:
        return

    retry_needed = False
    async with _drain_lock:
        manager = get_shell_session_manager()
        while _queue:
            item = _queue[0]
            if not manager.pool_has_capacity(item.run_id):
                retry_needed = True
                break
            _queue.popleft()
            websocket = get_plain_chat_ws(item.run_id)
            try:
                await handler(item, websocket)
            except Exception:
                logger.exception("pool queue resume failed run_id=%s", item.run_id)
                _queue.appendleft(item)
                retry_needed = True
                break

    await _refresh_queued_run_states()
    if retry_needed and _queue:
        _schedule_drain_retry()


def reset_for_tests() -> None:
    global _drain_task, _drain_retry_task
    _queue.clear()
    _ws_by_run_id.clear()
    if _drain_task is not None and not _drain_task.done():
        _drain_task.cancel()
    if _drain_retry_task is not None and not _drain_retry_task.done():
        _drain_retry_task.cancel()
    _drain_task = None
    _drain_retry_task = None
