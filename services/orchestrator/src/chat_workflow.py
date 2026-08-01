from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from typing import Any

from fastapi import HTTPException, WebSocket

from src.chat_messages import (
    _chat_message,
    _diff_summary_for_seal,
    _history_for_llm,
    _merge_files_changed_with_tool_steps,
    _sealed_tool_steps,
    _token_patch,
    _token_patch_turn,
    _verification_report_for_seal,
)
from src.chat_mcp_gates import _mcp_pause_gate_line, _messages_for_mcp_pause
from src.chat_plain import (
    _append_terminal_logs,
    _apply_hybrid_plain_chat_rejection,
    _compose_agent_system_prompt,
    _interrupt_plain_chat_shell,
    _llm_chat_reply,
    _maybe_notify_step_file_diff,
    _notify_workspace_files_changed,
    _path_diffs_from_tool_steps,
    _publish_diff_summary,
    _publish_verification_report,
    _uses_configured_llm,
)
from src.chat_run_live import (
    _commit_run_state,
    _get_or_create_run,
    _human_decision_inflight,
    _human_decision_locks,
    _merge_patch,
    _reasoning_live_patch,
    _run_sessions,
    _run_states,
    _setup_run_log_forwarder,
    _subtask_live_patch,
    _tool_step_live_patch,
)
from src.chat_ws_events import (
    _is_terminal_status,
    _notify_run_state,
    _send_human_required,
    _send_hybrid_execution_event,
    _send_log_event,
    _send_message_event,
    _send_pty_output,
    _send_pty_session_status,
    _send_state_patch,
    _send_validation_result,
    _try_ws_notify,
)
from src.compiler import WorkflowSession, begin_workflow, resume_workflow
from src.preferences_storage import tr
from src.run_history import update_run_record
from src.state import ClutchState, initial_state
from src.terminal_logs import TAG_HUMAN, TAG_WORKFLOW, stamp_log_line, tagged
from src.workflow_storage import resolve_workflow
from src.workflow_validator import WorkflowValidationError, load_and_validate_workflow, validate_workflow

logger = logging.getLogger(__name__)

def _iso_timestamp() -> str:
    from src.chat_runner import _iso_timestamp as _impl
    return _impl()


def _touch_session(*args, **kwargs):
    from src.chat_runner import _touch_session as _impl
    return _impl(*args, **kwargs)

def _apply_workflow_step_patch(run_id: str, patch: dict[str, Any]) -> None:
    state = _get_or_create_run(run_id)
    messages = list(state["messages"])
    new_messages: list[dict[str, Any]] = []
    for message in patch.get("new_messages", []):
        if not isinstance(message, dict):
            continue
        msg_id = str(message.get("id", ""))
        if msg_id and any(str(item.get("id", "")) == msg_id for item in messages):
            continue
        messages.append(message)
        new_messages.append(message)
    merged_patch = {key: value for key, value in patch.items() if key != "new_messages"}
    merged_patch["messages"] = messages
    if "hybrid_executions" in patch:
        merged_hybrid = dict(state.get("hybrid_executions") or {})
        incoming = patch.get("hybrid_executions") or {}
        if isinstance(incoming, dict):
            merged_hybrid.update(incoming)
        merged_patch["hybrid_executions"] = merged_hybrid
    state = _commit_run_state(run_id, _merge_patch(state, merged_patch))
    from src.run_log_forwarder import get_forwarder

    forwarder = get_forwarder(run_id)
    forwarder.emit_state_patch(merged_patch, state["status"])
    node_id = str(patch.get("active_node_id", ""))
    for message in new_messages:
        forwarder.emit_message(message, node_id=node_id)
    hybrid_patch = patch.get("hybrid_executions")
    if isinstance(hybrid_patch, dict):
        for message_id, entry in hybrid_patch.items():
            if not isinstance(entry, dict):
                continue
            forwarder.emit_hybrid_execution(
                str(message_id),
                raw_output=entry.get("rawOutput"),  # type: ignore[arg-type]
                output_events=entry.get("outputEvents"),  # type: ignore[arg-type]
            )


