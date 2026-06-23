"""Project LangGraph compiler state into ClutchState patches."""

from __future__ import annotations

from typing import Any

from src.chat_events import chat_message
from src.compiler.compiler import CompilerState
from src.state import ClutchState


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def token_patch_turn(state: ClutchState, *, user_text: str, assistant_text: str) -> dict[str, int | float]:
    input_tokens = state.get("token_input", 0) + _estimate_tokens(user_text)
    output_tokens = state.get("token_output", 0) + _estimate_tokens(assistant_text)
    total = input_tokens + output_tokens
    return {
        "token_input": input_tokens,
        "token_output": output_tokens,
        "session_tokens": total,
        "session_cost_usd": round(total * 0.00000015, 6),
    }


def project_graph_to_clutch(
    state: ClutchState,
    graph_result: CompilerState,
    *,
    workflow: dict[str, Any],
    instruction: str,
    prepend_logs: list[str] | None = None,
) -> dict[str, Any]:
    messages = list(state["messages"])
    logs = list(state["terminal_logs"])
    if prepend_logs:
        logs.extend(prepend_logs)

    if instruction.strip():
        messages.append(chat_message("User", instruction.strip()))

    for message in graph_result.get("task_messages", []):
        messages.append(message)

    logs.extend(graph_result.get("task_logs", []))
    logs.append(f"[LANGGRAPH] Active node → {graph_result['active_node_id']}")

    if graph_result["status"] == "awaiting_human":
        logs.append("[SUPERVISOR] Human gate reached — awaiting decision.")
        messages.append(
            chat_message(
                "Evaluator",
                "Validation checks did not pass. Review the terminal log, then approve, reject, or retry with instructions.",
                status="FAILED",
                badge_text="VALIDATION FAILED",
            )
        )

    assistant_text = " ".join(
        str(message.get("text", ""))
        for message in graph_result.get("task_messages", [])
        if message.get("agent") != "User"
    )
    token_patch = (
        token_patch_turn(state, user_text=instruction, assistant_text=assistant_text)
        if instruction.strip() or assistant_text
        else {}
    )

    return {
        "workflow_id": workflow["id"],
        "current_instruction": instruction,
        "messages": messages,
        "terminal_logs": logs,
        "active_node_id": graph_result["active_node_id"],
        "active_agent": graph_result["active_agent"],
        "status": graph_result["status"],
        **token_patch,
    }
