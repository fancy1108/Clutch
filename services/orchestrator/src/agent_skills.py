"""Resolve Clutch Skills Registry entries for prompt injection (P2-14 / D53 / D7)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from src.skills_storage import (
    discover_user_skill_directories,
    load_registry,
)
from src.workspace import get_workspace

SkillScope = Literal["project", "custom", "global"]

# Lower rank wins on same short-name (Grok: local/repo > user; Clutch: project > custom > global).
_SCOPE_RANK: dict[SkillScope, int] = {
    "project": 0,
    "custom": 1,
    "global": 2,
}


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


def _short_name(key: str) -> str:
    return key.rsplit("/", 1)[-1].strip().lower()


def _under_any(path: str, roots: list[str]) -> bool:
    try:
        resolved = Path(path).resolve()
    except OSError:
        return False
    for root in roots:
        try:
            resolved.relative_to(Path(root).resolve())
            return True
        except ValueError:
            continue
    return False


def classify_skill_scope(
    source: str,
    *,
    workspace_path: str | None,
    auto_workspace_mounts: list[str],
    global_roots: list[str],
) -> SkillScope:
    src = str(Path(source).expanduser().resolve()) if source else ""
    auto = {str(Path(p).expanduser().resolve()) for p in auto_workspace_mounts}
    if src in auto:
        return "project"
    if workspace_path and _under_any(src, [workspace_path]):
        return "project"
    if _under_any(src, global_roots):
        return "global"
    return "custom"


def resolve_effective_skill_keys(agent: dict[str, Any] | None = None) -> list[str]:
    """
    Open catalog (Grok-aligned D7): Enabled global∪project∪custom, plus agent binds.

    Same short-name dedupe: project > custom > global. Agent-bound keys always kept.
    """
    agent = agent or {}
    bound = [
        str(k).strip()
        for k in (agent.get("skills") or [])
        if str(k).strip()
    ]
    bound_set = set(bound)

    registry = load_registry()
    skills = list(registry.get("skills") or [])
    if not skills and not bound:
        return []

    workspace = get_workspace()
    workspace_path = workspace.get("workspace_path") if workspace else None
    auto_ws = [str(p) for p in (registry.get("auto_workspace_mounts") or [])]
    global_roots = discover_user_skill_directories()

    # Legacy registries defaulted every toggle to False — treat "all off" as all enabled.
    any_enabled = any(bool(item.get("isActiveGlobally")) for item in skills)
    legacy_all_off = bool(skills) and not any_enabled

    ranked: dict[str, tuple[int, str]] = {}
    for item in skills:
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        enabled = bool(item.get("isActiveGlobally")) or legacy_all_off or key in bound_set
        if not enabled:
            continue
        scope = classify_skill_scope(
            str(item.get("source") or ""),
            workspace_path=str(workspace_path) if workspace_path else None,
            auto_workspace_mounts=auto_ws,
            global_roots=global_roots,
        )
        name = _short_name(key)
        rank = _SCOPE_RANK[scope]
        prev = ranked.get(name)
        if prev is None or rank < prev[0]:
            ranked[name] = (rank, key)

    # Force-include agent binds even if disabled / lost the dedupe race under another key.
    for key in bound:
        name = _short_name(key)
        ranked[name] = (-1, key)

    # Stable order: by scope rank then key
    ordered = sorted(ranked.values(), key=lambda item: (item[0], item[1]))
    return [key for _, key in ordered]


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
        "Full skill bodies are not in this catalog. Call clutch-tools `read_skill` "
        "with the skill key (e.g. `my-skills/secure-review`) when you need the full "
        "SKILL.md instructions."
    )
    return "\n".join(lines)


def load_skill_body(skill_key: str) -> str:
    """Return full SKILL.md for one registry key, or empty string if missing (D7)."""
    key = str(skill_key or "").strip()
    if not key:
        return ""
    return compose_skills_section([key], include_bodies=True)
