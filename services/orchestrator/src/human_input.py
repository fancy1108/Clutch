"""Human input kinds for WAITING_FOR_INPUT (Runtime-level)."""

from __future__ import annotations

from enum import Enum
from typing import Any


class HumanInputKind(str, Enum):
    BOOT_TRUST = "boot_trust"
    TOOL_CONFIRM = "tool_confirm"
    TEXT = "text"
    AUTH = "auth"


def human_required_payload(
    *,
    run_id: str,
    kind: HumanInputKind,
    message: str,
    node_id: str = "plain_chat",
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "node_id": node_id,
        "kind": kind.value,
        "message": message,
    }
