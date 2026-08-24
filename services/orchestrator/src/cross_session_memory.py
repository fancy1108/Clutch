"""D16 — cross-session memory (local JSON store + prompt injection)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from src.platform_lock import file_lock

_MAX_ENTRIES = 64
_MAX_ENTRY_CHARS = 400


def _memory_file() -> Path:
    from src.storage_helper import get_storage_dir

    path = get_storage_dir() / "cross_session_memory.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_raw() -> dict[str, Any]:
    path = _memory_file()
    if not path.is_file():
        return {"entries": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"entries": []}
    if not isinstance(data, dict):
        return {"entries": []}
    entries = data.get("entries")
    if not isinstance(entries, list):
        return {"entries": []}
    return {"entries": entries}


def _save_raw(data: dict[str, Any]) -> None:
    path = _memory_file()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def list_entries() -> list[dict[str, Any]]:
    return list(_load_raw().get("entries") or [])


def add_entry(text: str, *, source_run_id: str | None = None) -> dict[str, Any]:
    trimmed = text.strip()
    if not trimmed:
        raise ValueError("memory text is required")
    from src.workspace_memory import is_poisoned_memory

    if is_poisoned_memory(trimmed):
        raise ValueError("refused to store webpage/MCP memory-poison text")
    if len(trimmed) > _MAX_ENTRY_CHARS:
        trimmed = trimmed[: _MAX_ENTRY_CHARS - 1] + "…"
    entry = {
        "id": f"mem_{int(time.time() * 1000)}",
        "text": trimmed,
        "created_at": time.time(),
        "source_run_id": source_run_id or "",
    }
    path = _memory_file()
    if not path.is_file():
        _save_raw({"entries": [entry]})
        return entry
    with path.open("r+", encoding="utf-8") as handle:
        with file_lock(handle):
            handle.seek(0)
            raw = handle.read().strip()
            data = json.loads(raw) if raw else {"entries": []}
            entries = list(data.get("entries") or [])
            entries.append(entry)
            data["entries"] = entries[-_MAX_ENTRIES:]
            handle.seek(0)
            handle.truncate()
            handle.write(json.dumps(data, indent=2, ensure_ascii=False))
            handle.write("\n")
    return entry


def clear_all() -> int:
    entries = list_entries()
    count = len(entries)
    _save_raw({"entries": []})
    return count


def format_memory_prompt_block() -> str:
    from src.preferences_storage import load_cross_session_memory_enabled

    if not load_cross_session_memory_enabled():
        return ""
    entries = list_entries()
    if not entries:
        return ""
    lines = [str(item.get("text") or "").strip() for item in entries]
    lines = [line for line in lines if line]
    if not lines:
        return ""
    body = "\n".join(f"- {line}" for line in lines[-16:])
    return (
        "## Cross-session memory (user preferences)\n"
        "The user asked Clutch to remember these across Chat sessions:\n"
        f"{body}\n"
        "Honor them when relevant; do not contradict without asking."
    )

