from __future__ import annotations

import asyncio
import json
import logging
import threading
import uuid
from collections.abc import Awaitable, Callable
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, Field

from src.release_hardening import api_docs_enabled, debug_api_enabled
from src.sidecar_auth import auth_required, public_http_paths, validate_bearer, validate_token

from src.compiler import WorkflowSession, begin_workflow, resume_workflow
from src.run_history import append_run_record, list_runs, update_run_record, upsert_session
from src.state import ClutchState, initial_state
from src.workspace import WorkspaceError
from src.workflow_storage import resolve_workflow
from src.workflow_validator import WorkflowValidationError, load_and_validate_workflow, validate_workflow
from src.preferences_storage import tr
from src.terminal_logs import TAG_HUMAN, TAG_WORKFLOW, stamp_log_line, tagged

logger = logging.getLogger(__name__)

async def _lifespan(app: FastAPI):
    from src.plain_chat_pool_queue import set_event_loop, set_refresh_handler, set_resume_handler
    from src.shell_session import get_shell_session_manager

    loop = asyncio.get_running_loop()
    set_event_loop(loop)
    set_resume_handler(_resume_pool_queued_turn)
    set_refresh_handler(_refresh_pool_queued_run_states)

    from src.interactive_pty_runtime import interactive_pty_manager
    from src.plain_chat_pool_queue import get_plain_chat_ws

    async def _forward_interactive_pty_output(session_key: str, chunk: str) -> None:
        from src.terminal_orchestra import parse_pty_session_key

        parent_run_id, lane_id = parse_pty_session_key(session_key)
        websocket = get_plain_chat_ws(parent_run_id)
        if websocket is not None:
            await _send_pty_output(websocket, parent_run_id, chunk, lane_id=lane_id)

    interactive_pty_manager.set_event_loop(loop)
    interactive_pty_manager.set_output_handler(_forward_interactive_pty_output)

    async def _sweep_shell_sessions() -> None:
        manager = get_shell_session_manager()
        while True:
            await asyncio.sleep(60)
            try:
                terminated = await asyncio.to_thread(manager.sweep_idle)
                for run_id in terminated:
                    logger.info("shell_session idle sweep terminated run_id=%s", run_id)
                from src.session_snapshot import prune_stale_snapshots

                pruned = await asyncio.to_thread(prune_stale_snapshots)
                for run_id in pruned:
                    logger.info("shell_snapshot pruned run_id=%s", run_id)
            except Exception:
                logger.exception("shell_session sweep failed")

    task = asyncio.create_task(_sweep_shell_sessions())

    async def _prefetch_cc_switch_bundle() -> None:
        try:
            from src.cli_agent_config import prefetch_cc_switch_cli_bundle, resolve_cc_switch_cli_path

            if resolve_cc_switch_cli_path():
                return
            await asyncio.to_thread(prefetch_cc_switch_cli_bundle)
        except Exception:
            logger.debug("cc-switch bundle prefetch skipped", exc_info=True)

    asyncio.create_task(_prefetch_cc_switch_bundle())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

_docs_disabled = not api_docs_enabled()

_run_states: dict[str, ClutchState] = {}

_run_sessions: dict[str, WorkflowSession] = {}

_human_decision_locks: dict[str, threading.Lock] = {}

_human_decision_inflight: set[str] = set()

class StartRunRequest(BaseModel):
    workflow_id: str = Field(default="video-production")
    instruction: str = Field(default="")

class ValidateWorkflowRequest(BaseModel):
    workflow_id: str | None = None
    workflow: dict[str, Any] | None = None

class SaveUserWorkflowRequest(BaseModel):
    workflow: dict[str, Any]

class WorkspaceRequest(BaseModel):
    path: str

class RepositoryGroupRequest(BaseModel):
    name: str

class RepositoryGroupUpdateRequest(BaseModel):
    name: str | None = None
    collapsed: bool | None = None
    workspace_ids: list[str] | None = None

class AgentsSaveRequest(BaseModel):
    agents: list[dict[str, Any]]

class AgentPromptGenerateRequest(BaseModel):
    name: str
    description: str = Field(default="")

class ModelsConfigRequest(BaseModel):
    active_model_id: str | None = None
    provider_id: str | None = None
    api_key: str | None = None

class OpenCodeZenListRequest(BaseModel):
    api_key: str | None = None

class ModelTestRequest(BaseModel):
    model_id: str

class CustomImageModelRequest(BaseModel):
    name: str
    api_model: str
    base_url: str
    provider_id: str = Field(default="custom")
    image_backend: str = Field(default="")
    api_key: str | None = None

class CustomChatModelRequest(BaseModel):
    name: str
    api_model: str
    base_url: str
    provider_id: str = Field(default="custom")
    api_key: str | None = None

class CustomVideoModelRequest(BaseModel):
    name: str
    api_model: str
    base_url: str
    provider_id: str = Field(default="custom")
    video_backend: str = Field(default="agnes")
    api_key: str | None = None

class CustomModelUpdateRequest(BaseModel):
    name: str
    api_model: str
    base_url: str
    api_key: str | None = None

class ToolConnectRequest(BaseModel):
    tool_id: str

class ReassignRequest(BaseModel):
    instructions: str = Field(default="reassign_to_builder")

class HumanDecisionRequest(BaseModel):
    decision: str = Field(default="approve")
    instructions: str = Field(default="")

class SessionCreateRequest(BaseModel):
    run_id: str
    title: str = Field(default="New session")
    workflow_id: str = Field(default="")
    mode: str = Field(default="coding")
    status: str | None = None

class SkillsMountRequest(BaseModel):
    path: str

class SkillsToggleRequest(BaseModel):
    key: str
    is_active: bool = Field(default=True)

class McpRegisterRequest(BaseModel):
    name: str
    transport: str = Field(default="stdio")
    endpoint: str

class McpServerIdRequest(BaseModel):
    id: str
    enabled: bool | None = None

class McpSaveConfigRequest(BaseModel):
    servers: list[dict[str, Any]]

class CliActivateProviderRequest(BaseModel):
    provider_id: str

class CliActivateModelRequest(BaseModel):
    model_ref: str

class ThemePreferenceRequest(BaseModel):
    theme_id: str

class LanguagePreferenceRequest(BaseModel):
    language: str

class PermissionModeRequest(BaseModel):
    mode: str

class FontSizePreferenceRequest(BaseModel):
    font_size: str

class AvatarPreferenceRequest(BaseModel):
    avatar: str

class UserNamePreferenceRequest(BaseModel):
    user_name: str

def _skills_registry_payload(*, rescan: bool = True) -> dict[str, Any]:
    from src.skills_scanner import scan_mounted_directories
    from src.skills_storage import sync_workspace_skill_mounts, load_registry, save_registry
    from src.workspace import get_workspace

    workspace = get_workspace()
    workspace_path = workspace.get("workspace_path") if workspace else None
    sync_workspace_skill_mounts(workspace_path=workspace_path)

    data = load_registry()
    if rescan:
        data["skills"] = scan_mounted_directories(
            data["mounted_directories"],
            existing_skills=data["skills"],
        )
        save_registry(
            mounted_directories=data["mounted_directories"],
            skills=data["skills"],
        )
    return data

def _session_workspace_fields() -> dict[str, str]:
    from src.workspace import get_workspace

    workspace = get_workspace()
    if workspace is None:
        return {}
    return {
        "workspace_id": workspace["id"],
        "workspace_name": workspace["name"],
    }

def _touch_session(
    run_id: str,
    *,
    title: str | None = None,
    workflow_id: str | None = None,
    status: str | None = None,
) -> None:
    from src.run_history import list_runs, upsert_session
    from src.session_content import session_has_persistable_content

    fields = _session_workspace_fields()
    if not fields:
        return
    state = _get_or_create_run(run_id)
    existing = next((record for record in list_runs() if record.get("run_id") == run_id), None)
    if not existing and not session_has_persistable_content(state):
        return
    patch: dict[str, Any] = {**fields, "run_id": run_id}
    if title is not None:
        patch["title"] = title[:80]
    if workflow_id is not None:
        patch["workflow_id"] = workflow_id
    if status is not None:
        patch["status"] = status
    if existing:
        upsert_session({**existing, **patch})
    else:
        upsert_session(
            {
                **patch,
                "title": patch.get("title", "New session"),
                "workflow_id": patch.get("workflow_id", ""),
                "status": patch.get("status", "idle"),
                "started_at": _iso_timestamp(),
            }
        )

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

def _iso_timestamp() -> str:
    return datetime.now(UTC).isoformat()

def _get_or_create_run(run_id: str) -> ClutchState:
    if run_id not in _run_states:
        from src.run_state_store import load_run_state

        persisted = load_run_state(run_id)
        _run_states[run_id] = persisted if persisted else initial_state(run_id)
    return _run_states[run_id]

def _commit_run_state(run_id: str, state: ClutchState) -> ClutchState:
    from src.run_state_store import save_run_state

    _run_states[run_id] = state
    save_run_state(state)
    return state

def _apply_delete_message(
    state: ClutchState,
    message_id: str,
) -> tuple[ClutchState, dict[str, Any]]:
    trimmed_id = message_id.strip()
    if not trimmed_id:
        return state, {}
    messages = [
        message
        for message in state["messages"]
        if str(message.get("id", "")) != trimmed_id
    ]
    if len(messages) == len(state["messages"]):
        return state, {}
    patch: dict[str, Any] = {"messages": messages}
    hybrid = dict(state.get("hybrid_executions") or {})
    if trimmed_id in hybrid:
        del hybrid[trimmed_id]
        patch["hybrid_executions"] = hybrid
    state = _merge_patch(state, patch)
    return state, patch

def _merge_patch(state: ClutchState, patch: dict[str, Any]) -> ClutchState:
    merged = deepcopy(state)
    optional_keys = frozenset({
        "hybrid_executions",
        "shell_session_status",
        "shell_pool_blocker_run_ids",
        "shell_pool_blockers",
        "shell_pool_queue_position",
        "shell_pool_queue_depth",
        "pty_lanes",
        "dispatch_log",
        "dispatch_edges",
        "pending_handoff_drafts",
        "focused_lane_id",
        "pending_tool_steps",
        "agent_todos",
        "verification_report",
        "diff_summary",
        "refining_node_id",
        "refine_draft_output",
        "refine_agent_id",
        "pending_pty_inject",
    })
    for key, value in patch.items():
        if key in merged or key in optional_keys:
            merged[key] = value  # type: ignore[literal-required, index]
    return merged

def _persist_run_log(run_id: str, line: str, node_id: str) -> None:
    state = _get_or_create_run(run_id)
    logs = list(state["terminal_logs"]) + [stamp_log_line(line)]
    patch: dict[str, Any] = {"terminal_logs": logs}
    if node_id:
        patch["active_node_id"] = node_id
    _commit_run_state(run_id, _merge_patch(state, patch))

def _setup_run_log_forwarder(run_id: str) -> None:
    from src.run_log_forwarder import get_forwarder

    get_forwarder(run_id).set_persist(
        lambda line, node_id: _persist_run_log(run_id, line, node_id)
    )

def _emit_workflow_graph_tail(run_id: str, graph_result: dict[str, Any]) -> None:
    from src.run_log_forwarder import get_forwarder

    forwarder = get_forwarder(run_id)
    node_id = str(graph_result.get("active_node_id", ""))
    forwarder.emit(tagged(TAG_WORKFLOW, f"Active node → {node_id}"), node_id=node_id)
    if graph_result.get("status") == "awaiting_human":
        forwarder.emit(tagged(TAG_HUMAN, "Human gate reached — awaiting decision."), node_id=node_id)

def _is_terminal_status(status: str) -> bool:
    return status in {"passed", "failed"}

def _serialize_clutch_state(state: ClutchState) -> dict[str, Any]:
    return dict(state)

async def _send_state_patch(websocket: WebSocket, run_id: str, patch: dict[str, Any]) -> None:
    envelope = {
        "event": "state_patch",
        "data": {
            "run_id": run_id,
            "timestamp": _iso_timestamp(),
            "patch": patch,
        },
    }
    await websocket.send_text(json.dumps(envelope))

async def _send_run_completed(websocket: WebSocket, run_id: str, state: ClutchState) -> None:
    envelope = {
        "event": "run_completed",
        "data": {
            "run_id": run_id,
            "timestamp": _iso_timestamp(),
            "status": state["status"],
            "state": _serialize_clutch_state(state),
        },
    }
    await websocket.send_text(json.dumps(envelope))

async def _notify_run_state(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    patch: dict[str, Any],
) -> None:
    await _send_state_patch(websocket, run_id, patch)
    if _is_terminal_status(state["status"]):
        await _send_run_completed(websocket, run_id, state)

async def _try_ws_notify(
    coro: Awaitable[None],
    *,
    run_id: str,
    what: str,
) -> None:
    try:
        await coro
    except WebSocketDisconnect:
        logger.warning(
            "WebSocket disconnected during %s run_id=%s",
            what,
            run_id,
        )

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
    paths = list(report.get("changedFiles") or [])
    for path in files_changed or []:
        rel = str(path).strip()
        if rel and rel not in paths:
            paths.append(rel)
    if paths:
        report["changedFiles"] = paths
    return report


