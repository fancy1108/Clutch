"""Clutch orchestration sidecar — M0 skeleton with ClutchState projection."""

from __future__ import annotations

import json
import logging
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.compiler import WorkflowSession, begin_workflow, resume_workflow
from src.run_history import append_run_record, list_runs, update_run_record
from src.state import ClutchState, initial_state
from src.workspace import WorkspaceError
from src.workflow_storage import resolve_workflow
from src.workflow_validator import WorkflowValidationError, load_and_validate_workflow, validate_workflow

logger = logging.getLogger(__name__)

app = FastAPI(title="Clutch Orchestrator", version="0.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000"],
    allow_credentials=True,
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


class ReassignRequest(BaseModel):
    instructions: str = Field(default="reassign_to_builder")


class HumanDecisionRequest(BaseModel):
    decision: str = Field(default="approve")
    instructions: str = Field(default="")


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
        graph_result = resume_workflow(session, run_id, decision)
        patch = {
            "messages": messages,
            "terminal_logs": logs,
            "status": graph_result["status"],
            "active_node_id": graph_result["active_node_id"],
            "active_agent": graph_result["active_agent"],
        }
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
    _run_states[run_id] = state
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
        _run_states[run_id] = initial_state(run_id)
    return _run_states[run_id]


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
    return {"status": "ok"}


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
async def get_run_history() -> dict[str, list[dict[str, Any]]]:
    return {"runs": list_runs()}


def _workspace_http_error(exc: WorkspaceError) -> HTTPException:
    return HTTPException(status_code=403, detail={"message": str(exc)})


@app.get("/api/workspace")
async def get_workspace_endpoint() -> dict[str, str]:
    from src.workspace import get_workspace

    info = get_workspace()
    if info is None:
        raise HTTPException(status_code=404, detail={"message": "尚未授权工作区"})
    return info


@app.post("/api/workspace")
async def set_workspace_endpoint(body: WorkspaceRequest) -> dict[str, str]:
    from src.workspace import WorkspaceError, set_workspace

    try:
        return set_workspace(body.path)
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


@app.get("/api/models/credentials")
async def get_models_credentials() -> dict[str, Any]:
    from src.credentials.claude_code import credential_status
    from src.models_config import get_router

    return credential_status(get_router())


@app.get("/api/models/config")
async def get_models_config() -> dict[str, Any]:
    from src.models_config import get_router

    router = get_router()
    return {
        "active_model_id": router.active_model_id,
        "models": [
            {"id": spec.id, "name": spec.name, "provider_id": spec.provider_id}
            for spec in router.list_models()
        ],
    }


@app.post("/api/models/config")
async def update_models_config(body: ModelsConfigRequest) -> dict[str, str]:
    from src.llm.router import ProviderId
    from src.models_config import get_router, save_router

    router = get_router()
    if body.active_model_id:
        router.set_active_model(body.active_model_id)
    if body.provider_id and body.api_key is not None:
        router.set_api_key(body.provider_id, body.api_key)  # type: ignore[arg-type]
    save_router(router)
    return {"status": "saved", "active_model_id": router.active_model_id}


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
    from src.workspace import get_workspace

    workspace = get_workspace()
    connected = workspace is not None
    return {
        "filesystem": {
            "connected": connected,
            "tools": 5 if connected else 0,
            "workspace_path": workspace["workspace_path"] if workspace else None,
        }
    }


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
        _run_states[run_id] = state
    else:
        patch = {
            "status": "running",
            "active_agent": "Builder",
            "active_node_id": "n1",
        }
        state = _merge_patch(state, patch)
        _run_states[run_id] = state
    logs = list(state["terminal_logs"])
    logs.append(f"[USER] Re-assign to Builder: {body.instructions}")
    logs.append("[BUILDER] Resuming repair task per supervisor directive.")
    state = _merge_patch(state, {"terminal_logs": logs})
    _run_states[run_id] = state
    return {"run_id": run_id, "status": state["status"]}


@app.post("/api/runs/start")
async def start_run(body: StartRunRequest) -> dict[str, str]:
    try:
        workflow, _source = resolve_workflow(body.workflow_id)
    except WorkflowValidationError as exc:
        raise _validation_http_error(exc) from exc

    run_id = f"run_{uuid.uuid4().hex[:8]}"
    state = initial_state(run_id, workflow["id"])
    state["current_instruction"] = body.instruction

    logs = list(state["terminal_logs"])
    logs.append(f"[ORCHESTRATOR] Starting workflow: {workflow['name']} ({workflow['id']})")
    session, graph_result = begin_workflow(workflow, run_id)
    _run_sessions[run_id] = session
    logs.append(f"[LANGGRAPH] Active node → {graph_result['active_node_id']}")
    if graph_result["status"] == "awaiting_human":
        logs.append("[SUPERVISOR] Human gate reached — awaiting decision.")

    state = _merge_patch(
        state,
        {
            "active_node_id": graph_result["active_node_id"],
            "active_agent": graph_result["active_agent"],
            "status": graph_result["status"],
            "terminal_logs": logs,
        },
    )
    _run_states[run_id] = state
    append_run_record(
        {
            "run_id": run_id,
            "workflow_id": workflow["id"],
            "status": state["status"],
            "started_at": _iso_timestamp(),
        }
    )

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
    return {"run_id": run_id, "status": state["status"]}


@app.post("/api/runs/{run_id}/stop")
async def stop_run(run_id: str) -> dict[str, str]:
    state = _get_or_create_run(run_id)
    logs = list(state["terminal_logs"])
    logs.append("[ORCHESTRATOR] Run stopped via HTTP.")
    state = _merge_patch(state, {"status": "failed", "terminal_logs": logs})
    _run_states[run_id] = state
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
                node_id = state["active_node_id"]
                user_message = _chat_message("User", text, msg_id=f"user_{uuid.uuid4().hex[:8]}")
                reply = _chat_message(
                    "Orchestrator",
                    f"已收到指令，将分派给 {state['active_agent']}：{text}",
                )
                log_line = f"[ORCHESTRATOR] Received: {text}"

                messages = list(state["messages"]) + [user_message, reply]
                logs = list(state["terminal_logs"]) + [log_line]

                patch = {
                    "messages": messages,
                    "terminal_logs": logs,
                    "active_node_id": "n1",
                    "active_agent": "Builder",
                    "status": "running",
                    **_token_patch(state, text + reply["text"]),
                }
                state = _merge_patch(state, patch)
                _run_states[run_id] = state

                await _send_message_event(websocket, run_id, user_message, node_id)
                await _send_log_event(websocket, run_id, log_line, node_id=node_id)
                await _send_message_event(websocket, run_id, reply, "n1")
                await _notify_run_state(websocket, run_id, state, patch)
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
                _run_states[run_id] = state
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
