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
    """True when hybrid shell-exec is enabled for the given dispatch source."""
    if source == "flow_refine" and agent_type == "claude-cli":
        return True
    if runtime_mode() != "hybrid":
        return False
    if agent_type == "claude-cli":
        return source in ("plain_chat", "flow")
    if agent_type in ("antigravity-cli", "codex-cli", "aider-cli"):
        return source == "plain_chat"
    return False