async def _publish_verification_report(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    report: dict[str, Any],
    *,
    reply_label: str,
) -> ClutchState:
    """Seal a D5/D50 verification card into the Chat timeline immediately."""
    card = dict(report)
    messages = list(state["messages"])
    last = messages[-1] if messages else None
    prev = last.get("verificationReport") if isinstance(last, dict) else None
    if (
        isinstance(prev, dict)
        and prev.get("title") == card.get("title")
        and prev.get("conclusion") == card.get("conclusion")
    ):
        state = _merge_patch(state, {"verification_report": card})
        _commit_run_state(run_id, state)
        return state

    card_msg = _chat_message(reply_label or "Clutch Agent", "", verification_report=card)
    messages = messages + [card_msg]
    state = _merge_patch(
        state,
        {
            "messages": messages,
            "verification_report": card,
        },
    )
    _commit_run_state(run_id, state)
    await _send_message_event(websocket, run_id, card_msg, "")
    await _notify_run_state(
        websocket,
        run_id,
        state,
        {"messages": messages, "verification_report": card},
    )
    return state


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


async def _publish_diff_summary(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    report: dict[str, Any],
    *,
    reply_label: str,
) -> ClutchState:
    """Seal a D6/D50 diff card into the Chat timeline immediately (per-edit or review)."""
    card = dict(report)
    if not card.get("files"):
        return state
    messages = list(state["messages"])
    last = messages[-1] if messages else None
    prev = last.get("diffSummary") if isinstance(last, dict) else None
    # Inline cards: skip only exact duplicate of the same single-file patch.
    if isinstance(prev, dict) and prev.get("inline") and card.get("inline"):
        prev_files = prev.get("files") or []
        next_files = card.get("files") or []
        if (
            len(prev_files) == 1
            and len(next_files) == 1
            and isinstance(prev_files[0], dict)
            and isinstance(next_files[0], dict)
            and prev_files[0].get("path") == next_files[0].get("path")
            and prev_files[0].get("patch") == next_files[0].get("patch")
        ):
            state = _merge_patch(state, {"diff_summary": card})
            _commit_run_state(run_id, state)
            return state
    elif (
        isinstance(prev, dict)
        and not card.get("inline")
        and prev.get("title") == card.get("title")
    ):
        prev_paths = [str(f.get("path")) for f in (prev.get("files") or []) if isinstance(f, dict)]
        next_paths = [str(f.get("path")) for f in (card.get("files") or []) if isinstance(f, dict)]
        if prev_paths == next_paths:
            state = _merge_patch(state, {"diff_summary": card})
            _commit_run_state(run_id, state)
            return state

    card_msg = _chat_message(reply_label or "Clutch Agent", "", diff_summary=card)
    messages = messages + [card_msg]
    state = _merge_patch(
        state,
        {
            "messages": messages,
            "diff_summary": card,
        },
    )
    _commit_run_state(run_id, state)
    await _send_message_event(websocket, run_id, card_msg, "")
    # Push Changes panel for inline edits as they land.
    paths = [
        str(f.get("path")).strip()
        for f in (card.get("files") or [])
        if isinstance(f, dict) and str(f.get("path") or "").strip()
    ]
    if paths:
        await _notify_workspace_files_changed(websocket, run_id, paths)
    await _notify_run_state(
        websocket,
        run_id,
        state,
        {"messages": messages, "diff_summary": card},
    )
    return state


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


def _hybrid_execution_entry(
    *,
    raw_output: str | None,
    output_events: list[dict[str, Any]] | None,
    system_prompt: str | None = None,
) -> dict[str, object]:
    events = list(output_events or [])
    if system_prompt and not any(event.get("type") == "system_prompt" for event in events):
        events.insert(
            0,
            {"type": "system_prompt", "visible": False, "content": system_prompt},
        )
    return {
        "rawOutput": raw_output,
        "outputEvents": events,
    }

def _merge_hybrid_executions(
    state: ClutchState,
    *,
    message_id: str,
    raw_output: str | None,
    output_events: list[dict[str, Any]] | None,
    system_prompt: str | None = None,
) -> dict[str, dict[str, object]]:
    merged = dict(state.get("hybrid_executions") or {})
    merged[message_id] = _hybrid_execution_entry(
        raw_output=raw_output,
        output_events=output_events,
        system_prompt=system_prompt,
    )
    return merged

async def _send_message_event(
    websocket: WebSocket, run_id: str, message: dict[str, Any], node_id: str
) -> None:
    envelope = {
        "event": "message",
        "data": {
            "run_id": run_id,
            "node_id": node_id,
            "source": "orchestrator",
            "timestamp": _iso_timestamp(),
            "message": message,
        },
    }
    await websocket.send_text(json.dumps(envelope))

async def _send_hybrid_execution_event(
    websocket: WebSocket,
    run_id: str,
    *,
    message_id: str,
    raw_output: str | None,
    output_events: list[dict[str, Any]] | None,
) -> None:
    envelope = {
        "event": "hybrid_execution",
        "data": {
            "run_id": run_id,
            "node_id": "",
            "source": "orchestrator",
            "timestamp": _iso_timestamp(),
            "messageId": message_id,
            "rawOutput": raw_output,
            "outputEvents": output_events or [],
        },
    }
    await websocket.send_text(json.dumps(envelope))

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
) -> list[dict[str, Any]]:
    updated = list(messages)
    for idx in range(len(updated) - 1, -1, -1):
        card = updated[idx].get("planCard")
        if isinstance(card, dict) and card.get("status") == "pending":
            next_card = {**card, "status": status}
            if note:
                next_card["note"] = note
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


async def _send_human_required(
    websocket: WebSocket,
    run_id: str,
    *,
    node_id: str,
    prompt: str,
) -> None:
    envelope = {
        "event": "human_required",
        "data": {
            "run_id": run_id,
            "node_id": node_id,
            "source": "orchestrator",
            "level": "info",
            "message": prompt,
            "timestamp": _iso_timestamp(),
        },
    }
    await websocket.send_text(json.dumps(envelope))

async def _send_pty_output(
    websocket: WebSocket,
    run_id: str,
    chunk: str,
    *,
    node_id: str = "",
    lane_id: str = "",
) -> None:
    envelope = {
        "event": "pty_output",
        "data": {
            "run_id": run_id,
            "lane_id": lane_id,
            "node_id": node_id,
            "source": "interactive_pty",
            "level": "info",
            "message": "pty output chunk",
            "timestamp": _iso_timestamp(),
            "chunk": chunk,
            "encoding": "utf8",
        },
    }
    await websocket.send_text(json.dumps(envelope))

async def _send_pty_session_status(
    websocket: WebSocket,
    run_id: str,
    status: str,
    *,
    node_id: str = "",
    detail: str = "",
    lane_id: str = "",
) -> None:
    envelope = {
        "event": "pty_session_status",
        "data": {
            "run_id": run_id,
            "lane_id": lane_id,
            "node_id": node_id,
            "source": "interactive_pty",
            "level": "info",
            "message": detail or f"pty session {status}",
            "timestamp": _iso_timestamp(),
            "status": status,
        },
    }
    await websocket.send_text(json.dumps(envelope))

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

def _uses_configured_llm(agent: dict[str, Any] | None) -> bool:
    from src.agent_type import is_clutch_agent

    if not agent:
        return True
    return is_clutch_agent(agent)

def _compose_agent_system_prompt(
    agent: dict[str, Any],
    *,
    model_name: str,
    model_api: str,
    mcp_servers_bound: bool = True,
    user_turn_text: str | None = None,
    state: dict[str, Any] | None = None,
) -> str:
    from src.agent_prompt import compose_agent_system_prompt
    from src.preferences_storage import load_permission_mode
    from src.task_state import latest_plan_card

    agent_todos = list((state or {}).get("agent_todos") or [])
    plan_card = latest_plan_card(list((state or {}).get("messages") or []))

    return compose_agent_system_prompt(
        agent,
        model_name=model_name,
        model_api=model_api,
        mcp_servers_bound=mcp_servers_bound,
        permission_mode=load_permission_mode(),
        user_turn_text=user_turn_text,
        agent_todos=agent_todos,
        plan_card=plan_card,
    )

def _append_terminal_logs(
    current_logs: list[str],
    route_logs: list[str],
    tail_line: str,
    *,
    streamed: bool,
) -> list[str]:
    stamped_tail = stamp_log_line(tail_line)
    if streamed:
        merged = list(current_logs)
        if not merged or merged[-1] != stamped_tail:
            merged.append(stamped_tail)
        return merged
    return list(current_logs) + [stamp_log_line(line) for line in route_logs] + [stamped_tail]

