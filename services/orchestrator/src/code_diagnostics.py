"""D24 — lightweight code diagnostics (tsc / ruff / py_compile)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from src.preferences_storage import tr

_pending_by_run: dict[str, list[dict[str, Any]]] = {}


def store_pending_diagnostics(run_id: str, issues: list[dict[str, Any]]) -> None:
    if not run_id:
        return
    _pending_by_run[run_id] = list(issues)


def pop_pending_diagnostics(run_id: str) -> list[dict[str, Any]]:
    return _pending_by_run.pop(run_id, [])


def peek_pending_diagnostics(run_id: str) -> list[dict[str, Any]]:
    return list(_pending_by_run.get(run_id) or [])


def format_diagnostics_for_prompt(issues: list[dict[str, Any]]) -> str:
    if not issues:
        return ""
    lines = [tr("Code diagnostics:", "代码诊断：")]
    for item in issues[:40]:
        path = item.get("path", "")
        line = item.get("line", "")
        message = item.get("message", "")
        tool = item.get("tool", "")
        lines.append(f"- [{tool}] {path}:{line} {message}".strip())
    return "\n".join(lines)


def _run_cmd(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)


def run_code_diagnostics(workspace: Path, paths: list[str] | None = None) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    root = workspace.resolve()
    scoped = [p for p in (paths or []) if p.strip()]

    # TypeScript
    if (root / "tsconfig.json").is_file() and shutil.which("tsc"):
        proc = _run_cmd(["tsc", "--noEmit", "--pretty", "false"], root)
        if proc.stdout or proc.stderr:
            blob = (proc.stdout or "") + (proc.stderr or "")
            for line in blob.splitlines():
                line = line.strip()
                if not line or "error TS" not in line:
                    continue
                issues.append({"tool": "tsc", "path": line.split("(", 1)[0], "line": "", "message": line})

    # Python — ruff
    if shutil.which("ruff"):
        args = ["ruff", "check", "--output-format", "json"]
        if scoped:
            args.extend(scoped)
        else:
            args.append(".")
        proc = _run_cmd(args, root)
        if proc.stdout.strip():
            try:
                for item in json.loads(proc.stdout):
                    issues.append(
                        {
                            "tool": "ruff",
                            "path": str(item.get("filename", "")),
                            "line": str(item.get("location", {}).get("row", "")),
                            "message": str(item.get("message", "")),
                        }
                    )
            except json.JSONDecodeError:
                issues.append({"tool": "ruff", "path": "", "line": "", "message": proc.stdout[:500]})

    # Python — py_compile fallback for explicit paths
    py_paths = scoped or [p for p in root.rglob("*.py") if ".clutch" not in p.parts][:20]
    for rel in py_paths:
        target = (root / rel).resolve() if not Path(rel).is_absolute() else Path(rel)
        if not target.is_file() or target.suffix != ".py":
            continue
        proc = _run_cmd(["python3", "-m", "py_compile", str(target)], root)
        if proc.returncode != 0:
            issues.append(
                {
                    "tool": "py_compile",
                    "path": str(target.relative_to(root)) if root in target.parents else str(target),
                    "line": "",
                    "message": (proc.stderr or proc.stdout or "syntax error").strip(),
                }
            )

    return issues
