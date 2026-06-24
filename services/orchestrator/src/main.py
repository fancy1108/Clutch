"""Clutch orchestration sidecar — M0 skeleton with ClutchState projection."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
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


class AgentsSaveRequest(BaseModel):
    agents: list[dict[str, Any]]


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


class ThemePreferenceRequest(BaseModel):
    theme_id: str


class LanguagePreferenceRequest(BaseModel):
    language: str


def _skills_registry_payload(*, rescan: bool = True) -> dict[str, Any]:
    from src.skills_scanner import scan_mounted_directories
    from src.skills_storage import load_registry, save_registry

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
    workflow, _source = resolve_workflow(workflow_id)
    state = _get_or_create_run(run_id)
    prepend_logs = [f"[ORCHESTRATOR] Starting workflow: {workflow['name']} ({workflow['id']})"]
    session, graph_result = begin_workflow(workflow, run_id, instruction=instruction)
    _run_sessions[run_id] = session
    from src.workflow_projection import project_graph_to_clutch

    patch = project_graph_to_clutch(
        state,
        graph_result,
        workflow=workflow,
        instruction=instruction,
        prepend_logs=prepend_logs,
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
) -> dict[str, Any]:
    messages = list(base_messages)
    logs = list(base_logs)
    messages.extend(graph_result.get("task_messages", []))
    logs.extend(graph_result.get("task_logs", []))
    logs.append(f"[LANGGRAPH] Active node → {graph_result['active_node_id']}")
    if graph_result["status"] == "awaiting_human":
        logs.append("[SUPERVISOR] Human gate reached — awaiting decision.")
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
    state = _get_or_create_run(run_id)
    if decision == "approve":
        supervisor_text = "人工审批：已通过，继续执行工作流。"
    elif decision == "reject":
        supervisor_text = "人工审批：已拒绝，运行标记为失败。"
    else:
        supervisor_text = f"人工审批：按指令重试 — {instructions or '（无附加说明）'}"

    supervisor_message = _chat_message("Supervisor", supervisor_text)
    log_line = f"[SUPERVISOR] {supervisor_text}"
    messages = list(state["messages"]) + [supervisor_message]
    logs = list(state["terminal_logs"]) + [log_line]

    session = _run_sessions.get(run_id)
    if session and state["status"] == "awaiting_human":
        graph_result = resume_workflow(
            session,
            run_id,
            decision,
            instruction=instructions if decision == "retry" else "",
        )
        patch = _merge_graph_resume(
            state,
            graph_result,
            base_messages=messages,
            base_logs=logs,
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
    "Supervisor": "https://lh3.googleusercontent.com/aida-public/AB6AXuCmb7VGaQXE-4sYnIZR3VrcHVAPhv4Px14kMlkayJj8kVm8htTWITmPi26wsj8P6B9RrqykIWj81S2ilmGR0e8cXhA1gjc3U-Nw0DsgHV3HvVmBskuoUksIt6YM6Z3ORjFtRhBphqAXxRKf9ke-zYcPs0TcEFKxw_bwGXSDiAKV5CL7kZf9i6lSZDe91ccUNjaAIsgTMKEEvYc7bZpXYz3D5dClulRwbNru5SZB-1E5FM0A2qMPs-IAfiR8OB1-cUvFh3WYKx9qlGgN",
    "User": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=100",
}


def _chat_time() -> str:
    return datetime.now(UTC).strftime("%H:%M")


def _chat_message(
    agent: str,
    text: str,
    *,
    status: str | None = None,
    msg_id: str | None = None,
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


async def _llm_chat_reply(state: ClutchState, text: str) -> tuple[str, str]:
    from src.models_config import get_router

    router = get_router()
    model = router.get_active_model()
    history = _history_for_llm(state["messages"])
    history.append({"role": "user", "content": text})
    try:
        reply_text = await asyncio.to_thread(router.chat, history)
    except RuntimeError as exc:
        reply_text = (
            f"Cannot reach the configured model ({model.name}). "
            f"Add an API key in Settings → Models. ({exc})"
        )
    return model.name, reply_text


async def _handle_plain_chat(
    websocket: WebSocket,
    run_id: str,
    state: ClutchState,
    text: str,
) -> ClutchState:
    user_message = _chat_message("User", text, msg_id=f"user_{uuid.uuid4().hex[:8]}")
    model_name, reply_text = await _llm_chat_reply(state, text)
    reply = _chat_message(model_name, reply_text)
    log_line = f"[CHAT] {model_name}: {len(reply_text)} chars"

    messages = list(state["messages"]) + [user_message, reply]
    logs = list(state["terminal_logs"]) + [log_line]
    patch = {
        "messages": messages,
        "terminal_logs": logs,
        "status": "idle",
        **_token_patch_turn(state, user_text=text, assistant_text=reply_text),
    }
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    _touch_session(run_id, title=text.strip()[:80] or "New session", status=state["status"])

    await _send_message_event(websocket, run_id, user_message, "")
    await _send_log_event(websocket, run_id, log_line, node_id="")
    await _send_message_event(websocket, run_id, reply, "")
    await _notify_run_state(websocket, run_id, state, patch)
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
    logs.append(f"[USER] {text}")

    if state["status"] == "awaiting_human":
        state, patch, supervisor_message, log_line = _apply_human_decision(
            run_id, "retry", text
        )
        await _send_message_event(websocket, run_id, user_message, state["active_node_id"])
        await _send_message_event(websocket, run_id, supervisor_message, state["active_node_id"])
        await _send_log_event(websocket, run_id, log_line, node_id=state["active_node_id"])
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
            "path": path,
            "diff_lines": diff_lines,
            "timestamp": _iso_timestamp(),
        },
    }
    await websocket.send_text(json.dumps(envelope))


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
    envelope = {
        "event": "log",
        "data": {
            "run_id": run_id,
            "node_id": node_id,
            "source": "orchestrator",
            "level": level,
            "message": line,
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
            raise WorkflowValidationError("请提供 workflow_id 或 workflow 对象", [])
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
        raise HTTPException(status_code=400, detail={"message": "请先选择并授权一个项目工作区"})
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
    from src.workspace import WorkspaceError, add_workspace

    try:
        return add_workspace(body.path)
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc


@app.post("/api/workspaces/{workspace_id}/activate")
async def activate_workspace_endpoint(workspace_id: str) -> dict[str, str]:
    from src.workspace import WorkspaceError, activate_workspace

    try:
        return activate_workspace(workspace_id)
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


@app.get("/api/workspace")
async def get_workspace_endpoint() -> dict[str, str]:
    from src.workspace import get_workspace

    info = get_workspace()
    if info is None:
        raise HTTPException(status_code=404, detail={"message": "尚未授权工作区"})
    return info


@app.post("/api/workspace")
async def set_workspace_endpoint(body: WorkspaceRequest) -> dict[str, str]:
    from src.workspace import WorkspaceError, add_workspace

    try:
        return add_workspace(body.path)
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


@app.get("/api/skills")
async def get_skills_registry() -> dict[str, Any]:
    return _skills_registry_payload(rescan=True)


@app.post("/api/skills/mount")
async def mount_skills_directory(body: SkillsMountRequest) -> dict[str, Any]:
    from src.skills_storage import load_registry, save_registry

    raw = body.path.strip()
    if not raw:
        raise HTTPException(status_code=400, detail={"message": "路径不能为空"})
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
        raise HTTPException(status_code=400, detail={"message": "路径不能为空"})
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
        raise HTTPException(status_code=404, detail={"message": "未找到该 Skill"})
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

    return build_mcp_status_payload()


@app.post("/api/mcp/servers/register")
async def register_mcp_server(body: McpRegisterRequest) -> dict[str, Any]:
    from src.mcp_storage import build_mcp_status_payload, register_server

    try:
        register_server(name=body.name, transport=body.transport, endpoint=body.endpoint)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return build_mcp_status_payload()


@app.post("/api/mcp/servers/remove")
async def remove_mcp_server(body: McpServerIdRequest) -> dict[str, Any]:
    from src.mcp_storage import build_mcp_status_payload, remove_server

    try:
        remove_server(body.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    return build_mcp_status_payload()


@app.post("/api/mcp/servers/toggle")
async def toggle_mcp_server(body: McpServerIdRequest) -> dict[str, Any]:
    from src.mcp_storage import build_mcp_status_payload, toggle_server

    if body.enabled is None:
        raise HTTPException(status_code=400, detail={"message": "enabled 字段必填"})
    try:
        toggle_server(body.id, enabled=body.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    return build_mcp_status_payload()


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
    state, _patch, _message, _log = _apply_human_decision(
        run_id, body.decision, body.instructions
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
    logs.append(f"[USER] Re-assign to Builder: {body.instructions}")
    logs.append("[BUILDER] Resuming repair task per supervisor directive.")
    state = _merge_patch(state, {"terminal_logs": logs})
    _commit_run_state(run_id, state)
    return {"run_id": run_id, "status": state["status"]}


@app.post("/api/runs/start")
async def start_run(body: StartRunRequest) -> dict[str, Any]:
    try:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        state = _run_workflow(run_id, body.workflow_id, body.instruction)
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
        state = _run_workflow(run_id, body.workflow_id, body.instruction)
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


@app.post("/api/runs/{run_id}/stop")
async def stop_run(run_id: str) -> dict[str, str]:
    state = _get_or_create_run(run_id)
    logs = list(state["terminal_logs"])
    logs.append("[ORCHESTRATOR] Run stopped via HTTP.")
    state = _merge_patch(state, {"status": "failed", "terminal_logs": logs})
    _commit_run_state(run_id, state)
    update_run_record(run_id, {"status": "failed", "ended_at": _iso_timestamp()})
    return {"run_id": run_id, "status": state["status"]}


@app.websocket("/ws/runs/{run_id}")
async def ws_run(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    state = _get_or_create_run(run_id)

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
            message="Evaluator 检查未通过，等待人工审批。",
        )
        await _send_human_required(
            websocket,
            run_id,
            node_id=state["active_node_id"],
            prompt="检查未通过，等待人工确认。",
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
                if state["workflow_id"]:
                    state = await _handle_workflow_chat_message(websocket, run_id, state, text)
                else:
                    state = await _handle_plain_chat(websocket, run_id, state, text)
            elif isinstance(payload, dict) and payload.get("action") == "human_decision":
                decision = str(payload.get("decision", "approve"))
                instructions = str(payload.get("instructions", ""))
                node_id = state["active_node_id"]

                state, patch, supervisor_message, log_line = _apply_human_decision(
                    run_id, decision, instructions
                )

                await _send_message_event(websocket, run_id, supervisor_message, node_id)
                await _send_log_event(websocket, run_id, log_line, node_id=node_id)
                await _notify_run_state(websocket, run_id, state, patch)
                if state["status"] == "awaiting_human":
                    await _send_validation_result(
                        websocket,
                        run_id,
                        node_id=state["active_node_id"],
                        passed=False,
                        message="Evaluator 检查未通过，等待人工审批。",
                    )
                    await _send_human_required(
                        websocket,
                        run_id,
                        node_id=state["active_node_id"],
                        prompt="检查未通过，等待人工确认。",
                    )
            elif isinstance(payload, dict) and payload.get("action") == "stop_run":
                logs = list(state["terminal_logs"])
                log_line = "[ORCHESTRATOR] Run stopped by supervisor."
                logs.append(log_line)
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
                    f"未识别的 WebSocket 载荷：{payload!r}",
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