async def _llm_chat_reply(
    state: ClutchState,
    text: str,
    agent_id: str | None = None,
    *,
    session_model_id: str | None = None,
    cli_session_id: str | None = None,
    emit_log: Callable[[str], Awaitable[None]] | None = None,
    emit_tool_step: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    emit_todos: Callable[[list[dict[str, Any]]], Awaitable[None]] | None = None,
    emit_verification: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    emit_diff_summary: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    tool_steps_sink: list[dict[str, Any]] | None = None,
    mcp_approved_tool: dict[str, Any] | None = None,
    mcp_resume: dict[str, Any] | None = None,
    isolate_cli_history: bool = False,
    chat_source: str = "plain_chat",
    system_prompt_suffix: str = "",
) -> tuple[str, str, str, list[str], str | None, dict[str, Any] | None, list[str], str | None, list[dict[str, Any]] | None, bool]:
    from src.agent_storage import BUILTIN_AGENT_ID, get_agent_by_id
    from src.engine_router import route_engine
    from src.models_config import get_router
    from src.workspace import get_workspace

    resolved_id = (agent_id or "").strip() or BUILTIN_AGENT_ID
    agent = get_agent_by_id(resolved_id)
    agent_ref = str(agent.get("id", resolved_id)) if agent else resolved_id
    reply_label = str(agent.get("name", "Clutch Agent")) if agent else (state.get("active_agent") or "Builder")

    router = get_router()
    from src.agent_type import agent_type_from_record, is_clutch_agent, resolve_model_for_agent

    uses_clutch_model = is_clutch_agent(agent)
    model, resolved_model_id = resolve_model_for_agent(
        router,
        agent,
        session_model_id=session_model_id if uses_clutch_model else None,
    )
    if uses_clutch_model:
        runtime_model_name = model.name
        model_api = getattr(model, "api_model", None) or runtime_model_name
    else:
        runtime_model_name = str(agent.get("name", reply_label)) if agent else reply_label
        model_api = agent_type_from_record(agent) if agent else "cli"
    from src.adapters.ollama_adapter import model_supports_vision
    from src.image_router import format_image_reply, generate_image_for_model, is_image_model
    from src.video_router import format_video_reply, generate_video_for_model, is_video_model
    from src.chat_content import extract_image_data_urls

    _plain, attached_images = extract_image_data_urls(text)

    # Try-first: always send attached images multimodally for Clutch chat models.
    # Soft/API vision failures retry with local OCR/palette analysis below.
    # Local CLI agents: deliver workspace file paths first (same idea as Terminal);
    # OCR only after the CLI refuses / cannot read the image.
    cli_path_images = False
    if uses_clutch_model:
        if is_image_model(model) or is_video_model(model):
            vision_enabled = False
        elif attached_images:
            vision_enabled = True
        else:
            vision_enabled = model_supports_vision(model)
    elif agent and agent_type_from_record(agent) == "ollama-cli":
        from src.llm.router import ModelSpec

        tag = str(agent.get("ollamaModel", "")).strip()
        if tag:
            vision_enabled = model_supports_vision(
                ModelSpec(
                    id=tag,
                    name=tag,
                    provider_id="ollama",
                    api_model=tag,
                    base_url="http://localhost:11434/v1",
                )
            )
        else:
            vision_enabled = False
    else:
        vision_enabled = False
        cli_path_images = bool(attached_images)

    if uses_clutch_model and is_video_model(model):
        if attached_images:
            err = (
                "This model only generates videos and cannot read uploaded screenshots. "
                "Switch to a vision chat model (e.g. Qwen 2.5 VL 7B) using the Model menu in the footer."
            )
            return (
                reply_label,
                runtime_model_name,
                err,
                [f"[CHAT] Vision input ignored for video-generation model {runtime_model_name}"],
                None,
                None,
                [],
                None,
                None,
                False,
            )
        spec, api_key = router.resolve_for_model(resolved_model_id)
        loop = asyncio.get_running_loop()
        video_logs: list[str] = []

        def on_video_log(line: str) -> None:
            if emit_log:
                asyncio.run_coroutine_threadsafe(emit_log(line), loop)

        try:
            video_prompt = (_plain or text).strip()
            result = await asyncio.to_thread(
                generate_video_for_model,
                spec,
                video_prompt,
                api_key=router._require_api_key(spec.provider_id, api_key),
                on_log=on_video_log if emit_log else None,
            )
            return reply_label, runtime_model_name, format_video_reply(result), video_logs, None, None, [], None, None, False
        except Exception as exc:
            from src.models_config import format_connection_error

            err = format_connection_error(exc)
            return (
                reply_label,
                runtime_model_name,
                err,
                [f"Error generating video: {err}"],
                None,
                None,
                [],
                None,
                None,
                False,
            )

    if uses_clutch_model and is_image_model(model):
        if attached_images:
            err = (
                "This model only generates images and cannot read uploaded screenshots. "
                "Switch to a vision chat model (e.g. Qwen 2.5 VL 7B) using the Model menu in the footer."
            )
            return (
                reply_label,
                runtime_model_name,
                err,
                [f"[CHAT] Vision input ignored for image-generation model {runtime_model_name}"],
                None,
                None,
                [],
                None,
                None,
                False,
            )
        spec, api_key = router.resolve_for_model(resolved_model_id)
        loop = asyncio.get_running_loop()
        image_logs: list[str] = []

        def on_image_log(line: str) -> None:
            if emit_log:
                asyncio.run_coroutine_threadsafe(emit_log(line), loop)

        try:
            result = await asyncio.to_thread(
                generate_image_for_model,
                spec,
                text,
                api_key=router._require_api_key(spec.provider_id, api_key),
                on_log=on_image_log if emit_log else None,
            )
            return reply_label, runtime_model_name, format_image_reply(result), image_logs, None, None, [], None, None, False
        except Exception as exc:
            err = str(exc)
            return (
                reply_label,
                runtime_model_name,
                err,
                [f"Error generating image: {err}"],
                None,
                None,
                [],
                None,
                None,
                False,
            )

    from src.agent_mcp import resolve_agent_mcp_servers

    mcp_servers_bound = bool(resolve_agent_mcp_servers(agent)) if agent else False
    system_prompt = (
        _compose_agent_system_prompt(
            agent,
            model_name=runtime_model_name,
            model_api=model_api,
            mcp_servers_bound=mcp_servers_bound,
            user_turn_text=text,
            state=state,
        )
        if agent
        else None
    )
    if system_prompt_suffix.strip():
        system_prompt = (system_prompt or "") + system_prompt_suffix

    history = _history_for_llm(
        state["messages"],
        vision_enabled=vision_enabled,
        image_delivery="paths" if cli_path_images else "auto",
        hybrid_executions=state.get("hybrid_executions"),
    )
    if system_prompt:
        history = [{"role": "system", "content": system_prompt}] + [
            item for item in history if item.get("role") != "system"
        ]

    workspace = get_workspace()
    cwd = workspace.get("workspace_path") if workspace else None
    llm_only_logs: list[str] = []

    from src.hybrid_concurrency import HybridPlainChatRejected

    try:
        if mcp_resume or (agent and _uses_configured_llm(agent)):
            from src.mcp_pending import get_approved_mcp_keys
            from src.mcp_react import run_mcp_react_loop

            mcp_servers = (
                list(mcp_resume.get("servers") or [])
                if mcp_resume
                else resolve_agent_mcp_servers(agent)
            )
            if mcp_servers:
                chat_messages: list[dict[str, Any]] = (
                    list(mcp_resume.get("chat_messages") or [])
                    if mcp_resume
                    else list(history)
                )
                loop = asyncio.get_running_loop()
                step_futures: list[Any] = []

                def on_log(line: str) -> None:
                    if emit_log:
                        asyncio.run_coroutine_threadsafe(emit_log(line), loop)

                def on_tool_step(step: dict[str, Any]) -> None:
                    if emit_tool_step:
                        step_futures.append(
                            asyncio.run_coroutine_threadsafe(emit_tool_step(step), loop)
                        )

                def on_todos(todos: list[dict[str, Any]]) -> None:
                    if emit_todos:
                        step_futures.append(
                            asyncio.run_coroutine_threadsafe(emit_todos(todos), loop)
                        )

                def on_verification(report: dict[str, Any]) -> None:
                    if emit_verification:
                        step_futures.append(
                            asyncio.run_coroutine_threadsafe(emit_verification(report), loop)
                        )

                def on_diff_summary(report: dict[str, Any]) -> None:
                    if emit_diff_summary:
                        step_futures.append(
                            asyncio.run_coroutine_threadsafe(emit_diff_summary(report), loop)
                        )

                outcome = await asyncio.to_thread(
                    run_mcp_react_loop,
                    messages=chat_messages,
                    servers=mcp_servers,
                    log_prefix="CHAT",
                    on_log=on_log if emit_log else None,
                    on_tool_step=on_tool_step if emit_tool_step else None,
                    on_todos=on_todos if emit_todos else None,
                    on_verification=on_verification if emit_verification else None,
                    on_diff_summary=on_diff_summary if emit_diff_summary else None,
                    existing_todos=list(state.get("agent_todos") or []),
                    pause_on_risky=True,
                    permission_mode=__import__(
                        "src.preferences_storage", fromlist=["load_permission_mode"]
                    ).load_permission_mode(),
                    approved_tool=mcp_approved_tool,
                    approved_keys=get_approved_mcp_keys(state["run_id"]),
                    model_id=resolved_model_id,
                )
                for fut in step_futures:
                    await asyncio.wrap_future(fut)
                if tool_steps_sink is not None:
                    tool_steps_sink.clear()
                    tool_steps_sink.extend(list(outcome.tool_steps or []))
                if outcome.todos is not None and emit_todos:
                    await emit_todos(list(outcome.todos))
                if outcome.verification_report is not None and emit_verification:
                    await emit_verification(dict(outcome.verification_report))
                if outcome.diff_summary is not None and emit_diff_summary:
                    await emit_diff_summary(dict(outcome.diff_summary))
                if outcome.approval_required:
                    pause_payload = {
                        **outcome.approval_required,
                        "servers": mcp_servers,
                        "agent_id": resolved_id,
                        "reply_label": reply_label,
                        "engine_label": outcome.engine_label,
                        "tool_steps": list(outcome.tool_steps or []),
                    }
                    if outcome.todos is not None:
                        pause_payload["todos"] = list(outcome.todos)
                    if outcome.verification_report is not None:
                        pause_payload["verification_report"] = dict(
                            outcome.verification_report
                        )
                    if outcome.diff_summary is not None:
                        pause_payload["diff_summary"] = dict(outcome.diff_summary)
                    return (
                        reply_label,
                        outcome.engine_label,
                        "",
                        outcome.logs,
                        None,
                        pause_payload,
                        list(outcome.files_changed or []),
                        None,
                        None,
                        False,
                    )
                return (
                    reply_label,
                    outcome.engine_label,
                    outcome.output,
                    outcome.logs,
                    None,
                    None,
                    list(outcome.files_changed or []),
                    None,
                    None,
                    False,
                )

            llm_only_logs = [
                tr(
                    "[CHAT] No tools available for this agent — using LLM text only. "
                    "Clutch Agent needs an authorized workspace for builtin tools; "
                    "other agents need MCP Hub bindings or a CLI engine.",
                    "[CHAT] 此 Agent 无可用工具，仅使用 LLM 文本回复。"
                    "Clutch Agent 需要已授权工作区以启用内置工具；其他 Agent 需绑定 MCP 或使用 CLI 引擎。",
                )
            ]
            system_prompt = _compose_agent_system_prompt(
                agent,
                model_name=runtime_model_name,
                model_api=model_api,
                mcp_servers_bound=False,
                user_turn_text=text,
                state=state,
            )
            history = _history_for_llm(
                state["messages"],
                vision_enabled=vision_enabled,
                image_delivery="paths" if cli_path_images else "auto",
                hybrid_executions=state.get("hybrid_executions"),
            )
            if system_prompt:
                history = [{"role": "system", "content": system_prompt}] + [
                    item for item in history if item.get("role") != "system"
                ]

        loop = asyncio.get_running_loop()

        def on_log(line: str) -> None:
            if emit_log:
                asyncio.run_coroutine_threadsafe(emit_log(line), loop)

        route_history = history
        tried_vision = bool(attached_images and vision_enabled)
        tried_cli_paths = bool(cli_path_images)
        from src.chat_content import (
            materialize_images_as_file_refs,
            ocr_fallback_prompt_for_engine,
        )

        # Never put raw data:image on CLI argv. Paths first; OCR only on refusal.
        if cli_path_images:
            engine_prompt = materialize_images_as_file_refs(text)
        elif attached_images and not vision_enabled:
            engine_prompt = ocr_fallback_prompt_for_engine(text)
        else:
            engine_prompt = text

        def _route_once(hist: list[dict[str, Any]], *, prompt: str | None = None):
            return route_engine(
                agent_name=agent_ref,
                prompt=prompt if prompt is not None else engine_prompt,
                cwd=cwd,
                history=hist,
                system_prompt=system_prompt,
                cli_session_id=cli_session_id,
                on_log=on_log if emit_log else None,
                run_id=state.get("run_id"),
                source=chat_source,
                session_model_id=session_model_id,
            )

        def _ocr_retry_history() -> list[dict[str, Any]]:
            hist = _history_for_llm(
                state["messages"],
                vision_enabled=False,
                image_delivery="ocr",
                hybrid_executions=state.get("hybrid_executions"),
            )
            if system_prompt:
                return [{"role": "system", "content": system_prompt}] + [
                    item for item in hist if item.get("role") != "system"
                ]
            return hist

        try:
            result = await asyncio.to_thread(_route_once, route_history)
        except HybridPlainChatRejected:
            raise
        except Exception as vision_exc:
            from src.chat_content import looks_like_vision_api_error

            if not (tried_vision and looks_like_vision_api_error(vision_exc)):
                raise
            if emit_log:
                await emit_log(
                    "[CHAT] Vision API rejected image input — retrying with local OCR/palette analysis."
                )
            llm_only_logs.append(
                "[CHAT] Vision API rejected image input — retrying with local OCR/palette analysis."
            )
            ocr_prompt = ocr_fallback_prompt_for_engine(text)
            result = await asyncio.to_thread(
                _route_once, _ocr_retry_history(), prompt=ocr_prompt
            )
        else:
            from src.chat_content import looks_like_vision_error

            if (tried_vision or tried_cli_paths) and looks_like_vision_error(
                result.output or ""
            ):
                if emit_log:
                    await emit_log(
                        "[CHAT] Model refused vision input — retrying with local OCR/palette analysis."
                    )
                llm_only_logs.append(
                    "[CHAT] Model refused vision input — retrying with local OCR/palette analysis."
                )
                ocr_prompt = ocr_fallback_prompt_for_engine(text)
                result = await asyncio.to_thread(
                    _route_once, _ocr_retry_history(), prompt=ocr_prompt
                )

        return (
            reply_label,
            result.engine,
            result.output,
            llm_only_logs + result.logs,
            result.cli_session_id,
            None,
            [],
            result.raw_output,
            result.output_events,
            result.shell_recovered,
        )
    except HybridPlainChatRejected:
        raise
    except Exception as exc:
        from src.agent_type import agent_type_from_record

        err = str(exc)
        agent_type = agent_type_from_record(agent) if agent else "clutch"
        if agent_type == "claude-cli" or "Claude CLI" in err:
            runtime_engine = "Claude CLI"
        else:
            runtime_engine = runtime_model_name
        return reply_label, runtime_engine, err, [f"Error routing plain chat request: {err}"], None, None, [], None, None, False

