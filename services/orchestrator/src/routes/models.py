"""HTTP API for LLM Provider settings and credentials configuration."""

from __future__ import annotations

import asyncio
from typing import Any
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

router = APIRouter(tags=["models"])


class ModelsConfigRequest(BaseModel):
    active_model_id: str | None = None
    provider_id: str | None = None
    api_key: str | None = None
    planner_model_id: str | None = None
    executor_model_id: str | None = None


class CliActivateProviderRequest(BaseModel):
    provider_id: str


class CliActivateModelRequest(BaseModel):
    model_ref: str


class ModelTestRequest(BaseModel):
    model_id: str


class CustomImageModelRequest(BaseModel):
    name: str
    api_model: str
    base_url: str
    provider_id: str = Field(default="custom")
    image_backend: str = Field(default="")
    api_key: str | None = None


class CustomChatModelRequest(BaseModel):
    name: str
    api_model: str
    base_url: str
    provider_id: str = Field(default="custom")
    api_key: str | None = None


class CustomVideoModelRequest(BaseModel):
    name: str
    api_model: str
    base_url: str
    provider_id: str = Field(default="custom")
    video_backend: str = Field(default="agnes")
    api_key: str | None = None


class CustomModelUpdateRequest(BaseModel):
    name: str
    api_model: str
    base_url: str
    api_key: str | None = None


class OpenCodeZenListRequest(BaseModel):
    api_key: str | None = None


@router.get("/api/models/credentials")
async def get_models_credentials() -> dict[str, Any]:
    from src.credentials.claude_code import credential_status
    from src.models_config import get_router

    return credential_status(get_router())


@router.get("/api/models/config")
async def get_models_config(response: Response) -> dict[str, Any]:
    from src.models_config import get_router, serialize_models_config

    response.headers["Cache-Control"] = "no-store"
    return serialize_models_config(get_router())


@router.post("/api/models/config")
async def update_models_config(body: ModelsConfigRequest) -> dict[str, str]:
    from src.adapters.opencode_zen_adapter import ZEN_DEFAULT_MODEL_ID, validate_opencode_zen_save
    from src.models_config import get_router, is_model_available, save_router, sync_local_ollama_models

    router = get_router()
    if body.provider_id is not None or (
        body.active_model_id and str(body.active_model_id).startswith("ollama")
    ):
        sync_local_ollama_models(router)
    if body.provider_id == "opencode" and body.api_key is not None:
        key = body.api_key.strip()
        model_id = body.active_model_id
        if not model_id:
            active = router._models.get(router.active_model_id)
            model_id = (
                router.active_model_id
                if active and active.provider_id == "opencode"
                else ZEN_DEFAULT_MODEL_ID
            )
        try:
            validate_opencode_zen_save(key, str(model_id), router)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
        router.set_api_key("opencode", key)
    elif body.provider_id and body.api_key is not None:
        router.set_api_key(body.provider_id, body.api_key.strip())  # type: ignore[arg-type]
    if body.active_model_id:
        if not is_model_available(router, body.active_model_id):
            raise HTTPException(
                status_code=400,
                detail={"message": "Model is not available — configure provider API key first"},
            )
        from src.custom_models import unhide_model_from_list

        unhide_model_from_list(body.active_model_id)
        router.set_active_model(body.active_model_id)
    if body.planner_model_id is not None or body.executor_model_id is not None:
        from src.preferences_storage import load_model_roles, save_model_roles

        current = load_model_roles()
        save_model_roles(
            body.planner_model_id if body.planner_model_id is not None else current["planner_model_id"],
            body.executor_model_id if body.executor_model_id is not None else current["executor_model_id"],
        )
        if body.executor_model_id and is_model_available(router, body.executor_model_id):
            router.set_active_model(body.executor_model_id)
    save_router(router)
    return {"status": "saved", "active_model_id": router.active_model_id}


