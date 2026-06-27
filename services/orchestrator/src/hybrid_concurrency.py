"""Hybrid plain-chat concurrency rejections (HRT-08 · strategy C)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.preferences_storage import tr
from src.shell_session import ShellSessionBusyError, ShellSessionError, ShellSessionPoolFullError

HYBRID_CONCURRENCY_CODES = frozenset({"run_in_progress", "session_busy", "pool_full"})


class HybridPlainChatRejected(ShellSessionError):
    """Hybrid turn rejected; must not fall back to legacy subprocess."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def hybrid_rejection_for_exception(exc: Exception) -> HybridPlainChatRejected | None:
    if isinstance(exc, HybridPlainChatRejected):
        return exc
    if isinstance(exc, ShellSessionBusyError):
        return HybridPlainChatRejected(
            "session_busy",
            tr(
                "This chat is still running a Hybrid shell turn. Wait for the reply or press Stop, then try again.",
                "此会话仍在执行 Hybrid shell 轮次。请等待回复或点击 Stop 后再试。",
            ),
        )
    if isinstance(exc, ShellSessionPoolFullError):
        return HybridPlainChatRejected(
            "pool_full",
            tr(
                "All Hybrid shell sessions are busy. Wait for another chat to finish or try again shortly.",
                "所有 Hybrid shell 会话均在忙碌中。请等待其他会话完成后再试。",
            ),
        )
    return None


def hybrid_rejection_message(code: str) -> str:
    if code == "run_in_progress":
        return tr(
            "A message is already being processed in this chat. Wait for the reply or press Stop before sending again.",
            "此会话已有消息正在处理。请等待回复或点击 Stop 后再发送。",
        )
    if code == "session_busy":
        return tr(
            "This chat is still running a Hybrid shell turn. Wait for the reply or press Stop, then try again.",
            "此会话仍在执行 Hybrid shell 轮次。请等待回复或点击 Stop 后再试。",
        )
    if code == "pool_full":
        return tr(
            "All Hybrid shell sessions are busy. Wait for another chat to finish or try again shortly.",
            "所有 Hybrid shell 会话均在忙碌中。请等待其他会话完成后再试。",
        )
    return tr("Hybrid request rejected.", "Hybrid 请求被拒绝。")


def shell_session_status_for_rejection(code: str) -> str:
    return f"rejected_{code}"


def clear_stale_shell_rejection_status(state: Mapping[str, Any]) -> dict[str, Any] | None:
    """Drop persisted rejected_* when run is idle (queue supersedes run_in_progress)."""
    raw = state.get("shell_session_status")
    if state.get("status") != "idle":
        return None
    if not isinstance(raw, str) or not raw.startswith("rejected_"):
        return None
    return {"shell_session_status": "ready"}
