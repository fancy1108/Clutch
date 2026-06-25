"""In-memory pending MCP tool approvals for plain chat (P2-19)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class McpPendingApproval:
    agent_id: str
    reply_label: str
    chat_messages: list[dict[str, Any]]
    servers: list[dict[str, Any]]
    tool_call_id: str
    func_name: str
    func_args: dict[str, Any]
    step_idx: int
    logs: list[str] = field(default_factory=list)


_pending: dict[str, McpPendingApproval] = {}
_approved_keys: dict[str, set[str]] = {}


def store_pending(run_id: str, pending: McpPendingApproval) -> None:
    _pending[run_id] = pending


def pop_pending(run_id: str) -> McpPendingApproval | None:
    return _pending.pop(run_id, None)


def get_pending(run_id: str) -> McpPendingApproval | None:
    return _pending.get(run_id)


def record_mcp_approval(run_id: str, tool_name: str, func_args: dict[str, Any]) -> None:
    from src.mcp_risk import mcp_approval_key

    _approved_keys.setdefault(run_id, set()).add(mcp_approval_key(tool_name, func_args))


def get_approved_mcp_keys(run_id: str) -> set[str]:
    return set(_approved_keys.get(run_id, set()))


def clear_mcp_approval_state(run_id: str) -> None:
    _pending.pop(run_id, None)
    _approved_keys.pop(run_id, None)
