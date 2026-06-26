"""Session snapshot for Context Continuity (Step 3)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.storage_helper import get_storage_dir


@dataclass
class SessionSnapshot:
    run_id: str
    workspace_path: str
    cwd: str
    git_branch: str | None = None
    recent_commands: list[str] | None = None
    active_dev_servers: list[str] | None = None
    task_summary: str = ""
    open_todos: list[str] | None = None
    cli_session_id: str | None = None
    captured_at: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        if not data.get("captured_at"):
            data["captured_at"] = datetime.now(timezone.utc).isoformat()
        return data


def snapshot_dir() -> Path:
    path = get_storage_dir() / "shell_snapshots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_snapshot(snapshot: SessionSnapshot) -> Path:
    if not snapshot.captured_at:
        snapshot.captured_at = datetime.now(timezone.utc).isoformat()
    out = snapshot_dir() / f"{snapshot.run_id}.json"
    out.write_text(json.dumps(snapshot.to_dict(), indent=2) + "\n", encoding="utf-8")
    return out


def load_snapshot(run_id: str) -> SessionSnapshot | None:
    path = snapshot_dir() / f"{run_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return SessionSnapshot(
        run_id=data.get("run_id", run_id),
        workspace_path=data.get("workspace_path", data.get("cwd", "")),
        cwd=data.get("cwd", ""),
        git_branch=data.get("git_branch"),
        recent_commands=data.get("recent_commands"),
        active_dev_servers=data.get("active_dev_servers"),
        task_summary=data.get("task_summary", ""),
        open_todos=data.get("open_todos"),
        cli_session_id=data.get("cli_session_id"),
        captured_at=data.get("captured_at", ""),
    )


def format_handoff_prefix(snapshot: SessionSnapshot) -> str:
    """Inject into a new Claude turn when resuming after snapshot."""
    parts = ["[Clutch session context]"]
    if snapshot.task_summary:
        parts.append(f"Task summary: {snapshot.task_summary}")
    if snapshot.open_todos:
        parts.append("Open todos:\n- " + "\n- ".join(snapshot.open_todos))
    if snapshot.cwd:
        parts.append(f"Working directory: {snapshot.cwd}")
    return "\n".join(parts)
