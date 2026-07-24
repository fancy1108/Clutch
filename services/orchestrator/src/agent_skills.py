"""Resolve agent-linked skills from the Clutch Skills Registry (P2-14 / D53)."""

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


def _one_liner(meta: dict[str, Any], path: Path | None) -> str:
    desc = str(meta.get("desc") or "").strip()
    if desc:
        return desc[:160]
    if path is None:
        return ""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    for line in lines:
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#") or trimmed.startswith("---"):
            continue
        return trimmed[:160]
    return ""


def compose_skills_section(
    skill_keys: list[str],
    *,
    include_bodies: bool = False,
) -> str:
    """Skills layer for D53: catalog (name + one-liner) by default; full body on demand."""
    if not skill_keys:
        return ""
    registry = load_registry()
    by_key = {
        str(item.get("key", "")): item
        for item in registry.get("skills", [])
        if item.get("key")
    }
    if include_bodies:
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

    lines: list[str] = ["## Skills catalog", ""]
    any_row = False
    for raw_key in skill_keys:
        key = str(raw_key).strip()
        if not key:
            continue
        meta = by_key.get(key)
        if meta is None:
            continue
        path = _skill_md_path(meta)
        label = str(meta.get("label", key))
        blurb = _one_liner(meta, path) or "Linked skill"
        lines.append(f"- **{label}** (`{key}`): {blurb}")
        any_row = True
    if not any_row:
        return ""
    lines.append("")
    lines.append(
        "Full skill bodies are disclosed on demand when a skill is invoked; "
        "do not assume the full SKILL.md is in context."
    )
    return "\n".join(lines)
