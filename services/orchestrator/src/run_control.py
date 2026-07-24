"""D9 run control helpers — loop fuse, continue-after-stop, chat-visible stats."""

from __future__ import annotations

import os
from typing import Any

DEFAULT_MAX_CONSECUTIVE_FAILURES = 3
DEFAULT_MAX_TOOL_STEPS = 24


def max_consecutive_failures() -> int:
    raw = (os.environ.get("CLUTCH_LOOP_FUSE_FAILURES") or "").strip()
    if not raw:
        return DEFAULT_MAX_CONSECUTIVE_FAILURES
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_CONSECUTIVE_FAILURES
    return max(1, value)


def is_tool_failure_result(result: str | None) -> bool:
    text = (result or "").strip()
    if not text:
        return True
    lowered = text.lower()
    if text.startswith("Error executing tool"):
        return True
    if text.startswith("MCP server not connected"):
        return True
    if "error executing tool" in lowered:
        return True
    return False


def fuse_message(*, failures: int, max_failures: int, lang: str = "en") -> str:
    if lang == "zh":
        return (
            f"已触发死循环熔断：连续 {failures} 次工具失败"
            f"（阈值 {max_failures}）。运行已停止，可点「继续」或发送新消息再试。"
        )
    return (
        f"Loop fuse triggered: {failures} consecutive tool failures "
        f"(threshold {max_failures}). Run stopped — click Continue or send a new message."
    )


def stop_supervisor_message(*, lang: str = "en") -> str:
    if lang == "zh":
        return "已停止当前运行。可点「继续」从中断处接着做，或直接发送新消息。"
    return "Run stopped. Click Continue to resume, or send a new message."


def continue_user_prompt(*, lang: str = "en") -> str:
    if lang == "zh":
        return "请从刚才中断处继续。"
    return "Continue from where you left off."


def build_run_stats(
    *,
    tool_steps: int = 0,
    max_steps: int = DEFAULT_MAX_TOOL_STEPS,
    session_tokens: int = 0,
    fuse_triggered: bool = False,
    consecutive_failures: int = 0,
) -> dict[str, Any]:
    return {
        "tool_steps": max(0, int(tool_steps)),
        "max_steps": max(1, int(max_steps)),
        "session_tokens": max(0, int(session_tokens)),
        "fuse_triggered": bool(fuse_triggered),
        "consecutive_failures": max(0, int(consecutive_failures)),
    }


def should_offer_continue(reply_text: str | None) -> bool:
    """True when the assistant reply indicates stop/fuse/limit — Chat should show Continue."""
    text = reply_text or ""
    markers = (
        "Loop fuse triggered",
        "死循环熔断",
        "maximum tool call iteration limit",
        "Run stopped",
        "已停止当前运行",
    )
    return any(marker in text for marker in markers)