async def _handle_plain_chat_mcp_decision(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    decision: str,
    instructions: str = "",
) -> ClutchState:
    from src.builtin_tools import (
        is_ask_user_question_tool,
        is_propose_plan_tool,
        parse_question_selection,
    )
    from src.mcp_pending import get_pending, pop_pending, record_mcp_approval

    pending = get_pending(run_id)
    if pending is None:
        return state

    is_plan = is_propose_plan_tool(pending.func_name)
    is_question = is_ask_user_question_tool(pending.func_name)
    normalized = (decision or "").strip().lower()
    if normalized == "retry":
        normalized = "revise"

    # Free-text on a question card = the user's custom answer (continue).
    if is_question and normalized == "revise":
        normalized = "approve"

    if is_plan and normalized == "revise":
        pop_pending(run_id)
        note = (instructions or "").strip() or tr("(no comments)", "（无附加说明）")
        messages = _patch_plan_card_status(
            list(state["messages"]), status="revised", note=note
        )
        revise_line = tagged(TAG_HUMAN, f"Plan revise requested: {note}")
        chat_messages = list(pending.chat_messages)
        chat_messages.append(
            {
                "role": "tool",
                "tool_call_id": pending.tool_call_id,
                "content": (
                    "User requested changes to the plan before approval.\n"
                    f"Feedback: {note}\n"
                    "Call propose_plan again with a revised title and steps. "
                    "Do not edit files until the new plan is approved."
                ),
            }
        )
        state = _merge_patch(
            state,
            {
                "messages": messages,
                "terminal_logs": list(state["terminal_logs"]) + [stamp_log_line(revise_line)],
                "status": "running",
                "active_agent": pending.reply_label,
                "pending_tool_steps": [],
            },
        )
        _commit_run_state(run_id, state)
        _touch_session(run_id, status=state["status"])
        await _send_log_event(websocket, run_id, revise_line, node_id="")
        await _notify_run_state(
            websocket,
            run_id,
            state,
            {"messages": messages, "status": "running", "pending_tool_steps": []},
        )

        streamed_logs = False
        tool_steps_sink: list[dict[str, Any]] = []

        async def emit_log(line: str) -> None:
            nonlocal streamed_logs, state
            streamed_logs = True
            stamped = stamp_log_line(line)
            await _send_log_event(websocket, run_id, stamped, node_id="")
            logs = list(state["terminal_logs"]) + [stamped]
            state = _merge_patch(state, {"terminal_logs": logs})
            _commit_run_state(run_id, state)
            await _notify_run_state(websocket, run_id, state, {"terminal_logs": logs})

        async def emit_tool_step(step: dict[str, Any]) -> None:
            nonlocal state
            from src.tool_steps import upsert_tool_step

            steps = upsert_tool_step(list(state.get("pending_tool_steps") or []), step)
            state = _merge_patch(state, {"pending_tool_steps": steps})
            _commit_run_state(run_id, state)
            await _notify_run_state(websocket, run_id, state, {"pending_tool_steps": steps})
            await _maybe_notify_step_file_diff(websocket, run_id, step)

        async def emit_todos(todos: list[dict[str, Any]]) -> None:
            nonlocal state
            state = _merge_patch(state, {"agent_todos": list(todos)})
            _commit_run_state(run_id, state)
            await _notify_run_state(websocket, run_id, state, {"agent_todos": list(todos)})

        async def emit_verification(report: dict[str, Any]) -> None:
            nonlocal state
            label = str(state.get("active_agent") or pending.reply_label or "Clutch Agent")
            state = await _publish_verification_report(
                websocket, run_id, state, dict(report), reply_label=label
            )

        async def emit_diff_summary(report: dict[str, Any]) -> None:
            nonlocal state
            label = str(state.get("active_agent") or pending.reply_label or "Clutch Agent")
            state = await _publish_diff_summary(
                websocket, run_id, state, dict(report), reply_label=label
            )

        (
            model_name,
            runtime_engine,
            reply_text,
            route_logs,
            _cli_session_id,
            mcp_pause,
            files_changed,
            raw_output,
            output_events,
            shell_recovered,
        ) = await _llm_chat_reply(
            state,
            "",
            agent_id=pending.agent_id,
            emit_log=emit_log,
            emit_tool_step=emit_tool_step,
            emit_todos=emit_todos,
            emit_verification=emit_verification,
            emit_diff_summary=emit_diff_summary,
            tool_steps_sink=tool_steps_sink,
            mcp_resume={
                "chat_messages": chat_messages,
                "servers": pending.servers,
            },
        )
        # Fall through into shared pause/complete handling below via recursive-style continue:
        return await _finish_plain_chat_after_llm(
            websocket,
            run_id,
            state,
            model_name=model_name,
            runtime_engine=runtime_engine,
            reply_text=reply_text,
            route_logs=route_logs,
            mcp_pause=mcp_pause,
            files_changed=files_changed,
            raw_output=raw_output,
            output_events=output_events,
            shell_recovered=shell_recovered,
            tool_steps_sink=tool_steps_sink,
            streamed_logs=streamed_logs,
            active_agent=pending.reply_label,
            pending_agent_id=pending.agent_id,
            user_text_for_tokens="",
        )

    if normalized != "approve":
        pop_pending(run_id)
        if is_plan:
            messages = _patch_plan_card_status(list(state["messages"]), status="cancelled")
            supervisor = _chat_message(
                "Supervisor",
                tr("Plan cancelled by supervisor.", "监督者已取消计划。"),
            )
            log_line = tagged(TAG_HUMAN, f"Plan {pending.func_name} cancelled")
        elif is_question:
            messages = _patch_question_card_status(
                list(state["messages"]), status="cancelled"
            )
            supervisor = _chat_message(
                "Supervisor",
                tr("Question cancelled by supervisor.", "监督者已取消提问。"),
            )
            log_line = tagged(TAG_HUMAN, f"Question {pending.func_name} cancelled")
        else:
            messages = list(state["messages"])
            supervisor = _chat_message(
                "Supervisor",
                tr("MCP tool call rejected by supervisor.", "监督者已拒绝 MCP 工具调用。"),
            )
            log_line = tagged(TAG_HUMAN, f"MCP tool {pending.func_name} rejected")
        final_messages = messages + [supervisor]
        final_patch: dict[str, Any] = {
            "messages": final_messages,
            "terminal_logs": list(state["terminal_logs"]) + [stamp_log_line(log_line)],
            "status": "idle",
            "active_agent": pending.reply_label,
            "pending_tool_steps": [],
        }
        state = _merge_patch(state, final_patch)
        _commit_run_state(run_id, state)
        _touch_session(run_id, status=state["status"])
        await _send_message_event(websocket, run_id, supervisor, "")
        await _send_log_event(websocket, run_id, log_line, node_id="")
        await _notify_run_state(websocket, run_id, state, final_patch)
        return state

    pop_pending(run_id)
    if not is_plan and not is_question:
        record_mcp_approval(run_id, pending.func_name, pending.func_args)
    question_selection: dict[str, str] | None = None
    if is_question:
        question_selection = parse_question_selection(
            instructions, dict(pending.func_args or {})
        )
        messages = _patch_question_card_status(
            list(state["messages"]),
            status="answered",
            selected=question_selection,
        )
    elif is_plan:
        messages = _patch_plan_card_status(list(state["messages"]), status="approved")
    else:
        messages = list(state["messages"])
    state = _merge_patch(
        state,
        {
            "messages": messages,
            "status": "running",
            "active_agent": pending.reply_label,
        },
    )
    await _notify_run_state(
        websocket, run_id, state, {"status": "running", "messages": messages}
    )

    streamed_logs = False
    tool_steps_sink: list[dict[str, Any]] = []

    async def emit_log(line: str) -> None:
        nonlocal streamed_logs, state
        streamed_logs = True
        stamped = stamp_log_line(line)
        await _send_log_event(websocket, run_id, stamped, node_id="")
        logs = list(state["terminal_logs"]) + [stamped]
        state = _merge_patch(state, {"terminal_logs": logs})
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, {"terminal_logs": logs})

    async def emit_tool_step(step: dict[str, Any]) -> None:
        nonlocal state
        from src.tool_steps import upsert_tool_step

        steps = upsert_tool_step(list(state.get("pending_tool_steps") or []), step)
        state = _merge_patch(state, {"pending_tool_steps": steps})
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, {"pending_tool_steps": steps})
        await _maybe_notify_step_file_diff(websocket, run_id, step)

    async def emit_todos(todos: list[dict[str, Any]]) -> None:
        nonlocal state
        state = _merge_patch(state, {"agent_todos": list(todos)})
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, {"agent_todos": list(todos)})

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

    resume_args = dict(pending.func_args or {})
    if question_selection is not None:
        resume_args["selected"] = question_selection
    approved_tool = {
        "tool_call_id": pending.tool_call_id,
        "func_name": pending.func_name,
        "func_args": resume_args,
        "step_idx": pending.step_idx,
        "step_id": pending.step_id or f"tool_{pending.step_idx}",
    }
    mcp_resume = {
        "chat_messages": pending.chat_messages,
        "servers": pending.servers,
    }

    (
        model_name,
        runtime_engine,
        reply_text,
        route_logs,
        _cli_session_id,
        mcp_pause,
        files_changed,
        raw_output,
        output_events,
        shell_recovered,
    ) = await _llm_chat_reply(
        state,
        "",
        agent_id=pending.agent_id,
        emit_log=emit_log,
        emit_tool_step=emit_tool_step,
        emit_todos=emit_todos,
        emit_verification=emit_verification,
        emit_diff_summary=emit_diff_summary,
        tool_steps_sink=tool_steps_sink,
        mcp_approved_tool=approved_tool,
        mcp_resume=mcp_resume,
    )

    return await _finish_plain_chat_after_llm(
        websocket,
        run_id,
        state,
        model_name=model_name,
        runtime_engine=runtime_engine,
        reply_text=reply_text,
        route_logs=route_logs,
        mcp_pause=mcp_pause,
        files_changed=files_changed,
        raw_output=raw_output,
        output_events=output_events,
        shell_recovered=shell_recovered,
        tool_steps_sink=tool_steps_sink,
        streamed_logs=streamed_logs,
        active_agent=pending.reply_label,
        pending_agent_id=pending.agent_id,
        user_text_for_tokens="",
    )


