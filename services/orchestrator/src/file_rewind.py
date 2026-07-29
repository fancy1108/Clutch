"""D23 — shadow snapshots before Agent file writes; one-click rewind."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from src.platform_lock import file_lock
from src.workspace import WorkspaceError, require_workspace, resolve_allowed_path, to_workspace_relative

_MAX_SNAPSHOTS = 64


def _rewind_dir(root: Path, run_id: str) -> Path:
    path = root / ".clutch" / "rewind" / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _index_path(root: Path, run_id: str) -> Path:
    return _rewind_dir(root, run_id) / "snapshots.json"


def _load_index(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return list(data)
    if isinstance(data, dict) and isinstance(data.get("entries"), list):
        return list(data["entries"])
    return []


def _save_index(path: Path, entries: list[dict[str, Any]]) -> None:
    trimmed = entries[-_MAX_SNAPSHOTS:]
    path.write_text(
        json.dumps({"entries": trimmed}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def snapshot_before_write(run_id: str, rel_path: str) -> None:
    """Record pre-write file content (missing file → exists=false)."""
    if not run_id or not rel_path.strip():
        return
    try:
        root = require_workspace()
        target = resolve_allowed_path(rel_path)
        rel = to_workspace_relative(str(target)) or rel_path.strip()
    except WorkspaceError:
        return
    index_path = _index_path(root, run_id)
    entry: dict[str, Any] = {
        "path": rel,
        "timestamp": time.time(),
        "exists": target.is_file(),
        "content": target.read_text(encoding="utf-8", errors="replace") if target.is_file() else "",
    }
    with index_path.open("a+", encoding="utf-8") as handle:
        with file_lock(handle):
            handle.seek(0)
            raw = handle.read().strip()
            entries = _load_index(index_path) if not raw else []
            if raw:
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict) and isinstance(parsed.get("entries"), list):
                        entries = list(parsed["entries"])
                    elif isinstance(parsed, list):
                        entries = list(parsed)
                except json.JSONDecodeError:
                    entries = []
            entries.append(entry)
            handle.seek(0)
            handle.truncate()
            handle.write(json.dumps({"entries": entries[-_MAX_SNAPSHOTS:]}, ensure_ascii=False))
            handle.write("\n")


def snapshot_paths_before_write(run_id: str, paths: list[str]) -> None:
    for rel in paths:
        if rel.strip():
            snapshot_before_write(run_id, rel)


def rewind_last_writes(run_id: str, count: int = 1) -> list[dict[str, Any]]:
    """Restore the last N agent write snapshots; return restored entries."""
    if count <= 0:
        return []
    try:
        root = require_workspace()
    except WorkspaceError as exc:
        raise ValueError(str(exc)) from exc
    index_path = _index_path(root, run_id)
    if not index_path.is_file():
        return []
    with index_path.open("r+", encoding="utf-8") as handle:
        with file_lock(handle):
            handle.seek(0)
            raw = handle.read().strip()
            entries = _load_index(index_path) if raw else []
            if not entries:
                return []
            batch = entries[-count:]
            remaining = entries[:-count]
            restored: list[dict[str, Any]] = []
            for entry in reversed(batch):
                rel = str(entry.get("path") or "").strip()
                if not rel:
                    continue
                target = resolve_allowed_path(rel)
                if entry.get("exists"):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(str(entry.get("content") or ""), encoding="utf-8")
                elif target.is_file():
                    target.unlink()
                restored.append({"path": rel, "restored": True})
            handle.seek(0)
            handle.truncate()
            if remaining:
                handle.write(json.dumps({"entries": remaining}, ensure_ascii=False))
                handle.write("\n")
            else:
                handle.write("")
    return restored


def snapshot_count(run_id: str) -> int:
    try:
        root = require_workspace()
    except WorkspaceError:
        return 0
    return len(_load_index(_index_path(root, run_id)))