def _apply_workflow_refining_pause(
    run_id: str,
    session: WorkflowSession,
    *,
    prepend_log: bool = True,
) -> ClutchState:
    from src.flow_refine import compiler_snapshot_values, infer_refining_node_id, pause_log_line
    from src.runtime_config import runtime_mode

    state = _get_or_create_run(run_id)
    compiler_values = compiler_snapshot_values(session)
    refining_node_id = infer_refining_node_id(
        clutch_active_node_id=str(state.get("active_node_id", "")),
        compiler_values=compiler_values,
    )
    messages = list(state.get("messages") or [])
    for message in compiler_values.get("task_messages") or []:
        if not isinstance(message, dict):
            continue
        msg_id = str(message.get("id", ""))
        if msg_id and any(str(item.get("id", "")) == msg_id for item in messages):
            continue
        messages.append(message)
    logs = list(state["terminal_logs"])
    pause_line = pause_log_line()
    if prepend_log and not any(pause_line in line for line in logs[-5:]):
        logs.append(stamp_log_line(pause_line))
    patch: dict[str, Any] = {
        "status": "refining",
        "refining_node_id": refining_node_id,
        "messages": messages,
        "terminal_logs": logs,
    }
    if runtime_mode() == "hybrid":
        patch["shell_session_status"] = "ready"
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    _touch_session(run_id, status="refining")
    return state


def _prepare_workflow_refine_state(
    run_id: str,
    state: ClutchState,
    *,
    target_agent_id: str | None = None,
    prepend_log: bool = True,
) -> ClutchState:
    from src.flow_refine import (
        ensure_workflow_session_for_refine,
        infer_refining_node_id,
        workflow_node_id_for_agent,
    )

    session = ensure_workflow_session_for_refine(run_id, state, sessions=_run_sessions)
    if session is None:
        return state
    if state.get("status") == "refining" and not target_agent_id:
        return state

    if state.get("status") != "refining":
        state = _apply_workflow_refining_pause(run_id, session, prepend_log=prepend_log)

    refining_node_id = str(state.get("refining_node_id") or "").strip()
    if target_agent_id:
        node_from_agent = workflow_node_id_for_agent(session.workflow, target_agent_id)
        if node_from_agent:
            refining_node_id = node_from_agent
            patch = {"refining_node_id": refining_node_id}
            state = _merge_patch(state, patch)
            _commit_run_state(run_id, state)
    elif not refining_node_id:
        compiler_values = session.compiled.get_state(session.config).values or {}
        refining_node_id = infer_refining_node_id(
            clutch_active_node_id=str(state.get("active_node_id") or ""),
            compiler_values=dict(compiler_values),
        )
        if refining_node_id:
            state = _merge_patch(state, {"refining_node_id": refining_node_id})
            _commit_run_state(run_id, state)
    return state