async def _finish_plain_chat_after_llm(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    *,
    model_name: str,
    runtime_engine: str,
    reply_text: str,
    route_logs: list[str],
    mcp_pause: dict[str, Any] | None,
    files_changed: list[str] | None,
    raw_output: str | None,
    output_events: list[dict[str, Any]] | None,
    shell_recovered: bool,
    tool_steps_sink: list[dict[str, Any]],
    streamed_logs: bool,
    active_agent: str,
    pending_agent_id: str,
    user_text_for_tokens: str,
    cli_session_id: str | None = None,
) -> ClutchState:
    """Shared pause/complete path after plain-chat LLM (+ MCP) returns."""
    if mcp_pause:
        from src.mcp_pending import McpPendingApproval, store_pending

        store_pending(
            run_id,
            McpPendingApproval(
                agent_id=pending_agent_id,
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
        is_plan = _is_plan_pause(mcp_pause)
        gate_line = _mcp_pause_gate_line(mcp_pause)
        pause_messages, pause_msg, pause_created = _messages_for_mcp_pause(
            list(state["messages"]),
            mcp_pause,
            reply_label=model_name or active_agent,
        )
        pause_patch: dict[str, Any] = {
            "messages": pause_messages,
            "terminal_logs": _append_terminal_logs(
                list(state["terminal_logs"]), route_logs, gate_line, streamed=streamed_logs
            ),
            "status": "awaiting_human",
            "active_agent": active_agent,
            "pending_tool_steps": list(mcp_pause.get("tool_steps") or tool_steps_sink),
        }
        if mcp_pause.get("todos") is not None:
            pause_patch["agent_todos"] = list(mcp_pause.get("todos") or [])
        if mcp_pause.get("verification_report") is not None:
            pause_patch["verification_report"] = dict(mcp_pause["verification_report"])
        if mcp_pause.get("diff_summary") is not None:
            pause_patch["diff_summary"] = dict(mcp_pause["diff_summary"])
        state = _merge_patch(state, pause_patch)
        _commit_run_state(run_id, state)
        _touch_session(run_id, status=state["status"])
        if pause_created:
            await _send_message_event(websocket, run_id, pause_msg, "")
        if not streamed_logs:
            for log in route_logs:
                await _send_log_event(websocket, run_id, log, node_id="")
        await _send_log_event(websocket, run_id, gate_line, node_id="")
        await _notify_run_state(websocket, run_id, state, pause_patch)
        await _send_human_required(
            websocket, run_id, node_id="", prompt=_mcp_pause_human_prompt(mcp_pause)
        )
        return state

    sealed_steps = _sealed_tool_steps(state, sink=tool_steps_sink)
    merged_changed = _merge_files_changed_with_tool_steps(files_changed, sealed_steps)
    files_changed = merged_changed
    reply = _chat_message(
        model_name,
        reply_text,
        runtime_engine=runtime_engine,
        raw_output=raw_output,
        output_events=output_events,
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
    log_line = f"[CHAT] {model_name} via {runtime_engine}: {len(reply_text)} chars"
    if not streamed_logs:
        for log in route_logs:
            await _send_log_event(websocket, run_id, log, node_id="")
    await _send_log_event(websocket, run_id, log_line, node_id="")

    final_messages = list(state["messages"]) + [reply]
    final_logs = _append_terminal_logs(
        list(state["terminal_logs"]), route_logs, log_line, streamed=streamed_logs
    )
    final_patch = {
        "messages": final_messages,
        "terminal_logs": final_logs,
        "status": "idle",
        "active_agent": active_agent,
        "pending_tool_steps": [],
        **_token_patch_turn(
            state, user_text=user_text_for_tokens, assistant_text=reply_text
        ),
    }
    if shell_recovered:
        final_patch["shell_session_status"] = "recovering"
    elif runtime_engine and "Hybrid" in runtime_engine:
        final_patch["shell_session_status"] = "ready"
    if cli_session_id:
        from src.state import cli_session_patch

        final_patch.update(cli_session_patch(cli_session_id, pending_agent_id))
    state = _merge_patch(state, final_patch)
    _commit_run_state(run_id, state)
    _touch_session(run_id, status=state["status"])
    await _send_message_event(websocket, run_id, reply, "")
    if runtime_engine and "Hybrid" in runtime_engine:
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
            path_diffs=_path_diffs_from_tool_steps(sealed_steps),
        )
    await _notify_run_state(websocket, run_id, state, final_patch)
    return state


def _interrupt_plain_chat_shell(run_id: str) -> None:
    from src.shell_session import get_shell_session_manager

    get_shell_session_manager().release(run_id)

def _interrupt_workflow_run(run_id: str) -> None:
    from src.workflow_cancel import request_workflow_cancel

    request_workflow_cancel(run_id)
    _interrupt_plain_chat_shell(run_id)

async def _apply_plain_chat_stop(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
) -> ClutchState:
    from src.runtime_config import runtime_mode

    await asyncio.to_thread(_interrupt_plain_chat_shell, run_id)
    if runtime_mode() == "hybrid":
        log_line = stamp_log_line(tagged(TAG_WORKFLOW, "[HYBRID] Plain chat stopped by user."))
    else:
        log_line = stamp_log_line(tagged(TAG_WORKFLOW, "Run stopped by supervisor."))
    logs = list(state["terminal_logs"]) + [log_line]
    patch: dict[str, Any] = {"status": "idle", "terminal_logs": logs}
    if runtime_mode() == "hybrid":
        patch["shell_session_status"] = "ready"
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    _touch_session(run_id, status=state["status"])
    await _send_log_event(websocket, run_id, log_line, node_id="")
    await _notify_run_state(websocket, run_id, state, patch)
    return state

async def _recover_stuck_plain_chat(run_id: str) -> None:
    from src.runtime_config import runtime_mode

    state = _get_or_create_run(run_id)
    if state.get("workflow_id"):
        return
    if state["status"] != "running":
        return
    log_line = stamp_log_line(
        tagged(
            TAG_WORKFLOW,
            "[HYBRID] Recovered plain chat after WebSocket disconnect.",
        )
    )
    logs = list(state["terminal_logs"]) + [log_line]
    patch: dict[str, Any] = {"status": "idle", "terminal_logs": logs}
    if runtime_mode() == "hybrid":
        patch["shell_session_status"] = "ready"
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    _touch_session(run_id, status=state["status"])

async def _apply_hybrid_plain_chat_rejection(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    *,
    code: str,
    keep_running: bool = False,
) -> ClutchState:
    from src.hybrid_audit_log import append_hybrid_rejection_audit
    from src.hybrid_concurrency import hybrid_rejection_message, shell_session_status_for_rejection
    from src.runtime_config import runtime_mode

    user_text = hybrid_rejection_message(code)
    log_line = f"[HYBRID] rejected ({code}): {user_text}"
    append_hybrid_rejection_audit(run_id=run_id, reason=code, message=user_text)

    supervisor = _chat_message("Supervisor", user_text)
    logs = list(state["terminal_logs"]) + [stamp_log_line(log_line)]
    patch: dict[str, Any] = {
        "messages": list(state["messages"]) + [supervisor],
        "terminal_logs": logs,
    }
    if runtime_mode() == "hybrid":
        patch["shell_session_status"] = shell_session_status_for_rejection(code)
    if not keep_running:
        patch["status"] = "idle"
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    _touch_session(run_id, status=state["status"])
    await _send_message_event(websocket, run_id, supervisor, "")
    await _send_log_event(websocket, run_id, log_line, node_id="")
    await _notify_run_state(websocket, run_id, state, patch)
    return state

class _NullWebSocket:
    """Placeholder when resuming a pool-queued turn after the client disconnected."""

    async def send_text(self, _data: str) -> None:
        return

async def _refresh_pool_queued_run_states() -> None:
    from src.plain_chat_pool_queue import iter_queued_run_ids, pool_queue_state_patch

    for run_id in iter_queued_run_ids():
        state = _get_or_create_run(run_id)
        if state.get("shell_session_status") != "queued_pool":
            continue
        patch = pool_queue_state_patch(run_id)
        state = _merge_patch(state, patch)
        _run_states[run_id] = state
        _commit_run_state(run_id, state)
        from src.plain_chat_pool_queue import get_plain_chat_ws

        websocket = get_plain_chat_ws(run_id)
        if websocket is not None:
            await _notify_run_state(websocket, run_id, state, patch)

async def _apply_pool_full_queue(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    *,
    text: str,
    agent_id: str,
    session_model_id: str | None,
    client_message_id: str | None,
) -> ClutchState:
    from src.hybrid_concurrency import shell_session_status_for_pool_queue
    from src.plain_chat_pool_queue import (
        PoolQueuedTurn,
        clear_pool_queue_state_patch,
        enqueue_turn,
        pool_queue_state_patch,
        register_plain_chat_ws,
        schedule_pool_drain,
    )
    from src.runtime_config import runtime_mode

    register_plain_chat_ws(run_id, websocket)
    pending = enqueue_turn(
        PoolQueuedTurn(
            run_id=run_id,
            text=text,
            agent_id=agent_id,
            session_model_id=session_model_id,
            client_message_id=client_message_id,
        )
    )
    log_line = stamp_log_line(
        tagged(
            TAG_WORKFLOW,
            f"[HYBRID] queued waiting for shell pool ({pending} pending globally)",
        )
    )
    logs = list(state["terminal_logs"]) + [log_line]
    patch: dict[str, Any] = {
        "terminal_logs": logs,
        "status": "running",
    }
    if runtime_mode() == "hybrid":
        patch["shell_session_status"] = shell_session_status_for_pool_queue()
        patch.update(pool_queue_state_patch(run_id))
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    await _send_log_event(websocket, run_id, log_line, node_id="")
    await _notify_run_state(websocket, run_id, state, patch)
    await schedule_pool_drain()
    return state

async def _resume_pool_queued_turn(
    item: "PoolQueuedTurn",
    websocket: WebSocket | None,
) -> None:
    from src.plain_chat_pool_queue import PoolQueuedTurn, register_plain_chat_ws
    from src.run_state_store import sync_run_state_from_disk

    assert isinstance(item, PoolQueuedTurn)
    run_id = item.run_id
    ws: WebSocket = websocket if websocket is not None else _NullWebSocket()  # type: ignore[assignment]
    if websocket is not None:
        register_plain_chat_ws(run_id, websocket)
    state = sync_run_state_from_disk(run_id, _get_or_create_run(run_id))
    _run_states[run_id] = state
    await _handle_plain_chat(
        ws,
        run_id,
        state,
        item.text,
        agent_id=item.agent_id,
        session_model_id=item.session_model_id,
        client_message_id=item.client_message_id,
        resume_after_pool_queue=True,
    )

async def _persist_plain_chat_user_message(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    text: str,
    agent_id: str | None = None,
    client_message_id: str | None = None,
) -> ClutchState:
    """Commit user turn + session list entry before LLM work starts."""
    from src.agent_storage import BUILTIN_AGENT_ID, get_agent_by_id
    from src.runtime_config import runtime_mode

    resolved_id = (agent_id or "").strip() or BUILTIN_AGENT_ID
    agent = get_agent_by_id(resolved_id)
    active_agent = str(agent.get("name", "Clutch Agent")) if agent else "Clutch Agent"

    stripped = text.strip()
    client_id = (client_message_id or "").strip()
    user_message = _chat_message(
        "User",
        text,
        msg_id=client_id or f"user_{uuid.uuid4().hex[:8]}",
    )
    messages = list(state["messages"])
    already_has_client_id = bool(
        client_id and any(str(item.get("id", "")) == client_id for item in messages)
    )
    user_message_added = not already_has_client_id and not (
        messages
        and messages[-1].get("agent") == "User"
        and str(messages[-1].get("text", "")).strip() == stripped
    )
    if user_message_added:
        messages = messages + [user_message]
    user_patch: dict[str, Any] = {
        "messages": messages,
        "status": "running",
        "active_agent": active_agent,
    }
    if runtime_mode() == "hybrid":
        user_patch["shell_session_status"] = "ready"
    state = _merge_patch(state, user_patch)
    _commit_run_state(run_id, state)
    _touch_session(run_id, title=text.strip()[:80] or "New session", status=state["status"])
    if user_message_added:
        await _send_message_event(websocket, run_id, user_message, "")
    await _notify_run_state(websocket, run_id, state, user_patch)
    return state

async def _handle_plain_chat(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    text: str,
    agent_id: str | None = None,
    session_model_id: str | None = None,
    client_message_id: str | None = None,
    *,
    resume_after_pool_queue: bool = False,
    user_persisted: bool = False,
) -> ClutchState:
    from src.agent_storage import BUILTIN_AGENT_ID, get_agent_by_id
    from src.runtime_config import runtime_mode

    resolved_id = (agent_id or "").strip() or BUILTIN_AGENT_ID
    agent = get_agent_by_id(resolved_id)
    active_agent = str(agent.get("name", "Clutch Agent")) if agent else "Clutch Agent"

    if (
        state["status"] == "running"
        and runtime_mode() == "hybrid"
        and not resume_after_pool_queue
        and not user_persisted
    ):
        return state

    stripped = text.strip()
    client_id = (client_message_id or "").strip()
    if not resume_after_pool_queue and not user_persisted:
        user_message = _chat_message(
            "User",
            text,
            msg_id=client_id or f"user_{uuid.uuid4().hex[:8]}",
        )
        messages = list(state["messages"])
        already_has_client_id = bool(
            client_id and any(str(item.get("id", "")) == client_id for item in messages)
        )
        user_message_added = not already_has_client_id and not (
            messages
            and messages[-1].get("agent") == "User"
            and str(messages[-1].get("text", "")).strip() == stripped
        )
        if user_message_added:
            messages = messages + [user_message]
        user_patch: dict[str, Any] = {
            "messages": messages,
            "status": "running",
            "active_agent": active_agent,
            "pending_tool_steps": [],
        }
        if runtime_mode() == "hybrid":
            user_patch["shell_session_status"] = "ready"
        state = _merge_patch(state, user_patch)
        _commit_run_state(run_id, state)
        _touch_session(run_id, title=text.strip()[:80] or "New session", status=state["status"])

        if user_message_added:
            await _send_message_event(websocket, run_id, user_message, "")
        await _notify_run_state(websocket, run_id, state, user_patch)
    elif runtime_mode() == "hybrid":
        from src.plain_chat_pool_queue import clear_pool_queue_state_patch

        ready_patch = {
            "shell_session_status": "ready",
            "status": "running",
            **clear_pool_queue_state_patch(),
        }
        state = _merge_patch(state, ready_patch)
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, ready_patch)

    from src.state import cli_session_patch, read_cli_session_agent_id, read_cli_session_id

    stored_session_id = read_cli_session_id(state) or None
    stored_session_agent = read_cli_session_agent_id(state)
    agent_switched = bool(stored_session_agent and stored_session_agent != resolved_id)
    if agent_switched:
        stored_session_id = None

    streamed_logs = False
    tool_steps_sink: list[dict[str, Any]] = []

    async def emit_log(line: str) -> None:
        nonlocal streamed_logs, state
        streamed_logs = True
        stamped = stamp_log_line(line)
        logs = list(state["terminal_logs"]) + [stamped]
        state = _merge_patch(state, {"terminal_logs": logs})
        _commit_run_state(run_id, state)
        await _try_ws_notify(
            _send_log_event(websocket, run_id, stamped, node_id=""),
            run_id=run_id,
            what="log",
        )
        await _try_ws_notify(
            _notify_run_state(websocket, run_id, state, {"terminal_logs": logs}),
            run_id=run_id,
            what="state_patch",
        )

    async def emit_tool_step(step: dict[str, Any]) -> None:
        nonlocal state
        from src.tool_steps import upsert_tool_step

        steps = upsert_tool_step(list(state.get("pending_tool_steps") or []), step)
        state = _merge_patch(state, {"pending_tool_steps": steps})
        _commit_run_state(run_id, state)
        await _try_ws_notify(
            _notify_run_state(websocket, run_id, state, {"pending_tool_steps": steps}),
            run_id=run_id,
            what="state_patch",
        )
        await _maybe_notify_step_file_diff(websocket, run_id, step)

    async def emit_todos(todos: list[dict[str, Any]]) -> None:
        nonlocal state
        state = _merge_patch(state, {"agent_todos": list(todos)})
        _commit_run_state(run_id, state)
        await _try_ws_notify(
            _notify_run_state(websocket, run_id, state, {"agent_todos": list(todos)}),
            run_id=run_id,
            what="state_patch",
        )

    async def emit_verification(report: dict[str, Any]) -> None:
        nonlocal state
        label = str(state.get("active_agent") or active_agent or "Clutch Agent")
        state = await _publish_verification_report(
            websocket, run_id, state, dict(report), reply_label=label
        )

    async def emit_diff_summary(report: dict[str, Any]) -> None:
        nonlocal state
        label = str(state.get("active_agent") or active_agent or "Clutch Agent")
        state = await _publish_diff_summary(
            websocket, run_id, state, dict(report), reply_label=label
        )

    from src.hybrid_concurrency import HybridPlainChatRejected

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
            text,
            agent_id=resolved_id,
            session_model_id=session_model_id,
            cli_session_id=stored_session_id,
            emit_log=emit_log,
            emit_tool_step=emit_tool_step,
            emit_todos=emit_todos,
            emit_verification=emit_verification,
            emit_diff_summary=emit_diff_summary,
            tool_steps_sink=tool_steps_sink,
        )
    except HybridPlainChatRejected as exc:
        if exc.code == "pool_full":
            return await _apply_pool_full_queue(
                websocket,
                run_id,
                state,
                text=text,
                agent_id=resolved_id,
                session_model_id=session_model_id,
                client_message_id=client_id or None,
            )
        keep_running = exc.code == "session_busy" and state["status"] == "running"
        return await _apply_hybrid_plain_chat_rejection(
            websocket,
            run_id,
            state,
            code=exc.code,
            keep_running=keep_running,
        )
    except Exception as exc:
        err_line = f"Error in plain chat: {exc}"
        logs = list(state["terminal_logs"]) + [stamp_log_line(err_line)]
        err_patch: dict[str, Any] = {"status": "idle", "terminal_logs": logs}
        if runtime_mode() == "hybrid":
            err_patch["shell_session_status"] = "ready"
        state = _merge_patch(state, err_patch)
        _commit_run_state(run_id, state)
        _touch_session(run_id, status=state["status"])
        await _try_ws_notify(
            _send_log_event(websocket, run_id, err_line, node_id=""),
            run_id=run_id,
            what="log",
        )
        await _try_ws_notify(
            _notify_run_state(websocket, run_id, state, err_patch),
            run_id=run_id,
            what="state_patch",
        )
        return state

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
        }
        state = _merge_patch(state, pause_patch)
        _commit_run_state(run_id, state)
        _touch_session(run_id, status=state["status"])
        if pause_created:
            await _send_message_event(websocket, run_id, pause_msg, "")
        if not streamed_logs:
            for log in route_logs:
                await _send_log_event(websocket, run_id, log, node_id="")
        await _send_log_event(websocket, run_id, gate_line, node_id="")
        await _notify_run_state(websocket, run_id, state, pause_patch)
        await _send_human_required(
            websocket,
            run_id,
            node_id="",
            prompt=_mcp_pause_human_prompt(mcp_pause),
        )
        return state

    sealed_steps = _sealed_tool_steps(state, sink=tool_steps_sink)
    merged_changed = _merge_files_changed_with_tool_steps(files_changed, sealed_steps)
    files_changed = merged_changed
    reply = _chat_message(
        model_name,
        reply_text,
        runtime_engine=runtime_engine,
        raw_output=raw_output,
        output_events=output_events,
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

    hybrid_system_prompt: str | None = None
    hybrid_executions_patch: dict[str, dict[str, object]] | None = None
    hybrid_detail_log: str | None = None
    if runtime_engine and "Hybrid" in runtime_engine:
        if agent:
            from src.agent_mcp import resolve_agent_mcp_servers
            from src.agent_type import resolve_model_for_agent
            from src.models_config import get_router

            router = get_router()
            model, _resolved_model_id = resolve_model_for_agent(
                router, agent, session_model_id=session_model_id
            )
            hybrid_system_prompt = _compose_agent_system_prompt(
                agent,
                model_name=model.name,
                model_api=getattr(model, "api_model", None) or model.name,
                mcp_servers_bound=bool(resolve_agent_mcp_servers(agent)),
                state=state,
            )
        hybrid_executions_patch = _merge_hybrid_executions(
            state,
            message_id=str(reply["id"]),
            raw_output=raw_output,
            output_events=output_events,
            system_prompt=hybrid_system_prompt,
        )
        entry = hybrid_executions_patch[str(reply["id"])]
        reply["rawOutput"] = entry.get("rawOutput")
        reply["outputEvents"] = entry.get("outputEvents")
        hybrid_detail_log = (
            f"[HYBRID] execution_details message={reply['id']} "
            f"events={len(entry.get('outputEvents') or [])} "
            f"raw_bytes={len(str(entry.get('rawOutput') or ''))}"
        )

    log_line = f"[CHAT] {model_name} via {runtime_engine}: {len(reply_text)} chars"

    final_messages = list(state["messages"]) + [reply]
    final_logs = _append_terminal_logs(
        list(state["terminal_logs"]), route_logs, log_line, streamed=streamed_logs
    )
    if hybrid_detail_log:
        final_logs.append(stamp_log_line(hybrid_detail_log))
    final_patch: dict[str, Any] = {
        "messages": final_messages,
        "terminal_logs": final_logs,
        "status": "idle",
        "active_agent": active_agent,
        "pending_tool_steps": [],
        **_token_patch_turn(state, user_text=text, assistant_text=reply_text),
    }
    if hybrid_executions_patch is not None:
        final_patch["hybrid_executions"] = hybrid_executions_patch
    if shell_recovered:
        final_patch["shell_session_status"] = "recovering"
    elif runtime_engine and "Hybrid" in runtime_engine:
        from src.plain_chat_pool_queue import clear_pool_queue_state_patch

        final_patch["shell_session_status"] = "ready"
        final_patch.update(clear_pool_queue_state_patch())
    if cli_session_id:
        final_patch.update(cli_session_patch(cli_session_id, resolved_id))
    elif stored_session_agent and stored_session_agent != resolved_id:
        final_patch.update(cli_session_patch(None, ""))
    state = _merge_patch(state, final_patch)

    from src.compaction import should_compact, compact_run_messages
    if should_compact(state):
        state = await compact_run_messages(run_id, state, model_id=resolved_id)
        final_patch.update({
            "messages": list(state["messages"]),
            "token_input": state["token_input"],
            "token_output": state["token_output"],
            "session_tokens": state["session_tokens"],
            "session_cost_usd": state["session_cost_usd"],
        })

    _commit_run_state(run_id, state)
    _touch_session(run_id, title=text.strip()[:80] or "New session", status=state["status"])

    if not streamed_logs:
        for log in route_logs:
            await _try_ws_notify(
                _send_log_event(websocket, run_id, log, node_id=""),
                run_id=run_id,
                what="log",
            )
    await _try_ws_notify(
        _send_log_event(websocket, run_id, log_line, node_id=""),
        run_id=run_id,
        what="log",
    )
    await _try_ws_notify(
        _send_message_event(websocket, run_id, reply, ""),
        run_id=run_id,
        what="message",
    )
    if runtime_engine and "Hybrid" in runtime_engine and hybrid_executions_patch:
        entry = hybrid_executions_patch[str(reply["id"])]
        await _try_ws_notify(
            _send_hybrid_execution_event(
                websocket,
                run_id,
                message_id=str(reply["id"]),
                raw_output=entry.get("rawOutput"),  # type: ignore[arg-type]
                output_events=entry.get("outputEvents"),  # type: ignore[arg-type]
            ),
            run_id=run_id,
            what="hybrid_execution",
        )
    if files_changed:
        await _try_ws_notify(
            _notify_workspace_files_changed(
                websocket,
                run_id,
                files_changed,
                path_diffs=_path_diffs_from_tool_steps(sealed_steps),
            ),
            run_id=run_id,
            what="file_changed",
        )
    await _try_ws_notify(
        _notify_run_state(websocket, run_id, state, final_patch),
        run_id=run_id,
        what="state_patch",
    )

    return state

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
        "pending_tool_steps": [],
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
        from src.tool_steps import upsert_tool_step

        steps = upsert_tool_step(list(state.get("pending_tool_steps") or []), step)
        state = _merge_patch(state, {"pending_tool_steps": steps})
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, {"pending_tool_steps": steps})
        await _maybe_notify_step_file_diff(websocket, run_id, step)

    async def emit_todos(todos: list[dict[str, Any]]) -> None:
        nonlocal state
        state = _merge_patch(state, {"agent_todos": list(todos)})
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, {"agent_todos": list(todos)})

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
            emit_todos=emit_todos,
            emit_verification=emit_verification,
            emit_diff_summary=emit_diff_summary,
            tool_steps_sink=tool_steps_sink,
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
        "pending_tool_steps": [],
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

