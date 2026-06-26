"""Runtime mode configuration for ShellSession hybrid vs legacy CLI paths."""

from __future__ import annotations

import os
from typing import Literal

RuntimeMode = Literal["legacy", "hybrid"]

_RUNTIME_MODE_ENV = "CLUTCH_RUNTIME_MODE"
_DEFAULT_MODE: RuntimeMode = "legacy"


def runtime_mode() -> RuntimeMode:
    raw = os.environ.get(_RUNTIME_MODE_ENV, _DEFAULT_MODE).strip().lower()
    if raw == "hybrid":
        return "hybrid"
    return "legacy"


def hybrid_eligible(*, source: str, agent_type: str) -> bool:
    """True only when hybrid is enabled and caller is Plain Chat + claude-cli."""
    return (
        runtime_mode() == "hybrid"
        and source == "plain_chat"
        and agent_type == "claude-cli"
    )
