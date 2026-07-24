"""Workspace image attachments (.clutch/attachments) and path resolve for preview."""

from __future__ import annotations

import base64
import logging
import re
import time
from pathlib import Path
from typing import Any

from src.workspace import WorkspaceError, require_workspace, to_workspace_relative

logger = logging.getLogger(__name__)

ATTACHMENTS_REL = ".clutch/attachments"
_GITIGNORE_STAR = "*\n"
_GC_SIZE_BYTES = 100 * 1024 * 1024
_GC_AGE_SECONDS = 3 * 24 * 60 * 60
_SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", "target", ".turbo"}
_DATA_URL_RE = re.compile(
    r"^data:(image/(png|jpeg|jpg|gif|webp|bmp));base64,(.+)$",
    re.IGNORECASE | re.DOTALL,
)
_EXT_MAP = {
    "png": ".png",
    "jpeg": ".jpg",
    "jpg": ".jpg",
    "gif": ".gif",
    "webp": ".webp",
    "bmp": ".bmp",
}


def attachments_dir(root: Path | None = None) -> Path:
    base = root or require_workspace()
    return base / ATTACHMENTS_REL


def ensure_attachments_gitignore(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    gitignore = directory / ".gitignore"
    if not gitignore.is_file():
        gitignore.write_text(_GITIGNORE_STAR, encoding="utf-8")


def _dir_size_bytes(directory: Path) -> int:
    total = 0
    try:
        for entry in directory.iterdir():
            if entry.is_file() and entry.name != ".gitignore":
                try:
                    total += entry.stat().st_size
                except OSError:
                    continue
    except OSError:
        return 0
    return total


def maybe_gc_attachments(directory: Path) -> int:
    """If dir ≥ ~100MB, delete image files older than 3 days. Returns deleted count."""
    if not directory.is_dir():
        return 0
    if _dir_size_bytes(directory) < _GC_SIZE_BYTES:
        return 0
    cutoff = time.time() - _GC_AGE_SECONDS
    deleted = 0
    try:
        for entry in directory.iterdir():
            if not entry.is_file() or entry.name == ".gitignore":
                continue
            try:
                if entry.stat().st_mtime < cutoff:
                    entry.unlink(missing_ok=True)
                    deleted += 1
            except OSError:
                continue
    except OSError as exc:
        logger.debug(
            "attachments GC failed",
            extra={
                "run_id": "-",
                "node_id": "-",
                "source": "workspace_attachments",
                "level": "debug",
                "message": str(exc),
                "timestamp": int(time.time() * 1000),
            },
        )
    return deleted


def save_attachment_data_url(data_url: str, *, analyze: bool = True) -> dict[str, Any]:
    """Decode data URL, write under .clutch/attachments, optional OCR fragment."""
    match = _DATA_URL_RE.match((data_url or "").strip())
    if not match:
        raise WorkspaceError("Invalid image data URL")
    mime_subtype = match.group(2).lower()
    raw_b64 = match.group(3)
    try:
        payload = base64.b64decode(raw_b64, validate=False)
    except Exception as exc:  # noqa: BLE001
        raise WorkspaceError("Invalid image base64 payload") from exc
    if not payload:
        raise WorkspaceError("Empty image payload")

    root = require_workspace()
    directory = attachments_dir(root)
    ensure_attachments_gitignore(directory)
    maybe_gc_attachments(directory)

    ext = _EXT_MAP.get(mime_subtype, ".png")
    name = f"{int(time.time() * 1000)}{ext}"
    target = directory / name
    target.write_bytes(payload)

    rel = f"{ATTACHMENTS_REL}/{name}"
    analysis_text = ""
    if analyze:
        try:
            from src.design.image_analysis import image_analysis_prompt_fragment_for_chat

            analysis_text = (image_analysis_prompt_fragment_for_chat(data_url) or "").strip()
        except Exception as exc:  # noqa: BLE001
            logger.debug("attachment image analysis skipped: %s", exc)

    return {"path": rel, "analysis_text": analysis_text}


def _normalize_candidate(raw: str) -> str:
    text = (raw or "").strip().strip("`\"'")
    text = text.rstrip(",.;:)]}>'\"")
    if text.startswith("./"):
        text = text[2:]
    return text


def _exact_relative_if_file(candidate: str) -> str | None:
    cleaned = _normalize_candidate(candidate)
    if not cleaned or cleaned in {".", ".."}:
        return None
    rel = to_workspace_relative(cleaned)
    if rel is None or rel == ".":
        return None
    try:
        from src.workspace import resolve_allowed_path

        target = resolve_allowed_path(rel)
        if target.is_file():
            return rel.replace("\\", "/")
    except WorkspaceError:
        return None
    return None


def _find_unique_basename(basename: str, *, max_hits: int = 8) -> str | None:
    name = Path(basename).name
    if not name or "." not in name:
        return None
    root = require_workspace()
    hits: list[str] = []

    def walk(directory: Path, depth: int) -> None:
        if len(hits) > max_hits or depth > 12:
            return
        try:
            entries = list(directory.iterdir())
        except OSError:
            return
        for entry in entries:
            if entry.is_dir():
                if entry.name in _SKIP_DIRS or (
                    entry.name.startswith(".") and entry.name not in {".clutch"}
                ):
                    continue
                walk(entry, depth + 1)
                continue
            if entry.name == name:
                try:
                    rel = str(entry.resolve().relative_to(root.resolve())).replace("\\", "/")
                except ValueError:
                    continue
                hits.append(rel)
                if len(hits) > max_hits:
                    return

    walk(root, 0)
    if len(hits) == 1:
        return hits[0]
    return None


def resolve_workspace_file_path(raw_path: str) -> dict[str, Any]:
    """Resolve a path or basename to a unique workspace-relative file.

    Returns ``{ok, path?, reason?}`` where reason is ``not_found`` or ``ambiguous``.
    """
    cleaned = _normalize_candidate(raw_path)
    if not cleaned:
        return {"ok": False, "reason": "not_found"}

    exact = _exact_relative_if_file(cleaned)
    if exact:
        return {"ok": True, "path": exact, "match": "exact"}

    basename = Path(cleaned).name
    unique = _find_unique_basename(basename)
    if unique:
        return {"ok": True, "path": unique, "match": "basename"}

    # Ambiguous if multiple basename hits
    root = require_workspace()
    count = 0
    name = Path(basename).name

    def count_walk(directory: Path, depth: int) -> None:
        nonlocal count
        if count > 1 or depth > 12:
            return
        try:
            entries = list(directory.iterdir())
        except OSError:
            return
        for entry in entries:
            if entry.is_dir():
                if entry.name in _SKIP_DIRS or (
                    entry.name.startswith(".") and entry.name not in {".clutch"}
                ):
                    continue
                count_walk(entry, depth + 1)
            elif entry.name == name:
                count += 1

    if name and "." in name:
        count_walk(root, 0)
        if count > 1:
            return {"ok": False, "reason": "ambiguous"}

    return {"ok": False, "reason": "not_found"}
