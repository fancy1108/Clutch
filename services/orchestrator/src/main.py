"""Clutch orchestration sidecar — M0 skeleton with ClutchState projection."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

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


@asynccontextmanager
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
app = FastAPI(
    title="Clutch Orchestrator",
    version="1.0.0",
    lifespan=_lifespan,
    **(
        {"docs_url": None, "redoc_url": None, "openapi_url": None}
        if _docs_disabled
        else {}
    ),
)

app.add_middleware(
    CORSMiddleware,
    # Sidecar binds 127.0.0.1 only — allow Vite dev + Tauri desktop webview origins.
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|tauri\.localhost)(:\d+)?|tauri://localhost",
    allow_methods=["*"],
    allow_headers=["*"],
)


class SidecarAuthMiddleware(BaseHTTPMiddleware):
    """OSR-08: require Bearer token when CLUTCH_SIDECAR_TOKEN is set."""

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        if path in public_http_paths():
            return await call_next(request)
        if not auth_required():
            return await call_next(request)
        if not validate_bearer(request.headers.get("authorization")):
            return JSONResponse(
                status_code=401,
                content={
                    "detail": {
                        "message": "Unauthorized sidecar request",
                        "message_zh": "未授权的 Sidecar 请求",
                    }
                },
            )
        return await call_next(request)


app.add_middleware(SidecarAuthMiddleware)

_run_states: dict[str, ClutchState] = {}
_run_sessions: dict[str, WorkflowSession] = {}


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
    from src.skills_storage import ensure_default_skill_mounts, load_registry, save_registry
    from src.workspace import get_workspace

    workspace = get_workspace()
    workspace_path = workspace.get("workspace_path") if workspace else None
    ensure_default_skill_mounts(workspace_path=workspace_path)

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

    fields = _session_workspace_fields()
    if not fields:
        return
    patch: dict[str, Any] = {**fields, "run_id": run_id}
    if title is not None:
        patch["title"] = title[:80]
    if workflow_id is not None:
        patch["workflow_id"] = workflow_id
    if status is not None:
        patch["status"] = status
    existing = next((record for record in list_runs() if record.get("run_id") == run_id), None)
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
    _setup_run_log_forwarder(run_id)
    from src.run_log_forwarder import get_forwarder

    forwarder = get_forwarder(run_id)
    state = _get_or_create_run(run_id)
    if decision == "approve":
        supervisor_text = tr("Human approval: Approved, continuing workflow.", "人工审批：已通过，继续执行工作流。")
    elif decision == "reject":
        supervisor_text = tr("Human approval: Rejected, run marked as failed.", "人工审批：已拒绝，运行标记为失败。")
    else:
        supervisor_text = tr(
            f"Human approval: Retry with instructions - {instructions or '(no comments)'}",
            f"人工审批：按指令重试 — {instructions or '（无附加说明）'}"
        )

    supervisor_message = _chat_message("Supervisor", supervisor_text)
    log_line = tagged(TAG_HUMAN, supervisor_text)
    messages = list(state["messages"]) + [supervisor_message]
    forwarder.emit(log_line, node_id=str(state.get("active_node_id", "")))
    state = _get_or_create_run(run_id)
    logs = list(state["terminal_logs"])

    session = _run_sessions.get(run_id)
    if session and state["status"] == "awaiting_human":
        graph_result = resume_workflow(
            session,
            run_id,
            decision,
            instruction=instructions if decision == "retry" else "",
        )
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
    return payload


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
        preview = json.dumps(display_args, ensure_ascii=False)
        if len(preview) > 120:
            preview = preview[:117] + "..."
        detail = f"\n\nArgs: `{preview}`"
    return tr(
        f"MCP tool `{func_name}` requires your approval before execution.{detail}",
        f"MCP 工具 `{func_name}` 需要您批准后才能执行。{detail}",
    )


def _supervisor_gate_messages(
    messages: list[dict[str, Any]],
    func_name: str,
    func_args: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Append a supervisor approval line; skip duplicate approval for the same tool intent."""
    from src.mcp_risk import mcp_approval_key

    approval_key = mcp_approval_key(func_name, func_args)
    text = _mcp_supervisor_approval_text(func_name, func_args)
    if messages:
        last = messages[-1]
        if last.get("agent") == "Supervisor" and last.get("approvalKey") == approval_key:
            return messages, last
    supervisor = _chat_message("Supervisor", text)
    supervisor["approvalKey"] = approval_key
    return [*messages, supervisor], supervisor


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
    hybrid_executions: dict[str, object] | None = None,
) -> list[dict[str, Any]]:
    from src.chat_content import normalize_text_content, user_message_content_for_llm

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
            content = user_message_content_for_llm(text, vision_enabled=vision_enabled)
        else:
            content = text
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
) -> str:
    from src.agent_prompt import compose_agent_system_prompt

    return compose_agent_system_prompt(
        agent,
        model_name=model_name,
        model_api=model_api,
        mcp_servers_bound=mcp_servers_bound,
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

    if uses_clutch_model:
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

    from src.image_router import format_image_reply, generate_image_for_model, is_image_model
    from src.video_router import format_video_reply, generate_video_for_model, is_video_model
    from src.chat_content import extract_image_data_urls

    _plain, attached_images = extract_image_data_urls(text)

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
        )
        if agent
        else None
    )
    if system_prompt_suffix.strip():
        system_prompt = (system_prompt or "") + system_prompt_suffix

    history = _history_for_llm(
        state["messages"],
        vision_enabled=vision_enabled,
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

                def on_log(line: str) -> None:
                    if emit_log:
                        asyncio.run_coroutine_threadsafe(emit_log(line), loop)

                outcome = await asyncio.to_thread(
                    run_mcp_react_loop,
                    messages=chat_messages,
                    servers=mcp_servers,
                    log_prefix="CHAT",
                    on_log=on_log if emit_log else None,
                    pause_on_risky=True,
                    permission_mode=__import__(
                        "src.preferences_storage", fromlist=["load_permission_mode"]
                    ).load_permission_mode(),
                    approved_tool=mcp_approved_tool,
                    approved_keys=get_approved_mcp_keys(state["run_id"]),
                    model_id=resolved_model_id,
                )
                if outcome.approval_required:
                    pause_payload = {
                        **outcome.approval_required,
                        "servers": mcp_servers,
                        "agent_id": resolved_id,
                        "reply_label": reply_label,
                        "engine_label": outcome.engine_label,
                    }
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
                    "[CHAT] No MCP servers bound on this agent — using LLM text only. "
                    "Bind Local Filesystem MCP Server in Agent Manager → Module 4 to enable file tools and approval gates.",
                    "[CHAT] 此 Agent 未绑定 MCP 服务器，仅使用 LLM 文本回复。"
                    "请在 Agent Manager → Module 4 绑定 Local Filesystem MCP Server 以启用文件工具与审批门。",
                )
            ]
            system_prompt = _compose_agent_system_prompt(
                agent,
                model_name=runtime_model_name,
                model_api=model_api,
                mcp_servers_bound=False,
            )
            history = _history_for_llm(
        state["messages"],
        vision_enabled=vision_enabled,
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

        result = await asyncio.to_thread(
            route_engine,
            agent_name=agent_ref,
            prompt=text,
            cwd=cwd,
            history=route_history,
            system_prompt=system_prompt,
            cli_session_id=cli_session_id,
            on_log=on_log if emit_log else None,
            run_id=state.get("run_id"),
            source=chat_source,
            session_model_id=session_model_id,
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
) -> ClutchState:
    from src.mcp_pending import get_pending, pop_pending, record_mcp_approval

    pending = get_pending(run_id)
    if pending is None:
        return state

    if decision != "approve":
        pop_pending(run_id)
        supervisor = _chat_message(
            "Supervisor",
            tr("MCP tool call rejected by supervisor.", "监督者已拒绝 MCP 工具调用。"),
        )
        log_line = tagged(TAG_HUMAN, f"MCP tool {pending.func_name} rejected")
        final_patch: dict[str, Any] = {
            "messages": list(state["messages"]) + [supervisor],
            "terminal_logs": list(state["terminal_logs"]) + [stamp_log_line(log_line)],
            "status": "idle",
            "active_agent": pending.reply_label,
        }
        state = _merge_patch(state, final_patch)
        _commit_run_state(run_id, state)
        await _send_message_event(websocket, run_id, supervisor, "")
        await _send_log_event(websocket, run_id, log_line, node_id="")
        await _notify_run_state(websocket, run_id, state, final_patch)
        return state

    pop_pending(run_id)
    record_mcp_approval(run_id, pending.func_name, pending.func_args)
    state = _merge_patch(state, {"status": "running", "active_agent": pending.reply_label})
    await _notify_run_state(websocket, run_id, state, {"status": "running"})

    streamed_logs = False

    async def emit_log(line: str) -> None:
        nonlocal streamed_logs, state
        streamed_logs = True
        stamped = stamp_log_line(line)
        await _send_log_event(websocket, run_id, stamped, node_id="")
        logs = list(state["terminal_logs"]) + [stamped]
        state = _merge_patch(state, {"terminal_logs": logs})
        _commit_run_state(run_id, state)
        await _notify_run_state(websocket, run_id, state, {"terminal_logs": logs})

    approved_tool = {
        "tool_call_id": pending.tool_call_id,
        "func_name": pending.func_name,
        "func_args": pending.func_args,
        "step_idx": pending.step_idx,
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
        mcp_approved_tool=approved_tool,
        mcp_resume=mcp_resume,
    )

    if mcp_pause:
        from src.mcp_pending import McpPendingApproval, store_pending

        store_pending(
            run_id,
            McpPendingApproval(
                agent_id=pending.agent_id,
                reply_label=model_name,
                chat_messages=list(mcp_pause["chat_messages"]),
                servers=list(mcp_pause["servers"]),
                tool_call_id=str(mcp_pause["tool_call_id"]),
                func_name=str(mcp_pause["func_name"]),
                func_args=dict(mcp_pause.get("func_args") or {}),
                step_idx=int(mcp_pause.get("step_idx", 0)),
                logs=list(route_logs),
            ),
        )
        gate_line = f"[CHAT] Awaiting approval for MCP tool: {mcp_pause['func_name']}"
        pause_messages, supervisor = _supervisor_gate_messages(
            list(state["messages"]),
            str(mcp_pause["func_name"]),
            dict(mcp_pause.get("func_args") or {}),
        )
        pause_patch: dict[str, Any] = {
            "messages": pause_messages,
            "terminal_logs": _append_terminal_logs(
                list(state["terminal_logs"]), route_logs, gate_line, streamed=streamed_logs
            ),
            "status": "awaiting_human",
            "active_agent": pending.reply_label,
        }
        state = _merge_patch(state, pause_patch)
        _commit_run_state(run_id, state)
        if pause_messages[-1] is supervisor:
            await _send_message_event(websocket, run_id, supervisor, "")
        if not streamed_logs:
            for log in route_logs:
                await _send_log_event(websocket, run_id, log, node_id="")
        await _send_log_event(websocket, run_id, gate_line, node_id="")
        await _notify_run_state(websocket, run_id, state, pause_patch)
        await _send_human_required(
            websocket,
            run_id,
            node_id="",
            prompt=tr(
                f"Approve MCP tool call: {mcp_pause['func_name']}",
                f"请审批 MCP 工具调用：{mcp_pause['func_name']}",
            ),
        )
        return state

    reply = _chat_message(
        model_name,
        reply_text,
        runtime_engine=runtime_engine,
        raw_output=raw_output,
        output_events=output_events,
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
        "active_agent": pending.reply_label,
        **_token_patch_turn(state, user_text="", assistant_text=reply_text),
    }
    if shell_recovered:
        final_patch["shell_session_status"] = "recovering"
    elif runtime_engine and "Hybrid" in runtime_engine:
        final_patch["shell_session_status"] = "ready"
    if _cli_session_id:
        from src.state import cli_session_patch
        final_patch.update(cli_session_patch(_cli_session_id, pending.agent_id))
    state = _merge_patch(state, final_patch)
    _commit_run_state(run_id, state)
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
        await _notify_workspace_files_changed(websocket, run_id, files_changed)
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
) -> ClutchState:
    from src.agent_storage import BUILTIN_AGENT_ID, get_agent_by_id
    from src.runtime_config import runtime_mode

    resolved_id = (agent_id or "").strip() or BUILTIN_AGENT_ID
    agent = get_agent_by_id(resolved_id)
    active_agent = str(agent.get("name", "Clutch Agent")) if agent else "Clutch Agent"

    if state["status"] == "running" and runtime_mode() == "hybrid" and not resume_after_pool_queue:
        return state

    stripped = text.strip()
    client_id = (client_message_id or "").strip()
    if not resume_after_pool_queue:
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
            ),
        )
        gate_line = f"[CHAT] Awaiting approval for MCP tool: {mcp_pause['func_name']}"
        pause_messages, supervisor = _supervisor_gate_messages(
            list(state["messages"]),
            str(mcp_pause["func_name"]),
            dict(mcp_pause.get("func_args") or {}),
        )
        pause_logs = _append_terminal_logs(
            list(state["terminal_logs"]), route_logs, gate_line, streamed=streamed_logs
        )
        pause_patch: dict[str, Any] = {
            "messages": pause_messages,
            "terminal_logs": pause_logs,
            "status": "awaiting_human",
            "active_agent": active_agent,
        }
        state = _merge_patch(state, pause_patch)
        _commit_run_state(run_id, state)
        if pause_messages[-1] is supervisor:
            await _send_message_event(websocket, run_id, supervisor, "")
        if not streamed_logs:
            for log in route_logs:
                await _send_log_event(websocket, run_id, log, node_id="")
        await _send_log_event(websocket, run_id, gate_line, node_id="")
        await _notify_run_state(websocket, run_id, state, pause_patch)
        await _send_human_required(
            websocket,
            run_id,
            node_id="",
            prompt=tr(
                f"Approve MCP tool call: {mcp_pause['func_name']}",
                f"请审批 MCP 工具调用：{mcp_pause['func_name']}",
            ),
        )
        return state

    reply = _chat_message(
        model_name,
        reply_text,
        runtime_engine=runtime_engine,
        raw_output=raw_output,
        output_events=output_events,
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
            _notify_workspace_files_changed(websocket, run_id, files_changed),
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

    async def emit_log(line: str) -> None:
        nonlocal streamed_logs, state
        streamed_logs = True
        stamped = stamp_log_line(line)
        logs = list(state["terminal_logs"]) + [stamped]
        state = _merge_patch(state, {"terminal_logs": logs})
        _commit_run_state(run_id, state)
        await _send_log_event(websocket, run_id, stamped, node_id=refining_node_id)
        await _notify_run_state(websocket, run_id, state, {"terminal_logs": logs})

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
            ),
        )
        gate_line = f"[CHAT] Awaiting approval for MCP tool: {mcp_pause['func_name']}"
        pause_messages, supervisor = _supervisor_gate_messages(
            list(state["messages"]),
            str(mcp_pause["func_name"]),
            dict(mcp_pause.get("func_args") or {}),
        )
        pause_logs = _append_terminal_logs(
            list(state["terminal_logs"]), route_logs, gate_line, streamed=streamed_logs
        )
        pause_patch: dict[str, Any] = {
            "messages": pause_messages,
            "terminal_logs": pause_logs,
            "status": "awaiting_human",
            "active_agent": active_agent,
        }
        state = _merge_patch(state, pause_patch)
        _commit_run_state(run_id, state)
        if pause_messages[-1] is supervisor:
            await _send_message_event(websocket, run_id, supervisor, refining_node_id)
        if not streamed_logs:
            for log in route_logs:
                await _send_log_event(websocket, run_id, log, node_id=refining_node_id)
        await _send_log_event(websocket, run_id, gate_line, node_id=refining_node_id)
        await _notify_run_state(websocket, run_id, state, pause_patch)
        return state

    reply = _chat_message(
        model_name,
        reply_text,
        runtime_engine=runtime_engine,
        msg_id=f"agent_{uuid.uuid4().hex[:8]}",
    )
    final_messages = list(state["messages"]) + [reply]
    final_patch: dict[str, Any] = {
        "messages": final_messages,
        "refine_draft_output": reply_text,
        "active_agent": model_name,
        "status": "refining",
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
        await _notify_workspace_files_changed(websocket, run_id, files_changed, node_id=refining_node_id)
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
) -> None:
    for path in paths:
        await _send_file_changed(
            websocket,
            run_id,
            node_id=node_id,
            path=path,
            diff_lines=[{"lineNum": 1, "type": "addition", "text": "(updated via MCP)"}],
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "api_version": "2"}