def _run_workflow(run_id: str, workflow_id: str, instruction: str) -> ClutchState:
    from src.compiler import (
        WorkflowSession,
        compile_workflow,
        initial_compiler_state,
        is_awaiting_human_gate,
        workflow_run_config,
    )
    from src.workflow_cancel import WorkflowCancelled, clear_workflow_cancel, is_workflow_cancelled, WorkflowStepFailed

    clear_workflow_cancel(run_id)
    _setup_run_log_forwarder(run_id)
    from src.run_log_forwarder import get_forwarder
    from src.workflow_runtime import clear_workflow_step_callback, register_workflow_step_callback

    register_workflow_step_callback(run_id, lambda patch: _apply_workflow_step_patch(run_id, patch))

    workflow, _source = resolve_workflow(workflow_id)
    state = _get_or_create_run(run_id)
    trimmed = instruction.strip()
    if trimmed:
        user_message = _chat_message("User", trimmed, msg_id=f"user_{uuid.uuid4().hex[:8]}")
        state = _merge_patch(
            state,
            {
                "workflow_id": workflow["id"],
                "status": "running",
                "current_instruction": trimmed,
                "messages": list(state["messages"]) + [user_message],
            },
        )
        _commit_run_state(run_id, state)
        get_forwarder(run_id).emit_state_patch(
            {
                "workflow_id": workflow["id"],
                "status": "running",
                "current_instruction": trimmed,
                "messages": list(state["messages"]),
            },
            "running",
        )
    get_forwarder(run_id).emit(
        tagged(TAG_WORKFLOW, f"Starting workflow: {workflow['name']} ({workflow['id']})"),
        node_id="start",
    )
    cancelled = False
    session: WorkflowSession | None = None
    graph_result = None
    compiled = compile_workflow(workflow)
    config = workflow_run_config(run_id)
    session = WorkflowSession(compiled=compiled, config=config, workflow=workflow)
    _run_sessions[run_id] = session
    graph_state = initial_compiler_state(run_id, instruction=instruction)
    if instruction.strip() and not graph_state.get("current_instruction"):
        graph_state = {**graph_state, "current_instruction": instruction.strip()}
    try:
        try:
            graph_result = compiled.invoke(graph_state, config)
            if is_awaiting_human_gate(compiled, config, workflow):
                gate_id = next(iter(compiled.get_state(config).next))
                graph_result = {
                    **graph_result,
                    "active_node_id": gate_id,
                    "active_agent": "Supervisor",
                    "status": "awaiting_human",
                }
        except WorkflowCancelled:
            return _apply_workflow_refining_pause(run_id, session)
        except WorkflowStepFailed as exc:
            state = _get_or_create_run(run_id)
            logs = list(state["terminal_logs"])
            logs.append(
                stamp_log_line(
                    tagged(
                        TAG_WORKFLOW,
                        tr(
                            f"Workflow stopped at {exc.agent}: downstream steps skipped.",
                            f"工作流在 {exc.agent} 处停止：后续步骤已跳过。",
                        ),
                    )
                )
            )
            state = _merge_patch(
                state,
                {
                    "status": "failed",
                    "terminal_logs": logs,
                    "active_node_id": exc.node_id,
                    "active_agent": exc.agent,
                },
            )
            _commit_run_state(run_id, state)
            _touch_session(run_id, status="failed")
            return state
        finally:
            clear_workflow_step_callback(run_id)
        cancelled = is_workflow_cancelled(run_id)
    finally:
        clear_workflow_cancel(run_id)

    if cancelled:
        state = _get_or_create_run(run_id)
        if state.get("status") != "refining" and session is not None:
            return _apply_workflow_refining_pause(run_id, session)
        _touch_session(run_id, status=str(state.get("status", "refining")))
        return state

    assert session is not None and graph_result is not None
    _emit_workflow_graph_tail(run_id, graph_result)
    from src.workflow_projection import project_graph_to_clutch

    state = _get_or_create_run(run_id)
    patch = project_graph_to_clutch(
        state,
        graph_result,
        workflow=workflow,
        instruction=instruction,
        include_logs=False,
    )
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    _touch_session(
        run_id,
        title=instruction.strip()[:80] or str(workflow.get("name") or workflow["id"]),
        workflow_id=workflow["id"],
        status=state["status"],
    )
    return state


def _merge_graph_resume(
    state: ClutchState,
    graph_result: dict[str, Any],
    *,
    base_messages: list[dict[str, Any]],
    base_logs: list[str],
    include_logs: bool = True,
) -> dict[str, Any]:
    messages = list(base_messages)
    logs = list(base_logs)
    messages.extend(graph_result.get("task_messages", []))
    if include_logs:
        logs.extend(graph_result.get("task_logs", []))
        logs.append(tagged(TAG_WORKFLOW, f"Active node → {graph_result['active_node_id']}"))
        if graph_result["status"] == "awaiting_human":
            logs.append(tagged(TAG_HUMAN, "Human gate reached — awaiting decision."))
        logs = [stamp_log_line(line) for line in logs[len(base_logs):]]
        logs = list(base_logs) + logs
    return {
        "messages": messages,
        "terminal_logs": logs,
        "status": graph_result["status"],
        "active_node_id": graph_result["active_node_id"],
        "active_agent": graph_result["active_agent"],
    }


def _apply_human_decision(
    run_id: str,
    decision: str,
    instructions: str = "",
) -> tuple[ClutchState, dict[str, Any], dict[str, Any], str]:
    lock = _human_decision_locks.setdefault(run_id, threading.Lock())
    with lock:
        return _apply_human_decision_locked(run_id, decision, instructions)


