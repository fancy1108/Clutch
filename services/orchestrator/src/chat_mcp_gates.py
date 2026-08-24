"""MCP approval / plan / question pause helpers (D38)."""

from __future__ import annotations

import json
from typing import Any

from src.preferences_storage import tr
from src.chat_messages import _chat_message

def _mcp_supervisor_approval_text(func_name: str, func_args: dict[str, Any]) -> str:
    from src.mcp_risk import normalize_mcp_func_args_for_display

    detail = ""
    if func_args:
        display_args = normalize_mcp_func_args_for_display(func_args)
        # Fenced JSON so Chat can Expand/scroll — do not crush to 120 chars.
        preview = json.dumps(display_args, ensure_ascii=False, indent=2)
        if len(preview) > 12_000:
            preview = preview[:12_000] + "\n…(truncated)"
        detail = f"\n\nArgs:\n```json\n{preview}\n```"
    return tr(
        f"MCP tool `{func_name}` requires your approval before execution.{detail}",
        f"MCP 工具 `{func_name}` 需要您批准后才能执行。{detail}",
    )

def _supervisor_gate_messages(
    messages: list[dict[str, Any]],
    func_name: str,
    func_args: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    """Append a supervisor approval line; skip duplicate approval for the same tool intent.

    Returns (messages, gate_message, created) where created=False if an existing
    Supervisor bubble with the same approvalKey was reused (do not re-emit WS message).
    """
    from src.mcp_risk import mcp_approval_key

    approval_key = mcp_approval_key(func_name, func_args)
    text = _mcp_supervisor_approval_text(func_name, func_args)
    for msg in reversed(messages[-12:]):
        if msg.get("agent") == "Supervisor" and msg.get("approvalKey") == approval_key:
            return messages, msg, False
    supervisor = _chat_message("Supervisor", text)
    supervisor["approvalKey"] = approval_key
    return [*messages, supervisor], supervisor, True


def _is_plan_pause(mcp_pause: dict[str, Any]) -> bool:
    from src.builtin_tools import is_propose_plan_tool

    if str(mcp_pause.get("kind") or "") == "plan":
        return True
    return is_propose_plan_tool(str(mcp_pause.get("func_name") or ""))


def _is_question_pause(mcp_pause: dict[str, Any]) -> bool:
    from src.builtin_tools import is_ask_user_question_tool

    if str(mcp_pause.get("kind") or "") == "question":
        return True
    return is_ask_user_question_tool(str(mcp_pause.get("func_name") or ""))


def _mcp_pause_gate_line(mcp_pause: dict[str, Any]) -> str:
    name = mcp_pause.get("func_name")
    if _is_plan_pause(mcp_pause):
        return f"[CHAT] Awaiting plan approval: {name}"
    if _is_question_pause(mcp_pause):
        return f"[CHAT] Awaiting answer for question: {name}"
    return f"[CHAT] Awaiting approval for MCP tool: {name}"


def _mcp_pause_human_prompt(mcp_pause: dict[str, Any]) -> str:
    if _is_plan_pause(mcp_pause):
        return tr("Approve the proposed plan to continue.", "请批准计划后继续执行。")
    if _is_question_pause(mcp_pause):
        return tr("Choose an option to continue.", "请选择一个选项以继续。")
    return tr(
        f"Approve MCP tool call: {mcp_pause['func_name']}",
        f"请审批 MCP 工具调用：{mcp_pause['func_name']}",
    )


def _messages_for_mcp_pause(
    messages: list[dict[str, Any]],
    mcp_pause: dict[str, Any],
    *,
    reply_label: str,
) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    """Append Supervisor gate, D49 plan card, or D49 question card for a pause.

    Returns (messages, pause_msg, created).
    """
    if _is_plan_pause(mcp_pause):
        from src.builtin_tools import normalize_plan_args

        plan = normalize_plan_args(dict(mcp_pause.get("func_args") or {}))
        card = {
            "title": plan["title"],
            "steps": plan["steps"],
            "status": "pending",
        }
        if plan["summary"]:
            card["summary"] = plan["summary"]
        plan_msg = _chat_message(
            reply_label,
            "",
            plan_card=card,
        )
        return [*messages, plan_msg], plan_msg, True
    if _is_question_pause(mcp_pause):
        from src.builtin_tools import normalize_question_args

        q = normalize_question_args(dict(mcp_pause.get("func_args") or {}))
        card = {
            "question": q["question"],
            "options": q["options"],
            "status": "pending",
            "allowCustom": q["allow_custom"],
        }
        question_msg = _chat_message(
            reply_label,
            "",
            question_card=card,
        )
        return [*messages, question_msg], question_msg, True
    return _supervisor_gate_messages(
        messages,
        str(mcp_pause["func_name"]),
        dict(mcp_pause.get("func_args") or {}),
    )


def _patch_plan_card_status(
    messages: list[dict[str, Any]],
    *,
    status: str,
    note: str | None = None,
    step_comments: list[str] | None = None,
) -> list[dict[str, Any]]:
    updated = list(messages)
    for idx in range(len(updated) - 1, -1, -1):
        card = updated[idx].get("planCard")
        if isinstance(card, dict) and card.get("status") == "pending":
            next_card = {**card, "status": status}
            if note:
                next_card["note"] = note
            if step_comments is not None:
                next_card["stepComments"] = list(step_comments)
            updated[idx] = {**updated[idx], "planCard": next_card}
            break
    return updated


def _patch_question_card_status(
    messages: list[dict[str, Any]],
    *,
    status: str,
    selected: dict[str, str] | None = None,
    note: str | None = None,
) -> list[dict[str, Any]]:
    updated = list(messages)
    for idx in range(len(updated) - 1, -1, -1):
        card = updated[idx].get("questionCard")
        if isinstance(card, dict) and card.get("status") == "pending":
            next_card = {**card, "status": status}
            if selected:
                next_card["selectedId"] = selected.get("id") or ""
                next_card["selectedLabel"] = selected.get("label") or ""
            if note:
                next_card["note"] = note
            updated[idx] = {**updated[idx], "questionCard": next_card}
            break
    return updated