@app.post("/api/workflows/validate")
async def validate_workflow_endpoint(body: ValidateWorkflowRequest) -> dict[str, str | bool]:
    try:
        if body.workflow is not None:
            validate_workflow(body.workflow)
            workflow_id = str(body.workflow.get("id", ""))
        elif body.workflow_id:
            workflow = load_and_validate_workflow(body.workflow_id)
            workflow_id = workflow["id"]
        else:
            raise WorkflowValidationError(tr("Please provide workflow_id or workflow object", "请提供 workflow_id 或 workflow 对象"), [])
    except WorkflowValidationError as exc:
        raise _validation_http_error(exc) from exc

    return {"valid": True, "workflow_id": workflow_id}


@app.get("/api/workflows/templates")
async def list_workflow_templates() -> dict[str, list[str]]:
    from src.workflow_storage import list_templates

    return {"workflow_ids": list_templates()}


@app.get("/api/workflows/templates/{workflow_id}")
async def get_workflow_template(workflow_id: str) -> dict[str, Any]:
    from src.workflow_storage import get_template

    try:
        workflow = get_template(workflow_id)
    except WorkflowValidationError as exc:
        raise _validation_http_error(exc) from exc
    return {"source": "template", "workflow": workflow}


@app.get("/api/workflows/user")
async def list_user_workflow_ids() -> dict[str, list[str]]:
    from src.workflow_storage import list_user_workflows

    return {"workflow_ids": list_user_workflows()}


