"""Handoff markdown writer for D34 terminal orchestra."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from src.handoff_summarizer import summarize_lane_transcripts


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


def _format_referenced_files_section(refs: list[str]) -> str:
    lines: list[str] = ["## Referenced files", ""]
    if refs:
        for ref in refs:
            lines.append(f"- @{ref}")
    else:
        lines.append("- (none)")
    return "\n".join(lines)


def write_handoff_markdown(
    workspace_path: str,
    *,
    sources: list[str],
    target: str,
    task: str,
    prompt: str,
    file_refs: list[str] | None = None,
    dispatch_history: list[dict[str, object]] | None = None,
    lane_transcripts: list[dict[str, object]] | None = None,
) -> tuple[str, str]:
    """Write handoff file; returns (relative_path, file_name)."""
    file_name = handoff_filename(sources, target)
    rel_path = f".clutch/handoffs/{file_name}"
    root = Path(workspace_path)
    out = root / rel_path
    out.parent.mkdir(parents=True, exist_ok=True)
    sources_label = " + ".join(sources) if sources else "工作区"
    refs = file_refs or []
    created_at = datetime.now(timezone.utc).isoformat()

    history_block = ""
    if dispatch_history:
        history_lines = ["## Dispatch history", ""]
        for entry in dispatch_history:
            src = str(entry.get("sources_label") or "?")
            tgt = str(entry.get("target") or "?")
            when = str(entry.get("time") or "")
            body = str(entry.get("prompt") or "").strip()
            history_lines.append(f"- **{src} → {tgt}** ({when}): {body}" if body else f"- **{src} → {tgt}** ({when})")
        history_lines.append("")
        history_block = "\n".join(history_lines)

    source_output = summarize_lane_transcripts(
        lane_transcripts,
        sources_label=sources_label,
        target=target,
        task_focus=task or prompt,
    )

    referenced_files_block = _format_referenced_files_section(refs)

    body = f"""# Handoff: {sources_label} → {target}

## From
{sources_label}

## To
{target}

## Time
{created_at}

## User prompt
{prompt}

## Source output
{source_output}

{history_block}## Goal
{task or prompt}

## Sources
{chr(10).join(f"- {s}" for s in sources) if sources else "- (cold start / workspace)"}

{referenced_files_block}

## Subtask for receiver
Read this handoff (including Source output above) and continue in your Lane. Mark complete when done.
"""
    out.write_text(body, encoding="utf-8")
    return rel_path, file_name