@router.get("/api/models/credentials/{provider_id}")
async def get_provider_credential(provider_id: str) -> dict[str, Any]:
    from src.credentials.sources import is_clutch_managed_credential
    from src.models_config import get_router

    router = get_router()
    if not is_clutch_managed_credential(provider_id):  # type: ignore[arg-type]
        raise HTTPException(
            status_code=404,
            detail={"message": "No Clutch-managed key for this provider."},
        )
    api_key = router.get_api_key(provider_id)  # type: ignore[arg-type]
    return {"provider_id": provider_id, "configured": bool(api_key), "api_key": api_key or ""}


@router.delete("/api/models/credentials/{provider_id}")
async def delete_provider_credential(provider_id: str) -> dict[str, str]:
    from src.models_config import clear_provider_credential, get_router

    router = get_router()
    try:
        clear_provider_credential(router, provider_id)  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return {"status": "removed", "provider_id": provider_id}


@router.post("/api/models/rehydrate-cc-switch")
async def rehydrate_cc_switch_endpoint() -> dict[str, Any]:
    from src.models_config import get_router, rehydrate_cc_switch_models

    return rehydrate_cc_switch_models(get_router())


@router.get("/api/cli-config/{agent_type}/models")
async def get_cli_config_models(agent_type: str) -> dict[str, Any]:
    from src.cli_agent_config import normalize_cli_agent_type, scan_cli_models
    from src.workspace import get_workspace

    try:
        normalized = normalize_cli_agent_type(agent_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    workspace = get_workspace()
    workspace_path = workspace.get("workspace_path") if workspace else None
    return scan_cli_models(normalized, workspace_path=workspace_path)


@router.post("/api/cli-config/install-cc-switch-cli")
async def install_cc_switch_cli_endpoint() -> dict[str, Any]:
    from src.cli_agent_config import install_cc_switch_cli

    result = await asyncio.to_thread(install_cc_switch_cli)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail={"message": result.get("message", "install failed")})
    return result


@router.post("/api/cli-config/prefetch-cc-switch-cli")
async def prefetch_cc_switch_cli_endpoint() -> dict[str, Any]:
    from src.cli_agent_config import prefetch_cc_switch_cli_bundle

    return await asyncio.to_thread(prefetch_cc_switch_cli_bundle)


@router.post("/api/cli-config/{agent_type}/activate-model")
async def activate_cli_config_model(
    agent_type: str,
    body: CliActivateModelRequest,
) -> dict[str, Any]:
    from src.cli_agent_config import activate_cli_model, normalize_cli_agent_type

    try:
        normalized = normalize_cli_agent_type(agent_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    result = activate_cli_model(normalized, body.model_ref)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail={"message": result.get("message", "activate failed")})
    return result


@router.post("/api/models/test")
async def test_models_connection(body: ModelTestRequest) -> dict[str, Any]:
    from src.models_config import get_router, test_model_connection

    return test_model_connection(get_router(), body.model_id)


