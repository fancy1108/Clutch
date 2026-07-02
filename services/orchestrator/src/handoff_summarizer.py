"""Summarize PTY lane transcripts for handoff markdown (Matt Pocock handoff skill)."""

from __future__ import annotations

import logging
import re
from typing import Any

from src.claude_hybrid_output_parser import _erase_backspaces, strip_ansi

logger = logging.getLogger(__name__)

# Matt Pocock handoff skill — ~/.claude/skills/handoff/SKILL.md
_HANDOFF_SKILL_SYSTEM = (
    "Write a handoff document summarising the current conversation so a fresh agent can continue the work.\n"
    "Include a brief \"Suggested skills\" subsection when relevant.\n"
    "Do not duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, diffs). "
    "Reference them by path or URL instead.\n"
    "Redact any sensitive information, such as API keys, passwords, or personally identifiable information.\n"
    "Be concise and bulleted. Focus on decisions, file changes, commands run, test results, and open blockers.\n"
    "Respond in the same language as the source transcript (English or Chinese).\n"
    "Return only the summary body — no YAML frontmatter or outer markdown title."
)

_FALLBACK_MAX_CHARS = 2400
_WS_RE = re.compile(r"[ \t]+\n")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def clean_pty_transcript(raw: str) -> str:
    """Strip ANSI/PTY control noise and normalize whitespace."""
    text = _erase_backspaces(strip_ansi(raw)).replace("\r\n", "\n").replace("\r", "\n")
    text = _WS_RE.sub("\n", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()


def truncate_transcript_fallback(text: str, *, max_chars: int = _FALLBACK_MAX_CHARS) -> str:
    """Intelligent truncation when LLM summarization is unavailable."""
    cleaned = clean_pty_transcript(text)
    if not cleaned:
        return "(no upstream session captured)"
    if len(cleaned) <= max_chars:
        return cleaned
    head = cleaned[: max_chars // 2].rsplit("\n", 1)[0]
    tail = cleaned[-(max_chars // 2) :].split("\n", 1)[-1]
    return f"{head}\n\n…\n\n{tail}"


def _format_transcripts_for_prompt(lane_transcripts: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for item in lane_transcripts:
        agent = str(item.get("agent") or item.get("lane_id") or "Agent")
        transcript = clean_pty_transcript(str(item.get("transcript") or ""))
        if transcript:
            blocks.append(f"### {agent}\n{transcript}")
    return "\n\n".join(blocks)


def summarize_lane_transcripts(
    lane_transcripts: list[dict[str, object]] | None,
    *,
    sources_label: str,
    target: str,
    task_focus: str = "",
) -> str:
    """Summarize upstream PTY session(s) via built-in LLM; fallback to cleaned truncation."""
    if not lane_transcripts:
        return "(no upstream session captured)"

    combined = _format_transcripts_for_prompt(lane_transcripts)  # type: ignore[arg-type]
    if not combined.strip():
        return "(no upstream session captured)"

    user_focus = task_focus.strip() or f"Continue work in {target} after handoff from {sources_label}."
    user_content = (
        f"Handoff context: {sources_label} → {target}\n"
        f"Next session focus: {user_focus}\n\n"
        f"Source terminal session transcript:\n\n{combined}"
    )

    try:
        from src.models_config import get_router

        router = get_router()
        messages = [
            {"role": "system", "content": _HANDOFF_SKILL_SYSTEM},
            {"role": "user", "content": user_content},
        ]
        response = router.chat(messages)
        if isinstance(response, dict):
            summary = str(response.get("content") or response).strip()
        else:
            summary = str(response).strip()
        if summary:
            return summary
    except Exception as exc:
        logger.warning("Handoff LLM summarization failed, using fallback: %s", exc)

    return truncate_transcript_fallback(combined)