async def _send_file_changed(
    websocket: WebSocket,
    run_id: str,
    *,
    node_id: str,
    path: str,
    diff_lines: list[dict[str, Any]],
) -> None:
    envelope = {
        "event": "file_changed",
        "data": {
            "run_id": run_id,
            "node_id": node_id,
            "source": "orchestrator",
            "level": "info",
            "message": f"Workspace file changed: {path}",
            "path": path,
            "diff_lines": diff_lines,
            "timestamp": _iso_timestamp(),
        },
    }
    await websocket.send_text(json.dumps(envelope))

async def _notify_workspace_files_changed(
    websocket: WebSocket,
    run_id: str,
    paths: list[str],
    *,
    node_id: str = "",
    path_diffs: dict[str, list[dict[str, Any]]] | None = None,
) -> None:
    """Push Changes-panel updates. Prefer edit-hunk diffs when provided (D6)."""
    from src.builtin_tools import enrich_diff_file_entry

    for path in paths:
        rel = str(path).strip()
        if not rel:
            continue
        diffs: list[dict[str, Any]] = []
        if path_diffs and rel in path_diffs:
            diffs = list(path_diffs[rel] or [])
        if not diffs:
            entry = enrich_diff_file_entry({"path": rel})
            diffs = list(entry.get("diffs") or [])
        if not diffs:
            diffs = [{"lineNum": 1, "type": "addition", "text": "(updated via MCP)"}]
        await _send_file_changed(
            websocket,
            run_id,
            node_id=node_id,
            path=rel,
            diff_lines=diffs,
        )


