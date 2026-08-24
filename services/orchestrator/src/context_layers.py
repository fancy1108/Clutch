"""B-36 layered context: offload → noise → batch (emergency compact stays in compaction.py)."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

POINTER = "[tool_result archived]"
_KEEP_RECENT_TOOLS = 2
_PREVIEW_CHARS = 400
_NOISE_HEAD = 80


@dataclass
class LayerStats:
    offloaded: int = 0
    noise_dropped: int = 0
    batched: int = 0


def offload_threshold() -> int:
    raw = os.environ.get("CLUTCH_TOOL_OFFLOAD_CHARS", "4000")
    try:
        return max(32, int(raw))
    except ValueError:
        return 4000


def batch_threshold() -> int:
    raw = os.environ.get("CLUTCH_TOOL_BATCH_CHARS", "8000")
    try:
        return max(64, int(raw))
    except ValueError:
        return 8000


def tool_results_dir(archive_dir: Path | None = None) -> Path:
    if archive_dir is not None:
        path = Path(archive_dir)
    else:
        from src.compaction import get_archive_dir

        path = get_archive_dir() / "tool_results"
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_tool_message(message: dict[str, Any]) -> bool:
    return str(message.get("role") or "").strip().lower() == "tool"


def is_pointer(content: str) -> bool:
    return content.lstrip().startswith(POINTER)


def _tool_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    return content if isinstance(content, str) else ""


def _head(content: str) -> str:
    return " ".join(content.split())[:_NOISE_HEAD]


def _write_archive(content: str, root: Path) -> Path:
    path = root / f"{uuid.uuid4().hex[:12]}.txt"
    path.write_text(content, encoding="utf-8")
    return path


def _pointer_for(content: str, path: Path) -> str:
    preview = content[:_PREVIEW_CHARS].rstrip()
    rel = path.as_posix()
    for marker in ("runs/archive/", "tool_results/"):
        idx = rel.find(marker)
        if idx >= 0:
            rel = rel[idx:]
            break
    return (
        f"{POINTER} file={rel} chars={len(content)}\n"
        f"preview:\n{preview}"
    )


def offload_if_needed(content: str, root: Path, *, force: bool = False) -> tuple[str, bool]:
    if not content or is_pointer(content):
        return content, False
    if not force and len(content) <= offload_threshold():
        return content, False
    return _pointer_for(content, _write_archive(content, root)), True


def _tool_chars(messages: list[dict[str, Any]]) -> int:
    return sum(len(_tool_text(m)) for m in messages if is_tool_message(m))


def _strip_noise(messages: list[dict[str, Any]]) -> int:
    idxs = [i for i, msg in enumerate(messages) if is_tool_message(msg)]
    keep = set(idxs[-_KEEP_RECENT_TOOLS:])
    seen: set[str] = set()
    dropped = 0
    for i in reversed(idxs):
        content = _tool_text(messages[i])
        if i in keep or is_pointer(content):
            if content:
                seen.add(_head(content))
            continue
        head = _head(content)
        tiny = len(content.strip()) < 24
        if tiny or (head and head in seen):
            messages[i]["content"] = f"[dropped as noise] {head}".strip()
            dropped += 1
        elif head:
            seen.add(head)
    return dropped


def apply_layered_context(
    messages: list[dict[str, Any]],
    *,
    archive_dir: Path | None = None,
) -> LayerStats:
    """Shrink tool messages in place. Layers 1–3; does not call an LLM."""
    stats = LayerStats()
    root = tool_results_dir(archive_dir)
    for msg in messages:
        if not is_tool_message(msg):
            continue
        next_text, wrote = offload_if_needed(_tool_text(msg), root)
        if wrote:
            msg["content"] = next_text
            stats.offloaded += 1
    stats.noise_dropped = _strip_noise(messages)
    if _tool_chars(messages) <= batch_threshold():
        return stats
    idxs = [i for i, msg in enumerate(messages) if is_tool_message(msg)]
    for i in idxs[:-_KEEP_RECENT_TOOLS]:
        next_text, wrote = offload_if_needed(_tool_text(messages[i]), root, force=True)
        if wrote:
            messages[i]["content"] = next_text
            stats.batched += 1
    return stats