@app.get("/api/workflows/user/{workflow_id}")
async def get_user_workflow_endpoint(workflow_id: str) -> dict[str, Any]:
    from src.workflow_storage import get_user_workflow

    try:
        workflow = get_user_workflow(workflow_id)
    except WorkflowValidationError as exc:
        raise _validation_http_error(exc) from exc
    return {"source": "user", "workflow": workflow}


@app.post("/api/workflows/user")
async def save_user_workflow_endpoint(body: SaveUserWorkflowRequest) -> dict[str, str]:
    from src.workflow_storage import save_user_workflow

    try:
        workflow = save_user_workflow(body.workflow)
    except WorkflowValidationError as exc:
        raise _validation_http_error(exc) from exc
    return {"workflow_id": str(workflow["id"]), "status": "saved"}


@app.delete("/api/workflows/user/{workflow_id}")
async def delete_user_workflow_endpoint(workflow_id: str) -> dict[str, str]:
    from src.workflow_storage import delete_user_workflow

    try:
        delete_user_workflow(workflow_id)
    except WorkflowValidationError as exc:
        raise _validation_http_error(exc) from exc
    return {"workflow_id": workflow_id, "status": "deleted"}


@app.get("/api/runs/history")
async def get_run_history(workspace_id: str | None = None) -> dict[str, list[dict[str, Any]]]:
    return {"runs": list_runs(workspace_id=workspace_id)}


@app.post("/api/sessions")
async def create_session_endpoint(body: SessionCreateRequest) -> dict[str, Any]:
    from src.workspace import get_workspace

    workspace = get_workspace()
    if workspace is None:
        raise HTTPException(status_code=400, detail={"message": tr("Please select and authorize a project workspace first", "请先选择并授权一个项目工作区")})
    record = upsert_session(
        {
            "run_id": body.run_id,
            "workspace_id": workspace["id"],
            "workspace_name": workspace["name"],
            "title": body.title[:80] or "New session",
            "workflow_id": body.workflow_id,
            "status": "idle",
            "started_at": _iso_timestamp(),
        }
    )
    return record


class ShellSnapshotUpdateRequest(BaseModel):
    task_summary: str = ""
    open_todos: list[str] = Field(default_factory=list)
    cwd: str | None = None
    cli_session_id: str | None = None


@app.get("/api/shell-snapshots")
async def list_shell_snapshots() -> dict[str, Any]:
    from src.session_snapshot import list_snapshots

    return {"snapshots": list_snapshots()}


@app.get("/api/shell-snapshots/{run_id}")
async def get_shell_snapshot(run_id: str) -> dict[str, Any]:
    from src.session_snapshot import load_snapshot

    snap = load_snapshot(run_id)
    if snap is None:
        raise HTTPException(status_code=404, detail={"message": "Snapshot not found"})
    return snap.to_dict()


