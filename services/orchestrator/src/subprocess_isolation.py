"""Subprocess crash isolation — Sidecar survives child failure (M3-07)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class IsolatedRunResult:
    exit_code: int
    stdout: str
    stderr: str
    crashed: bool


def run_isolated(command: list[str], *, cwd: str | None = None, timeout: float = 10.0) -> IsolatedRunResult:
    proc = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    crashed = proc.returncode not in {0} and "Traceback" in proc.stderr
    return IsolatedRunResult(
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        crashed=crashed or proc.returncode != 0,
    )
