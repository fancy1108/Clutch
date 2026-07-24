"""Skills registry persistence (P2-01 / D7 workspace mount hygiene)."""

from __future__ import annotations

import json
import os
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
        return {
            "mounted_directories": [],
            "skills": [],
            "auto_workspace_mounts": [],
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "mounted_directories": list(data.get("mounted_directories") or []),
        "skills": list(data.get("skills") or []),
        "auto_workspace_mounts": list(data.get("auto_workspace_mounts") or []),
    }


def _resolve_mount(raw: str) -> str:
    return str(Path(raw).expanduser().resolve())


def discover_user_skill_directories() -> list[str]:
    """User-global skill roots (Grok/Cursor/Claude/OpenCode/Copilot home dirs)."""
    from src.skills_scanner import directory_has_skills

    home = Path.home()
    candidates = [
        home / ".cursor" / "skills-cursor",
        home / ".cursor" / "skills",
        home / ".claude" / "skills",
        home / ".agents" / "skills",
        home / ".grok" / "skills",
        home / ".codex" / "skills",
        home / ".config" / "opencode" / "skills",
        home / ".copilot" / "skills",
    ]
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


def discover_workspace_skill_directories(workspace_path: str | None) -> list[str]:
    """Project skill roots under the active workspace (Grok-compatible set)."""
    from src.skills_scanner import directory_has_skills

    if not workspace_path:
        return []
    ws = Path(workspace_path).expanduser().resolve()
    candidates = [
        ws / "skills",
        ws / ".cursor" / "skills",
        ws / ".claude" / "skills",
        ws / ".agents" / "skills",
        ws / ".grok" / "skills",
        ws / ".opencode" / "skills",
        ws / ".codex" / "skills",
        ws / ".github" / "skills",
    ]
    discovered: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        if not directory_has_skills(raw):
            continue
        resolved = str(raw.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        discovered.append(resolved)
    return discovered


def discover_default_skill_directories(*, workspace_path: str | None = None) -> list[str]:
    """Well-known skill roots (user home + current workspace)."""
    discovered: list[str] = []
    seen: set[str] = set()
    for item in (
        *discover_user_skill_directories(),
        *discover_workspace_skill_directories(workspace_path),
    ):
        if item in seen:
            continue
        seen.add(item)
        discovered.append(item)
    return discovered


def sync_workspace_skill_mounts(*, workspace_path: str | None = None) -> dict[str, Any]:
    """
    Keep user Search Paths (manual Mount Root) forever; only rotate *auto*
    workspace skill mounts when the active workspace changes (D7).

    Custom directories from Skills Registry SEARCH PATHS are never pruned here.
    """
    data = load_registry()
    mounted = [_resolve_mount(item) for item in data["mounted_directories"]]
    mounted_set = set(mounted)
    prev_auto = {_resolve_mount(item) for item in data.get("auto_workspace_mounts") or []}
    added: list[str] = []
    removed: list[str] = []

    for candidate in discover_user_skill_directories():
        if candidate in mounted_set:
            continue
        mounted.append(candidate)
        mounted_set.add(candidate)
        added.append(candidate)

    # Only drop previous *auto* workspace mounts — never user-mounted Search Paths.
    new_auto = discover_workspace_skill_directories(workspace_path)
    new_auto_set = set(new_auto)
    stale = prev_auto - new_auto_set

    new_mounted = [m for m in mounted if m not in stale]
    for item in stale:
        if item in mounted_set:
            removed.append(item)
    mounted_set = set(new_mounted)

    for candidate in new_auto:
        if candidate in mounted_set:
            continue
        new_mounted.append(candidate)
        mounted_set.add(candidate)
        added.append(candidate)

    skills = [
        skill
        for skill in data["skills"]
        if _resolve_mount(str(skill.get("source") or "")) in mounted_set
    ]

    save_registry(
        mounted_directories=new_mounted,
        skills=skills,
        auto_workspace_mounts=new_auto,
    )
    return {
        "added": added,
        "removed": removed,
        "auto_workspace_mounts": new_auto,
    }


def ensure_default_skill_mounts(*, workspace_path: str | None = None) -> list[str]:
    """Merge/sync default skill directories. Returns newly added paths."""
    return list(sync_workspace_skill_mounts(workspace_path=workspace_path)["added"])


def save_registry(
    *,
    mounted_directories: list[str] | None = None,
    skills: list[dict[str, Any]] | None = None,
    auto_workspace_mounts: list[str] | None = None,
) -> dict[str, Any]:
    current = load_registry()
    if mounted_directories is not None:
        current["mounted_directories"] = mounted_directories
    if skills is not None:
        current["skills"] = skills
    if auto_workspace_mounts is not None:
        current["auto_workspace_mounts"] = auto_workspace_mounts
    _registry_file().write_text(
        json.dumps(current, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return current