@app.put("/api/shell-snapshots/{run_id}")
async def upsert_shell_snapshot(run_id: str, body: ShellSnapshotUpdateRequest) -> dict[str, Any]:
    from src.session_snapshot import SessionSnapshot, load_snapshot, save_snapshot
    from src.workspace import get_workspace

    workspace = get_workspace()
    existing = load_snapshot(run_id)
    workspace_path = ""
    if workspace:
        workspace_path = str(workspace.get("workspace_path", ""))
    elif existing:
        workspace_path = existing.workspace_path

    snap = SessionSnapshot(
        run_id=run_id,
        workspace_path=workspace_path,
        cwd=body.cwd or (existing.cwd if existing else workspace_path),
        task_summary=body.task_summary or (existing.task_summary if existing else ""),
        open_todos=body.open_todos or (existing.open_todos if existing else None),
        cli_session_id=body.cli_session_id or (existing.cli_session_id if existing else None),
    )
    save_snapshot(snap)
    return snap.to_dict()


def _workspace_http_error(exc: WorkspaceError) -> HTTPException:
    return HTTPException(status_code=403, detail={"message": str(exc)})


@app.get("/api/workspaces")
async def list_workspaces_endpoint() -> dict[str, Any]:
    from src.workspace import list_workspaces

    return list_workspaces()


@app.post("/api/workspaces")
async def add_workspace_endpoint(body: WorkspaceRequest) -> dict[str, str]:
    from src.skills_storage import ensure_default_skill_mounts
    from src.workspace import WorkspaceError, add_workspace

    try:
        entry = add_workspace(body.path)
        ensure_default_skill_mounts(workspace_path=entry.get("workspace_path"))
        return entry
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc


@app.post("/api/workspaces/{workspace_id}/activate")
async def activate_workspace_endpoint(workspace_id: str) -> dict[str, str]:
    from src.skills_storage import ensure_default_skill_mounts
    from src.workspace import WorkspaceError, activate_workspace

    try:
        entry = activate_workspace(workspace_id)
        ensure_default_skill_mounts(workspace_path=entry.get("workspace_path"))
        return entry
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc


@app.delete("/api/workspaces/{workspace_id}")
async def remove_workspace_endpoint(workspace_id: str) -> dict[str, str]:
    from src.workspace import WorkspaceError, remove_workspace

    try:
        remove_workspace(workspace_id)
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc
    return {"status": "removed", "workspace_id": workspace_id}


@app.get("/api/repository-groups")
async def list_repository_groups_endpoint() -> dict[str, Any]:
    from src.workspace import list_repository_groups

    return list_repository_groups()


