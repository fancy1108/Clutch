"""D10 — isolated nested subagent runs for delegate_subtask."""

from __future__ import annotations

import contextvars
import json
import uuid
from collections.abc import Callable
from typing import Any

_delegate_context: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "delegate_context", default=None
)


def get_delegate_context() -> dict[str, Any] | None:
    return _delegate_context.get()


def bind_delegate_context(ctx: dict[str, Any]) -> contextvars.Token[dict[str, Any] | None]:
    return _delegate_context.set(ctx)


def release_delegate_context(token: contextvars.Token[dict[str, Any] | None]) -> None:
    _delegate_context.reset(token)


_EXPLORE_SYSTEM = (
    "You are a read-only exploration subagent (D10). "
    "Use only read/list/search tools to investigate. "
    "Do NOT write files, run mutating shell commands, or call delegate_subtask."
)
_IMPLEMENT_SYSTEM = (
    "You are an implementation subagent (D10). "
    "Complete the scoped task with available tools. Do not call delegate_subtask."
)


def normalize_delegate_args(raw: dict[str, Any]) -> dict[str, Any]:
    task_type = str(raw.get("type") or "explore").strip().lower()
    if task_type not in {"explore", "implement"}:
        task_type = "explore"
    prompt = str(raw.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("delegate_subtask requires a non-empty `prompt`")
    title = str(raw.get("title") or "").strip()
    if not title:
        title = prompt.splitlines()[0][:80] or ("Explore" if task_type == "explore" else "Implement")
    return {"type": task_type, "prompt": prompt, "title": title}


def initial_subtask_card(args: dict[str, Any], *, subtask_id: str | None = None) -> dict[str, Any]:
    return {
        "id": subtask_id or f"sub_{uuid.uuid4().hex[:8]}",
        "type": args["type"],
        "title": args["title"],
        "summary": "",
        "status": "running",
        "toolSteps": [],
    }


def upsert_subtask(subtasks: list[dict[str, Any]], card: dict[str, Any]) -> list[dict[str, Any]]:
    sid = str(card.get("id") or "").strip()
    if not sid:
        return subtasks + [card]
    out = list(subtasks)
    for idx, item in enumerate(out):
        if str(item.get("id") or "") == sid:
            out[idx] = {**item, **card, "id": sid}
            return out
    out.append(card)
    return out


def _brief_tool_steps(steps: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    brief: list[dict[str, str]] = []
    for step in steps or []:
        name = str(step.get("tool") or step.get("name") or "tool").strip()
        status = str(step.get("status") or "completed").strip()
        brief.append({"name": name, "status": status})
    return brief


def run_subagent(
    *,
    task_type: str,
    prompt: str,
    title: str | None = None,
    servers: list[dict[str, Any]],
    model_id: str | None = None,
    on_log: Callable[[str], None] | None = None,
    on_subtask_update: Callable[[dict[str, Any]], None] | None = None,
    max_steps: int = 8,
    permission_mode: str = "ask",
    pause_on_risky: bool = True,
    subtask_id: str | None = None,
) -> dict[str, Any]:
    """Run an isolated nested ReAct loop; returns a subtask card dict."""
    from src.mcp_react import run_mcp_react_loop

    args = normalize_delegate_args(
        {"type": task_type, "prompt": prompt, "title": title or ""}
    )
    card = initial_subtask_card(args, subtask_id=subtask_id)

    def emit(card_patch: dict[str, Any]) -> None:
        nonlocal card
        card = {**card, **card_patch, "id": card["id"]}
        if on_subtask_update:
            on_subtask_update(dict(card))

    emit(card)
    system = _EXPLORE_SYSTEM if args["type"] == "explore" else _IMPLEMENT_SYSTEM
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": args["prompt"]},
    ]
    sub_permission = "plan" if args["type"] == "explore" else permission_mode
    collected_steps: list[dict[str, Any]] = []

    def on_tool_step(step: dict[str, Any]) -> None:
        from src.tool_steps import upsert_tool_step

        collected_steps[:] = upsert_tool_step(collected_steps, step)
        emit({"toolSteps": _brief_tool_steps(collected_steps)})

    try:
        outcome = run_mcp_react_loop(
            messages=messages,
            servers=servers,
            log_prefix="SUBAGENT",
            max_steps=max_steps,
            on_log=on_log,
            on_tool_step=on_tool_step,
            pause_on_risky=pause_on_risky,
            permission_mode=sub_permission,
            model_id=model_id,
            exclude_builtin_tools=frozenset({"delegate_subtask"}),
        )
    except Exception as exc:
        failed = {
            **card,
            "status": "failed",
            "summary": str(exc),
            "error": str(exc),
        }
        emit(failed)
        return failed

    output = (outcome.output or "").strip()
    tool_steps = _brief_tool_steps(outcome.tool_steps)
    failed = bool(outcome.fuse_triggered) or (
        output.startswith("Error executing tool") or output.startswith("Agent task hit maximum")
    )
    if failed and not output:
        output = "Subagent failed without a summary."
    status = "failed" if failed else "done"
    summary = output[:2000] if output else ("Completed" if status == "done" else "Failed")
    result = {
        **card,
        "status": status,
        "summary": summary,
        "toolSteps": tool_steps,
    }
    if status == "failed":
        result["error"] = summary
    emit(result)
    return result


def delegate_result_json(card: dict[str, Any]) -> str:
    payload = {
        "id": card.get("id"),
        "type": card.get("type"),
        "title": card.get("title"),
        "status": card.get("status"),
        "summary": card.get("summary"),
        "tool_steps": card.get("toolSteps") or [],
        "error": card.get("error"),
    }
    return json.dumps(payload, ensure_ascii=False)