def _path_diffs_from_tool_steps(
    sealed_steps: list[dict[str, Any]] | None,
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for step in sealed_steps or []:
        if not isinstance(step, dict):
            continue
        file_diff = step.get("fileDiff")
        if not isinstance(file_diff, dict):
            continue
        rel = str(file_diff.get("path") or "").strip()
        if not rel:
            continue
        diffs = file_diff.get("diffs")
        if isinstance(diffs, list) and diffs:
            out[rel] = [dict(d) for d in diffs if isinstance(d, dict)]
    return out



async def _maybe_notify_step_file_diff(
    websocket: WebSocket,
    run_id: str,
    step: dict[str, Any],
    *,
    node_id: str = "",
) -> None:
    """Live-push Changes panel using the same hunk as the Chat Diff card."""
    file_diff = step.get("fileDiff") if isinstance(step, dict) else None
    if not isinstance(file_diff, dict):
        return
    path = str(file_diff.get("path") or "").strip()
    if not path:
        return
    raw_diffs = file_diff.get("diffs")
    diffs = [dict(d) for d in raw_diffs if isinstance(d, dict)] if isinstance(raw_diffs, list) else []
    await _notify_workspace_files_changed(
        websocket,
        run_id,
        [path],
        node_id=node_id,
        path_diffs={path: diffs},
    )


async def _send_validation_result(
    websocket: WebSocket,
    run_id: str,
    *,
    node_id: str,
    passed: bool,
    message: str,
) -> None:
    envelope = {
        "event": "validation_result",
        "data": {
            "run_id": run_id,
            "node_id": node_id,
            "source": "orchestrator",
            "level": "error" if not passed else "info",
            "passed": passed,
            "message": message,
            "timestamp": _iso_timestamp(),
        },
    }
    await websocket.send_text(json.dumps(envelope))

async def _send_log_event(
    websocket: WebSocket,
    run_id: str,
    line: str,
    *,
    node_id: str,
    level: str = "info",
) -> None:
    stamped = stamp_log_line(line)
    envelope = {
        "event": "log",
        "data": {
            "run_id": run_id,
            "node_id": node_id,
            "source": "orchestrator",
            "level": level,
            "message": stamped,
            "timestamp": _iso_timestamp(),
        },
    }
    await websocket.send_text(json.dumps(envelope))

class ShellSnapshotUpdateRequest(BaseModel):
    task_summary: str = ""
    open_todos: list[str] = Field(default_factory=list)
    cwd: str | None = None
    cli_session_id: str | None = None

def _workspace_http_error(exc: WorkspaceError) -> HTTPException:
    return HTTPException(status_code=403, detail={"message": str(exc)})

def _build_agent_prompt_skeleton_fallback(name: str, description: str) -> str:
    agent_name = name.strip() or "Custom Agent"
    mission = description.strip() or "Define your core execution task here."
    return (
        f"# {agent_name}\n\n"
        f"You are **{agent_name}**, an operational AI agent in the Clutch workspace.\n\n"
        f"## Mission\n{mission}\n\n"
        "## Operating Principles\n"
        "- Stay focused on the assigned task.\n"
        "- Surface blockers clearly before proceeding.\n"
        "- Prefer actionable outputs over vague summaries.\n\n"
        "## Constraints\n"
        "- Follow workspace conventions and user instructions.\n"
        "- Ask for clarification when requirements are ambiguous."
    )

def _extract_llm_text(result: object) -> str:
    if isinstance(result, dict):
        content = result.get("content")
        return str(content).strip() if content else ""
    return str(result).strip()

async def _async_handoff_summarization_task(
    run_id: str,
    websocket: WebSocket,
    workspace_path: str,
    sources: list[str],
    target: str,
    task: str,
    prompt: str,
    file_refs: list[str] | None,
    dispatch_history: list[dict[str, object]] | None,
    lane_transcripts: list[dict[str, object]] | None,
    custom_file_name: str,
    entry_id: str,
    chat_messages: list[dict[str, object]] | None = None,
):
    try:
        from src.interactive_pty_runtime import interactive_pty_manager, configured_cli_binaries
        from src.handoff_summarizer import find_recent_temp_handoff_file, strip_yaml_frontmatter

        HANDOFF_INJECTION_PROMPT = (
            "[System: Please generate a handoff summary file of our current conversation. "
            "Save it to the OS temporary directory as a markdown file starting with 'handoff-'. "
            "You can use your handoff skill or write it directly. "
            "Print the exact path once saved.]"
        )

        agent_handoff_summary = None
        state = _run_states.get(run_id)
        if state:
            lanes = state.get("pty_lanes") or []
            cli_binaries = configured_cli_binaries()
            injected_any = False
            for source_name in sources:
                target_lane = None
                for lane in lanes:
                    if str(lane.get("configured_agent_name") or "").lower() == source_name.lower():
                        target_lane = lane
                        break
                if not target_lane:
                    for lane in lanes:
                        agent_type = str(lane.get("agent_type") or "").lower()
                        clean_type = agent_type.replace("-cli", "")
                        if clean_type == source_name.lower() or source_name.lower() in clean_type:
                            target_lane = lane
                            break
                if target_lane:
                    agent_type = target_lane.get("agent_type")
                    is_cli_agent = (
                        agent_type in ["claude-cli", "opencode-cli", "mimo-cli", "codex-cli"]
                        or source_name.lower() in cli_binaries
                    )
                    if is_cli_agent:
                        lane_id = target_lane.get("lane_id")
                        session_key = f"{run_id}::{lane_id}"
                        session = interactive_pty_manager.get(session_key)
                        if session and session.alive():
                            try:
                                # Ensure we clear any half-typed commands, write prompt, and execute with \r
                                session.write_input("\r")
                                await asyncio.sleep(0.15)
                                session.write_input(HANDOFF_INJECTION_PROMPT)
                                await asyncio.sleep(0.15)
                                session.write_input("\r")
                                injected_any = True
                            except Exception as e:
                                logger.warning("Failed to inject handoff prompt into session %s: %s", session_key, e)

            if injected_any:
                # Poll for the newly generated handoff file (up to 30.0s to accommodate slower LLM thought/write cycles)
                recent_file_path = None
                for _ in range(30):
                    recent_file_path = find_recent_temp_handoff_file(max_age_seconds=45.0)
                    if recent_file_path:
                        break
                    await asyncio.sleep(1.0)

                if recent_file_path:
                    try:
                        from pathlib import Path
                        p = Path(recent_file_path)
                        raw_content = p.read_text(encoding="utf-8", errors="replace")
                        agent_handoff_summary = strip_yaml_frontmatter(raw_content)
                        p.unlink(missing_ok=True)
                    except Exception as exc:
                        logger.warning("Failed to process temp handoff file %s: %s", recent_file_path, exc)

        from src.handoff_writer import write_handoff_markdown
        def do_write():
            return write_handoff_markdown(
                workspace_path,
                sources=sources,
                target=target,
                task=task,
                prompt=prompt,
                file_refs=file_refs,
                dispatch_history=dispatch_history,
                lane_transcripts=lane_transcripts,
                chat_messages=chat_messages,
                agent_handoff_summary=agent_handoff_summary,
                skip_llm_summary=False,
                custom_file_name=custom_file_name,
            )
        
        await asyncio.to_thread(do_write)
        
        state = _run_states.get(run_id)
        if state:
            log = [dict(e) for e in (state.get("dispatch_log") or [])]
            updated = False
            for entry in log:
                if entry.get("id") == entry_id:
                    if entry.get("step_status") == "generating_handoff":
                        entry["step_status"] = "opening_terminal"
                        updated = True
                    break
            if updated:
                from src.terminal_orchestra import transition_handoff_layout
                new_lanes = transition_handoff_layout(state, sources, target)
                patch = {"dispatch_log": log, "pty_lanes": new_lanes}
                state = _merge_patch(state, patch)
                _run_states[run_id] = state
                _commit_run_state(run_id, state)
                try:
                    await _notify_run_state(websocket, run_id, state, patch)
                except Exception as ws_exc:
                    logger.warning("Failed to notify ws in async handoff: %s", ws_exc)
    except Exception as exc:
        logger.exception("Async handoff summarization failed: %s", exc)
        state = _run_states.get(run_id)
        if state:
            log = [dict(e) for e in (state.get("dispatch_log") or [])]
            updated = False
            for entry in log:
                if entry.get("id") == entry_id:
                    if entry.get("step_status") == "generating_handoff":
                        entry["step_status"] = "opening_terminal"
                        updated = True
                    break
            if updated:
                from src.terminal_orchestra import transition_handoff_layout
                new_lanes = transition_handoff_layout(state, sources, target)
                patch = {"dispatch_log": log, "pty_lanes": new_lanes}
                state = _merge_patch(state, patch)
                _run_states[run_id] = state
                _commit_run_state(run_id, state)
                try:
                    await _notify_run_state(websocket, run_id, state, patch)
                except Exception as ws_exc:
                    logger.warning("Failed to notify ws in async handoff error: %s", ws_exc)

async def ws_run(websocket: WebSocket, run_id: str) -> None:
    if auth_required():
        ws_token = websocket.query_params.get("token")
        if not validate_token(ws_token):
            await websocket.close(code=4401, reason="Unauthorized")
            return
    await websocket.accept()
    from src.plain_chat_pool_queue import register_plain_chat_ws, unregister_plain_chat_ws
    from src.run_state_store import sync_run_state_from_disk

    register_plain_chat_ws(run_id, websocket)
    state = sync_run_state_from_disk(run_id, _get_or_create_run(run_id))
    _run_states[run_id] = state
    _setup_run_log_forwarder(run_id)
    from src.run_log_forwarder import get_forwarder

    forwarder = get_forwarder(run_id)
    loop = asyncio.get_running_loop()

    async def ws_log_emit(line: str, node_id: str) -> None:
        await _send_log_event(websocket, run_id, line, node_id=node_id)
        current = _get_or_create_run(run_id)
        await _notify_run_state(
            websocket,
            run_id,
            current,
            {"terminal_logs": list(current["terminal_logs"])},
        )

    async def ws_state_patch_emit(patch: dict[str, Any], status: str) -> None:
        current = _get_or_create_run(run_id)
        await _notify_run_state(websocket, run_id, current, patch)

    async def ws_message_emit(message: dict[str, Any], node_id: str) -> None:
        await _send_message_event(websocket, run_id, message, node_id)

    async def ws_hybrid_execution_emit(
        message_id: str,
        raw_output: str | None,
        output_events: list[dict[str, Any]] | None,
    ) -> None:
        await _send_hybrid_execution_event(
            websocket,
            run_id,
            message_id=message_id,
            raw_output=raw_output,
            output_events=output_events,
        )

    forwarder.attach_ws(
        loop,
        ws_log_emit,
        ws_state_patch_emit,
        ws_message_emit,
        ws_hybrid_execution_emit,
    )

    logger.info(
        "WebSocket connected",
        extra={
            "run_id": run_id,
            "node_id": state["active_node_id"],
            "source": "orchestrator",
            "level": "info",
            "message": "client connected",
            "timestamp": _iso_timestamp(),
        },
    )

    await _send_state_patch(websocket, run_id, dict(state))
    if state["status"] == "awaiting_human":
        await _send_validation_result(
            websocket,
            run_id,
            node_id=state["active_node_id"],
            passed=False,
            message=tr("Evaluator checks failed, waiting for human approval.", "Evaluator 检查未通过，等待人工审批。"),
        )
        await _send_human_required(
            websocket,
            run_id,
            node_id=state["active_node_id"],
            prompt=tr("Checks failed, waiting for human confirmation.", "检查未通过，等待人工确认。"),
        )
    if _is_terminal_status(state["status"]):
        await _send_run_completed(websocket, run_id, state)

    ws_loop = asyncio.get_running_loop()
    from src.hybrid_concurrency import plain_chat_turn_in_progress
    from src.runtime_config import runtime_mode

    plain_chat_task: asyncio.Task[ClutchState] | None = None
    plain_chat_queue: list[dict[str, str | None]] = []

    async def _start_plain_chat_turn(
        text: str,
        agent_id: str | None,
        session_model_id: str | None,
        client_message_id: str | None = None,
    ) -> None:
        nonlocal plain_chat_task, state
        if plain_chat_task is not None and not plain_chat_task.done():
            return
        state = await _persist_plain_chat_user_message(
            websocket,
            run_id,
            state,
            text,
            agent_id=agent_id,
            client_message_id=client_message_id,
        )
        plain_chat_task = asyncio.create_task(
            _handle_plain_chat(
                websocket,
                run_id,
                state,
                text,
                agent_id=agent_id,
                session_model_id=session_model_id,
                client_message_id=client_message_id,
                user_persisted=True,
            )
        )
        plain_chat_task.add_done_callback(_plain_chat_done)

    async def _enqueue_plain_chat(
        text: str,
        agent_id: str | None,
        session_model_id: str | None,
        client_message_id: str | None = None,
    ) -> None:
        nonlocal state
        plain_chat_queue.append(
            {
                "text": text,
                "agent_id": agent_id,
                "session_model_id": session_model_id,
                "client_message_id": client_message_id,
            }
        )
        stripped = text.strip()
        client_id = (client_message_id or "").strip()
        user_message = _chat_message(
            "User",
            text,
            msg_id=client_id or f"user_{uuid.uuid4().hex[:8]}",
        )
        messages = list(state["messages"])
        already_has_client_id = bool(
            client_id and any(str(item.get("id", "")) == client_id for item in messages)
        )
        user_message_added = not already_has_client_id and not (
            messages
            and messages[-1].get("agent") == "User"
            and str(messages[-1].get("text", "")).strip() == stripped
        )
        if user_message_added:
            messages = messages + [user_message]
        log_line = stamp_log_line(
            tagged(
                TAG_WORKFLOW,
                f"[HYBRID] queued plain chat ({len(plain_chat_queue)} pending)",
            )
        )
        logs = list(state["terminal_logs"]) + [log_line]
        patch: dict[str, Any] = {
            "messages": messages,
            "terminal_logs": logs,
            "shell_session_status": "ready",
            "status": "running",
        }
        state = _merge_patch(state, patch)
        _commit_run_state(run_id, state)
        if user_message_added:
            _touch_session(run_id, title=text.strip()[:80] or "New session", status=state["status"])
        if user_message_added:
            await _send_message_event(websocket, run_id, user_message, "")
        await _send_log_event(websocket, run_id, log_line, node_id="")
        await _notify_run_state(websocket, run_id, state, patch)

    async def _drain_plain_chat_queue() -> None:
        if not plain_chat_queue or (plain_chat_task is not None and not plain_chat_task.done()):
            return
        if plain_chat_turn_in_progress(
            plain_chat_task_done=True,
            state=state,
            hybrid_runtime=runtime_mode() == "hybrid",
        ):
            ws_loop.call_later(0.5, lambda: ws_loop.create_task(_drain_plain_chat_queue()))
            return
        item = plain_chat_queue.pop(0)
        await _start_plain_chat_turn(
            str(item["text"]),
            item.get("agent_id"),
            item.get("session_model_id"),
            item.get("client_message_id"),
        )

    def _plain_chat_done(task: asyncio.Task[ClutchState]) -> None:
        nonlocal plain_chat_task, state
        if plain_chat_task is not task:
            return
        plain_chat_task = None
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.exception("plain chat task failed run_id=%s", run_id, exc_info=exc)
            loop = ws_loop
            loop.create_task(_recover_stuck_plain_chat(run_id))
            return
        try:
            state = task.result()
        except Exception:
            logger.exception("plain chat task result failed run_id=%s", run_id)
        loop = ws_loop
        loop.create_task(_drain_plain_chat_queue())

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"raw": raw}

            logger.info(
                "WebSocket message received",
                extra={
                    "run_id": run_id,
                    "node_id": state["active_node_id"],
                    "source": "orchestrator",
                    "level": "info",
                    "message": raw,
                    "timestamp": _iso_timestamp(),
                },
            )

            patch: dict[str, Any] = {}
            if isinstance(payload, dict) and payload.get("text") and not payload.get("action"):
                text = str(payload["text"])
                agent_id = str(payload.get("agent_id", "")).strip() or None
                session_model_id = str(payload.get("model_id", "")).strip() or None
                client_message_id = str(payload.get("client_message_id", "")).strip() or None
                if state.get("workflow_id"):
                    from src.flow_refine import is_workflow_refine_eligible, refine_triggered_by_message

                    status = str(state.get("status") or "")
                    session = _run_sessions.get(run_id)
                    workflow = session.workflow if session else None
                    if not workflow:
                        try:
                            workflow, _ = resolve_workflow(str(state["workflow_id"]))
                        except Exception:
                            workflow = None
                    if is_workflow_refine_eligible(state) and refine_triggered_by_message(
                        text,
                        status=status,
                        workflow=workflow,
                    ):
                        state = await _handle_flow_refine_message(
                            websocket, run_id, state, text, agent_id
                        )
                    elif status == "refining":
                        state = await _handle_flow_refine_message(
                            websocket, run_id, state, text, agent_id
                        )
                    else:
                        state = await _handle_workflow_chat_message(
                            websocket, run_id, state, text, agent_id
                        )
                elif plain_chat_turn_in_progress(
                    plain_chat_task_done=plain_chat_task is None or plain_chat_task.done(),
                    state=state,
                    hybrid_runtime=runtime_mode() == "hybrid",
                ):
                    await _enqueue_plain_chat(text, agent_id, session_model_id, client_message_id)
                else:
                    await _start_plain_chat_turn(text, agent_id, session_model_id, client_message_id)
            elif isinstance(payload, dict) and payload.get("action") == "human_decision":
                decision = str(payload.get("decision", "approve"))
                from src.mcp_pending import get_pending

                if get_pending(run_id) and not state.get("workflow_id"):
                    instructions = str(payload.get("instructions", ""))
                    state = await _handle_plain_chat_mcp_decision(
                        websocket, run_id, state, decision, instructions
                    )
                else:
                    instructions = str(payload.get("instructions", ""))
                    node_id = state["active_node_id"]

                    state, patch, supervisor_message, log_line = await asyncio.to_thread(
                        _apply_human_decision,
                        run_id,
                        decision,
                        instructions,
                    )

                    await _send_message_event(websocket, run_id, supervisor_message, node_id)
                    await _notify_run_state(websocket, run_id, state, patch)
                    if state["status"] == "awaiting_human":
                        await _send_validation_result(
                            websocket,
                            run_id,
                            node_id=state["active_node_id"],
                            passed=False,
                            message=tr("Evaluator checks failed, waiting for human approval.", "Evaluator 检查未通过，等待人工审批。"),
                        )
                        await _send_human_required(
                            websocket,
                            run_id,
                            node_id=state["active_node_id"],
                            prompt=tr("Checks failed, waiting for human confirmation.", "检查未通过，等待人工确认。"),
                        )
            elif isinstance(payload, dict) and payload.get("action") == "stop_run":
                if not state.get("workflow_id"):
                    plain_chat_queue.clear()
                    await asyncio.to_thread(_interrupt_plain_chat_shell, run_id)
                    if plain_chat_task is not None and not plain_chat_task.done():
                        plain_chat_task.cancel()
                    plain_chat_task = None
                    state = await _apply_plain_chat_stop(websocket, run_id, state)
                else:
                    await asyncio.to_thread(_interrupt_workflow_run, run_id)
                    session = _run_sessions.get(run_id)
                    if session:
                        state = _apply_workflow_refining_pause(run_id, session, prepend_log=False)
                        await _send_log_event(
                            websocket,
                            run_id,
                            state["terminal_logs"][-1],
                            node_id=state.get("active_node_id", ""),
                        )
                        await _notify_run_state(
                            websocket,
                            run_id,
                            state,
                            {
                                "status": "refining",
                                "refining_node_id": state.get("refining_node_id", ""),
                                "terminal_logs": state["terminal_logs"],
                            },
                        )
                    else:
                        logs = list(state["terminal_logs"])
                        log_line = stamp_log_line(
                            tagged(TAG_WORKFLOW, "Run stopped by supervisor — entering refine mode.")
                        )
                        logs.append(log_line)
                        patch = {
                            "status": "refining",
                            "refining_node_id": state.get("active_node_id", ""),
                            "terminal_logs": logs,
                        }
                        state = _merge_patch(state, patch)
                        _commit_run_state(run_id, state)
                        _touch_session(run_id, status="refining")
                        await _send_log_event(
                            websocket, run_id, log_line, node_id=state["active_node_id"]
                        )
                        await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "pty_attach":
                from src.interactive_pty_runtime import InteractivePtyError, interactive_pty_manager
                from src.terminal_orchestra import (
                    _ensure_lane_cli_session_id,
                    ensure_primary_lane,
                    normalize_lane_id,
                    pty_session_key,
                )
                from src.workspace import active_workspace_issue, get_workspace

                cli_tool = str(payload.get("cli_tool", "claude-cli")).strip() or "claude-cli"
                lane_id = normalize_lane_id(str(payload.get("lane_id", "primary")), state)
                workspace_issue = active_workspace_issue()
                workspace = get_workspace()
                workspace_path = str(workspace.get("workspace_path", "")).strip() if workspace else ""
                orch_patch = ensure_primary_lane(state, cli_tool=cli_tool)
                if orch_patch:
                    state = _merge_patch(state, orch_patch)
                    _commit_run_state(run_id, state)
                    await _notify_run_state(websocket, run_id, state, orch_patch)
                    lane_id = normalize_lane_id(lane_id, state)
                lane_cli_session_id: str | None = None
                ollama_model: str | None = None
                configured_agent_id = str(payload.get("configured_agent_id") or "").strip()
                if configured_agent_id:
                    from src.agent_storage import get_agent_by_id

                    agent = get_agent_by_id(configured_agent_id)
                    if agent:
                        tag = str(agent.get("ollamaModel", "")).strip()
                        if tag:
                            ollama_model = tag
                for lane in state.get("pty_lanes") or []:
                    if isinstance(lane, dict) and str(lane.get("lane_id") or "") == lane_id:
                        lane_cli_session_id = _ensure_lane_cli_session_id(lane)
                        _commit_run_state(run_id, state)
                        if cli_tool in {"ollama-cli", "ollama"} and not ollama_model:
                            lane_cfg_id = str(lane.get("configured_agent_id") or "").strip()
                            if lane_cfg_id:
                                from src.agent_storage import get_agent_by_id

                                agent = get_agent_by_id(lane_cfg_id)
                                if agent:
                                    tag = str(agent.get("ollamaModel", "")).strip()
                                    if tag:
                                        ollama_model = tag
                        break
                session_key = pty_session_key(run_id, lane_id)
                if workspace_issue or not workspace_path:
                    await _send_pty_session_status(
                        websocket,
                        run_id,
                        "blocked",
                        detail=workspace_issue or "No workspace authorized for interactive PTY",
                        lane_id=lane_id,
                    )
                else:
                    try:
                        session = await asyncio.to_thread(
                            interactive_pty_manager.attach,
                            session_key,
                            workspace_path=workspace_path,
                            cli_tool=cli_tool,
                            cli_session_id=lane_cli_session_id,
                            ollama_model=ollama_model,
                        )
                        await _send_pty_session_status(
                            websocket,
                            run_id,
                            session.status.value,
                            detail="Interactive PTY attached",
                            lane_id=lane_id,
                        )
                    except (InteractivePtyError, OSError) as exc:
                        await _send_pty_session_status(
                            websocket,
                            run_id,
                            "blocked",
                            detail=str(exc),
                            lane_id=lane_id,
                        )
                    except Exception as exc:
                        await _send_pty_session_status(
                            websocket,
                            run_id,
                            "blocked",
                            detail=str(exc),
                            lane_id=lane_id,
                        )
            elif isinstance(payload, dict) and payload.get("action") == "pty_detach":
                from src.interactive_pty_runtime import interactive_pty_manager
                from src.terminal_orchestra import normalize_lane_id, pty_session_key

                lane_id = normalize_lane_id(str(payload.get("lane_id", "primary")), state)
                await asyncio.to_thread(interactive_pty_manager.detach, pty_session_key(run_id, lane_id))
                await _send_pty_session_status(
                    websocket,
                    run_id,
                    "detached",
                    detail="Interactive PTY detached",
                    lane_id=lane_id,
                )
            elif isinstance(payload, dict) and payload.get("action") == "pty_input":
                from src.interactive_pty_runtime import InteractivePtyError, interactive_pty_manager
                from src.terminal_orchestra import normalize_lane_id, pty_session_key

                data = str(payload.get("data", ""))
                lane_id = normalize_lane_id(str(payload.get("lane_id", "primary")), state)
                if data:
                    try:
                        await asyncio.to_thread(
                            interactive_pty_manager.write_input,
                            pty_session_key(run_id, lane_id),
                            data,
                        )
                    except InteractivePtyError as exc:
                        await _send_pty_session_status(
                            websocket,
                            run_id,
                            "blocked",
                            detail=str(exc),
                            lane_id=lane_id,
                        )
            elif isinstance(payload, dict) and payload.get("action") == "pty_resize":
                from src.interactive_pty_runtime import interactive_pty_manager
                from src.terminal_orchestra import normalize_lane_id, pty_session_key

                cols = int(payload.get("cols", 80))
                rows = int(payload.get("rows", 24))
                lane_id = normalize_lane_id(str(payload.get("lane_id", "primary")), state)
                await asyncio.to_thread(
                    interactive_pty_manager.resize,
                    pty_session_key(run_id, lane_id),
                    cols,
                    rows,
                )
            elif isinstance(payload, dict) and payload.get("action") == "dispatch_preview":
                from src.terminal_orchestra import preview_dispatch, serialize_preview

                text = str(payload.get("text", "")).strip()
                preview = preview_dispatch(state, text)
                if preview is None:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "event": "dispatch_preview",
                                "data": {
                                    "run_id": run_id,
                                    "ok": False,
                                    "error": "输入需包含 @目标 Agent",
                                },
                            }
                        )
                    )
                else:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "event": "dispatch_preview",
                                "data": {
                                    "run_id": run_id,
                                    "ok": True,
                                    "preview": serialize_preview(preview),
                                },
                            }
                        )
                    )
            elif isinstance(payload, dict) and payload.get("action") == "dispatch_confirm":
                from src.terminal_orchestra import confirm_dispatch, preview_dispatch, serialize_preview
                from src.workspace import get_workspace

                text = str(payload.get("text", "")).strip()
                active_chips = payload.get("active_sources")
                chip_list = (
                    [str(x) for x in active_chips]
                    if isinstance(active_chips, list)
                    else None
                )
                preview = preview_dispatch(state, text)
                if preview is None:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "event": "dispatch_error",
                                "data": {"run_id": run_id, "error": "无法解析派发"},
                            }
                        )
                    )
                else:
                    workspace = get_workspace()
                    workspace_path = (
                        str(workspace.get("workspace_path", "")).strip() if workspace else ""
                    )
                    is_handoff = preview.dispatch_mode == "handoff"
                    patch = confirm_dispatch(
                        state,
                        preview=preview,
                        prompt=text,
                        workspace_path=workspace_path or ".",
                        active_chips=chip_list,
                        target_configured_agent_id=str(
                            payload.get("target_configured_agent_id") or ""
                        ),
                        target_configured_agent_name=str(
                            payload.get("target_configured_agent_name") or ""
                        ),
                        lane_transcripts=(
                            payload.get("lane_transcripts")
                            if isinstance(payload.get("lane_transcripts"), list)
                            else None
                        ),
                        skip_llm_summary=is_handoff,
                    )
                    sessions_to_close = patch.pop("pty_sessions_to_close", [])
                    for session_key in sessions_to_close:
                        await asyncio.to_thread(interactive_pty_manager.close, session_key)
                    state = _merge_patch(state, patch)
                    _commit_run_state(run_id, state)
                    _touch_session(run_id, title=text.strip()[:80] or "New session", status=state["status"])
                    await _notify_run_state(websocket, run_id, state, patch)

                    if is_handoff:
                        dispatch_log = patch.get("dispatch_log", [])
                        added_entry = dispatch_log[-1] if dispatch_log else None
                        if added_entry:
                            entry_id = added_entry["id"]
                            custom_file_name = added_entry["handoff_file"]
                            asyncio.create_task(
                                _async_handoff_summarization_task(
                                    run_id=run_id,
                                    websocket=websocket,
                                    workspace_path=workspace_path or ".",
                                    sources=list(chip_list if chip_list is not None else preview.sources),
                                    target=preview.target,
                                    task=preview.task,
                                    prompt=text,
                                    file_refs=preview.file_refs,
                                    dispatch_history=list(state.get("dispatch_log") or [])[:-1],
                                    lane_transcripts=payload.get("lane_transcripts"),
                                    custom_file_name=custom_file_name,
                                    entry_id=entry_id,
                                    chat_messages=list(state.get("messages") or []),
                                )
                            )
                    if sessions_to_close:
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "event": "pty_sessions_closed",
                                    "data": {"run_id": run_id, "mode": "dispatch"},
                                }
                            )
                        )
                    await websocket.send_text(
                        json.dumps(
                            {
                                "event": "dispatch_confirmed",
                                "data": {
                                    "run_id": run_id,
                                    "preview": serialize_preview(preview),
                                },
                            }
                        )
                    )
            elif isinstance(payload, dict) and payload.get("action") == "lane_focus":
                from src.terminal_orchestra import patch_lane_focus

                lane_id = str(payload.get("lane_id", "")).strip()
                if lane_id:
                    patch = patch_lane_focus(state, lane_id)
                    state = _merge_patch(state, patch)
                    _commit_run_state(run_id, state)
                    await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "lane_collapse":
                from src.terminal_orchestra import patch_lane_collapse

                lane_id = str(payload.get("lane_id", "")).strip()
                collapsed = bool(payload.get("collapsed", True))
                if lane_id:
                    patch = patch_lane_collapse(state, lane_id, collapsed=collapsed)
                    state = _merge_patch(state, patch)
                    _commit_run_state(run_id, state)
                    await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "lane_complete":
                from src.terminal_orchestra import patch_lane_complete

                lane_id = str(payload.get("lane_id", "")).strip()
                if lane_id:
                    patch = patch_lane_complete(state, lane_id)
                    state = _merge_patch(state, patch)
                    _commit_run_state(run_id, state)
                    await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "pty_session_stats":
                from src.interactive_pty_runtime import interactive_pty_manager

                sessions = interactive_pty_manager.list_alive_for_run(run_id, include_system=True)
                await websocket.send_text(
                    json.dumps(
                        {
                            "event": "pty_session_stats",
                            "data": {
                                "run_id": run_id,
                                "total": len(sessions),
                                "sessions": sessions,
                            },
                        }
                    )
                )
            elif isinstance(payload, dict) and payload.get("action") == "pty_close_all":
                from src.interactive_pty_runtime import interactive_pty_manager
                from src.terminal_orchestra import patch_close_terminal_lanes

                patch = patch_close_terminal_lanes(state, keep_lane_id=None)
                for session_key in patch.pop("pty_sessions_to_close", []):
                    await asyncio.to_thread(interactive_pty_manager.close, session_key)
                interactive_pty_manager.close_for_run(run_id)
                state = _merge_patch(state, patch)
                _commit_run_state(run_id, state)
                await _notify_run_state(websocket, run_id, state, patch)
                await websocket.send_text(
                    json.dumps(
                        {
                            "event": "pty_sessions_closed",
                            "data": {"run_id": run_id, "mode": "all"},
                        }
                    )
                )
            elif isinstance(payload, dict) and payload.get("action") == "pty_close_others":
                from src.interactive_pty_runtime import interactive_pty_manager

                keep_raw = payload.get("keep_lane_ids")
                keep_lane_ids: list[str] = []
                if isinstance(keep_raw, list):
                    keep_lane_ids = [str(item).strip() for item in keep_raw if str(item).strip()]
                else:
                    lane_id = str(payload.get("lane_id", "")).strip()
                    if lane_id:
                        keep_lane_ids = [lane_id]
                interactive_pty_manager.close_for_run(run_id, keep_lane_ids=keep_lane_ids)
                await websocket.send_text(
                    json.dumps(
                        {
                            "event": "pty_sessions_closed",
                            "data": {
                                "run_id": run_id,
                                "mode": "others",
                                "keep_lane_ids": keep_lane_ids,
                            },
                        }
                    )
                )
            elif isinstance(payload, dict) and payload.get("action") == "pty_inject_ack":
                patch = {"pending_pty_inject": None}
                log = list(state.get("dispatch_log") or [])
                if log:
                    last_entry = log[-1]
                    if last_entry.get("step_status") and last_entry["step_status"] != "done":
                        last_entry["step_status"] = "done"
                        patch["dispatch_log"] = log
                state = _merge_patch(state, patch)
                _commit_run_state(run_id, state)
                await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "delete_message":
                message_id = str(payload.get("message_id", "")).strip()
                if message_id:
                    state, patch = _apply_delete_message(state, message_id)
                    if patch:
                        _commit_run_state(run_id, state)
                        await _notify_run_state(websocket, run_id, state, patch)
            elif isinstance(payload, dict) and payload.get("action") == "clear_workflow":
                state = _merge_patch(state, {"workflow_id": ""})
                _commit_run_state(run_id, state)
                _touch_session(run_id, workflow_id="")
                if run_id in _run_sessions:
                    del _run_sessions[run_id]
                await _notify_run_state(websocket, run_id, state, {"workflow_id": ""})
            else:
                unknown = _chat_message(
                    "Orchestrator",
                    tr(f"Unrecognized WebSocket payload: {payload!r}", f"未识别的 WebSocket 载荷：{payload!r}"),
                )
                await _send_message_event(
                    websocket, run_id, unknown, state["active_node_id"]
                )

    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected",
            extra={
                "run_id": run_id,
                "node_id": state["active_node_id"],
                "source": "orchestrator",
                "level": "info",
                "message": "client disconnected",
                "timestamp": _iso_timestamp(),
            },
        )
    finally:
        unregister_plain_chat_ws(run_id)
        forwarder.detach_ws()