def _apply_human_decision_locked(
    run_id: str,
    decision: str,
    instructions: str = "",
) -> tuple[ClutchState, dict[str, Any], dict[str, Any], str]:
    """Apply approve/reject/retry once per gate; ignore duplicate clicks (#52)."""
    _setup_run_log_forwarder(run_id)
    from src.run_log_forwarder import get_forwarder
    from src.workflow_runtime import clear_workflow_step_callback, register_workflow_step_callback

    forwarder = get_forwarder(run_id)
    state = _get_or_create_run(run_id)

    # Duplicate / stale clicks after the gate already advanced.
    if state["status"] != "awaiting_human":
        empty = _chat_message("Supervisor", "")
        return state, {}, empty, ""

    if run_id in _human_decision_inflight:
        empty = _chat_message("Supervisor", "")
        return state, {}, empty, ""

    _human_decision_inflight.add(run_id)
    try:
        if decision == "approve":
            supervisor_text = tr(
                "Human approval: Approved, continuing workflow.",
                "人工审批：已通过，继续执行工作流。",
            )
        elif decision == "reject":
            supervisor_text = tr(
                "Human approval: Rejected, run marked as failed.",
                "人工审批：已拒绝，运行标记为失败。",
            )
        else:
            supervisor_text = tr(
                f"Human approval: Retry with instructions - {instructions or '(no comments)'}",
                f"人工审批：按指令重试 — {instructions or '（无附加说明）'}",
            )

        supervisor_message = _chat_message("Supervisor", supervisor_text)
        log_line = tagged(TAG_HUMAN, supervisor_text)
        messages = list(state["messages"]) + [supervisor_message]
        forwarder.emit(log_line, node_id=str(state.get("active_node_id", "")))
        state = _get_or_create_run(run_id)
        logs = list(state["terminal_logs"])

        session = _run_sessions.get(run_id)
        if session and state["status"] == "awaiting_human":
            # Leave HITL UI immediately while resume may run long downstream agents.
            early = {
                "messages": messages,
                "terminal_logs": logs,
                "status": "running",
                "active_agent": "Supervisor",
            }
            state = _commit_run_state(run_id, _merge_patch(state, early))
            forwarder.emit_state_patch(early, "running")
            register_workflow_step_callback(
                run_id, lambda patch: _apply_workflow_step_patch(run_id, patch)
            )
            try:
                graph_result = resume_workflow(
                    session,
                    run_id,
                    decision,
                    instruction=instructions if decision == "retry" else "",
                )
            finally:
                clear_workflow_step_callback(run_id)
            _emit_workflow_graph_tail(run_id, graph_result)
            patch = _merge_graph_resume(
                state,
                graph_result,
                base_messages=messages,
                base_logs=logs,
                include_logs=False,
            )
        elif decision == "reject":
            patch = {
                "messages": messages,
                "terminal_logs": logs,
                "status": "failed",
                "active_agent": "Supervisor",
            }
        elif decision == "approve":
            # No in-memory session (e.g. sidecar restart) — cannot resume graph.
            patch = {
                "messages": messages,
                "terminal_logs": logs,
                "status": "passed",
                "active_agent": "Supervisor",
            }
        else:
            patch = {
                "messages": messages,
                "terminal_logs": logs,
                "status": "running",
                "active_agent": "Builder",
                "active_node_id": "n1",
            }

        state = _merge_patch(state, patch)
        _commit_run_state(run_id, state)
        if _is_terminal_status(state["status"]):
            update_run_record(run_id, {"status": state["status"], "ended_at": _iso_timestamp()})
        return state, patch, supervisor_message, log_line
    finally:
        _human_decision_inflight.discard(run_id)


def _validation_http_error(exc: WorkflowValidationError) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={"message": exc.message, "errors": exc.errors},
    )


def _emit_workflow_graph_tail(run_id: str, graph_result: dict[str, Any]) -> None:
    from src.run_log_forwarder import get_forwarder

    forwarder = get_forwarder(run_id)
    node_id = str(graph_result.get("active_node_id", ""))
    forwarder.emit(tagged(TAG_WORKFLOW, f"Active node → {node_id}"), node_id=node_id)
    if graph_result.get("status") == "awaiting_human":
        forwarder.emit(tagged(TAG_HUMAN, "Human gate reached — awaiting decision."), node_id=node_id)


def _interrupt_workflow_run(run_id: str) -> None:
    from src.workflow_cancel import request_workflow_cancel

    request_workflow_cancel(run_id)
    _interrupt_plain_chat_shell(run_id)


