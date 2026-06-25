"""Resolve agent-linked skills from the Clutch Skills Registry (P2-14)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.skills_storage import load_registry


def _skill_md_path(skill_meta: dict[str, Any]) -> Path | None:
    key = str(skill_meta.get("key", "")).strip()
    source = str(skill_meta.get("source", "")).strip()
    if not key or not source or "/" not in key:
        return None
    segment = key.split("/", 1)[1]
    path = Path(source) / segment / "SKILL.md"
    return path if path.is_file() else None


def compose_skills_section(skill_keys: list[str]) -> str:
    """Return markdown block for linked SKILL.md files, or empty string."""
    if not skill_keys:
        return ""
    registry = load_registry()
    by_key = {
        str(item.get("key", "")): item
        for item in registry.get("skills", [])
        if item.get("key")
    }
    sections: list[str] = []
    for raw_key in skill_keys:
        key = str(raw_key).strip()
        if not key:
            continue
        meta = by_key.get(key)
        if meta is None:
            continue
        path = _skill_md_path(meta)
        if path is None:
            continue
        label = str(meta.get("label", key))
        body = path.read_text(encoding="utf-8", errors="replace").strip()
        if body:
            sections.append(f"### {label}\n{body}")
    if not sections:
        return ""
    return "## Attached Skills\n\n" + "\n\n".join(sections)
