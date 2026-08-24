"""Chat message construction, seal helpers, and LLM history (D38)."""

from __future__ import annotations

import uuid
from typing import Any

from src.state import ClutchState

def _sealed_subtasks(
    state: ClutchState,
    *,
    sink: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]] | None:
    from src.subagent_runner import upsert_subtask

    subtasks = list(state.get("pending_subtasks") or [])
    for item in sink or []:
        subtasks = upsert_subtask(subtasks, item)
    return subtasks or None


_AGENT_AVATARS: dict[str, str] = {
    "Orchestrator": "https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p",
    "Builder": "https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b",
    "Evaluator": "https://lh3.googleusercontent.com/aida-public/AB6AXuCmb7VGaQXE-4sYnIZR3VrcHVAPhv4Px14kMlkayJj8kVm8htTWITmPi26wsj8P6B9RrqykIWj81S2ilmGR0e8cXhA1gjc3U-Nw0DsgHV3HvVmBskuoUksIt6YM6Z3ORjFtRhBphqAXxRKf9ke-zYcPs0TcEFKxw_bwGXSDiAKV5CL7kZf9i6lSZDe91ccUNjaAIsgTMKEEvYc7bZpXYz3D5dClulRwbNru5SZB-1E5FM0A2qMPs-IAfiR8OB1-cUvFh3WYKx9qlGgN",
    "Supervisor": "",
    "User": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=100",
}

def _chat_time() -> str:
    from src.chat_events import chat_time

    return chat_time()

def _chat_message(
    agent: str,
    text: str,
    *,
    status: str | None = None,
    msg_id: str | None = None,
    runtime_engine: str | None = None,
    raw_output: str | None = None,
    output_events: list[dict[str, Any]] | None = None,
    tool_steps: list[dict[str, Any]] | None = None,
    files_changed: list[str] | None = None,
    plan_card: dict[str, Any] | None = None,
    todo_list: list[dict[str, Any]] | None = None,
    question_card: dict[str, Any] | None = None,
    verification_report: dict[str, Any] | None = None,
    diff_summary: dict[str, Any] | None = None,
    subtask_cards: list[dict[str, Any]] | None = None,
    bg_job: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": msg_id or f"msg_{uuid.uuid4().hex[:8]}",
        "agent": agent,
        "avatar": _AGENT_AVATARS.get(agent, ""),
        "time": _chat_time(),
        "text": text,
    }
    if status:
        payload["status"] = status
    if runtime_engine:
        payload["runtimeEngine"] = runtime_engine
    if raw_output is not None:
        payload["rawOutput"] = raw_output
    if output_events is not None:
        payload["outputEvents"] = output_events
    if tool_steps is not None:
        payload["toolSteps"] = tool_steps
    if files_changed:
        # D47: relative paths sealed onto the assistant bubble for clickable chips.
        payload["filesChanged"] = list(dict.fromkeys(files_changed))
    if plan_card is not None:
        # D49: structured plan card for Approve / revise / Cancel (D2).
        payload["planCard"] = plan_card
    if todo_list:
        # D3/D49: todo checklist sealed onto the assistant turn.
        payload["todoList"] = todo_list
    if question_card is not None:
        # D4/D49: multiple-choice question card.
        payload["questionCard"] = question_card
    if verification_report is not None:
        # D5/D50: self-check report card.
        payload["verificationReport"] = verification_report
    if diff_summary is not None:
        # D6/D50: diff review card.
        payload["diffSummary"] = diff_summary
    if subtask_cards:
        # D10/D48: nested subtask cards sealed onto the assistant turn.
        payload["subtaskCards"] = subtask_cards
    if bg_job is not None:
        # D11: finished background job card lives in the Chat timeline (not the composer).
        payload["bgJob"] = bg_job
    return payload

