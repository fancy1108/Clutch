"""D36 — headless Agent HTTP API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["headless-agent"])


class AgentRunRequest(BaseModel):
    prompt: str
    workspace_path: str = Field(default="")
    agent_id: str = Field(default="")


@router.post("/api/agent/run")
async def agent_run_route(body: AgentRunRequest) -> dict[str, Any]:
    from src.headless_agent import run_headless_agent

    result = await run_headless_agent(
        prompt=body.prompt,
        workspace_path=body.workspace_path,
        agent_id=body.agent_id,
    )
    return {
        "exit_code": result.exit_code,
        "output": result.output,
        "run_id": result.run_id,
        "logs": result.logs,
    }
