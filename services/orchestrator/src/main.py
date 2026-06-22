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

from src.graph import run_minimal_graph
from src.state import ClutchState, initial_state
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


@app.post("/api/runs/start")
async def start_run(body: StartRunRequest) -> dict[str, str]:
    try:
        workflow = load_and_validate_workflow(body.workflow_id)
    except WorkflowValidationError as exc:
        raise _validation_http_error(exc) from exc

    run_id = f"run_{uuid.uuid4().hex[:8]}"
    state = initial_state(run_id, workflow["id"])
    state["current_instruction"] = body.instruction

    logs = list(state["terminal_logs"])
    logs.append(f"[ORCHESTRATOR] Starting workflow: {workflow['name']} ({workflow['id']})")
    graph_result = run_minimal_graph(run_id)
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
                await _send_state_patch(websocket, run_id, patch)
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
