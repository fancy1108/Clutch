"""WebSocket envelope senders and transport-error helpers (D38)."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from src.state import ClutchState
from src.terminal_logs import stamp_log_line

logger = logging.getLogger(__name__)


def _iso_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _is_terminal_status(status: str) -> bool:
    return status in {"passed", "failed"}

def _serialize_clutch_state(state: ClutchState) -> dict[str, Any]:
    return dict(state)

async def _send_state_patch(websocket: WebSocket, run_id: str, patch: dict[str, Any]) -> None:
    envelope = {
        "event": "state_patch",
        "data": {
            "run_id": run_id,
            "timestamp": _iso_timestamp(),
            "patch": patch,
        },
    }
    await websocket.send_text(json.dumps(envelope))

async def _send_run_completed(websocket: WebSocket, run_id: str, state: ClutchState) -> None:
    envelope = {
        "event": "run_completed",
        "data": {
            "run_id": run_id,
            "timestamp": _iso_timestamp(),
            "status": state["status"],
            "state": _serialize_clutch_state(state),
        },
    }
    await websocket.send_text(json.dumps(envelope))

async def _notify_run_state(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    patch: dict[str, Any],
) -> None:
    await _send_state_patch(websocket, run_id, patch)
    if _is_terminal_status(state["status"]):
        await _send_run_completed(websocket, run_id, state)

def _is_ws_transport_error(exc: BaseException) -> bool:
    """True when the socket is already closed / ASGI cycle finished (not a logic bug)."""
    if isinstance(exc, WebSocketDisconnect):
        return True
    msg = str(exc).lower()
    return any(
        token in msg
        for token in (
            "websocket.close",
            "websocket.send",
            "not connected",
            "connection closed",
            "asgi message",
            "response already completed",
        )
    )


async def _try_ws_notify(
    coro: Awaitable[None],
    *,
    run_id: str,
    what: str,
) -> None:
    try:
        await coro
    except WebSocketDisconnect:
        logger.warning(
            "WebSocket disconnected during %s run_id=%s",
            what,
            run_id,
        )
    except RuntimeError as exc:
        if _is_ws_transport_error(exc):
            logger.warning(
                "WebSocket unavailable during %s run_id=%s: %s",
                what,
                run_id,
                exc,
            )
            return
        raise

async def _send_message_event(
    websocket: WebSocket, run_id: str, message: dict[str, Any], node_id: str
) -> None:
    envelope = {
        "event": "message",
        "data": {
            "run_id": run_id,
            "node_id": node_id,
            "source": "orchestrator",
            "timestamp": _iso_timestamp(),
            "message": message,
        },
    }
    await websocket.send_text(json.dumps(envelope))

async def _send_hybrid_execution_event(
    websocket: WebSocket,
    run_id: str,
    *,
    message_id: str,
    raw_output: str | None,
    output_events: list[dict[str, Any]] | None,
) -> None:
    envelope = {
        "event": "hybrid_execution",
        "data": {
            "run_id": run_id,
            "node_id": "",
            "source": "orchestrator",
            "timestamp": _iso_timestamp(),
            "messageId": message_id,
            "rawOutput": raw_output,
            "outputEvents": output_events or [],
        },
    }
    await websocket.send_text(json.dumps(envelope))

async def _send_human_required(
    websocket: WebSocket,
    run_id: str,
    *,
    node_id: str,
    prompt: str,
) -> None:
    envelope = {
        "event": "human_required",
        "data": {
            "run_id": run_id,
            "node_id": node_id,
            "source": "orchestrator",
            "level": "info",
            "message": prompt,
            "timestamp": _iso_timestamp(),
        },
    }
    await websocket.send_text(json.dumps(envelope))

async def _send_pty_output(
    websocket: WebSocket,
    run_id: str,
    chunk: str,
    *,
    node_id: str = "",
    lane_id: str = "",
) -> None:
    envelope = {
        "event": "pty_output",
        "data": {
            "run_id": run_id,
            "lane_id": lane_id,
            "node_id": node_id,
            "source": "interactive_pty",
            "level": "info",
            "message": "pty output chunk",
            "timestamp": _iso_timestamp(),
            "chunk": chunk,
            "encoding": "utf8",
        },
    }
    await websocket.send_text(json.dumps(envelope))

async def _send_pty_session_status(
    websocket: WebSocket,
    run_id: str,
    status: str,
    *,
    node_id: str = "",
    detail: str = "",
    lane_id: str = "",
) -> None:
    envelope = {
        "event": "pty_session_status",
        "data": {
            "run_id": run_id,
            "lane_id": lane_id,
            "node_id": node_id,
            "source": "interactive_pty",
            "level": "info",
            "message": detail or f"pty session {status}",
            "timestamp": _iso_timestamp(),
            "status": status,
        },
    }
    await websocket.send_text(json.dumps(envelope))

async def _send_file_changed(
    websocket: WebSocket,
    run_id: str,
    *,
    node_id: str,
    path: str,
    diff_lines: list[dict[str, Any]],
) -> None:
    envelope = {
        "event": "file_changed",
        "data": {
            "run_id": run_id,
            "node_id": node_id,
            "source": "orchestrator",
            "level": "info",
            "message": f"Workspace file changed: {path}",
            "path": path,
            "diff_lines": diff_lines,
            "timestamp": _iso_timestamp(),
        },
    }
    await websocket.send_text(json.dumps(envelope))


async def _send_files_committed(
    websocket: WebSocket,
    run_id: str,
    *,
    node_id: str,
    paths: list[str],
) -> None:
    envelope = {
        "event": "files_committed",
        "data": {
            "run_id": run_id,
            "node_id": node_id,
            "source": "orchestrator",
            "level": "info",
            "message": "Working tree files committed",
            "paths": paths,
            "timestamp": _iso_timestamp(),
        },
    }
    await websocket.send_text(json.dumps(envelope))

async def _send_validation_result(
    websocket: WebSocket,
    run_id: str,
    *,
    node_id: str,
    passed: bool,
    message: str,
) -> None:
    envelope = {
        "event": "validation_result",
        "data": {
            "run_id": run_id,
            "node_id": node_id,
            "source": "orchestrator",
            "level": "error" if not passed else "info",
            "passed": passed,
            "message": message,
            "timestamp": _iso_timestamp(),
        },
    }
    await websocket.send_text(json.dumps(envelope))

async def _send_log_event(
    websocket: WebSocket,
    run_id: str,
    line: str,
    *,
    node_id: str,
    level: str = "info",
) -> None:
    stamped = stamp_log_line(line)
    envelope = {
        "event": "log",
        "data": {
            "run_id": run_id,
            "node_id": node_id,
            "source": "orchestrator",
            "level": level,
            "message": stamped,
            "timestamp": _iso_timestamp(),
        },
    }
    await websocket.send_text(json.dumps(envelope))

