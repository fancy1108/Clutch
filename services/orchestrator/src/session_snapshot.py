"""Session snapshot for Context Continuity (Step 3)."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.storage_helper import get_storage_dir

logger = logging.getLogger(__name__)


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


def snapshot_max_age_days() -> int:
    """0 disables pruning. Default 30 days."""
    raw = os.environ.get("CLUTCH_SHELL_SNAPSHOT_MAX_AGE_DAYS", "30").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 30


def prune_stale_snapshots(*, max_age_days: int | None = None) -> list[str]:
    """Delete snapshot files older than max_age_days. Returns removed run_ids."""
    limit_days = snapshot_max_age_days() if max_age_days is None else max(0, max_age_days)
    if limit_days <= 0:
        return []

    root = snapshot_dir()
    if not root.is_dir():
        return []

    cutoff = datetime.now(timezone.utc).timestamp() - (limit_days * 86400)
    removed: list[str] = []
    for path in root.glob("*.json"):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime >= cutoff:
            continue
        run_id = path.stem
        try:
            path.unlink()
            removed.append(run_id)
            logger.info(
                "shell_snapshot pruned run_id=%s age_days>=%s source=session_snapshot",
                run_id,
                limit_days,
            )
        except OSError:
            logger.warning("shell_snapshot prune failed run_id=%s", run_id)
    return removed


def list_snapshots() -> list[dict[str, object]]:
    """Summaries for all persisted snapshots (newest first)."""
    root = snapshot_dir()
    if not root.is_dir():
        return []

    paths = list(root.glob("*.json"))
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    items: list[dict[str, object]] = []
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        items.append(
            {
                "run_id": data.get("run_id", path.stem),
                "workspace_path": data.get("workspace_path", ""),
                "cwd": data.get("cwd", ""),
                "task_summary": data.get("task_summary", ""),
                "open_todos": data.get("open_todos") or [],
                "cli_session_id": data.get("cli_session_id"),
                "captured_at": data.get("captured_at", ""),
            }
        )
    return items