def _verification_report_for_seal(
    state: ClutchState,
    *,
    files_changed: list[str] | None = None,
    mcp_pause: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    report = None
    if mcp_pause and isinstance(mcp_pause.get("verification_report"), dict):
        report = dict(mcp_pause["verification_report"])
    elif isinstance(state.get("verification_report"), dict):
        report = dict(state["verification_report"])  # type: ignore[arg-type]
    if not report:
        return None
    # Do not copy a leftover card onto a later turn (e.g. 记住: after a prior 验证报告).
    messages = list(state.get("messages") or [])
    last_user = -1
    last_card = -1
    title = report.get("title")
    conclusion = report.get("conclusion")
    for idx, msg in enumerate(messages):
        if not isinstance(msg, dict):
            continue
        if str(msg.get("agent") or "") == "User":
            last_user = idx
        existing = msg.get("verificationReport")
        if (
            isinstance(existing, dict)
            and existing.get("title") == title
            and existing.get("conclusion") == conclusion
        ):
            last_card = idx
    if last_card >= 0 and last_user > last_card:
        return None
    paths = list(report.get("changedFiles") or [])
    for path in files_changed or []:
        rel = str(path).strip()
        if rel and rel not in paths:
            paths.append(rel)
    if paths:
        report["changedFiles"] = paths
    return report

def _diff_summary_for_seal(
    state: ClutchState,
    *,
    files_changed: list[str] | None = None,
    mcp_pause: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Seal only an explicit (non-inline) DiffSummary onto the final reply.

    Cursor-style inline per-edit cards are already published mid-turn; do not
    re-attach an aggregate card under the closing text bubble.
    """
    card = None
    if mcp_pause and isinstance(mcp_pause.get("diff_summary"), dict):
        card = dict(mcp_pause["diff_summary"])
    elif isinstance(state.get("diff_summary"), dict):
        card = dict(state["diff_summary"])  # type: ignore[arg-type]
    if not card or not card.get("files"):
        return None
    if card.get("inline"):
        return None
    return card

def _sealed_tool_steps(
    state: ClutchState,
    *,
    sink: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]] | None:
    from src.tool_steps import complete_running_steps, upsert_tool_step

    steps = list(state.get("pending_tool_steps") or [])
    for item in sink or []:
        steps = upsert_tool_step(steps, item)
    sealed = complete_running_steps(steps)
    return sealed or None


def _merge_files_changed_with_tool_steps(
    files_changed: list[str] | None,
    sealed_steps: list[dict[str, Any]] | None,
) -> list[str]:
    """Union outcome paths with D6 fileDiff paths so chips/Changes match Diff cards."""
    merged: list[str] = []
    for path in files_changed or []:
        rel = str(path).strip()
        if rel and rel not in merged:
            merged.append(rel)
    for step in sealed_steps or []:
        if not isinstance(step, dict):
            continue
        file_diff = step.get("fileDiff")
        if not isinstance(file_diff, dict):
            continue
        rel = str(file_diff.get("path") or "").strip()
        if rel and rel not in merged:
            merged.append(rel)
    return merged

def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))

def _token_patch(state: ClutchState, text: str) -> dict[str, int | float]:
    added = _estimate_tokens(text)
    input_tokens = state.get("token_input", 0) + added
    output_tokens = state.get("token_output", 0) + max(1, added // 2)
    total = input_tokens + output_tokens
    return {
        "token_input": input_tokens,
        "token_output": output_tokens,
        "session_tokens": total,
        "session_cost_usd": round(total * 0.00000015, 6),
    }

def _token_patch_turn(
    state: ClutchState, *, user_text: str, assistant_text: str
) -> dict[str, int | float]:
    input_tokens = state.get("token_input", 0) + _estimate_tokens(user_text)
    output_tokens = state.get("token_output", 0) + _estimate_tokens(assistant_text)
    total = input_tokens + output_tokens
    return {
        "token_input": input_tokens,
        "token_output": output_tokens,
        "session_tokens": total,
        "session_cost_usd": round(total * 0.00000015, 6),
    }

def _history_for_llm(
    messages: list[dict[str, object]],
    *,
    vision_enabled: bool = False,
    image_delivery: str = "auto",
    hybrid_executions: dict[str, object] | None = None,
) -> list[dict[str, Any]]:
    """Build chat history for an engine.

    image_delivery:
      - ``auto``: multimodal parts when vision_enabled else OCR text fallback
      - ``paths``: persist data-URLs to workspace files and pass ``@path`` (CLI-first)
      - ``ocr``: force local OCR/palette text (refusal fallback)
      - ``multimodal``: force vision parts
    """
    from src.chat_content import (
        materialize_images_as_file_refs,
        normalize_text_content,
        user_message_content_for_llm,
    )

    if image_delivery == "auto":
        mode = "multimodal" if vision_enabled else "ocr"
    else:
        mode = image_delivery

    history: list[dict[str, Any]] = []
    hybrid_map = hybrid_executions or {}
    for message in messages:
        agent = str(message.get("agent", ""))
        text = str(message.get("text", "")).strip()
        if not text:
            msg_id = str(message.get("id", ""))
            entry = hybrid_map.get(msg_id) if msg_id else None
            if isinstance(entry, dict):
                events = entry.get("outputEvents") or message.get("outputEvents") or []
                if isinstance(events, list):
                    for event in events:
                        if not isinstance(event, dict):
                            continue
                        if event.get("type") == "assistant" and event.get("visible", True) is not False:
                            text = str(event.get("content", "")).strip()
                            if text:
                                break
        if not text:
            continue
        if agent in {"Supervisor", "Orchestrator"}:
            continue
        role = "user" if agent == "User" else "assistant"
        if role == "user":
            if mode == "paths":
                content = materialize_images_as_file_refs(text)
            elif mode == "multimodal":
                content = user_message_content_for_llm(text, vision_enabled=True)
            else:
                content = user_message_content_for_llm(text, vision_enabled=False)
        else:
            content = text
        # Preserve multimodal parts for vision-capable chat models; flatten for CLIs / text-only.
        if mode == "multimodal" and isinstance(content, list):
            if not content:
                continue
            history.append({"role": role, "content": content})
            continue
        normalized = normalize_text_content(content)
        if not normalized:
            continue
        history.append({"role": role, "content": normalized})
    return history