async def _commit_flow_refine_and_continue(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
) -> ClutchState:
    from src.flow_refine import continue_workflow_after_refine
    from src.workflow_projection import project_graph_to_clutch
    from src.workflow_runtime import clear_workflow_step_callback, register_workflow_step_callback

    session = _run_sessions.get(run_id)
    node_id = str(state.get("refining_node_id") or state.get("active_node_id") or "").strip()
    output = str(state.get("refine_draft_output") or "").strip()
    if not output:
        for message in reversed(state["messages"]):
            if message.get("agent") == "User":
                continue
            text = str(message.get("text", "")).strip()
            if text:
                output = text
                break
    if not session or not node_id or not output:
        supervisor = _chat_message(
            "Supervisor",
            tr(
                "Cannot continue: @ an agent with feedback first.",
                "无法继续：请先 @ Agent 给出修改意见。",
            ),
        )
        messages = list(state["messages"]) + [supervisor]
        patch = {"messages": messages}
        state = _merge_patch(state, patch)
        _commit_run_state(run_id, state)
        await _send_message_event(websocket, run_id, supervisor, node_id)
        await _notify_run_state(websocket, run_id, state, patch)
        return state

    register_workflow_step_callback(run_id, lambda patch: _apply_workflow_step_patch(run_id, patch))
    try:
        graph_result = await asyncio.to_thread(
            continue_workflow_after_refine,
            session,
            node_id=node_id,
            node_output=output,
        )
    finally:
        clear_workflow_step_callback(run_id)

    _emit_workflow_graph_tail(run_id, graph_result)
    workflow, _ = resolve_workflow(str(state.get("workflow_id") or ""))
    supervisor = _chat_message(
        "Supervisor",
        tr(
            "Refine committed — continuing workflow with legacy step execution.",
            "精修已提交 — 后续步骤将以 Legacy 模式继续执行。",
        ),
    )
    messages = list(state["messages"]) + [supervisor]
    base_patch = project_graph_to_clutch(
        state,
        graph_result,
        workflow=workflow,
        instruction=str(state.get("current_instruction") or ""),
        include_logs=False,
    )
    patch: dict[str, Any] = {
        **base_patch,
        "messages": messages,
        "refining_node_id": "",
        "refine_draft_output": "",
        "refine_agent_id": "",
    }
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    _touch_session(run_id, status=state["status"])
    await _send_message_event(websocket, run_id, supervisor, node_id)
    await _notify_run_state(websocket, run_id, state, patch)
    if state["status"] == "awaiting_human":
        await _send_human_required(
            websocket,
            run_id,
            node_id=state["active_node_id"],
            prompt=tr("Checks failed, waiting for human confirmation.", "检查未通过，等待人工确认。"),
        )
    return state


