"""Handoff markdown writer for D34 terminal orchestra."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


def handoff_filename(sources: list[str], target: str) -> str:
    sources_key = ",".join(s.replace(" ", "") for s in sources) or "workspace"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    slug = target.replace(" ", "")
    return f"{ts}-{sources_key}→{slug}.md"


def parse_handoff_meta_from_name(file_name: str) -> dict[str, object]:
    """Best-effort metadata from handoff filename."""
    name = file_name.split("/")[-1]
    match = re.match(r"^(\d{8})-(.+?)→(.+?)\.md$", name)
    if not match:
        return {"name": name, "sources": [], "target": None, "sources_label": "未知"}
    _ts, sources_part, target_part = match.groups()
    if sources_part == "workspace":
        sources = ["工作区"]
    else:
        sources = [s.strip() for s in sources_part.split(",") if s.strip()]
    target = target_part.replace("opencode", "OpenCode").replace("claude", "Claude Code")
    if target_part.lower() == "opencode":
        target = "OpenCode"
    elif "claude" in target_part.lower():
        target = "Claude Code"
    return {
        "name": name,
        "sources": sources,
        "target": target,
        "sources_label": " + ".join(sources) if sources else "工作区",
    }


def write_handoff_markdown(
    workspace_path: str,
    *,
    sources: list[str],
    target: str,
    task: str,
    prompt: str,
    file_refs: list[str] | None = None,
) -> tuple[str, str]:
    """Write handoff file; returns (relative_path, file_name)."""
    file_name = handoff_filename(sources, target)
    rel_path = f".clutch/handoffs/{file_name}"
    root = Path(workspace_path)
    out = root / rel_path
    out.parent.mkdir(parents=True, exist_ok=True)
    sources_label = " + ".join(sources) if sources else "工作区"
    refs = file_refs or []
    body = f"""# Handoff: {sources_label} → {target}

## Goal
{task or prompt}

## User prompt
{prompt}

## Sources
{chr(10).join(f"- {s}" for s in sources) if sources else "- (cold start / workspace)"}

## Referenced files
{chr(10).join(f"- @{r}" for r in refs) if refs else "- (none)"}

## Subtask for receiver
Read this handoff and continue in your Lane. Mark complete when done.
"""
    out.write_text(body, encoding="utf-8")
    return rel_path, file_name
