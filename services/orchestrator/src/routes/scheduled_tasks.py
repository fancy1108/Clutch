"""Cap-D25 — scheduled / loop tasks API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.preferences_storage import tr

router = APIRouter(tags=["scheduled-tasks"])


class ScheduledTaskCreateRequest(BaseModel):
    title: str = Field(default="")
    prompt: str
    interval_sec: int = Field(ge=30)
    enabled: bool = Field(default=False)
    run_agent_turn: bool = Field(default=False)
    agent_id: str = Field(default="")
    workspace_path: str = Field(default="")
    confirm: bool = Field(default=False)


@router.get("/api/scheduled-tasks")
async def list_scheduled_tasks_route() -> dict[str, Any]:
    from src.scheduled_tasks import list_scheduled_tasks

    return {"tasks": list_scheduled_tasks()}


@router.post("/api/scheduled-tasks")
async def create_scheduled_task_route(body: ScheduledTaskCreateRequest) -> dict[str, Any]:
    from src.scheduled_tasks import confirm_enable_scheduled_task, create_scheduled_task

    if body.enabled and not body.confirm:
        raise HTTPException(
            status_code=400,
            detail=tr(
                "Creating an enabled scheduled task requires confirm=true.",
                "创建已启用的定时任务需要 confirm=true。",
            ),
        )
    try:
        task = create_scheduled_task(
            title=body.title,
            prompt=body.prompt,
            interval_sec=body.interval_sec,
            enabled=body.enabled,
            run_agent_turn=body.run_agent_turn,
            agent_id=body.agent_id,
            workspace_path=body.workspace_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if body.enabled:
        task = confirm_enable_scheduled_task(task["id"]) or task
    return {"task": task}


@router.delete("/api/scheduled-tasks/{task_id}")
async def delete_scheduled_task_route(task_id: str) -> dict[str, Any]:
    from src.scheduled_tasks import delete_scheduled_task

    if not delete_scheduled_task(task_id):
        raise HTTPException(status_code=404, detail="task not found")
    return {"deleted": task_id}


@router.post("/api/scheduled-tasks/{task_id}/enable")
async def enable_scheduled_task_route(task_id: str) -> dict[str, Any]:
    from src.scheduled_tasks import confirm_enable_scheduled_task

    task = confirm_enable_scheduled_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return {"task": task}
