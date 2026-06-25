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


def store_pending(run_id: str, pending: McpPendingApproval) -> None:
    _pending[run_id] = pending


def pop_pending(run_id: str) -> McpPendingApproval | None:
    return _pending.pop(run_id, None)


def get_pending(run_id: str) -> McpPendingApproval | None:
    return _pending.get(run_id)
