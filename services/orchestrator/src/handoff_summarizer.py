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


def clean_pty_transcript(raw: str, max_chars: int = 12000) -> str:
    """Strip ANSI/PTY control noise, filter out TUI draw/status lines, and normalize whitespace."""
    text = _erase_backspaces(strip_ansi(raw)).replace("\r\n", "\n").replace("\r", "\n")
    
    # Filter lines to remove terminal UI borders, status lines, and control noise
    lines = text.split("\n")
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Filter out repeated blocks and lines that are purely TUI layout artifacts
        if len(stripped) > 5 and len(set(stripped)) <= 2: # e.g. "━━━━━━" or "██████"
            continue
        # Filter out common TUI status bars and hotkey guides
        if "切换模式" in stripped or "ctrl+p" in stripped or "添加文件" in stripped or "唤起命令" in stripped:
            continue
        if "esc interrupt" in stripped or "Background terminals" in stripped:
            continue
        if "Xiaomi" in stripped or "Mimo Code" in stripped or "MiMo Auto" in stripped or "DeepSeek V4" in stripped:
            # Skip Mimo/Opencode TUI headers
            if "你好" not in stripped and "我刚刚" not in stripped:
                continue
        # Clean up block characters
        line_clean = line.replace("█", "").replace("░", "").replace("▒", "").strip()
        if not line_clean:
            continue
        filtered_lines.append(line_clean)
        
    text = "\n".join(filtered_lines)
    text = _WS_RE.sub("\n", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    cleaned = text.strip()
    
    if len(cleaned) > max_chars:
        truncated = cleaned[-max_chars:]
        if "\n" in truncated:
            truncated = truncated.split("\n", 1)[-1]
        return truncated.strip()
    return cleaned


def truncate_transcript_fallback(text: str, *, max_chars: int = _FALLBACK_MAX_CHARS) -> str:
    """Intelligent truncation when LLM summarization is unavailable."""
    cleaned = clean_pty_transcript(text, max_chars=999999)
    if not cleaned:
        return "(no upstream session captured)"
    if len(cleaned) <= max_chars:
        return cleaned
    head = cleaned[: max_chars // 2].rsplit("\n", 1)[0]
    tail = cleaned[-(max_chars // 2) :].split("\n", 1)[-1]
    return f"{head}\n\n…\n\n{tail}"


def _format_chat_messages_for_prompt(chat_messages: list[dict[str, Any]] | None) -> str:
    if not chat_messages:
        return ""
    blocks = []
    for msg in chat_messages:
        role = str(msg.get("role") or "").capitalize()
        content = msg.get("content")
        text = ""
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(str(part.get("text") or ""))
            text = "\n".join(text_parts)
        if text.strip():
            agent_prefix = f" ({msg.get('agent_id')})" if msg.get("agent_id") else ""
            blocks.append(f"[{role}{agent_prefix}]: {text.strip()}")
    return "\n".join(blocks)


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
    chat_messages: list[dict[str, Any]] | None = None,
) -> str:
    """Summarize upstream PTY session(s) and chat context via built-in LLM; fallback to cleaned truncation."""
    combined = _format_transcripts_for_prompt(lane_transcripts or [])
    chat_history_str = _format_chat_messages_for_prompt(chat_messages)

    if not combined.strip() and not chat_history_str.strip():
        return "(no upstream session captured)"

    user_focus = task_focus.strip() or f"Continue work in {target} after handoff from {sources_label}."
    
    prompt_parts = [
        f"Handoff context: {sources_label} → {target}",
        f"Next session focus: {user_focus}"
    ]
    if chat_history_str.strip():
        prompt_parts.append(f"### Chat History Context:\n\n{chat_history_str}")
    if combined.strip():
        prompt_parts.append(f"### Source Terminal Session Transcript:\n\n{combined}")

    user_content = "\n\n".join(prompt_parts)

    try:
        from src.models_config import get_router
        from src.llm.router import LLMProviderRouter

        router = get_router()
        messages = [
            {"role": "system", "content": _HANDOFF_SKILL_SYSTEM},
            {"role": "user", "content": user_content},
        ]
        response = router.chat(messages, max_tokens=600, timeout_sec=10.0)
        summary = LLMProviderRouter.extract_content(response)
        if summary:
            return summary
    except Exception as exc:
        logger.warning("Handoff LLM summarization failed, using fallback: %s", exc)

    return truncate_transcript_fallback(combined) if combined.strip() else "(no upstream session captured)"




