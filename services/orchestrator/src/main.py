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

from src.compiler import run_workflow
from src.state import ClutchState, initial_state
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


class StartRunRequest(BaseModel):
    workflow_id: str = Field(default="video-production")
    instruction: str = Field(default="")


class ValidateWorkflowRequest(BaseModel):
    workflow_id: str | None = None
    workflow: dict[str, Any] | None = None


class SaveUserWorkflowRequest(BaseModel):
    workflow: dict[str, Any]


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
    graph_result = run_workflow(workflow, run_id)
    logs.append(f"[LANGGRAPH] Active node → {graph_result['active_node_id']}")

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
                logs = list(state["terminal_logs"])
                logs.append(f"[ORCHESTRATOR] Received: {payload['text']}")
                patch = {
                    "terminal_logs": logs,
                    "active_node_id": "n1",
                    "active_agent": "Builder",
                    "status": "running",
                }
            elif isinstance(payload, dict) and payload.get("action") == "human_decision":
                decision = payload.get("decision", "approve")
                patch = {
                    "status": "passed" if decision == "approve" else "failed",
                    "active_agent": "Supervisor",
                }
            elif isinstance(payload, dict) and payload.get("action") == "stop_run":
                logs = list(state["terminal_logs"])
                logs.append("[ORCHESTRATOR] Run stopped by supervisor.")
                patch = {"status": "failed", "terminal_logs": logs}

            if patch:
                state = _merge_patch(state, patch)
                _run_states[run_id] = state
                await _notify_run_state(websocket, run_id, state, patch)
            else:
                envelope = {
                    "event": "message",
                    "data": {
                        "run_id": run_id,
                        "echo": payload,
                        "timestamp": _iso_timestamp(),
                    },
                }
                await websocket.send_text(json.dumps(envelope))

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
