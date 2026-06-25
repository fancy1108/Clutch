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

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.compiler import WorkflowSession, begin_workflow, resume_workflow
from src.run_history import append_run_record, list_runs, update_run_record, upsert_session
from src.state import ClutchState, initial_state
from src.workspace import WorkspaceError
from src.workflow_storage import resolve_workflow
from src.workflow_validator import WorkflowValidationError, load_and_validate_workflow, validate_workflow
from src.preferences_storage import tr
from src.terminal_logs import TAG_HUMAN, TAG_WORKFLOW, stamp_log_line, tagged

logger = logging.getLogger(__name__)

app = FastAPI(title="Clutch Orchestrator", version="0.0.0")

app.add_middleware(
    CORSMiddleware,
    # Sidecar binds 127.0.0.1 only — allow Vite dev + Tauri desktop webview origins.
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|tauri\.localhost)(:\d+)?|tauri://localhost",
    allow_methods=["*"],
    allow_headers=["*"],
)

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


class ModelTestRequest(BaseModel):
    model_id: str


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



class ThemePreferenceRequest(BaseModel):
    theme_id: str


class LanguagePreferenceRequest(BaseModel):
    language: str


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


def _run_workflow(run_id: str, workflow_id: str, instruction: str) -> ClutchState:
    _setup_run_log_forwarder(run_id)
    from src.run_log_forwarder import get_forwarder

    workflow, _source = resolve_workflow(workflow_id)
    _get_or_create_run(run_id)
    get_forwarder(run_id).emit(
        tagged(TAG_WORKFLOW, f"Starting workflow: {workflow['name']} ({workflow['id']})"),
        node_id="start",
    )
    session, graph_result = begin_workflow(workflow, run_id, instruction=instruction)
    _run_sessions[run_id] = session
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


def _merge_patch(state: ClutchState, patch: dict[str, Any]) -> ClutchState:
    merged = deepcopy(state)
    for key, value in patch.items():
        if key in merged:
            merged[key] = value  # type: ignore[literal-required]
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


_AGENT_AVATARS: dict[str, str] = {
    "Orchestrator": "https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p",
    "Builder": "https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b",
    "Evaluator": "https://lh3.googleusercontent.com/aida-public/AB6AXuCmb7VGaQXE-4sYnIZR3VrcHVAPhv4Px14kMlkayJj8kVm8htTWITmPi26wsj8P6B9RrqykIWj81S2ilmGR0e8cXhA1gjc3U-Nw0DsgHV3HvVmBskuoUksIt6YM6Z3ORjFtRhBphqAXxRKf9ke-zYcPs0TcEFKxw_bwGXSDiAKV5CL7kZf9i6lSZDe91ccUNjaAIsgTMKEEvYc7bZpXYz3D5dClulRwbNru5SZB-1E5FM0A2qMPs-IAfiR8OB1-cUvFh3WYKx9qlGgN",
    "Supervisor": "",
    "User": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=100",
}


def _chat_time() -> str:
    return datetime.now().strftime("%H:%M")


