"""Scan mounted directories for Cursor-style SKILL.md files (P2-01)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _parse_skill_md(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    heading = _HEADING_RE.search(text)
    label = heading.group(1).strip() if heading else path.parent.name
    desc = ""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        desc = stripped
        break
    if not desc:
        desc = f"Skill from {path.parent.name}"
    return label, desc[:240]


def scan_mounted_directories(
    mounted_directories: list[str],
    *,
    existing_skills: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    active_by_key = {
        item["key"]: bool(item.get("isActiveGlobally"))
        for item in (existing_skills or [])
        if item.get("key")
    }
    discovered: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for raw in mounted_directories:
        root = Path(raw).expanduser()
        if not root.is_dir():
            continue
        root_resolved = str(root.resolve())
        for skill_md in sorted(root.rglob("SKILL.md")):
            if not skill_md.is_file():
                continue
            label, desc = _parse_skill_md(skill_md)
            rel_parent = skill_md.parent.relative_to(root)
            segment = rel_parent.as_posix() if rel_parent.parts else skill_md.parent.name
            key = f"{root.name}/{segment}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            discovered.append(
                {
                    "key": key,
                    "label": label,
                    "source": root_resolved,
                    "desc": desc,
                    "isActiveGlobally": active_by_key.get(key, False),
                }
            )
    return discovered