@app.post("/api/repository-groups")
async def create_repository_group_endpoint(body: RepositoryGroupRequest) -> dict[str, Any]:
    from src.workspace import create_repository_group

    try:
        return create_repository_group(body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@app.patch("/api/repository-groups/{group_id}")
async def update_repository_group_endpoint(
    group_id: str, body: RepositoryGroupUpdateRequest
) -> dict[str, Any]:
    from src.workspace import WorkspaceError, update_repository_group

    try:
        return update_repository_group(
            group_id,
            name=body.name,
            collapsed=body.collapsed,
            workspace_ids=body.workspace_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc


@app.delete("/api/repository-groups/{group_id}")
async def delete_repository_group_endpoint(group_id: str) -> dict[str, str]:
    from src.workspace import WorkspaceError, delete_repository_group

    try:
        delete_repository_group(group_id)
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc
    return {"status": "removed", "group_id": group_id}


@app.get("/api/workspace")
async def get_workspace_endpoint() -> dict[str, str]:
    from src.workspace import get_workspace

    info = get_workspace()
    if info is None:
        raise HTTPException(status_code=404, detail={"message": tr("Workspace not authorized yet", "尚未授权工作区")})
    return info


@app.post("/api/workspace")
async def set_workspace_endpoint(body: WorkspaceRequest) -> dict[str, str]:
    from src.skills_storage import ensure_default_skill_mounts
    from src.workspace import WorkspaceError, add_workspace

    try:
        entry = add_workspace(body.path)
        ensure_default_skill_mounts(workspace_path=entry.get("workspace_path"))
        return entry
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc


@app.get("/api/workspace/git")
async def get_workspace_git() -> dict[str, Any]:
    from src.workspace import WorkspaceError, get_git_info

    try:
        return get_git_info()
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc


@app.get("/api/workspace/tree")
async def get_workspace_tree() -> dict[str, Any]:
    from src.workspace import WorkspaceError, list_tree

    try:
        return {"nodes": list_tree()}
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc


@app.get("/api/workspace/file")
async def read_workspace_file(path: str) -> dict[str, str]:
    from src.workspace import WorkspaceError, read_file

    try:
        return {"path": path, "content": read_file(path)}
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc


@app.get("/api/agents")
async def list_agents_endpoint() -> dict[str, list[dict[str, Any]]]:
    from src.agent_storage import list_agents

    return {"agents": list_agents()}


@app.post("/api/agents")
async def save_agents_endpoint(body: AgentsSaveRequest) -> dict[str, str]:
    from src.agent_storage import save_agents

    save_agents(body.agents)
    return {"status": "saved"}


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


@app.post("/api/agents/generate-prompt")
async def generate_agent_prompt_endpoint(body: AgentPromptGenerateRequest) -> dict[str, str]:
    from src.models_config import get_router, is_model_available

    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail={"message": "Agent name is required."})

    description = body.description.strip()
    fallback = _build_agent_prompt_skeleton_fallback(name, description)

    router = get_router()
    model_id = router.active_model_id
    if not is_model_available(router, model_id):
        return {"prompt": fallback, "source": "template"}

    meta_prompt = (
        "You are helping design an AI agent system prompt skeleton.\n"
        f"Agent Name: {name}\n"
        f"Short Description: {description or '(none provided)'}\n\n"
        "Generate a concise system prompt skeleton in markdown with:\n"
        '1. One clear persona line (e.g. "You are a ...")\n'
        "2. Core responsibilities (3-5 bullets)\n"
        "3. Output/constraints section (2-3 bullets)\n\n"
        "Keep it under 20 lines. Output only the prompt text, no preamble or explanation."
    )
    try:
        result = router.complete(meta_prompt, model_id=model_id)
        text = _extract_llm_text(result)
        if not text:
            return {"prompt": fallback, "source": "template"}
        return {"prompt": text, "source": "llm"}
    except Exception:
        return {"prompt": fallback, "source": "template"}


@app.get("/api/skills")
async def get_skills_registry() -> dict[str, Any]:
    return _skills_registry_payload(rescan=True)


@app.post("/api/skills/mount")
async def mount_skills_directory(body: SkillsMountRequest) -> dict[str, Any]:
    from src.skills_storage import load_registry, save_registry

    raw = body.path.strip()
    if not raw:
        raise HTTPException(status_code=400, detail={"message": tr("Path cannot be empty", "路径不能为空")})
    resolved = str(Path(raw).expanduser().resolve())
    data = load_registry()
    mounted = list(data["mounted_directories"])
    if resolved not in mounted:
        mounted.append(resolved)
    save_registry(mounted_directories=mounted)
    return _skills_registry_payload(rescan=True)


@app.post("/api/skills/unmount")
async def unmount_skills_directory(body: SkillsMountRequest) -> dict[str, Any]:
    from src.skills_storage import load_registry, save_registry

    raw = body.path.strip()
    if not raw:
        raise HTTPException(status_code=400, detail={"message": tr("Path cannot be empty", "路径不能为空")})
    resolved = str(Path(raw).expanduser().resolve())
    data = load_registry()
    mounted = [item for item in data["mounted_directories"] if item != resolved]
    skills = [item for item in data["skills"] if item.get("source") != resolved]
    save_registry(mounted_directories=mounted, skills=skills)
    return _skills_registry_payload(rescan=True)


@app.post("/api/skills/toggle")
async def toggle_skill(body: SkillsToggleRequest) -> dict[str, Any]:
    from src.skills_storage import load_registry, save_registry

    data = _skills_registry_payload(rescan=False)
    updated = False
    skills = []
    for item in data["skills"]:
        if item.get("key") == body.key:
            skills.append({**item, "isActiveGlobally": body.is_active})
            updated = True
        else:
            skills.append(item)
    if not updated:
        raise HTTPException(status_code=404, detail={"message": tr("Skill not found", "未找到该 Skill")})
    save_registry(skills=skills)
    return _skills_registry_payload(rescan=False)


@app.get("/api/models/credentials")
async def get_models_credentials() -> dict[str, Any]:
    from src.credentials.claude_code import credential_status
    from src.models_config import get_router

    return credential_status(get_router())


@app.get("/api/models/config")
async def get_models_config(response: Response) -> dict[str, Any]:
    from src.models_config import get_router, serialize_models_config

    response.headers["Cache-Control"] = "no-store"
    return serialize_models_config(get_router())


@app.post("/api/models/config")
async def update_models_config(body: ModelsConfigRequest) -> dict[str, str]:
    from src.adapters.opencode_zen_adapter import ZEN_DEFAULT_MODEL_ID, validate_opencode_zen_save
    from src.models_config import get_router, is_model_available, save_router, sync_local_ollama_models

    router = get_router()
    sync_local_ollama_models(router)
    if body.provider_id == "opencode" and body.api_key is not None:
        key = body.api_key.strip()
        model_id = body.active_model_id
        if not model_id:
            active = router._models.get(router.active_model_id)
            model_id = (
                router.active_model_id
                if active and active.provider_id == "opencode"
                else ZEN_DEFAULT_MODEL_ID
            )
        try:
            validate_opencode_zen_save(key, str(model_id), router)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
        router.set_api_key("opencode", key)
    elif body.provider_id and body.api_key is not None:
        router.set_api_key(body.provider_id, body.api_key.strip())  # type: ignore[arg-type]
    if body.active_model_id:
        if not is_model_available(router, body.active_model_id):
            raise HTTPException(
                status_code=400,
                detail={"message": "Model is not available — configure provider API key first"},
            )
        from src.custom_models import unhide_model_from_list

        unhide_model_from_list(body.active_model_id)
        router.set_active_model(body.active_model_id)
    save_router(router)
    return {"status": "saved", "active_model_id": router.active_model_id}


@app.get("/api/models/credentials/{provider_id}")
async def get_provider_credential(provider_id: str) -> dict[str, Any]:
    from src.credentials.sources import is_clutch_managed_credential
    from src.models_config import get_router

    router = get_router()
    if not is_clutch_managed_credential(provider_id):  # type: ignore[arg-type]
        raise HTTPException(
            status_code=404,
            detail={"message": "No Clutch-managed key for this provider."},
        )
    api_key = router.get_api_key(provider_id)  # type: ignore[arg-type]
    return {"provider_id": provider_id, "configured": bool(api_key), "api_key": api_key or ""}


@app.delete("/api/models/credentials/{provider_id}")
async def delete_provider_credential(provider_id: str) -> dict[str, str]:
    from src.models_config import clear_provider_credential, get_router

    router = get_router()
    try:
        clear_provider_credential(router, provider_id)  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return {"status": "removed", "provider_id": provider_id}


@app.post("/api/models/rehydrate-cc-switch")
async def rehydrate_cc_switch_endpoint() -> dict[str, Any]:
    from src.models_config import get_router, rehydrate_cc_switch_models

    return rehydrate_cc_switch_models(get_router())


@app.get("/api/cli-config/{agent_type}/models")
async def get_cli_config_models(agent_type: str) -> dict[str, Any]:
    from src.cli_agent_config import normalize_cli_agent_type, scan_cli_models
    from src.workspace import get_workspace

    try:
        normalized = normalize_cli_agent_type(agent_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    workspace = get_workspace()
    workspace_path = workspace.get("workspace_path") if workspace else None
    return scan_cli_models(normalized, workspace_path=workspace_path)


@app.get("/api/cli-config/{agent_type}/skills")
async def get_cli_config_skills(agent_type: str) -> dict[str, Any]:
    from src.cli_agent_config import normalize_cli_agent_type, scan_cli_skills
    from src.workspace import get_workspace

    try:
        normalized = normalize_cli_agent_type(agent_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    workspace = get_workspace()
    workspace_path = workspace.get("workspace_path") if workspace else None
    return scan_cli_skills(normalized, workspace_path=workspace_path)


@app.get("/api/cli-config/{agent_type}/mcp")
async def get_cli_config_mcp(agent_type: str) -> dict[str, Any]:
    from src.cli_agent_config import normalize_cli_agent_type, scan_cli_mcp
    from src.workspace import get_workspace

    try:
        normalized = normalize_cli_agent_type(agent_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    workspace = get_workspace()
    workspace_path = workspace.get("workspace_path") if workspace else None
    return scan_cli_mcp(normalized, workspace_path=workspace_path)


@app.post("/api/cli-config/{agent_type}/activate-provider")
async def activate_cli_config_provider(
    agent_type: str,
    body: CliActivateProviderRequest,
) -> dict[str, Any]:
    from src.cli_agent_config import activate_cli_provider, normalize_cli_agent_type

    try:
        normalized = normalize_cli_agent_type(agent_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    result = activate_cli_provider(normalized, body.provider_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail={"message": result.get("message", "activate failed")})
    return result


@app.post("/api/cli-config/install-cc-switch-cli")
async def install_cc_switch_cli_endpoint() -> dict[str, Any]:
    from src.cli_agent_config import install_cc_switch_cli

    result = await asyncio.to_thread(install_cc_switch_cli)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail={"message": result.get("message", "install failed")})
    return result


@app.post("/api/cli-config/prefetch-cc-switch-cli")
async def prefetch_cc_switch_cli_endpoint() -> dict[str, Any]:
    from src.cli_agent_config import prefetch_cc_switch_cli_bundle

    return await asyncio.to_thread(prefetch_cc_switch_cli_bundle)


@app.post("/api/cli-config/{agent_type}/activate-model")
async def activate_cli_config_model(
    agent_type: str,
    body: CliActivateModelRequest,
) -> dict[str, Any]:
    from src.cli_agent_config import activate_cli_model, normalize_cli_agent_type

    try:
        normalized = normalize_cli_agent_type(agent_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    result = activate_cli_model(normalized, body.model_ref)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail={"message": result.get("message", "activate failed")})
    return result


@app.post("/api/models/test")
async def test_models_connection(body: ModelTestRequest) -> dict[str, Any]:
    from src.models_config import get_router, test_model_connection

    return test_model_connection(get_router(), body.model_id)


@app.post("/api/models/custom/image")
async def add_custom_image_model(body: CustomImageModelRequest) -> dict[str, Any]:
    from src.custom_models import add_custom_model
    from src.models_config import get_router, serialize_models_config

    router = get_router()
    try:
        spec = add_custom_model(
            router,
            name=body.name,
            api_model=body.api_model,
            base_url=body.base_url,
            provider_id=body.provider_id,
            model_kind="image",
            image_backend=body.image_backend,
            api_key=body.api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return {
        "status": "created",
        "model_id": spec.id,
        "config": serialize_models_config(router),
    }


@app.post("/api/models/custom/chat")
async def add_custom_chat_model(body: CustomChatModelRequest) -> dict[str, Any]:
    from src.custom_models import add_custom_model
    from src.models_config import get_router, serialize_models_config

    router = get_router()
    try:
        spec = add_custom_model(
            router,
            name=body.name,
            api_model=body.api_model,
            base_url=body.base_url,
            provider_id=body.provider_id,
            model_kind="chat",
            api_key=body.api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return {
        "status": "created",
        "model_id": spec.id,
        "config": serialize_models_config(router),
    }


@app.post("/api/models/custom/video")
async def add_custom_video_model(body: CustomVideoModelRequest) -> dict[str, Any]:
    from src.custom_models import add_custom_model
    from src.models_config import get_router, serialize_models_config

    router = get_router()
    try:
        spec = add_custom_model(
            router,
            name=body.name,
            api_model=body.api_model,
            base_url=body.base_url,
            provider_id=body.provider_id,
            model_kind="video",
            video_backend=body.video_backend or "agnes",
            api_key=body.api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return {
        "status": "created",
        "model_id": spec.id,
        "config": serialize_models_config(router),
    }


@app.patch("/api/models/custom/{model_id}")
async def update_custom_model_entry(model_id: str, body: CustomModelUpdateRequest) -> dict[str, Any]:
    from src.custom_models import update_custom_model
    from src.models_config import get_router, serialize_models_config

    router = get_router()
    try:
        spec = update_custom_model(
            router,
            model_id,
            name=body.name,
            api_model=body.api_model,
            base_url=body.base_url,
            api_key=body.api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return {
        "status": "updated",
        "model_id": spec.id,
        "config": serialize_models_config(router),
    }


@app.delete("/api/models/custom/{model_id}")
async def delete_custom_image_model(model_id: str) -> dict[str, Any]:
    from src.custom_models import remove_model_from_list
    from src.models_config import get_router, serialize_models_config

    router = get_router()
    try:
        remove_model_from_list(router, model_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return {"status": "deleted", "model_id": model_id, "config": serialize_models_config(router)}


@app.post("/api/models/opencode-zen/list")
async def list_opencode_zen_catalog(_body: OpenCodeZenListRequest) -> dict[str, Any]:
    from src.adapters.opencode_zen_adapter import fetch_opencode_zen_catalog

    try:
        models = fetch_opencode_zen_catalog()
        return {"ok": True, "models": models}
    except Exception as exc:
        return {"ok": False, "models": [], "message": str(exc)}


@app.get("/api/models/ollama")
async def list_local_ollama_models() -> dict[str, Any]:
    import urllib.error
    import shutil
    from pathlib import Path
    try:
        from src.adapters.ollama_adapter import get_ollama_models
        models = get_ollama_models()
        return {"ok": True, "models": models}
    except Exception as exc:
        reason = "unknown"
        inner = exc.__cause__ if hasattr(exc, "__cause__") else None
        if "ConnectionRefusedError" in str(exc) or "connection refused" in str(exc).lower() or (inner and isinstance(inner, urllib.error.URLError)):
            reason = "connection_refused"
            
        app_exists = Path("/Applications/Ollama.app").is_dir() or Path("~/Applications/Ollama.app").expanduser().is_dir()
        binary_exists = shutil.which("ollama") is not None
        
        return {
            "ok": False,
            "models": [],
            "error": str(exc),
            "reason": reason,
            "app_installed": app_exists,
            "binary_installed": binary_exists
        }


@app.post("/api/models/ollama/start")
async def start_ollama_service() -> dict[str, Any]:
    import subprocess
    import shutil
    from pathlib import Path
    
    app_paths = ["/Applications/Ollama.app", str(Path.home() / "Applications/Ollama.app")]
    app_exists = any(Path(p).is_dir() for p in app_paths)
    
    if app_exists:
        try:
            subprocess.Popen(["open", "-a", "Ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"ok": True, "message": "Launching Ollama.app..."}
        except Exception as exc:
            pass
            
    binary = shutil.which("ollama")
    if binary:
        try:
            subprocess.Popen([binary, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return {"ok": True, "message": "Starting `ollama serve` in background..."}
        except Exception as exc:
            return {"ok": False, "error": f"Failed to run `ollama serve`: {exc}"}
            
    return {"ok": False, "error": "Ollama.app not found and `ollama` command not in PATH."}


@app.get("/api/tools/status")
async def tools_status() -> dict[str, list[dict[str, Any]]]:
    from src.tools_status import list_tools_status

    return {"tools": list_tools_status(include_all=True)}


@app.post("/api/tools/auto-configure")
async def auto_configure_tool_endpoint(body: ToolConnectRequest) -> dict[str, Any]:
    from src.tools_status import resolve_tool_binary
    from src.engine_router import CLI_ROUTING_CONFIGS, save_custom_cli_configs, load_custom_cli_configs
    from src.agent_type import AGENT_TYPES, _LEGACY_AI_ENGINE_TO_TYPE

    binary_path = resolve_tool_binary(body.tool_id)
    if not binary_path:
        raise HTTPException(status_code=400, detail={"message": f"Tool {body.tool_id} is not installed on this machine."})

    from src.agent_type import normalize_agent_type
    from src.provider_registry import resolve_provider_spec
    from src.runtime_strategy import RuntimeStrategy

    if resolve_provider_spec(normalize_agent_type(body.tool_id)).runtime_strategy == RuntimeStrategy.HTTP_DAEMON:
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    f"{body.tool_id} uses Clutch's native HTTP integration "
                    "and does not need shell CLI auto-configure."
                ),
            },
        )

    try:
        from src.tools_status import auto_configure_cli_via_llm
        config = auto_configure_cli_via_llm(body.tool_id, binary_path)

        # Determine the right routing key: use the known agent_type if this tool_id maps
        # to one that's already in AGENT_TYPES (e.g. 'agy-cli' -> 'antigravity-cli').
        # Otherwise use tool_id directly. Never use normalize_agent_type() here because
        # it falls back to 'clutch' for unknown IDs, which would corrupt CLI_ROUTING_CONFIGS.
        candidate = _LEGACY_AI_ENGINE_TO_TYPE.get(body.tool_id, body.tool_id)
        agent_type_key = candidate if candidate in AGENT_TYPES else body.tool_id

        custom_configs = load_custom_cli_configs()
        custom_configs[agent_type_key] = config
        save_custom_cli_configs(custom_configs)

        CLI_ROUTING_CONFIGS[agent_type_key] = config

        return {"status": "configured", "config": config}
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": str(exc)}) from exc



@app.post("/api/tools/connect")
async def connect_tool_endpoint(body: ToolConnectRequest) -> dict[str, Any]:
    from src.tools_status import connect_tool

    try:
        return connect_tool(body.tool_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@app.post("/api/tools/disconnect")
async def disconnect_tool_endpoint(body: ToolConnectRequest) -> dict[str, Any]:
    from src.tools_status import disconnect_tool

    try:
        return disconnect_tool(body.tool_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@app.get("/api/mcp/status")
async def mcp_status() -> dict[str, Any]:
    from src.mcp_storage import build_mcp_status_payload

    return await build_mcp_status_payload()


@app.post("/api/mcp/servers/register")
async def register_mcp_server(body: McpRegisterRequest) -> dict[str, Any]:
    from src.mcp_storage import build_mcp_status_payload, register_server

    try:
        register_server(name=body.name, transport=body.transport, endpoint=body.endpoint)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return await build_mcp_status_payload()


@app.post("/api/mcp/servers/remove")
async def remove_mcp_server(body: McpServerIdRequest) -> dict[str, Any]:
    from src.mcp_storage import build_mcp_status_payload, remove_server

    try:
        remove_server(body.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    return await build_mcp_status_payload()


@app.post("/api/mcp/servers/toggle")
async def toggle_mcp_server(body: McpServerIdRequest) -> dict[str, Any]:
    from src.mcp_storage import build_mcp_status_payload, toggle_server

    if body.enabled is None:
        raise HTTPException(status_code=400, detail={"message": tr("enabled field is required", "enabled 字段必填")})
    try:
        toggle_server(body.id, enabled=body.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    return await build_mcp_status_payload()


@app.post("/api/mcp/config/save")
async def save_mcp_config(body: McpSaveConfigRequest) -> dict[str, Any]:
    from src.mcp_storage import build_mcp_status_payload, save_raw_config

    try:
        save_raw_config(body.servers)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return await build_mcp_status_payload()


@app.post("/api/mcp/import/claude")
async def import_claude_mcp() -> dict[str, Any]:
    from src.mcp_storage import build_mcp_status_payload, import_from_claude

    import_from_claude()
    return await build_mcp_status_payload()



@app.get("/api/preferences")
async def get_preferences() -> dict[str, str]:
    from src.preferences_storage import load_preferences

    return load_preferences()


@app.get("/api/preferences/theme")
async def get_theme_preference() -> dict[str, str]:
    from src.preferences_storage import load_preferences

    return load_preferences()


@app.post("/api/preferences/theme")
async def save_theme_preference(body: ThemePreferenceRequest) -> dict[str, str]:
    from src.preferences_storage import save_theme

    try:
        return save_theme(body.theme_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@app.get("/api/preferences/language")
async def get_language_preference() -> dict[str, str]:
    from src.preferences_storage import load_preferences

    prefs = load_preferences()
    return {"active_language": prefs["active_language"]}


@app.post("/api/preferences/language")
async def save_language_preference(body: LanguagePreferenceRequest) -> dict[str, str]:
    from src.preferences_storage import save_language

    try:
        return save_language(body.language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@app.post("/api/preferences/onboarding-complete")
async def complete_onboarding_preference() -> dict[str, str]:
    from src.preferences_storage import save_onboarding_completed

    return save_onboarding_completed()


@app.post("/api/preferences/onboarding-reset")
async def reset_onboarding_preference() -> dict[str, str]:
    from src.preferences_storage import reset_onboarding_completed

    return reset_onboarding_completed()


@app.get("/api/preferences/permission-mode")
async def get_permission_mode() -> dict[str, str]:
    from src.preferences_storage import load_permission_mode

    return {"permission_mode": load_permission_mode()}


@app.post("/api/preferences/permission-mode")
async def save_permission_mode_route(body: PermissionModeRequest) -> dict[str, str]:
    from src.preferences_storage import save_permission_mode

    try:
        return save_permission_mode(body.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@app.post("/api/preferences/font-size")
async def save_font_size_preference(body: FontSizePreferenceRequest) -> dict[str, str]:
    from src.preferences_storage import save_font_size

    try:
        return save_font_size(body.font_size)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@app.post("/api/preferences/avatar")
async def save_avatar_preference(body: AvatarPreferenceRequest) -> dict[str, str]:
    from src.preferences_storage import save_avatar

    try:
        return save_avatar(body.avatar)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@app.post("/api/preferences/name")
async def save_user_name_preference(body: UserNamePreferenceRequest) -> dict[str, str]:
    from src.preferences_storage import save_user_name

    try:
        return save_user_name(body.user_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@app.post("/api/runs/{run_id}/human-decision")
async def human_decision_http(run_id: str, body: HumanDecisionRequest) -> dict[str, Any]:
    state, _patch, _message, _log = await asyncio.to_thread(
        _apply_human_decision,
        run_id,
        body.decision,
        body.instructions,
    )
    return {"run_id": run_id, "status": state["status"], "active_node_id": state["active_node_id"]}


@app.post("/api/runs/{run_id}/reassign")
async def reassign_run(run_id: str, body: ReassignRequest) -> dict[str, str]:
    state = _get_or_create_run(run_id)
    session = _run_sessions.get(run_id)
    if session and state["status"] == "awaiting_human":
        graph_result = resume_workflow(session, run_id, "retry")
        patch = {
            "status": graph_result["status"],
            "active_node_id": graph_result["active_node_id"],
            "active_agent": graph_result["active_agent"],
        }
        state = _merge_patch(state, patch)
        _commit_run_state(run_id, state)
    else:
        patch = {
            "status": "running",
            "active_agent": "Builder",
            "active_node_id": "n1",
        }
        state = _merge_patch(state, patch)
        _commit_run_state(run_id, state)
    logs = list(state["terminal_logs"])
    logs.append(stamp_log_line(f"[USER] Re-assign to Builder: {body.instructions}"))
    logs.append(stamp_log_line(tagged(TAG_WORKFLOW, "Resuming task per supervisor directive.")))
    state = _merge_patch(state, {"terminal_logs": logs})
    _commit_run_state(run_id, state)
    return {"run_id": run_id, "status": state["status"]}


@app.post("/api/runs/start")
async def start_run(body: StartRunRequest) -> dict[str, Any]:
    try:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        state = await asyncio.to_thread(_run_workflow, run_id, body.workflow_id, body.instruction)
    except WorkflowValidationError as exc:
        raise _validation_http_error(exc) from exc

    logger.info(
        "Run started",
        extra={
            "run_id": run_id,
            "node_id": state["active_node_id"],
            "source": "orchestrator",
            "level": "info",
            "message": f"workflow={body.workflow_id}",
            "timestamp": _iso_timestamp(),
        },
    )
    return {
        "run_id": run_id,
        "status": state["status"],
        "state": _serialize_clutch_state(state),
    }


@app.post("/api/runs/{run_id}/start")
async def start_run_on_session(run_id: str, body: StartRunRequest) -> dict[str, Any]:
    try:
        state = await asyncio.to_thread(_run_workflow, run_id, body.workflow_id, body.instruction)
    except WorkflowValidationError as exc:
        raise _validation_http_error(exc) from exc

    logger.info(
        "Session workflow started",
        extra={
            "run_id": run_id,
            "node_id": state["active_node_id"],
            "source": "orchestrator",
            "level": "info",
            "message": f"workflow={body.workflow_id}",
            "timestamp": _iso_timestamp(),
        },
    )
    return {
        "run_id": run_id,
        "status": state["status"],
        "state": _serialize_clutch_state(state),
    }


@app.get("/api/runs/{run_id}/state")
async def get_run_state(run_id: str) -> dict[str, Any]:
    state = _get_or_create_run(run_id)
    return {"run_id": run_id, "state": _serialize_clutch_state(state)}


@app.get("/api/runs/{run_id}/debug")
async def get_run_debug(
    run_id: str,
    logs_limit: int | None = None,
    audit_limit: int | None = None,
) -> dict[str, Any]:
    if not debug_api_enabled():
        raise HTTPException(status_code=404, detail={"message": "Not found"})

    from src.run_debug import build_run_debug_payload

    state = _get_or_create_run(run_id)
    return build_run_debug_payload(
        run_id,
        state,
        logs_limit=logs_limit,
        audit_limit=audit_limit,
    )


@app.delete("/api/runs/{run_id}")
async def delete_run_endpoint(run_id: str) -> dict[str, str]:
    from src.run_history import delete_session
    from src.run_state_store import delete_run_state
    from src.shell_session import get_shell_session_manager

    try:
        get_shell_session_manager().release(run_id)
        delete_session(run_id)
        delete_run_state(run_id)
        if run_id in _run_states:
            del _run_states[run_id]
        if run_id in _run_sessions:
            del _run_sessions[run_id]
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": str(exc)}) from exc
    return {"status": "deleted", "run_id": run_id}


@app.post("/api/runs/{run_id}/stop")
async def stop_run(run_id: str) -> dict[str, str]:
    state = _get_or_create_run(run_id)
    if not state.get("workflow_id"):
        await asyncio.to_thread(_interrupt_plain_chat_shell, run_id)
        logs = list(state["terminal_logs"])
        logs.append(stamp_log_line(tagged(TAG_WORKFLOW, "[HYBRID] Plain chat stopped via HTTP.")))
        patch: dict[str, Any] = {"status": "idle", "terminal_logs": logs}
        from src.runtime_config import runtime_mode

        if runtime_mode() == "hybrid":
            patch["shell_session_status"] = "ready"
        state = _merge_patch(state, patch)
        _commit_run_state(run_id, state)
        _touch_session(run_id, status=state["status"])
        update_run_record(run_id, {"status": "idle", "ended_at": _iso_timestamp()})
        return {"run_id": run_id, "status": state["status"]}
    await asyncio.to_thread(_interrupt_workflow_run, run_id)
    logs = list(state["terminal_logs"])
    logs.append(stamp_log_line(tagged(TAG_WORKFLOW, "Run stopped via HTTP.")))
    state = _merge_patch(state, {"status": "failed", "terminal_logs": logs})
    _commit_run_state(run_id, state)
    _touch_session(run_id, status="failed")
    update_run_record(run_id, {"status": "failed", "ended_at": _iso_timestamp()})
    return {"run_id": run_id, "status": state["status"]}


@app.websocket("/ws/runs/{run_id}")
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
        plain_chat_task = asyncio.create_task(
            _handle_plain_chat(
                websocket,
                run_id,
                state,
                text,
                agent_id=agent_id,
                session_model_id=session_model_id,
                client_message_id=client_message_id,
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
                    state = await _handle_plain_chat_mcp_decision(
                        websocket, run_id, state, decision
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
                from src.terminal_orchestra import ensure_primary_lane, pty_session_key
                from src.workspace import get_workspace

                cli_tool = str(payload.get("cli_tool", "claude-cli")).strip() or "claude-cli"
                lane_id = str(payload.get("lane_id", "primary")).strip() or "primary"
                workspace = get_workspace()
                workspace_path = str(workspace.get("workspace_path", "")).strip() if workspace else ""
                orch_patch = ensure_primary_lane(state, cli_tool=cli_tool)
                if orch_patch:
                    state = _merge_patch(state, orch_patch)
                    _commit_run_state(run_id, state)
                    await _notify_run_state(websocket, run_id, state, orch_patch)
                    if not lane_id or lane_id == "primary":
                        lane_id = str(state.get("focused_lane_id") or "lane_primary")
                session_key = pty_session_key(run_id, lane_id)
                if not workspace_path:
                    await _send_pty_session_status(
                        websocket,
                        run_id,
                        "blocked",
                        detail="No workspace authorized for interactive PTY",
                        lane_id=lane_id,
                    )
                else:
                    try:
                        session = await asyncio.to_thread(
                            interactive_pty_manager.attach,
                            session_key,
                            workspace_path=workspace_path,
                            cli_tool=cli_tool,
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
            elif isinstance(payload, dict) and payload.get("action") == "pty_detach":
                from src.interactive_pty_runtime import interactive_pty_manager
                from src.terminal_orchestra import pty_session_key

                lane_id = str(payload.get("lane_id", "primary")).strip() or "primary"
                if lane_id == "primary" and state.get("focused_lane_id"):
                    lane_id = str(state.get("focused_lane_id"))
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
                from src.terminal_orchestra import pty_session_key

                data = str(payload.get("data", ""))
                lane_id = str(payload.get("lane_id", "primary")).strip() or "primary"
                if lane_id == "primary" and state.get("focused_lane_id"):
                    lane_id = str(state.get("focused_lane_id"))
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
                from src.terminal_orchestra import pty_session_key

                cols = int(payload.get("cols", 80))
                rows = int(payload.get("rows", 24))
                lane_id = str(payload.get("lane_id", "primary")).strip() or "primary"
                if lane_id == "primary" and state.get("focused_lane_id"):
                    lane_id = str(state.get("focused_lane_id"))
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
                    patch = confirm_dispatch(
                        state,
                        preview=preview,
                        prompt=text,
                        workspace_path=workspace_path or ".",
                        active_chips=chip_list,
                    )
                    state = _merge_patch(state, patch)
                    _commit_run_state(run_id, state)
                    await _notify_run_state(websocket, run_id, state, patch)
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