def _chat_message(
    agent: str,
    text: str,
    *,
    status: str | None = None,
    msg_id: str | None = None,
    runtime_engine: str | None = None,
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
    return payload


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


def _history_for_llm(messages: list[dict[str, object]]) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []
    for message in messages:
        agent = str(message.get("agent", ""))
        text = str(message.get("text", "")).strip()
        if not text:
            continue
        role = "user" if agent == "User" else "assistant"
        history.append({"role": role, "content": text})
    return history


def _uses_configured_llm(agent: dict[str, Any] | None) -> bool:
    from src.engine_router import _normalize_engine_type

    if not agent:
        return True
    return _normalize_engine_type(str(agent.get("aiEngine", ""))) != "Claude Code (Local CLI)"


def _compose_agent_system_prompt(
    agent: dict[str, Any],
    *,
    model_name: str,
    model_api: str,
    mcp_servers_bound: bool = True,
) -> str:
    from src.agent_skills import compose_skills_section

    protocol = str(agent.get("markdownDoc", "")).strip()
    agent_name = str(agent.get("name", "Clutch Agent"))
    header = (
        f"You are {agent_name}, the active agent in the user's Clutch workspace.\n"
        f"When asked who you are, identify yourself as {agent_name}. "
        f"Do not claim to be a different product, vendor, or base model.\n"
        f"Runtime model: {model_name} ({model_api}).\n"
        "Treat every instruction in the agent protocol below as mandatory.\n"
    )
    parts = [header.strip()]
    if protocol:
        parts.append(protocol)
    if _uses_configured_llm(agent):
        if not mcp_servers_bound:
            parts.append(
                "No MCP tools are bound for this agent in this run. "
                "You cannot create, modify, or delete files on disk. "
                "Never claim a file operation succeeded without MCP tool evidence. "
                "Tell the user to bind **Local Filesystem MCP Server** in "
                "Agent Manager → Module 4 (MCP Hub Server Bindings)."
            )
        else:
            from src.workspace import get_workspace

            workspace = get_workspace()
            workspace_path = workspace.get("workspace_path") if workspace else None
            if workspace_path:
                parts.append(
                    f"Workspace root: {workspace_path}\n"
                    "Filesystem MCP tools only accept paths inside this workspace. "
                    "Prefer workspace-relative paths (e.g. `test.txt`), not `/test.txt` or other roots.\n"
                    "For create, edit, delete, or rename files, prefer the builtin "
                    "`clutch-tools__apply_patch` tool with Codex patch syntax. "
                    "Delete example (dotfiles need the leading dot):\n"
                    "```\n*** Begin Patch\n*** Delete File: .deleted_test.txt\n*** End Patch\n```\n"
                    "Never use local-fs move_file to delete or to rename `.foo` → `foo`. "
                    "Do not rename files to `.deleted_*` as a delete workaround when apply_patch is available."
                )
        skills_block = compose_skills_section(list(agent.get("skills") or []))
        if skills_block:
            parts.append(skills_block)
    return "\n\n".join(parts)


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
    claude_session_id: str | None = None,
    emit_log: Callable[[str], Awaitable[None]] | None = None,
    mcp_approved_tool: dict[str, Any] | None = None,
    mcp_resume: dict[str, Any] | None = None,
) -> tuple[str, str, str, list[str], str | None, dict[str, Any] | None, list[str]]:
    from src.agent_storage import BUILTIN_AGENT_ID, get_agent_by_id
    from src.engine_router import route_engine
    from src.models_config import get_router
    from src.workspace import get_workspace

    resolved_id = (agent_id or "").strip() or BUILTIN_AGENT_ID
    agent = get_agent_by_id(resolved_id)
    agent_ref = str(agent.get("id", resolved_id)) if agent else resolved_id
    reply_label = str(agent.get("name", "Clutch Agent")) if agent else (state.get("active_agent") or "Builder")

    router = get_router()
    model = router.get_active_model()
    runtime_model_name = model.name
    model_api = getattr(model, "api_model", None) or runtime_model_name

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

    history = _history_for_llm(state["messages"])
    if system_prompt:
        history = [{"role": "system", "content": system_prompt}] + [
            item for item in history if item.get("role") != "system"
        ]

    workspace = get_workspace()
    cwd = workspace.get("workspace_path") if workspace else None
    llm_only_logs: list[str] = []

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
                    approved_tool=mcp_approved_tool,
                    approved_keys=get_approved_mcp_keys(state["run_id"]),
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
                    )
                return (
                    reply_label,
                    outcome.engine_label,
                    outcome.output,
                    outcome.logs,
                    None,
                    None,
                    list(outcome.files_changed or []),
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
            history = _history_for_llm(state["messages"])
            if system_prompt:
                history = [{"role": "system", "content": system_prompt}] + [
                    item for item in history if item.get("role") != "system"
                ]

        loop = asyncio.get_running_loop()

        def on_log(line: str) -> None:
            if emit_log:
                asyncio.run_coroutine_threadsafe(emit_log(line), loop)

        result = await asyncio.to_thread(
            route_engine,
            agent_name=agent_ref,
            prompt=text,
            cwd=cwd,
            history=history,
            system_prompt=system_prompt,
            claude_session_id=claude_session_id,
            on_log=on_log if emit_log else None,
        )
        return reply_label, result.engine, result.output, llm_only_logs + result.logs, result.claude_session_id, None, []
    except Exception as exc:
        from src.engine_router import _normalize_engine_type

        err = str(exc)
        raw_engine = str(agent.get("aiEngine", "")) if agent else ""
        if _normalize_engine_type(raw_engine) == "Claude Code (Local CLI)" or "Claude CLI" in err:
            runtime_engine = "Claude CLI"
        else:
            runtime_engine = runtime_model_name
        return reply_label, runtime_engine, err, [f"Error routing plain chat request: {err}"], None, None, []


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
        _claude_session_id,
        mcp_pause,
        files_changed,
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

    reply = _chat_message(model_name, reply_text, runtime_engine=runtime_engine)
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
    state = _merge_patch(state, final_patch)
    _commit_run_state(run_id, state)
    await _send_message_event(websocket, run_id, reply, "")
    if files_changed:
        await _notify_workspace_files_changed(websocket, run_id, files_changed)
    await _notify_run_state(websocket, run_id, state, final_patch)
    return state


async def _handle_plain_chat(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    text: str,
    agent_id: str | None = None,
) -> ClutchState:
    from src.agent_storage import BUILTIN_AGENT_ID, get_agent_by_id

    resolved_id = (agent_id or "").strip() or BUILTIN_AGENT_ID
    agent = get_agent_by_id(resolved_id)
    active_agent = str(agent.get("name", "Clutch Agent")) if agent else "Clutch Agent"

    user_message = _chat_message("User", text, msg_id=f"user_{uuid.uuid4().hex[:8]}")
    user_patch = {
        "messages": list(state["messages"]) + [user_message],
        "status": "running",
        "active_agent": active_agent,
    }
    state = _merge_patch(state, user_patch)
    _commit_run_state(run_id, state)
    _touch_session(run_id, title=text.strip()[:80] or "New session", status=state["status"])

    await _send_message_event(websocket, run_id, user_message, "")
    await _notify_run_state(websocket, run_id, state, user_patch)

    stored_session_id = str(state.get("claude_session_id", "")).strip() or None
    stored_session_agent = str(state.get("claude_session_agent_id", "")).strip()
    if stored_session_agent and stored_session_agent != resolved_id:
        stored_session_id = None

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

    (
        model_name,
        runtime_engine,
        reply_text,
        route_logs,
        claude_session_id,
        mcp_pause,
        files_changed,
    ) = await _llm_chat_reply(
        state,
        text,
        agent_id=resolved_id,
        claude_session_id=stored_session_id,
        emit_log=emit_log,
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

    reply = _chat_message(model_name, reply_text, runtime_engine=runtime_engine)
    log_line = f"[CHAT] {model_name} via {runtime_engine}: {len(reply_text)} chars"

    if not streamed_logs:
        for log in route_logs:
            await _send_log_event(websocket, run_id, log, node_id="")
    await _send_log_event(websocket, run_id, log_line, node_id="")

    final_messages = list(state["messages"]) + [reply]
    final_logs = _append_terminal_logs(
        list(state["terminal_logs"]), route_logs, log_line, streamed=streamed_logs
    )
    final_patch: dict[str, Any] = {
        "messages": final_messages,
        "terminal_logs": final_logs,
        "status": "idle",
        "active_agent": active_agent,
        **_token_patch_turn(state, user_text=text, assistant_text=reply_text),
    }
    if claude_session_id:
        final_patch["claude_session_id"] = claude_session_id
        final_patch["claude_session_agent_id"] = resolved_id
    elif stored_session_agent and stored_session_agent != resolved_id:
        final_patch["claude_session_id"] = ""
        final_patch["claude_session_agent_id"] = ""
    state = _merge_patch(state, final_patch)
    _commit_run_state(run_id, state)
    _touch_session(run_id, title=text.strip()[:80] or "New session", status=state["status"])

    await _send_message_event(websocket, run_id, reply, "")
    if files_changed:
        await _notify_workspace_files_changed(websocket, run_id, files_changed)
    await _notify_run_state(websocket, run_id, state, final_patch)
    return state


async def _handle_workflow_chat_message(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    text: str,
) -> ClutchState:
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
async def get_models_config() -> dict[str, Any]:
    from src.models_config import get_router, serialize_models_config

    return serialize_models_config(get_router())


@app.post("/api/models/config")
async def update_models_config(body: ModelsConfigRequest) -> dict[str, str]:
    from src.llm.router import ProviderId
    from src.models_config import get_router, is_model_available, save_router

    router = get_router()
    if body.active_model_id:
        if not is_model_available(router, body.active_model_id):
            raise HTTPException(
                status_code=400,
                detail={"message": "Model is not available — configure provider API key first"},
            )
        router.set_active_model(body.active_model_id)
    if body.provider_id and body.api_key is not None:
        router.set_api_key(body.provider_id, body.api_key)  # type: ignore[arg-type]
    save_router(router)
    return {"status": "saved", "active_model_id": router.active_model_id}


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


@app.post("/api/models/test")
async def test_models_connection(body: ModelTestRequest) -> dict[str, Any]:
    from src.models_config import get_router, test_model_connection

    return test_model_connection(get_router(), body.model_id)


@app.get("/api/tools/status")
async def tools_status() -> dict[str, list[dict[str, Any]]]:
    from src.tools_status import list_tools_status

    return {"tools": list_tools_status()}


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


@app.post("/api/tools/open-cursor")
async def open_cursor_tool() -> dict[str, str]:
    from src.adapters.cursor_adapter import open_workspace_in_cursor
    from src.workspace import WorkspaceError, require_workspace

    try:
        root = require_workspace()
        open_workspace_in_cursor(str(root))
    except (WorkspaceError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return {"status": "opened"}


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


@app.delete("/api/runs/{run_id}")
async def delete_run_endpoint(run_id: str) -> dict[str, str]:
    from src.run_history import delete_session
    from src.run_state_store import delete_run_state

    try:
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
    logs = list(state["terminal_logs"])
    logs.append(stamp_log_line(tagged(TAG_WORKFLOW, "Run stopped via HTTP.")))
    state = _merge_patch(state, {"status": "failed", "terminal_logs": logs})
    _commit_run_state(run_id, state)
    update_run_record(run_id, {"status": "failed", "ended_at": _iso_timestamp()})
    return {"run_id": run_id, "status": state["status"]}


@app.websocket("/ws/runs/{run_id}")
async def ws_run(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    state = _get_or_create_run(run_id)
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

    forwarder.attach_ws(loop, ws_log_emit)

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
            if isinstance(payload, dict) and payload.get("text"):
                text = str(payload["text"])
                agent_id = str(payload.get("agent_id", "")).strip() or None
                if state["workflow_id"]:
                    state = await _handle_workflow_chat_message(websocket, run_id, state, text)
                else:
                    state = await _handle_plain_chat(
                        websocket, run_id, state, text, agent_id=agent_id
                    )
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
                logs = list(state["terminal_logs"])
                log_line = tagged(TAG_WORKFLOW, "Run stopped by supervisor.")
                logs.append(stamp_log_line(log_line))
                patch = {"status": "failed", "terminal_logs": logs}
                state = _merge_patch(state, patch)
                _commit_run_state(run_id, state)
                update_run_record(run_id, {"status": "failed", "ended_at": _iso_timestamp()})
                await _send_log_event(
                    websocket, run_id, log_line, node_id=state["active_node_id"]
                )
                await _notify_run_state(websocket, run_id, state, patch)
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
        forwarder.detach_ws()
