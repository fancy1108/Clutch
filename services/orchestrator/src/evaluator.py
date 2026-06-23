"""Workflow check node execution (M3-05 / M3-06)."""

from __future__ import annotations

import subprocess
from typing import Any

from src.adapters.cli_adapter import CliAdapterError, run_cli
from src.workspace import WorkspaceError, resolve_allowed_path, require_workspace


def run_checks(checks: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """Run configured checks; return (passed|failed, log lines)."""
    logs: list[str] = []
    require_workspace()
    for index, check in enumerate(checks, start=1):
        check_type = check.get("type", "")
        if check_type == "file_exists":
            rel = str(check.get("path", ""))
            target = resolve_allowed_path(rel)
            if target.is_file():
                logs.append(f"[EVALUATOR] check {index} file_exists OK: {rel}")
            else:
                logs.append(f"[EVALUATOR] check {index} file_exists FAILED: {rel}")
                return "failed", logs
        elif check_type in {"shell", "lint"}:
            command = check.get("command")
            root = str(require_workspace())
            try:
                if isinstance(command, str):
                    proc = subprocess.run(
                        command,
                        shell=True,
                        cwd=root,
                        capture_output=True,
                        text=True,
                        timeout=20.0,
                        check=False,
                    )
                    if proc.returncode != 0:
                        raise CliAdapterError(proc.stderr.strip() or proc.stdout.strip())
                    logs.append(f"[EVALUATOR] check {index} shell OK")
                    if proc.stdout.strip():
                        logs.append(proc.stdout.strip())
                elif isinstance(command, list):
                    result = run_cli([str(part) for part in command], cwd=root, timeout=20.0)
                    logs.append(f"[EVALUATOR] check {index} shell OK: {' '.join(result.command)}")
                    if result.stdout.strip():
                        logs.append(result.stdout.strip())
                else:
                    logs.append(f"[EVALUATOR] check {index} invalid shell command")
                    return "failed", logs
            except (CliAdapterError, subprocess.TimeoutExpired, OSError) as exc:
                logs.append(f"[EVALUATOR] check {index} shell FAILED: {exc}")
                return "failed", logs
        else:
            logs.append(f"[EVALUATOR] check {index} unsupported type: {check_type}")
            return "failed", logs
    return "passed", logs


def evaluate_node_data(data: dict[str, Any]) -> tuple[str, list[str]]:
    checks = data.get("checks", [])
    if not isinstance(checks, list):
        return "failed", ["[EVALUATOR] checks 配置无效"]
    return run_checks(checks)
