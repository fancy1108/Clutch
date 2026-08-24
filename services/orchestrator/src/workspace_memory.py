"""B-39: workspace MEMORY.md overview (Q-AGENT-4 C via B)."""

from __future__ import annotations

import re
from pathlib import Path

MEMORY_REL = ".clutch/memory/MEMORY.md"
_MAX_BULLETS = 40
_MAX_CHARS = 240
_HEADER = (
    "# Project memory\n\n"
    "Short facts for this workspace. Edit freely.\n\n"
    "## Notes\n"
)
_REMEMBER_RE = re.compile(
    r"(?:记住|remember(?:\s+that)?)\s*[:：]\s*(.+)",
    re.IGNORECASE,
)


def memory_path() -> Path | None:
    from src.workspace import get_workspace

    info = get_workspace()
    if not info:
        return None
    root = Path(str(info.get("workspace_path") or "")).expanduser()
    if not root.is_dir():
        return None
    return root / MEMORY_REL


def read_notes() -> list[str]:
    path = memory_path()
    if path is None or not path.is_file():
        return []
    notes: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            notes.append(stripped[2:].strip())
    return notes


def append_note(text: str) -> str | None:
    """Append a unique bullet; compact to last N. Returns relative path or None."""
    trimmed = (text or "").strip()
    if not trimmed:
        return None
    if len(trimmed) > _MAX_CHARS:
        trimmed = trimmed[: _MAX_CHARS - 1] + "…"
    path = memory_path()
    if path is None:
        return None
    existing = read_notes()
    key = trimmed.casefold()
    if any(item.casefold() == key for item in existing):
        return MEMORY_REL
    notes = (existing + [trimmed])[-_MAX_BULLETS:]
    path.parent.mkdir(parents=True, exist_ok=True)
    body = _HEADER + "".join(f"- {item}\n" for item in notes)
    path.write_text(body, encoding="utf-8")
    return MEMORY_REL


def harvest_user_remember(user_text: str | None) -> list[str]:
    """If the user said 记住/remember:, persist it. Returns changed relative paths."""
    from src.preferences_storage import load_cross_session_memory_enabled

    if not load_cross_session_memory_enabled():
        return []
    blob = (user_text or "").strip()
    if not blob:
        return []
    match = _REMEMBER_RE.search(blob)
    if not match:
        return []
    written = append_note(match.group(1).strip().rstrip("。."))
    return [written] if written else []


def format_workspace_memory_block() -> str:
    notes = read_notes()
    if not notes:
        return ""
    body = "\n".join(f"- {item}" for item in notes[-16:])
    return (
        "## Project memory (MEMORY.md)\n"
        "Honor these workspace notes; the user can edit `.clutch/memory/MEMORY.md`:\n"
        f"{body}"
    )


def remember_outcome(report: dict[str, object] | None) -> str | None:
    """B-40: persist verification passed/failed as a short workspace note."""
    if not isinstance(report, dict):
        return None
    conclusion = str(report.get("conclusion") or "").strip().lower()
    title = str(report.get("title") or "task").strip() or "task"
    summary = str(report.get("summary") or "").strip()
    if conclusion == "passed":
        return append_note(f"Worked: {title}")
    if conclusion == "failed":
        extra = f" — {summary[:160]}" if summary else ""
        return append_note(f"Failed: {title}{extra}")
    return None