async def _handle_flow_refine_message(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    text: str,
    agent_id: str | None = None,
) -> ClutchState:
    from src.agent_storage import get_agent_by_id
    from src.engine_router import find_agent
    from src.flow_refine import (
        build_refine_system_appendix,
        is_continue_command,
        node_output_for_refine,
        parse_agent_mention,
        refine_reply_ready_to_commit,
        resolve_image_refine_prompt,
        workflow_node_label,
        ensure_workflow_session_for_refine,
    )
    from src.hybrid_concurrency import HybridPlainChatRejected
    from src.runtime_config import runtime_mode
    from src.state import cli_session_patch, read_cli_session_agent_id, read_cli_session_id

    if is_continue_command(text):
        state = _prepare_workflow_refine_state(run_id, state, prepend_log=False)
        return await _commit_flow_refine_and_continue(websocket, run_id, state)

    session = ensure_workflow_session_for_refine(run_id, state, sessions=_run_sessions)
    workflow = session.workflow if session else None
    mention_name, body = parse_agent_mention(text, workflow=workflow)
    resolved_id = (agent_id or "").strip()
    if mention_name:
        matched = find_agent(mention_name)
        if matched:
            resolved_id = str(matched.get("id", "")).strip()
    if not resolved_id:
        resolved_id = str(state.get("refine_agent_id") or "").strip()
    if resolved_id:
        state = _prepare_workflow_refine_state(
            run_id,
            state,
            target_agent_id=resolved_id,
            prepend_log=state.get("status") != "refining",
        )
    if not resolved_id or not (body or text.strip()):
        supervisor = _chat_message(
            "Supervisor",
            tr(
                "Refine mode: type @AgentName then your feedback (Hybrid). Downstream runs automatically after refine; use Stop if you need another round.",
                "精修模式：输入 @Agent名称 和修改意见（Hybrid）。精修完成后自动继续下游；不满意可先停止工作流再 @。",
            ),
        )
        messages = list(state["messages"]) + [supervisor]
        patch = {"messages": messages}
        state = _merge_patch(state, patch)
        await _send_message_event(websocket, run_id, supervisor, state.get("active_node_id", ""))
        await _notify_run_state(websocket, run_id, state, patch)
        return state

    agent = get_agent_by_id(resolved_id)
    active_agent = str(agent.get("name", "Agent")) if agent else mention_name or "Agent"
    user_message = _chat_message("User", text, msg_id=f"user_{uuid.uuid4().hex[:8]}")
    messages = list(state["messages"]) + [user_message]
    user_patch: dict[str, Any] = {
        "messages": messages,
        "status": "refining",
        "refine_agent_id": resolved_id,
        "active_agent": active_agent,
        "pending_tool_steps": [], "live_reasoning": "",
    }
    if runtime_mode() == "hybrid":
        user_patch["shell_session_status"] = "ready"
    state = _merge_patch(state, user_patch)
    _commit_run_state(run_id, state)
    await _send_message_event(websocket, run_id, user_message, state.get("active_node_id", ""))
    await _notify_run_state(websocket, run_id, state, user_patch)

    refining_node_id = str(state.get("refining_node_id") or state.get("active_node_id") or "")
    node_output = ""
    node_label = refining_node_id
    if session:
        node_output = node_output_for_refine(
            session=session,
            node_id=refining_node_id,
            messages=list(state["messages"]),
        )
        node_label = workflow_node_label(session, refining_node_id)
    refine_suffix = build_refine_system_appendix(
        node_id=refining_node_id,
        node_label=node_label,
        node_output=node_output,
    )

    stored_session_id = read_cli_session_id(state) or None
    stored_session_agent = read_cli_session_agent_id(state)
    if stored_session_agent and stored_session_agent != resolved_id:
        stored_session_id = None

    streamed_logs = False
    tool_steps_sink: list[dict[str, Any]] = []
    subtasks_sink: list[dict[str, Any]] = []

    async def emit_log(line: str) -> None:
        nonlocal streamed_logs, state
        streamed_logs = True
        stamped = stamp_log_line(line)
        logs = list(state["terminal_logs"]) + [stamped]
        state = _merge_patch(state, {"terminal_logs": logs})
        _commit_run_state(run_id, state)
        await _send_log_event(websocket, run_id, stamped, node_id=refining_node_id)
        await _notify_run_state(websocket, run_id, state, {"terminal_logs": logs})

    async def emit_tool_step(step: dict[str, Any]) -> None:
        nonlocal state
        patch = _tool_step_live_patch(state, step)
        state = _merge_patch(state, patch)
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, patch)
        await _maybe_notify_step_file_diff(websocket, run_id, step)

    async def emit_reasoning(text: str) -> None:
        nonlocal state
        patch = _reasoning_live_patch(text)
        state = _merge_patch(state, patch)
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, patch)

    async def emit_todos(todos: list[dict[str, Any]]) -> None:
        nonlocal state
        state = _merge_patch(state, {"agent_todos": list(todos)})
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, {"agent_todos": list(todos)})

    async def emit_goal(goal: dict[str, Any]) -> None:
        nonlocal state
        state = _merge_patch(state, {"agent_goal": dict(goal)})
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, {"agent_goal": dict(goal)})

    async def emit_verification(report: dict[str, Any]) -> None:
        nonlocal state
        label = str(state.get("active_agent") or "Clutch Agent")
        state = await _publish_verification_report(
            websocket, run_id, state, dict(report), reply_label=label
        )

    async def emit_diff_summary(report: dict[str, Any]) -> None:
        nonlocal state
        label = str(state.get("active_agent") or "Clutch Agent")
        state = await _publish_diff_summary(
            websocket, run_id, state, dict(report), reply_label=label
        )

    async def emit_subtask(card: dict[str, Any]) -> None:
        nonlocal state
        patch = _subtask_live_patch(state, card)
        state = _merge_patch(state, patch)
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, patch)

    from src.agent_type import is_clutch_agent, resolve_model_for_agent
    from src.image_router import is_image_model
    from src.models_config import get_router

    task_text = body or text.strip()
    image_refine = False
    if session and agent and is_clutch_agent(agent):
        router = get_router()
        spec, _model_id = resolve_model_for_agent(router, agent)
        if is_image_model(spec):
            image_refine = True
            task_text = resolve_image_refine_prompt(
                session=session,
                refining_node_id=refining_node_id,
                user_body=body,
                messages=list(state["messages"]),
            )

    try:
        (
            model_name,
            runtime_engine,
            reply_text,
            route_logs,
            cli_session_id,
            mcp_pause,
            files_changed,
            raw_output,
            output_events,
            shell_recovered,
        ) = await _llm_chat_reply(
            state,
            task_text,
            agent_id=resolved_id,
            cli_session_id=stored_session_id,
            emit_log=emit_log,
            emit_tool_step=emit_tool_step,
            emit_reasoning=emit_reasoning,
            emit_todos=emit_todos,
            emit_goal=emit_goal,
            emit_verification=emit_verification,
            emit_diff_summary=emit_diff_summary,
            emit_subtask=emit_subtask,
            tool_steps_sink=tool_steps_sink,
            subtasks_sink=subtasks_sink,
            chat_source="flow_refine",
            system_prompt_suffix=refine_suffix,
        )
    except HybridPlainChatRejected as exc:
        return await _apply_hybrid_plain_chat_rejection(
            websocket,
            run_id,
            state,
            code=str(exc),
            keep_running=True,
        )

    if mcp_pause:
        from src.mcp_pending import McpPendingApproval, store_pending

        store_pending(
            run_id,
            McpPendingApproval(
                agent_id=resolved_id,
                reply_label=model_name,
                chat_messages=list(mcp_pause["chat_messages"]),
                servers=list(mcp_pause["servers"]),
                tool_call_id=str(mcp_pause["tool_call_id"]),
                func_name=str(mcp_pause["func_name"]),
                func_args=dict(mcp_pause.get("func_args") or {}),
                step_idx=int(mcp_pause.get("step_idx", 0)),
                logs=list(route_logs),
                step_id=str(mcp_pause.get("step_id") or ""),
            ),
        )
        gate_line = _mcp_pause_gate_line(mcp_pause)
        pause_messages, pause_msg, pause_created = _messages_for_mcp_pause(
            list(state["messages"]),
            mcp_pause,
            reply_label=model_name or active_agent,
        )
        pause_logs = _append_terminal_logs(
            list(state["terminal_logs"]), route_logs, gate_line, streamed=streamed_logs
        )
        pause_patch: dict[str, Any] = {
            "messages": pause_messages,
            "terminal_logs": pause_logs,
            "status": "awaiting_human",
            "active_agent": active_agent,
            "pending_tool_steps": list(mcp_pause.get("tool_steps") or tool_steps_sink),
            "pending_subtasks": list(
                mcp_pause.get("subtasks") or subtasks_sink or []
            ),
        }
        state = _merge_patch(state, pause_patch)
        _commit_run_state(run_id, state)
        if pause_created:
            await _send_message_event(websocket, run_id, pause_msg, refining_node_id)
        if not streamed_logs:
            for log in route_logs:
                await _send_log_event(websocket, run_id, log, node_id=refining_node_id)
        await _send_log_event(websocket, run_id, gate_line, node_id=refining_node_id)
        await _notify_run_state(websocket, run_id, state, pause_patch)
        return state

    sealed_steps = _sealed_tool_steps(state, sink=tool_steps_sink)
    merged_changed = _merge_files_changed_with_tool_steps(files_changed, sealed_steps)
    files_changed = merged_changed
    reply = _chat_message(
        model_name,
        reply_text,
        runtime_engine=runtime_engine,
        msg_id=f"agent_{uuid.uuid4().hex[:8]}",
        tool_steps=sealed_steps,
        files_changed=merged_changed or None,
        todo_list=list(state.get("agent_todos") or []) or None,
        verification_report=_verification_report_for_seal(
            state, files_changed=merged_changed or None
        ),
        diff_summary=_diff_summary_for_seal(
            state, files_changed=merged_changed or None
        ),
    )
    final_messages = list(state["messages"]) + [reply]
    final_patch: dict[str, Any] = {
        "messages": final_messages,
        "refine_draft_output": reply_text,
        "active_agent": model_name,
        "status": "refining",
        "pending_tool_steps": [], "live_reasoning": "",
        **cli_session_patch(cli_session_id, resolved_id),
        **_token_patch_turn(state, user_text=body or text, assistant_text=reply_text),
    }
    if runtime_mode() == "hybrid":
        final_patch["shell_session_status"] = "ready"
    if shell_recovered:
        final_patch["shell_session_status"] = "ready"
    if route_logs and not streamed_logs:
        final_patch["terminal_logs"] = list(state["terminal_logs"]) + [
            stamp_log_line(line) for line in route_logs
        ]
    if merged_changed:
        prev = [str(p) for p in (state.get("changed_files") or []) if str(p).strip()]
        final_patch["changed_files"] = list(dict.fromkeys([*prev, *merged_changed]))
    state = _merge_patch(state, final_patch)
    _commit_run_state(run_id, state)
    await _send_message_event(websocket, run_id, reply, refining_node_id)
    if runtime_engine and "Hybrid" in runtime_engine and raw_output:
        await _send_hybrid_execution_event(
            websocket,
            run_id,
            message_id=str(reply["id"]),
            raw_output=raw_output,
            output_events=output_events,
        )
    if files_changed:
        await _notify_workspace_files_changed(
            websocket,
            run_id,
            files_changed,
            node_id=refining_node_id,
            path_diffs=_path_diffs_from_tool_steps(sealed_steps),
        )
    await _notify_run_state(websocket, run_id, state, final_patch)
    if refine_reply_ready_to_commit(reply_text):
        state = _prepare_workflow_refine_state(run_id, state, prepend_log=False)
        return await _commit_flow_refine_and_continue(websocket, run_id, state)
    return state


