"""CLI subprocess adapter (M3-01)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from src.preferences_storage import tr


@dataclass(frozen=True)
class CliResult:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


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
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        binary = command[0] if command else "cli"
        raise CliAdapterError(
            tr(
                f"`{binary}` timed out after {timeout:g}s. "
                "Try a simpler prompt, or set CLUTCH_CLAUDE_CLI_TIMEOUT (seconds).",
                f"`{binary}` 在 {timeout:g} 秒后超时。"
                "可尝试更简短的指令，或设置环境变量 CLUTCH_CLAUDE_CLI_TIMEOUT（秒）。",
            )
        ) from exc
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
