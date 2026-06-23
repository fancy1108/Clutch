"""Cursor GUI adapter — open workspace in Cursor (M3-03)."""

from __future__ import annotations

import shutil
import subprocess
import sys


def open_workspace_in_cursor(workspace_path: str) -> None:
    if sys.platform != "darwin":
        raise RuntimeError("Cursor GUI 适配器当前仅支持 macOS")
    if shutil.which("open") is None:
        raise RuntimeError("未找到 open 命令")
    subprocess.run(
        ["open", "-a", "Cursor", workspace_path],
        check=True,
        capture_output=True,
        text=True,
    )
