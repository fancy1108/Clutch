"""Build run debug payloads for HRT-06 GET /api/runs/{run_id}/debug."""

from __future__ import annotations

from typing import Any

from src.hybrid_audit_log import read_hybrid_audit_lines
from src.shell_session import get_shell_session_manager
from src.state import ClutchState

_DEFAULT_LOGS_LIMIT = 8
_DEFAULT_AUDIT_LIMIT = 20
_MAX_LOGS_LIMIT = 100
_MAX_AUDIT_LIMIT = 200


def _clamp_limit(value: int | None, *, default: int, maximum: int) -> int:
    if value is None:
        return default
    return max(1, min(value, maximum))


def _shell_session_debug(run_id: str) -> dict[str, Any] | None:
    return get_shell_session_manager().debug_snapshot(run_id)


def build_run_debug_payload(
    run_id: str,
    state: ClutchState,
    *,
    logs_limit: int | None = None,
    audit_limit: int | None = None,
) -> dict[str, Any]:
    logs_n = _clamp_limit(logs_limit, default=_DEFAULT_LOGS_LIMIT, maximum=_MAX_LOGS_LIMIT)
    audit_n = _clamp_limit(audit_limit, default=_DEFAULT_AUDIT_LIMIT, maximum=_MAX_AUDIT_LIMIT)
    terminal_logs = list(state.get("terminal_logs") or [])
    return {
        "run_id": run_id,
        "status": state.get("status", "unknown"),
        "workflow_id": state.get("workflow_id", ""),
        "terminal_logs": terminal_logs[-logs_n:],
        "terminal_logs_total": len(terminal_logs),
        "hybrid_audit": read_hybrid_audit_lines(run_id=run_id, limit=audit_n),
        "shell_session": _shell_session_debug(run_id),
    }
