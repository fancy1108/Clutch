"""CLI subprocess adapter (M3-01)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class CliResult:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


from src.preferences_storage import tr


class CliAdapterError(RuntimeError):
    pass


def run_cli(
    command: list[str],
    *,
    cwd: str | None = None,
    timeout: float = 30.0,
) -> CliResult:
    if not command:
        raise CliAdapterError(tr("CLI command cannot be empty", "CLI 命令不能为空"))
    proc = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    result = CliResult(
        command=command,
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
    if not result.ok:
        raise CliAdapterError(
            f"CLI 退出码 {result.exit_code}: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result
