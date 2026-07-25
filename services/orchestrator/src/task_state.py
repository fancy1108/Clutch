"""Format live Todo / Plan for compaction digests and D53 task_state layer (D8)."""

from __future__ import annotations

from typing import Any


def latest_plan_card(messages: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """Return the newest planCard on a message (skip cancelled if status present)."""
    latest: dict[str, Any] | None = None
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        card = message.get("planCard") or message.get("plan_card")
        if not isinstance(card, dict) or not card:
            continue
        status = str(card.get("status") or "").strip().lower()
        if status in {"cancelled", "canceled", "rejected"}:
            continue
        latest = card
    return latest


def format_task_state(
    *,
    agent_todos: list[dict[str, Any]] | None = None,
    plan_card: dict[str, Any] | None = None,
) -> str:
    """
    Short deterministic snapshot of open work for LLM context (D8).

    Empty string when there is nothing useful to inject.
    """
    lines: list[str] = []
    if isinstance(plan_card, dict) and plan_card:
        title = str(plan_card.get("title") or "Plan").strip() or "Plan"
        status = str(plan_card.get("status") or "").strip()
        header = f"Plan: {title}" + (f" ({status})" if status else "")
        lines.append(header)
        steps = plan_card.get("steps") or []
        if isinstance(steps, list):
            for i, step in enumerate(steps, 1):
                text = str(step).strip() if not isinstance(step, dict) else str(
                    step.get("content") or step.get("text") or step
                ).strip()
                if text:
                    lines.append(f"  {i}. {text}")

    todos = [t for t in (agent_todos or []) if isinstance(t, dict)]
    if todos:
        lines.append("Todos:")
        for item in todos:
            content = str(item.get("content") or item.get("text") or "").strip()
            if not content:
                continue
            status = str(item.get("status") or "pending").strip().lower()
            mark = {
                "completed": "x",
                "done": "x",
                "in_progress": "~",
                "pending": " ",
            }.get(status, " ")
            lines.append(f"  [{mark}] {content}")

    if not lines:
        return ""
    lines.append(
        "If the user only asks what remains / status / 还剩什么 / 还剩哪些 todo, "
        "answer from this list in plain text and do NOT call tools or resume edits "
        "unless they explicitly ask to continue working."
    )
    return "## Current task state\n" + "\n".join(lines)


def format_task_state_from_clutch_state(state: dict[str, Any] | None) -> str:
    if not state:
        return ""
    return format_task_state(
        agent_todos=list(state.get("agent_todos") or []),
        plan_card=latest_plan_card(list(state.get("messages") or [])),
    )
