"""Runtime strategy taxonomy (Step 4 prelude)."""

from __future__ import annotations

from enum import Enum


class RuntimeStrategy(str, Enum):
    SHELL_EXEC = "shell_exec"
    INTERACTIVE_PTY = "interactive_pty"
    HTTP_DAEMON = "http_daemon"
    SDK_NATIVE = "sdk_native"