async def _handle_workflow_chat_message(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    text: str,
    agent_id: str | None = None,
) -> ClutchState:
    from src.flow_refine import is_workflow_refine_eligible, refine_triggered_by_message

    session = _run_sessions.get(run_id)
    workflow = session.workflow if session else None
    if not workflow and state.get("workflow_id"):
        try:
            workflow, _ = resolve_workflow(str(state["workflow_id"]))
        except Exception:
            workflow = None
    status = str(state.get("status") or "")
    if is_workflow_refine_eligible(state) and refine_triggered_by_message(
        text,
        status=status,
        workflow=workflow,
    ):
        return await _handle_flow_refine_message(websocket, run_id, state, text, agent_id)

    user_message = _chat_message("User", text, msg_id=f"user_{uuid.uuid4().hex[:8]}")
    messages = list(state["messages"]) + [user_message]
    logs = list(state["terminal_logs"])
    logs.append(stamp_log_line(f"[USER] {text}"))

    if state["status"] == "awaiting_human":
        state, patch, supervisor_message, log_line = await asyncio.to_thread(
            _apply_human_decision,
            run_id,
            "retry",
            text,
        )
        await _send_message_event(websocket, run_id, user_message, state["active_node_id"])
        await _send_message_event(websocket, run_id, supervisor_message, state["active_node_id"])
        await _notify_run_state(websocket, run_id, state, patch)
        if state["status"] == "awaiting_human":
            await _send_validation_result(
                websocket,
                run_id,
                node_id=state["active_node_id"],
                passed=False,
                message="Evaluator checks still failing — awaiting approval.",
            )
            await _send_human_required(
                websocket,
                run_id,
                node_id=state["active_node_id"],
                prompt="Checks still failing — approve, reject, or retry again.",
            )
        return state

    patch = {"messages": messages, "terminal_logs": logs}
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    await _send_message_event(websocket, run_id, user_message, state["active_node_id"])
    await _send_log_event(websocket, run_id, logs[-1], node_id=state["active_node_id"])
    await _notify_run_state(websocket, run_id, state, patch)
    return state

