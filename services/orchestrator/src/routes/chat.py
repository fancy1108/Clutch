"""HTTP & WebSocket API for runs, sessions, chat workflows, and execution controls."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Response
from pydantic import BaseModel, Field

from src.release_hardening import debug_api_enabled
from src.sidecar_auth import auth_required, validate_token
from src.preferences_storage import tr
from src.terminal_logs import TAG_HUMAN, TAG_WORKFLOW, stamp_log_line, tagged
from src.run_history import list_runs, upsert_session
from src.workflow_validator import WorkflowValidationError, load_and_validate_workflow, validate_workflow

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


class ValidateWorkflowRequest(BaseModel):
    workflow_id: str | None = None
    workflow: dict[str, Any] | None = None


class SaveUserWorkflowRequest(BaseModel):
    workflow: dict[str, Any]


class SessionCreateRequest(BaseModel):
    run_id: str
    title: str = Field(default="New session")
    workflow_id: str = Field(default="")
    mode: str = Field(default="coding")
    status: str | None = None


class ShellSnapshotUpdateRequest(BaseModel):
    task_summary: str = ""
    open_todos: list[str] = Field(default_factory=list)
    cwd: str | None = None
    cli_session_id: str | None = None


class HumanDecisionRequest(BaseModel):
    decision: str = Field(default="approve")
    instructions: str = Field(default="")


class ReassignRequest(BaseModel):
    instructions: str = Field(default="reassign_to_builder")


class StartRunRequest(BaseModel):
    workflow_id: str = Field(default="video-production")
    instruction: str = Field(default="")


class ForkSessionRequest(BaseModel):
    message_index: int = Field(ge=0)


class RewindFilesRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=10)


@router.post("/api/workflows/validate")
async def validate_workflow_endpoint(body: ValidateWorkflowRequest) -> dict[str, str | bool]:
    from src.main import _validation_http_error
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


@router.get("/api/workflows/templates")
async def list_workflow_templates() -> dict[str, list[str]]:
    from src.workflow_storage import list_templates
    return {"workflow_ids": list_templates()}


@router.get("/api/workflows/templates/{workflow_id}")
async def get_workflow_template(workflow_id: str) -> dict[str, Any]:
    from src.main import _validation_http_error
    from src.workflow_storage import get_template

    try:
        workflow = get_template(workflow_id)
    except WorkflowValidationError as exc:
        raise _validation_http_error(exc) from exc
    return {"source": "template", "workflow": workflow}


@router.get("/api/workflows/user")
async def list_user_workflow_ids() -> dict[str, list[str]]:
    from src.workflow_storage import list_user_workflows
    return {"workflow_ids": list_user_workflows()}


@router.get("/api/workflows/user/{workflow_id}")
async def get_user_workflow_endpoint(workflow_id: str) -> dict[str, Any]:
    from src.main import _validation_http_error
    from src.workflow_storage import get_user_workflow

    try:
        workflow = get_user_workflow(workflow_id)
    except WorkflowValidationError as exc:
        raise _validation_http_error(exc) from exc
    return {"source": "user", "workflow": workflow}


@router.post("/api/workflows/user")
async def save_user_workflow_endpoint(body: SaveUserWorkflowRequest) -> dict[str, str]:
    from src.main import _validation_http_error
    from src.workflow_storage import save_user_workflow

    try:
        workflow = save_user_workflow(body.workflow)
    except WorkflowValidationError as exc:
        raise _validation_http_error(exc) from exc
    return {"workflow_id": str(workflow["id"]), "status": "saved"}


@router.delete("/api/workflows/user/{workflow_id}")
async def delete_user_workflow_endpoint(workflow_id: str) -> dict[str, str]:
    from src.main import _validation_http_error
    from src.workflow_storage import delete_user_workflow

    try:
        delete_user_workflow(workflow_id)
    except WorkflowValidationError as exc:
        raise _validation_http_error(exc) from exc
    return {"workflow_id": workflow_id, "status": "deleted"}


@router.get("/api/runs/history")
async def get_run_history(
    workspace_id: str | None = None,
    mode: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    runs = list_runs(workspace_id=workspace_id, mode=mode)
    # Heal stale coding "running" badges when the live run state is already idle/failed.
    try:
        from src.run_state_store import load_run_state

        for record in runs:
            if str(record.get("mode") or "coding").strip().lower() == "design":
                continue
            if str(record.get("status") or "").strip().lower() != "running":
                continue
            run_id = str(record.get("run_id") or "").strip()
            if not run_id:
                continue
            state = load_run_state(run_id)
            if not state:
                continue
            live = str(state.get("status") or "").strip().lower()
            if live in {"idle", "passed", "failed", "completed"}:
                record["status"] = "failed" if live == "failed" else "idle"
    except Exception:
        pass
    if (mode or "").strip().lower() == "design":
        try:
            from src.design import service as design_service

            for record in runs:
                run_id = str(record.get("run_id") or "")
                if not run_id:
                    continue
                thumb = design_service.thumbnail_data_url_for_run(run_id)
                if thumb:
                    record["thumbnail_url"] = thumb
                else:
                    record.pop("thumbnail_url", None)
                preview = design_service.design_ui_preview_path_for_run(run_id)
                if preview:
                    record["ui_preview_url"] = preview
                else:
                    record.pop("ui_preview_url", None)
                record["device"] = design_service.design_device_for_run(run_id)
                design_status = design_service.session_status_for_run(run_id)
                if design_status:
                    if design_status in {
                        "ready",
                        "error",
                        "prototype_approved",
                        "react_ready",
                        "draft",
                        "idle",
                    }:
                        record["status"] = "ready" if design_status in {
                            "prototype_approved",
                            "react_ready",
                        } else ("idle" if design_status in {"draft", "idle"} else design_status)
                    elif design_status in {"crafting_spec", "generating_ui", "iterating"}:
                        record["status"] = design_status
            keep = {str(r.get("run_id") or "") for r in runs if r.get("run_id")}
            design_service.prune_orphan_session_dirs(keep_run_ids=keep)
        except Exception:
            pass
    return {"runs": runs}


@router.post("/api/sessions")
async def create_session_endpoint(body: SessionCreateRequest) -> dict[str, Any]:
    from src.workspace import get_workspace
    from src.main import _get_or_create_run, _iso_timestamp

    workspace = get_workspace()
    if workspace is None:
        raise HTTPException(status_code=400, detail={"message": tr("Please select and authorize a project workspace first", "请先选择并授权一个项目工作区")})
    from src.run_state_store import load_run_state

    mode = (body.mode or "coding").strip().lower()
    if mode not in {"coding", "design"}:
        mode = "coding"
    state = load_run_state(body.run_id) or _get_or_create_run(body.run_id)
    status = (body.status or "").strip().lower() if body.status is not None else ""
    if status and status not in {
        "running",
        "idle",
        "ready",
        "failed",
        "completed",
        "crafting_spec",
        "generating_ui",
        "iterating",
    }:
        status = ""
    existing = next((r for r in list_runs() if r.get("run_id") == body.run_id), None)
    if not status:
        status = str((existing or {}).get("status") or "") or ("idle" if mode == "design" else "running")
    record_payload: dict[str, Any] = {
        "run_id": body.run_id,
        "workspace_id": workspace["id"],
        "workspace_name": workspace["name"],
        "title": body.title[:80] or ("New Design" if mode == "design" else "New session"),
        "workflow_id": body.workflow_id,
        "mode": mode,
        "status": status,
    }
    if existing and existing.get("started_at"):
        record_payload["started_at"] = existing["started_at"]
    else:
        record_payload["started_at"] = _iso_timestamp()
    record = upsert_session(record_payload)
    return record


@router.get("/api/shell-snapshots")
async def list_shell_snapshots() -> dict[str, Any]:
    from src.session_snapshot import list_snapshots
    return {"snapshots": list_snapshots()}


@router.get("/api/shell-snapshots/{run_id}")
async def get_shell_snapshot(run_id: str) -> dict[str, Any]:
    from src.session_snapshot import load_snapshot

    snap = load_snapshot(run_id)
    if snap is None:
        raise HTTPException(status_code=404, detail={"message": "Snapshot not found"})
    return snap.to_dict()


@router.put("/api/shell-snapshots/{run_id}")
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


@router.post("/api/runs/{run_id}/human-decision")
async def human_decision_http(run_id: str, body: HumanDecisionRequest) -> dict[str, Any]:
    from src.main import _apply_human_decision
    state, _patch, _message, _log = await asyncio.to_thread(
        _apply_human_decision,
        run_id,
        body.decision,
        body.instructions,
    )
    return {"run_id": run_id, "status": state["status"], "active_node_id": state["active_node_id"]}


@router.post("/api/runs/{run_id}/reassign")
async def reassign_run(run_id: str, body: ReassignRequest) -> dict[str, str]:
    from src.main import _get_or_create_run, _run_sessions, _merge_patch, _commit_run_state, resume_workflow
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


@router.post("/api/runs/start")
async def start_run(body: StartRunRequest) -> dict[str, Any]:
    from src.main import _run_workflow, _validation_http_error, _serialize_clutch_state, _iso_timestamp
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


@router.post("/api/runs/{run_id}/start")
async def start_run_on_session(run_id: str, body: StartRunRequest) -> dict[str, Any]:
    from src.main import _run_workflow, _validation_http_error, _serialize_clutch_state, _iso_timestamp
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


@router.get("/api/runs/{run_id}/state")
async def get_run_state(run_id: str) -> dict[str, Any]:
    from src.run_state_store import sync_run_state_from_disk
    from src.main import _get_or_create_run, _run_states, _serialize_clutch_state

    state = sync_run_state_from_disk(run_id, _get_or_create_run(run_id))
    _run_states[run_id] = state
    return {"run_id": run_id, "state": _serialize_clutch_state(state)}


@router.get("/api/runs/{run_id}/debug")
async def get_run_debug(
    run_id: str,
    logs_limit: int | None = None,
    audit_limit: int | None = None,
) -> dict[str, Any]:
    if not debug_api_enabled():
        raise HTTPException(status_code=404, detail={"message": "Not found"})

    from src.run_debug import build_run_debug_payload
    from src.main import _get_or_create_run

    state = _get_or_create_run(run_id)
    return build_run_debug_payload(
        run_id,
        state,
        logs_limit=logs_limit,
        audit_limit=audit_limit,
    )


@router.delete("/api/runs/{run_id}")
async def delete_run_endpoint(run_id: str) -> dict[str, Any]:
    from src.run_history import delete_session
    from src.run_state_store import delete_run_state
    from src.shell_session import get_shell_session_manager
    from src.main import _run_states, _run_sessions

    try:
        get_shell_session_manager().release(run_id)
        delete_session(run_id)
        delete_run_state(run_id)
        try:
            from src.design import service as design_service
            design_service.delete_session_artifacts(run_id)
        except Exception:
            logger.warning("design artifact cleanup failed run_id=%s", run_id, exc_info=True)
        if run_id in _run_states:
            del _run_states[run_id]
        if run_id in _run_sessions:
            del _run_sessions[run_id]
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": str(exc)}) from exc
    return {"status": "deleted", "run_id": run_id}


@router.post("/api/runs/{run_id}/fork")
async def fork_session_endpoint(run_id: str, body: ForkSessionRequest) -> dict[str, Any]:
    from src.session_fork import fork_session

    try:
        return await asyncio.to_thread(fork_session, run_id, body.message_index)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@router.post("/api/runs/{run_id}/rewind")
async def rewind_files_endpoint(run_id: str, body: RewindFilesRequest) -> dict[str, Any]:
    from src.file_rewind import rewind_last_writes, snapshot_count
    from src.main import (
        _chat_message,
        _commit_run_state,
        _get_or_create_run,
        _merge_patch,
    )

    try:
        restored = await asyncio.to_thread(rewind_last_writes, run_id, body.count)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    if not restored:
        return {
            "run_id": run_id,
            "restored": [],
            "remaining_snapshots": snapshot_count(run_id),
            "detail": "No file snapshots to rewind.",
        }
    paths = ", ".join(item["path"] for item in restored)
    notice = _chat_message(
        "Supervisor",
        tr(f"Rewound agent file changes: {paths}", f"已回滚 Agent 文件改动：{paths}"),
    )
    state = _get_or_create_run(run_id)
    patch = {"messages": list(state["messages"]) + [notice]}
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    return {
        "run_id": run_id,
        "restored": restored,
        "remaining_snapshots": snapshot_count(run_id),
        "message": notice,
        "state": state,
    }


@router.post("/api/runs/{run_id}/compact")
async def compact_run(run_id: str) -> dict[str, Any]:
    """D18 — manually trigger context compaction (slash `/compact`)."""
    from src.chat_runner import _get_or_create_run, _commit_run_state
    from src.compaction import compact_run_messages
    from src.run_log_forwarder import get_forwarder

    state = _get_or_create_run(run_id)
    before_count = len(state.get("messages") or [])
    if before_count <= 5:
        return {
            "run_id": run_id,
            "compacted": False,
            "message_count": before_count,
            "session_tokens": int(state.get("session_tokens") or 0),
            "detail": "Not enough messages to compact (need more than 5).",
        }
    new_state = await compact_run_messages(
        run_id, state, record_slash_command=True
    )
    after_count = len(new_state.get("messages") or [])
    # Manual compact appends a User `/compact` row; still counts as compacted when
    # intermediates were folded (message list shorter than before + slash row).
    compacted = after_count < before_count + 1
    _commit_run_state(run_id, new_state)
    patch = {
        "messages": new_state.get("messages"),
        "session_tokens": new_state.get("session_tokens"),
        "input_tokens": new_state.get("input_tokens"),
        "output_tokens": new_state.get("output_tokens"),
    }
    get_forwarder(run_id).emit_state_patch(patch, str(new_state.get("status") or "idle"))
    return {
        "run_id": run_id,
        "compacted": compacted,
        "message_count": after_count,
        "session_tokens": int(new_state.get("session_tokens") or 0),
        "detail": "Context compacted." if compacted else "Compaction returned unchanged state.",
    }


@router.post("/api/runs/{run_id}/stop")
async def stop_run(run_id: str) -> dict[str, str]:
    from src.main import (
        _get_or_create_run,
        _interrupt_plain_chat_shell,
        _interrupt_workflow_run,
        _merge_patch,
        _commit_run_state,
        _touch_session,
        _iso_timestamp,
        update_run_record,
    )
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


@router.websocket("/ws/runs/{run_id}")
async def ws_run(websocket: WebSocket, run_id: str) -> None:
    from src.main import ws_run as main_ws_run
    await main_ws_run(websocket, run_id)
