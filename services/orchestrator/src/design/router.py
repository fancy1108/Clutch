"""HTTP API for Design mode (D36 session-scoped)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.design import service
from src.workspace import WorkspaceError

router = APIRouter(prefix="/api/design", tags=["design"])


class EnsureSessionBody(BaseModel):
    run_id: str = Field(min_length=1)
    title: str = ""
    prompt: str = ""


class GenerateBody(BaseModel):
    prompt: str = Field(default="", max_length=8000)
    device: str = "web"
    reference_image: str | None = Field(
        default=None,
        description="Optional data URL (data:image/...) used as visual reference",
        max_length=12_000_000,
    )
    reference_md: str | None = Field(
        default=None,
        description="Optional Design.md / design-system markdown text",
        max_length=220_000,
    )
    reference_md_name: str | None = Field(default=None, max_length=240)
    reference_url: str | None = Field(
        default=None,
        description="Optional website URL used as visual/style reference",
        max_length=2000,
    )
    design_system: str | None = Field(
        default="clutch",
        description="Built-in design preset when no style reference is attached (default: clutch)",
        max_length=32,
    )


class IterateBody(BaseModel):
    instruction: str = Field(min_length=1, max_length=4000)
    target_kind: str | None = Field(
        default=None,
        description="Selected canvas target: ui | spec | md | image | url | process",
    )
    target_id: str | None = Field(default=None, description="Screen id when target is ui")
    element_path: str | None = Field(default=None, max_length=2000)
    element_label: str | None = Field(default=None, max_length=400)
    mode: str | None = Field(
        default=None,
        description="modify | add | auto — auto infers from instruction (unknown → add)",
    )


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, WorkspaceError):
        return HTTPException(status_code=400, detail={"message": str(exc)})
    if isinstance(exc, service.DesignError):
        return HTTPException(status_code=400, detail={"message": str(exc)})
    return HTTPException(status_code=500, detail={"message": str(exc) or "Internal Server Error"})


@router.post("/sessions")
async def ensure_design_session(body: EnsureSessionBody) -> dict[str, Any]:
    try:
        return service.ensure_session(body.run_id, title=body.title, prompt=body.prompt)
    except (WorkspaceError, service.DesignError, OSError, json.JSONDecodeError) as exc:
        raise _http(exc) from exc


@router.get("/sessions")
async def list_design_sessions() -> dict[str, Any]:
    try:
        return {"sessions": service.list_sessions()}
    except (WorkspaceError, OSError, json.JSONDecodeError) as exc:
        raise _http(exc) from exc


@router.get("/sessions/{run_id}")
async def get_design_session(run_id: str) -> dict[str, Any]:
    try:
        return service.get_session(run_id)
    except (WorkspaceError, service.DesignError, OSError, json.JSONDecodeError) as exc:
        raise _http(exc) from exc


@router.get("/sessions/{run_id}/screens/{screen_id}")
async def get_design_screen_html(run_id: str, screen_id: str):
    """Raw screen HTML for live sidebar thumbnails (matches canvas UI)."""
    from fastapi.responses import HTMLResponse

    try:
        html = service.read_screen_html(run_id, screen_id)
        return HTMLResponse(
            content=html,
            headers={"Cache-Control": "no-store"},
        )
    except (WorkspaceError, service.DesignError, OSError) as exc:
        raise _http(exc) from exc


@router.post("/sessions/{run_id}/generate")
async def generate_design_session(run_id: str, body: GenerateBody) -> dict[str, Any]:
    """Start two-phase generate in background; poll GET /sessions/{run_id} for progress."""
    try:
        prompt = (body.prompt or "").strip()
        has_ref = bool(
            (body.reference_image or "").strip()
            or (body.reference_md or "").strip()
            or (body.reference_url or "").strip()
        )
        if not prompt and not has_ref:
            raise service.DesignError("Prompt or reference is required")
        return service.start_generate_session(
            run_id,
            prompt=prompt,
            device=body.device,
            reference_image=body.reference_image,
            reference_md=body.reference_md,
            reference_md_name=body.reference_md_name,
            reference_url=body.reference_url,
            design_system=body.design_system,
        )
    except (WorkspaceError, service.DesignError, OSError, json.JSONDecodeError) as exc:
        raise _http(exc) from exc


@router.post("/sessions/{run_id}/iterate")
async def iterate_design_session(run_id: str, body: IterateBody) -> dict[str, Any]:
    try:
        return service.iterate_session(
            run_id,
            body.instruction,
            target_kind=body.target_kind,
            target_id=body.target_id,
            element_path=body.element_path,
            element_label=body.element_label,
            mode=body.mode,
        )
    except (WorkspaceError, service.DesignError, OSError, json.JSONDecodeError) as exc:
        raise _http(exc) from exc


@router.post("/sessions/{run_id}/approve-prototype")
async def approve_design_prototype(run_id: str) -> dict[str, Any]:
    try:
        return service.approve_prototype(run_id)
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc


@router.post("/sessions/{run_id}/generate-react")
async def generate_design_react(run_id: str) -> dict[str, Any]:
    try:
        return service.generate_react(run_id)
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc


@router.post("/sessions/{run_id}/preview/start")
async def start_design_preview(run_id: str) -> dict[str, Any]:
    try:
        return service.start_preview(run_id)
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc


@router.post("/sessions/{run_id}/preview/stop")
async def stop_design_preview(run_id: str) -> dict[str, Any]:
    try:
        return service.stop_preview(run_id)
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc


@router.post("/sessions/{run_id}/approve-react")
async def approve_design_react(run_id: str) -> dict[str, Any]:
    try:
        return service.approve_react(run_id)
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc


@router.post("/sessions/{run_id}/send-to-coding")
async def send_design_to_coding(run_id: str) -> dict[str, Any]:
    try:
        return service.coding_handoff_payload(run_id)
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc


# Legacy project routes kept for older clients / tests
@router.get("/templates")
async def list_design_templates() -> dict[str, Any]:
    return {"templates": service.list_templates()}


@router.get("/projects")
async def list_design_projects() -> dict[str, Any]:
    try:
        return {"projects": service.list_projects()}
    except WorkspaceError as exc:
        raise _http(exc) from exc


@router.post("/projects")
async def create_design_project(body: dict[str, Any]) -> dict[str, Any]:
    try:
        return service.create_project(
            name=str(body.get("name") or "Untitled"),
            prompt=str(body.get("prompt") or ""),
            template_id=str(body.get("template_id") or "neutral"),
        )
    except (WorkspaceError, service.DesignError, OSError) as exc:
        raise _http(exc) from exc


@router.get("/projects/{project_id}")
async def get_design_project(project_id: str) -> dict[str, Any]:
    try:
        return service.get_project(project_id)
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc


@router.delete("/projects/{project_id}")
async def delete_design_project(project_id: str) -> dict[str, str]:
    try:
        service.delete_project(project_id)
        return {"status": "ok"}
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc


@router.post("/projects/{project_id}/generate")
async def generate_design_prototype(project_id: str, body: dict[str, Any]) -> dict[str, Any]:
    try:
        return service.generate_prototype(
            project_id,
            prompt=body.get("prompt"),
            template_id=body.get("template_id"),
        )
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc


@router.post("/projects/{project_id}/screens/{screen_id}/iterate")
async def iterate_design_screen(project_id: str, screen_id: str, body: IterateBody) -> dict[str, Any]:
    try:
        return service.iterate_screen(project_id, screen_id, body.instruction)
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc


@router.post("/projects/{project_id}/approve-prototype")
async def approve_design_prototype_legacy(project_id: str) -> dict[str, Any]:
    try:
        return service.approve_prototype(project_id)
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc


@router.post("/projects/{project_id}/generate-react")
async def generate_design_react_legacy(project_id: str) -> dict[str, Any]:
    try:
        return service.generate_react(project_id)
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc


@router.post("/projects/{project_id}/preview/start")
async def start_design_preview_legacy(project_id: str) -> dict[str, Any]:
    try:
        return service.start_preview(project_id)
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc


@router.post("/projects/{project_id}/preview/stop")
async def stop_design_preview_legacy(project_id: str) -> dict[str, Any]:
    try:
        return service.stop_preview(project_id)
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc


@router.post("/projects/{project_id}/approve-react")
async def approve_design_react_legacy(project_id: str) -> dict[str, Any]:
    try:
        return service.approve_react(project_id)
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc


@router.post("/projects/{project_id}/send-to-coding")
async def send_design_to_coding_legacy(project_id: str) -> dict[str, Any]:
    try:
        return service.coding_handoff_payload(project_id)
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc


@router.post("/projects/{project_id}/vision")
async def design_vision_generate(project_id: str, body: dict[str, Any]) -> dict[str, Any]:
    try:
        return service.apply_vision_note(
            project_id,
            str(body.get("note") or ""),
            image_data_url=body.get("image_data_url"),
        )
    except (WorkspaceError, service.DesignError) as exc:
        raise _http(exc) from exc
