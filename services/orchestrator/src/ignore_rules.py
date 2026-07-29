"""Parse .gitignore / .clutchignore and filter builtin tool paths (D21)."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

_IGNORE_FILENAMES = (".gitignore", ".clutchignore")
_cache: dict[str, tuple[float, list[tuple[str, bool]]]] = {}


def clear_ignore_cache() -> None:
    _cache.clear()


def _mtime_key(root: Path) -> float:
    latest = 0.0
    for name in _IGNORE_FILENAMES:
        path = root / name
        if path.is_file():
            latest = max(latest, path.stat().st_mtime)
    return latest


def _read_pattern_lines(root: Path) -> list[tuple[str, bool]]:
    patterns: list[tuple[str, bool]] = []
    for name in _IGNORE_FILENAMES:
        path = root / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            negated = line.startswith("!")
            if negated:
                line = line[1:].strip()
            if not line:
                continue
            patterns.append((line, negated))
    return patterns


def _load_patterns(root: Path) -> list[tuple[str, bool]]:
    key = str(root.resolve())
    mtime = _mtime_key(root)
    cached = _cache.get(key)
    if cached and cached[0] == mtime:
        return cached[1]
    patterns = _read_pattern_lines(root)
    _cache[key] = (mtime, patterns)
    return patterns


def _normalize_rel(rel: str) -> str:
    cleaned = rel.replace("\\", "/").strip().lstrip("./")
    while cleaned.startswith("/"):
        cleaned = cleaned[1:]
    return cleaned


def _match_pattern(pattern: str, rel: str, *, is_dir: bool) -> bool:
    p = pattern.replace("\\", "/").strip()
    if not p:
        return False
    anchored = p.startswith("/")
    if anchored:
        p = p.lstrip("/")
    target = rel if anchored else rel.split("/")[-1] if "/" not in p and not p.endswith("/") else rel
    if p.endswith("/"):
        if not is_dir:
            return False
        p = p.rstrip("/")
    regex = (
        "^"
        + re.escape(p)
        .replace(r"\*\*/", "(?:.*/)?")
        .replace(r"\*\*", ".*")
        .replace(r"\*", "[^/]*")
        .replace(r"\?", ".")
        + "$"
    )
    if not anchored and "/" not in p:
        # Match basename anywhere in path.
        parts = rel.split("/")
        for idx in range(len(parts)):
            segment = "/".join(parts[idx:])
            if re.match(regex, segment):
                return True
        return False
    return bool(re.match(regex, target))


def is_ignored_path(root: Path, rel: str, *, is_dir: bool = False) -> bool:
    """True when a workspace-relative path matches ignore rules."""
    normalized = _normalize_rel(rel)
    if not normalized:
        return False
    patterns = _load_patterns(root)
    ignored = False
    for pattern, negated in patterns:
        if _match_pattern(pattern, normalized, is_dir=is_dir):
            ignored = not negated
    return ignored


def ignored_path_message(rel: str) -> str:
    from src.preferences_storage import tr

    return tr(
        f"Path is ignored by .gitignore/.clutchignore: {rel}",
        f"路径已被 .gitignore/.clutchignore 忽略：{rel}",
    )
