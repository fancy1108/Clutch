"""Skills registry persistence (P2-01)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

SKILLS_ENV = "CLUTCH_SKILLS_DIR"


def skills_dir() -> Path:
    override = os.environ.get(SKILLS_ENV)
    if override:
        return Path(override)
    from src.storage_helper import get_storage_dir
    return get_storage_dir() / "skills"


def _registry_file() -> Path:
    path = skills_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path / "registry.json"


def load_registry() -> dict[str, Any]:
    path = _registry_file()
    if not path.is_file():
        return {"mounted_directories": [], "skills": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "mounted_directories": list(data.get("mounted_directories") or []),
        "skills": list(data.get("skills") or []),
    }


def discover_default_skill_directories(*, workspace_path: str | None = None) -> list[str]:
    """Well-known skill roots that exist on this machine (Cursor, workspace project skills/, etc.)."""
    from src.skills_scanner import directory_has_skills

    candidates: list[Path] = [
        Path.home() / ".cursor" / "skills-cursor",
        Path.home() / ".cursor" / "skills",
    ]
    if workspace_path:
        ws = Path(workspace_path).expanduser().resolve()
        candidates.extend(
            [
                ws / "skills",
                ws / ".cursor" / "skills",
                ws / ".claude" / "skills",
            ]
        )
    discovered: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        root = raw.expanduser()
        if not directory_has_skills(root):
            continue
        resolved = str(root.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        discovered.append(resolved)
    return discovered


def ensure_default_skill_mounts(*, workspace_path: str | None = None) -> list[str]:
    """Merge default skill directories into the registry. Returns newly added paths."""
    data = load_registry()
    mounted = [str(Path(item).expanduser().resolve()) for item in data["mounted_directories"]]
    mounted_set = set(mounted)
    added: list[str] = []
    for candidate in discover_default_skill_directories(workspace_path=workspace_path):
        if candidate in mounted_set:
            continue
        mounted.append(candidate)
        mounted_set.add(candidate)
        added.append(candidate)
    if added:
        save_registry(mounted_directories=mounted)
    return added


def save_registry(
    *,
    mounted_directories: list[str] | None = None,
    skills: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    current = load_registry()
    if mounted_directories is not None:
        current["mounted_directories"] = mounted_directories
    if skills is not None:
        current["skills"] = skills
    _registry_file().write_text(
        json.dumps(current, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return current