@router.post("/api/models/custom/image")
async def add_custom_image_model(body: CustomImageModelRequest) -> dict[str, Any]:
    from src.custom_models import add_custom_model
    from src.models_config import get_router, serialize_models_config

    router = get_router()
    try:
        spec = add_custom_model(
            router,
            name=body.name,
            api_model=body.api_model,
            base_url=body.base_url,
            provider_id=body.provider_id,
            model_kind="image",
            image_backend=body.image_backend,
            api_key=body.api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return {
        "status": "created",
        "model_id": spec.id,
        "config": serialize_models_config(router),
    }


@router.post("/api/models/custom/chat")
async def add_custom_chat_model(body: CustomChatModelRequest) -> dict[str, Any]:
    from src.custom_models import add_custom_model
    from src.models_config import get_router, serialize_models_config

    router = get_router()
    try:
        spec = add_custom_model(
            router,
            name=body.name,
            api_model=body.api_model,
            base_url=body.base_url,
            provider_id=body.provider_id,
            model_kind="chat",
            api_key=body.api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return {
        "status": "created",
        "model_id": spec.id,
        "config": serialize_models_config(router),
    }


@router.post("/api/models/custom/video")
async def add_custom_video_model(body: CustomVideoModelRequest) -> dict[str, Any]:
    from src.custom_models import add_custom_model
    from src.models_config import get_router, serialize_models_config

    router = get_router()
    try:
        spec = add_custom_model(
            router,
            name=body.name,
            api_model=body.api_model,
            base_url=body.base_url,
            provider_id=body.provider_id,
            model_kind="video",
            video_backend=body.video_backend or "agnes",
            api_key=body.api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return {
        "status": "created",
        "model_id": spec.id,
        "config": serialize_models_config(router),
    }


@router.patch("/api/models/custom/{model_id}")
async def update_custom_model_entry(model_id: str, body: CustomModelUpdateRequest) -> dict[str, Any]:
    from src.custom_models import update_custom_model
    from src.models_config import get_router, serialize_models_config

    router = get_router()
    try:
        spec = update_custom_model(
            router,
            model_id,
            name=body.name,
            api_model=body.api_model,
            base_url=body.base_url,
            api_key=body.api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return {
        "status": "updated",
        "model_id": spec.id,
        "config": serialize_models_config(router),
    }


@router.delete("/api/models/custom/{model_id}")
async def delete_custom_image_model(model_id: str) -> dict[str, Any]:
    from src.custom_models import remove_model_from_list
    from src.models_config import get_router, serialize_models_config

    router = get_router()
    try:
        remove_model_from_list(router, model_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return {"status": "deleted", "model_id": model_id, "config": serialize_models_config(router)}


@router.post("/api/models/opencode-zen/list")
async def list_opencode_zen_catalog(_body: OpenCodeZenListRequest) -> dict[str, Any]:
    from src.adapters.opencode_zen_adapter import fetch_opencode_zen_catalog

    try:
        models = fetch_opencode_zen_catalog()
        return {"ok": True, "models": models}
    except Exception as exc:
        return {"ok": False, "models": [], "message": str(exc)}


@router.get("/api/models/ollama")
async def list_local_ollama_models() -> dict[str, Any]:
    import urllib.error
    import shutil
    from pathlib import Path
    try:
        from src.adapters.ollama_adapter import get_ollama_models
        models = get_ollama_models()
        return {"ok": True, "models": models}
    except Exception as exc:
        reason = "unknown"
        inner = exc.__cause__ if hasattr(exc, "__cause__") else None
        if "ConnectionRefusedError" in str(exc) or "connection refused" in str(exc).lower() or (inner and isinstance(inner, urllib.error.URLError)):
            reason = "connection_refused"
            
        app_exists = Path("/Applications/Ollama.app").is_dir() or Path("~/Applications/Ollama.app").expanduser().is_dir()
        binary_exists = shutil.which("ollama") is not None
        
        return {
            "ok": False,
            "models": [],
            "error": str(exc),
            "reason": reason,
            "app_installed": app_exists,
            "binary_installed": binary_exists
        }


@router.post("/api/models/ollama/start")
async def start_ollama_service() -> dict[str, Any]:
    import subprocess
    import shutil
    from pathlib import Path
    
    app_paths = ["/Applications/Ollama.app", str(Path.home() / "Applications/Ollama.app")]
    app_exists = any(Path(p).is_dir() for p in app_paths)
    
    if app_exists:
        try:
            subprocess.Popen(["open", "-a", "Ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"ok": True, "message": "Launching Ollama.app..."}
        except Exception as exc:
            pass
            
    binary = shutil.which("ollama")
    if binary:
        try:
            subprocess.Popen([binary, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return {"ok": True, "message": "Starting `ollama serve` in background..."}
        except Exception as exc:
            return {"ok": False, "error": f"Failed to run `ollama serve`: {exc}"}
            
    return {"ok": False, "error": "Ollama.app not found and `ollama` command not in PATH."}
