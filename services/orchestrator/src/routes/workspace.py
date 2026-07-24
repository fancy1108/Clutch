"""HTTP API for Workspace & Repository Groups management."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.workspace import WorkspaceError
from src.preferences_storage import tr

router = APIRouter(tags=["workspace"])


class WorkspaceRequest(BaseModel):
    path: str


class RepositoryGroupRequest(BaseModel):
    name: str


class RepositoryGroupUpdateRequest(BaseModel):
    name: str | None = None
    collapsed: bool | None = None
    workspace_ids: list[str] | None = None


def _workspace_http_error(exc: WorkspaceError) -> HTTPException:
    return HTTPException(status_code=403, detail={"message": str(exc)})


@router.get("/api/workspaces")
async def list_workspaces_endpoint() -> dict[str, Any]:
    from src.workspace import list_workspaces
    return list_workspaces()


@router.post("/api/workspaces")
async def add_workspace_endpoint(body: WorkspaceRequest) -> dict[str, str]:
    from src.skills_storage import ensure_default_skill_mounts
    from src.workspace import WorkspaceError, add_workspace

    try:
        entry = add_workspace(body.path)
        ensure_default_skill_mounts(workspace_path=entry.get("workspace_path"))
        return entry
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc


@router.post("/api/workspaces/{workspace_id}/activate")
async def activate_workspace_endpoint(workspace_id: str) -> dict[str, str]:
    from src.skills_storage import ensure_default_skill_mounts
    from src.workspace import WorkspaceError, activate_workspace

    try:
        entry = activate_workspace(workspace_id)
        ensure_default_skill_mounts(workspace_path=entry.get("workspace_path"))
        return entry
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc


@router.delete("/api/workspaces/{workspace_id}")
async def remove_workspace_endpoint(workspace_id: str) -> dict[str, str]:
    from src.workspace import WorkspaceError, remove_workspace

    try:
        remove_workspace(workspace_id)
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc
    return {"status": "removed", "workspace_id": workspace_id}


@router.get("/api/repository-groups")
async def list_repository_groups_endpoint() -> dict[str, Any]:
    from src.workspace import list_repository_groups
    return list_repository_groups()


@router.post("/api/repository-groups")
async def create_repository_group_endpoint(body: RepositoryGroupRequest) -> dict[str, Any]:
    from src.workspace import create_repository_group

    try:
        return create_repository_group(body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@router.patch("/api/repository-groups/{group_id}")
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


@router.delete("/api/repository-groups/{group_id}")
async def delete_repository_group_endpoint(group_id: str) -> dict[str, str]:
    from src.workspace import WorkspaceError, delete_repository_group

    try:
        delete_repository_group(group_id)
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc
    return {"status": "removed", "group_id": group_id}


@router.get("/api/workspace")
async def get_workspace_endpoint() -> dict[str, str]:
    from src.workspace import get_workspace

    info = get_workspace()
    if info is None:
        raise HTTPException(status_code=404, detail={"message": tr("Workspace not authorized yet", "尚未授权工作区")})
    return info


@router.post("/api/workspace")
async def set_workspace_endpoint(body: WorkspaceRequest) -> dict[str, str]:
    from src.skills_storage import ensure_default_skill_mounts
    from src.workspace import WorkspaceError, add_workspace

    try:
        entry = add_workspace(body.path)
        ensure_default_skill_mounts(workspace_path=entry.get("workspace_path"))
        return entry
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc


@router.get("/api/workspace/git")
async def get_workspace_git() -> dict[str, Any]:
    from src.workspace import WorkspaceError, get_git_info

    try:
        return get_git_info()
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc


@router.get("/api/workspace/tree")
async def get_workspace_tree() -> dict[str, Any]:
    from src.workspace import WorkspaceError, list_tree

    try:
        return {"nodes": list_tree()}
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc


@router.get("/api/workspace/file")
async def read_workspace_file(path: str) -> dict[str, str]:
    from src.workspace import WorkspaceError, read_file

    try:
        return {"path": path, "content": read_file(path)}
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc


class AttachmentUploadBody(BaseModel):
    data_url: str = Field(..., min_length=16)
    analyze: bool = True


@router.post("/api/workspace/attachments")
async def upload_workspace_attachment(body: AttachmentUploadBody) -> dict[str, Any]:
    from src.workspace import WorkspaceError
    from src.workspace_attachments import save_attachment_data_url

    try:
        return save_attachment_data_url(body.data_url, analyze=body.analyze)
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc


@router.get("/api/workspace/file/resolve")
async def resolve_workspace_file(path: str) -> dict[str, Any]:
    from src.workspace import WorkspaceError
    from src.workspace_attachments import resolve_workspace_file_path

    try:
        return resolve_workspace_file_path(path)
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc


@router.get("/api/workspace/media")
async def read_workspace_media(path: str) -> FileResponse:
    from src.workspace import WorkspaceError, resolve_allowed_path

    try:
        target = resolve_allowed_path(path)
    except WorkspaceError as exc:
        raise _workspace_http_error(exc) from exc
    if not target.is_file():
        raise HTTPException(
            status_code=404,
            detail={"message": tr("File does not exist", "文件不存在"), "message_zh": "文件不存在"},
        )
    suffix = target.suffix.lower()
    media_type = "video/mp4" if suffix == ".mp4" else "application/octet-stream"
    return FileResponse(target, media_type=media_type, filename=target.name)
