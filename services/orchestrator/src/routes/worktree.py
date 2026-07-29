"""D32 — HTTP API for git worktree isolation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.preferences_storage import tr
from src.workspace import require_workspace

router = APIRouter(tags=["worktree"])


class WorktreeEnableRequest(BaseModel):
  run_id: str = Field(default="")


class WorktreeActionRequest(BaseModel):
    run_id: str = Field(default="")


@router.post("/api/worktree/enable")
async def enable_worktree(body: WorktreeEnableRequest) -> dict[str, Any]:
    from src.chat_runner import _commit_run_state, _get_or_create_run, _merge_patch
    from src.worktree_isolation import create_worktree, describe_worktree

    run_id = body.run_id.strip()
    if not run_id:
        raise HTTPException(status_code=400, detail="run_id required")
    root = require_workspace()
    try:
        info = create_worktree(root)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = describe_worktree(info, root)
    state = _get_or_create_run(run_id)
    patch = {"worktree_isolation": payload}
    state = _merge_patch(state, patch)
    _commit_run_state(run_id, state)
    return {"run_id": run_id, "worktree": payload, "state": state}


@router.post("/api/worktree/{wt_id}/merge")
async def merge_worktree_route(wt_id: str, body: WorktreeActionRequest) -> dict[str, Any]:
    from src.chat_runner import _commit_run_state, _get_or_create_run, _merge_patch
    from src.worktree_isolation import merge_worktree

    run_id = body.run_id.strip()
    root = require_workspace()
    try:
        summary = merge_worktree(root, wt_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result: dict[str, Any] = {"wt_id": wt_id, "summary": summary}
    if run_id:
        state = _get_or_create_run(run_id)
        state = _merge_patch(state, {"worktree_isolation": None})
        _commit_run_state(run_id, state)
        result["state"] = state
    return result


@router.post("/api/worktree/{wt_id}/discard")
async def discard_worktree_route(wt_id: str, body: WorktreeActionRequest) -> dict[str, Any]:
    from src.chat_runner import _commit_run_state, _get_or_create_run, _merge_patch
    from src.worktree_isolation import discard_worktree

    run_id = body.run_id.strip()
    root = require_workspace()
    try:
        discard_worktree(root, wt_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result: dict[str, Any] = {"wt_id": wt_id, "discarded": True}
    if run_id:
        state = _get_or_create_run(run_id)
        state = _merge_patch(state, {"worktree_isolation": None})
        _commit_run_state(run_id, state)
        result["state"] = state
    return result


@router.get("/api/worktree/{wt_id}/status")
async def worktree_status(wt_id: str) -> dict[str, Any]:
    from src.worktree_isolation import describe_worktree, worktrees_parent

    root = require_workspace()
    wt_path = worktrees_parent(root) / wt_id
    if not wt_path.is_dir():
        raise HTTPException(status_code=404, detail=tr("Worktree not found", "Worktree 不存在"))
    info = {"id": wt_id, "path": str(wt_path.resolve()), "branch": f"clutch/{wt_id}", "enabled": True}
    return describe_worktree(info, root)
