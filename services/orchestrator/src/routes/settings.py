"""HTTP API for preferences, MCP, skills, tools, and agents configuration."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.preferences_storage import tr

router = APIRouter(tags=["settings"])


class AgentsSaveRequest(BaseModel):
    agents: list[dict[str, Any]]


class AgentPromptGenerateRequest(BaseModel):
    name: str
    description: str = Field(default="")


class SkillsMountRequest(BaseModel):
    path: str


class SkillsToggleRequest(BaseModel):
    key: str
    is_active: bool = Field(default=True)


class ToolConnectRequest(BaseModel):
    tool_id: str


class McpRegisterRequest(BaseModel):
    name: str
    transport: str = Field(default="stdio")
    endpoint: str
    env: dict[str, str] | None = None


class McpServerIdRequest(BaseModel):
    id: str
    enabled: bool | None = None


class McpSaveConfigRequest(BaseModel):
    servers: list[dict[str, Any]]


class ThemePreferenceRequest(BaseModel):
    theme_id: str


class LanguagePreferenceRequest(BaseModel):
    language: str


class PermissionModeRequest(BaseModel):
    mode: str


class StrictSandboxRequest(BaseModel):
    enabled: bool


class AllowNetworkRequest(BaseModel):
    enabled: bool


class CrossSessionMemoryRequest(BaseModel):
    enabled: bool


class DefaultWorkspaceRequest(BaseModel):
    workspace_id: str = ""


class HighRiskConfirmRequest(BaseModel):
    enabled: bool


class TrustItemRequest(BaseModel):
    kind: str
    item_id: str


class CapabilityPackImportRequest(BaseModel):
    path: str


class CapabilityPackIdRequest(BaseModel):
    pack_id: str


class PermissionRulesRequest(BaseModel):
    rules: list[dict[str, Any]] = Field(default_factory=list)


class FontSizePreferenceRequest(BaseModel):
    font_size: str


class AvatarPreferenceRequest(BaseModel):
    avatar: str


class UserNamePreferenceRequest(BaseModel):
    user_name: str


def _skills_registry_payload_local(*, rescan: bool = True) -> dict[str, Any]:
    from src.main import _skills_registry_payload
    return _skills_registry_payload(rescan=rescan)


def _extract_llm_text(result: object) -> str:
    if isinstance(result, dict):
        content = result.get("content")
        return str(content).strip() if content else ""
    return str(result).strip()


def _build_agent_prompt_skeleton_fallback(name: str, description: str) -> str:
    agent_name = name.strip() or "Custom Agent"
    mission = description.strip() or "Define your core execution task here."
    return (
        f"# {agent_name}\n\n"
        f"You are **{agent_name}**, an operational AI agent in the Clutch workspace.\n\n"
        f"## Mission\n{mission}\n\n"
        "## Operating Principles\n"
        "- Stay focused on the assigned task.\n"
        "- Surface blockers clearly before proceeding.\n"
        "- Prefer actionable outputs over vague summaries.\n\n"
        "## Constraints\n"
        "- Follow workspace conventions and user instructions.\n"
        "- Ask for clarification when requirements are ambiguous."
    )


@router.get("/api/agents")
async def list_agents_endpoint() -> dict[str, list[dict[str, Any]]]:
    from src.agent_storage import list_agents
    return {"agents": list_agents()}


@router.get("/api/agents/{agent_id}/prompt-assembly")
async def agent_prompt_assembly_endpoint(agent_id: str) -> dict[str, Any]:
    """D53: layer names + char counts for the current workspace / permission mode (no full dump)."""
    from src.agent_mcp import resolve_agent_mcp_servers
    from src.agent_prompt import compose_agent_prompt_assembly
    from src.agent_storage import BUILTIN_AGENT_ID, get_agent_by_id
    from src.agent_type import is_clutch_agent, resolve_model_for_agent
    from src.models_config import get_router
    from src.preferences_storage import load_permission_mode

    resolved = (agent_id or "").strip() or BUILTIN_AGENT_ID
    agent = get_agent_by_id(resolved)
    if agent is None:
        raise HTTPException(status_code=404, detail={"message": f"Agent not found: {resolved}"})

    router = get_router()
    model, _model_id = resolve_model_for_agent(router, agent)
    model_name = model.name if is_clutch_agent(agent) else str(agent.get("name", "Agent"))
    model_api = (
        (getattr(model, "api_model", None) or model.name)
        if is_clutch_agent(agent)
        else str(agent.get("agentType") or "cli")
    )
    assembly = compose_agent_prompt_assembly(
        agent,
        model_name=model_name,
        model_api=model_api,
        mcp_servers_bound=bool(resolve_agent_mcp_servers(agent)),
        permission_mode=load_permission_mode(),
        include_skill_bodies=False,
    )
    return {
        "agent_id": str(agent.get("id", resolved)),
        "permission_mode": load_permission_mode(),
        **assembly.summary(),
    }


@router.post("/api/agents")
async def save_agents_endpoint(body: AgentsSaveRequest) -> dict[str, str]:
    from src.agent_storage import save_agents

    save_agents(body.agents)
    return {"status": "saved"}


@router.post("/api/agents/generate-prompt")
async def generate_agent_prompt_endpoint(body: AgentPromptGenerateRequest) -> dict[str, str]:
    from src.models_config import get_router, is_model_available

    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail={"message": "Agent name is required."})

    description = body.description.strip()
    fallback = _build_agent_prompt_skeleton_fallback(name, description)

    router = get_router()
    model_id = router.active_model_id
    if not is_model_available(router, model_id):
        return {"prompt": fallback, "source": "template"}

    meta_prompt = (
        "You are helping design an AI agent system prompt skeleton.\n"
        f"Agent Name: {name}\n"
        f"Short Description: {description or '(none provided)'}\n\n"
        "Generate a concise system prompt skeleton in markdown with:\n"
        '1. One clear persona line (e.g. "You are a ...")\n'
        "2. Core responsibilities (3-5 bullets)\n"
        "3. Output/constraints section (2-3 bullets)\n\n"
        "Keep it under 20 lines. Output only the prompt text, no preamble or explanation."
    )
    try:
        result = router.complete(meta_prompt, model_id=model_id)
        text = _extract_llm_text(result)
        if not text:
            return {"prompt": fallback, "source": "template"}
        return {"prompt": text, "source": "llm"}
    except Exception:
        return {"prompt": fallback, "source": "template"}


@router.get("/api/skills")
async def get_skills_registry() -> dict[str, Any]:
    return _skills_registry_payload_local(rescan=True)


@router.post("/api/skills/mount")
async def mount_skills_directory(body: SkillsMountRequest) -> dict[str, Any]:
    from src.skills_storage import load_registry, save_registry

    raw = body.path.strip()
    if not raw:
        raise HTTPException(status_code=400, detail={"message": tr("Path cannot be empty", "路径不能为空")})
    resolved = str(Path(raw).expanduser().resolve())
    data = load_registry()
    mounted = list(data["mounted_directories"])
    if resolved not in mounted:
        mounted.append(resolved)
    save_registry(mounted_directories=mounted)
    return _skills_registry_payload_local(rescan=True)


@router.post("/api/skills/unmount")
async def unmount_skills_directory(body: SkillsMountRequest) -> dict[str, Any]:
    from src.skills_storage import load_registry, save_registry

    raw = body.path.strip()
    if not raw:
        raise HTTPException(status_code=400, detail={"message": tr("Path cannot be empty", "路径不能为空")})
    resolved = str(Path(raw).expanduser().resolve())
    data = load_registry()
    mounted = [item for item in data["mounted_directories"] if item != resolved]
    skills = [item for item in data["skills"] if item.get("source") != resolved]
    save_registry(mounted_directories=mounted, skills=skills)
    return _skills_registry_payload_local(rescan=True)


@router.post("/api/skills/toggle")
async def toggle_skill(body: SkillsToggleRequest) -> dict[str, Any]:
    from src.skills_storage import load_registry, save_registry

    data = _skills_registry_payload_local(rescan=False)
    updated = False
    skills = []
    for item in data["skills"]:
        if item.get("key") == body.key:
            skills.append({**item, "isActiveGlobally": body.is_active})
            updated = True
        else:
            skills.append(item)
    if not updated:
        raise HTTPException(status_code=404, detail={"message": tr("Skill not found", "未找到该 Skill")})
    save_registry(skills=skills)
    return _skills_registry_payload_local(rescan=False)


@router.get("/api/cli-config/{agent_type}/skills")
async def get_cli_config_skills(agent_type: str) -> dict[str, Any]:
    from src.cli_agent_config import normalize_cli_agent_type, scan_cli_skills
    from src.workspace import get_workspace

    try:
        normalized = normalize_cli_agent_type(agent_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    workspace = get_workspace()
    workspace_path = workspace.get("workspace_path") if workspace else None
    return scan_cli_skills(normalized, workspace_path=workspace_path)


@router.get("/api/cli-config/{agent_type}/mcp")
async def get_cli_config_mcp(agent_type: str) -> dict[str, Any]:
    from src.cli_agent_config import normalize_cli_agent_type, scan_cli_mcp
    from src.workspace import get_workspace

    try:
        normalized = normalize_cli_agent_type(agent_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    workspace = get_workspace()
    workspace_path = workspace.get("workspace_path") if workspace else None
    return scan_cli_mcp(normalized, workspace_path=workspace_path)


@router.post("/api/cli-config/{agent_type}/repair-settings")
async def repair_cli_config_settings(agent_type: str) -> dict[str, Any]:
    from src.cli_agent_config import repair_cli_agent_config

    result = await asyncio.to_thread(repair_cli_agent_config, agent_type)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail={"message": result.get("message", "repair failed")})
    return result


@router.post("/api/cli-config/{agent_type}/activate-provider")
async def activate_cli_config_provider(
    agent_type: str,
    body: Any,
) -> dict[str, Any]:
    from src.cli_agent_config import activate_cli_provider, normalize_cli_agent_type

    try:
        normalized = normalize_cli_agent_type(agent_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    provider_id = body.provider_id if hasattr(body, "provider_id") else body.get("provider_id")
    result = activate_cli_provider(normalized, provider_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail={"message": result.get("message", "activate failed")})
    return result


@router.get("/api/tools/status")
async def tools_status() -> dict[str, list[dict[str, Any]]]:
    from src.tools_status import list_tools_status
    return {"tools": list_tools_status(include_all=True)}


@router.post("/api/tools/auto-configure")
async def auto_configure_tool_endpoint(body: ToolConnectRequest) -> dict[str, Any]:
    from src.tools_status import resolve_tool_binary
    from src.engine_router import CLI_ROUTING_CONFIGS, save_custom_cli_configs, load_custom_cli_configs
    from src.agent_type import AGENT_TYPES, _LEGACY_AI_ENGINE_TO_TYPE

    binary_path = resolve_tool_binary(body.tool_id)
    if not binary_path:
        raise HTTPException(status_code=400, detail={"message": f"Tool {body.tool_id} is not installed on this machine."})

    from src.agent_type import normalize_agent_type
    from src.provider_registry import resolve_provider_spec
    from src.runtime_strategy import RuntimeStrategy

    if resolve_provider_spec(normalize_agent_type(body.tool_id)).runtime_strategy == RuntimeStrategy.HTTP_DAEMON:
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    f"{body.tool_id} uses Clutch's native HTTP integration "
                    "and does not need shell CLI auto-configure."
                ),
            },
        )

    try:
        from src.tools_status import auto_configure_cli_via_llm
        config = auto_configure_cli_via_llm(body.tool_id, binary_path)

        candidate = _LEGACY_AI_ENGINE_TO_TYPE.get(body.tool_id, body.tool_id)
        agent_type_key = candidate if candidate in AGENT_TYPES else body.tool_id

        custom_configs = load_custom_cli_configs()
        custom_configs[agent_type_key] = config
        save_custom_cli_configs(custom_configs)

        CLI_ROUTING_CONFIGS[agent_type_key] = config

        return {"status": "configured", "config": config}
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": str(exc)}) from exc


@router.post("/api/tools/connect")
async def connect_tool_endpoint(body: ToolConnectRequest) -> dict[str, Any]:
    from src.tools_status import connect_tool

    try:
        return connect_tool(body.tool_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@router.post("/api/tools/disconnect")
async def disconnect_tool_endpoint(body: ToolConnectRequest) -> dict[str, Any]:
    from src.tools_status import disconnect_tool

    try:
        return disconnect_tool(body.tool_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@router.get("/api/mcp/status")
async def mcp_status() -> dict[str, Any]:
    from src.mcp_storage import build_mcp_status_payload
    return await build_mcp_status_payload()


@router.post("/api/mcp/servers/register")
async def register_mcp_server(body: McpRegisterRequest) -> dict[str, Any]:
    from src.mcp_storage import build_mcp_status_payload, register_server

    try:
        register_server(
            name=body.name,
            transport=body.transport,
            endpoint=body.endpoint,
            env=body.env,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return await build_mcp_status_payload()


@router.post("/api/mcp/servers/remove")
async def remove_mcp_server(body: McpServerIdRequest) -> dict[str, Any]:
    from src.mcp_storage import build_mcp_status_payload, remove_server

    try:
        remove_server(body.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    return await build_mcp_status_payload()


@router.post("/api/mcp/servers/toggle")
async def toggle_mcp_server(body: McpServerIdRequest) -> dict[str, Any]:
    from src.mcp_storage import build_mcp_status_payload, toggle_server

    if body.enabled is None:
        raise HTTPException(status_code=400, detail={"message": tr("enabled field is required", "enabled 字段必填")})
    try:
        toggle_server(body.id, enabled=body.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    return await build_mcp_status_payload()


@router.post("/api/mcp/servers/test")
async def test_mcp_server(body: McpServerIdRequest) -> dict[str, Any]:
    """D38 — probe one Hub server; return ok + toolsCount or a readable error."""
    from src.mcp_storage import probe_server_by_id

    try:
        return await probe_server_by_id(body.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc


class McpResourceReadRequest(BaseModel):
    id: str
    uri: str


class McpResourcePinRequest(BaseModel):
    server_id: str
    uri: str
    name: str | None = None
    mimeType: str | None = None
    text: str | None = None


@router.get("/api/mcp/servers/{server_id}/resources")
async def list_mcp_resources(server_id: str) -> dict[str, Any]:
    """D43 — list resources exposed by a Hub server."""
    from src.mcp_resources import list_server_resources

    try:
        return await list_server_resources(server_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@router.post("/api/mcp/servers/resources/read")
async def read_mcp_resource(body: McpResourceReadRequest) -> dict[str, Any]:
    """D43 — read one resource body."""
    from src.mcp_resources import read_server_resource

    try:
        return await read_server_resource(body.id, body.uri)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@router.get("/api/mcp/resource-pins")
async def get_mcp_resource_pins() -> dict[str, Any]:
    from src.mcp_resources import load_resource_pins

    pins = load_resource_pins()
    return {"pins": pins, "count": len(pins)}


@router.post("/api/mcp/resource-pins")
async def add_mcp_resource_pin(body: McpResourcePinRequest) -> dict[str, Any]:
    from src.mcp_resources import pin_resource

    try:
        pins = await pin_resource(
            {
                "server_id": body.server_id,
                "uri": body.uri,
                "name": body.name,
                "mimeType": body.mimeType,
                "text": body.text,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return {"pins": pins, "count": len(pins)}


@router.post("/api/mcp/resource-pins/remove")
async def remove_mcp_resource_pin(body: McpResourcePinRequest) -> dict[str, Any]:
    from src.mcp_resources import unpin_resource

    pins = unpin_resource(server_id=body.server_id, uri=body.uri)
    return {"pins": pins, "count": len(pins)}


@router.post("/api/mcp/config/save")
async def save_mcp_config(body: McpSaveConfigRequest) -> dict[str, Any]:
    from src.mcp_storage import build_mcp_status_payload, save_raw_config

    try:
        save_raw_config(body.servers)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return await build_mcp_status_payload()


@router.post("/api/mcp/import/claude")
async def import_claude_mcp() -> dict[str, Any]:
    from src.mcp_storage import build_mcp_status_payload, import_from_claude

    import_from_claude()
    return await build_mcp_status_payload()


@router.get("/api/preferences")
async def get_preferences() -> dict[str, str]:
    from src.preferences_storage import load_preferences
    return load_preferences()


@router.get("/api/preferences/theme")
async def get_theme_preference() -> dict[str, str]:
    from src.preferences_storage import load_preferences
    return load_preferences()


@router.post("/api/preferences/theme")
async def save_theme_preference(body: ThemePreferenceRequest) -> dict[str, str]:
    from src.preferences_storage import save_theme

    try:
        return save_theme(body.theme_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@router.get("/api/preferences/language")
async def get_language_preference() -> dict[str, str]:
    from src.preferences_storage import load_preferences

    prefs = load_preferences()
    return {"active_language": prefs["active_language"]}


@router.post("/api/preferences/language")
async def save_language_preference(body: LanguagePreferenceRequest) -> dict[str, str]:
    from src.preferences_storage import save_language

    try:
        return save_language(body.language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@router.post("/api/preferences/onboarding-complete")
async def complete_onboarding_preference() -> dict[str, str]:
    from src.preferences_storage import save_onboarding_completed
    return save_onboarding_completed()


@router.post("/api/preferences/onboarding-reset")
async def reset_onboarding_preference() -> dict[str, str]:
    from src.preferences_storage import reset_onboarding_completed
    return reset_onboarding_completed()


@router.get("/api/preferences/permission-mode")
async def get_permission_mode() -> dict[str, str]:
    from src.preferences_storage import load_permission_mode
    return {"permission_mode": load_permission_mode()}


@router.get("/api/preferences/permission-rules")
async def get_permission_rules() -> dict[str, Any]:
    from src.permission_rules import load_permission_rules

    return {"rules": load_permission_rules()}


@router.post("/api/preferences/permission-rules")
async def save_permission_rules_route(body: PermissionRulesRequest) -> dict[str, Any]:
    from src.permission_rules import save_permission_rules

    return {"rules": save_permission_rules(body.rules)}


@router.get("/api/preferences/strict-sandbox")
async def get_strict_sandbox() -> dict[str, bool]:
    from src.preferences_storage import load_strict_sandbox

    return {"strict_sandbox": load_strict_sandbox()}


@router.post("/api/preferences/strict-sandbox")
async def save_strict_sandbox_route(body: StrictSandboxRequest) -> dict[str, str]:
    from src.preferences_storage import save_strict_sandbox

    return save_strict_sandbox(body.enabled)


@router.get("/api/preferences/allow-network")
async def get_allow_network() -> dict[str, bool]:
    from src.preferences_storage import load_allow_network

    return {"allow_network": load_allow_network()}


@router.post("/api/preferences/allow-network")
async def save_allow_network_route(body: AllowNetworkRequest) -> dict[str, str]:
    from src.preferences_storage import save_allow_network

    return save_allow_network(body.enabled)


@router.get("/api/preferences/cross-session-memory")
async def get_cross_session_memory() -> dict[str, Any]:
    from src.cross_session_memory import list_entries
    from src.preferences_storage import load_cross_session_memory_enabled

    return {
        "enabled": load_cross_session_memory_enabled(),
        "entries": list_entries(),
    }


@router.post("/api/preferences/cross-session-memory")
async def save_cross_session_memory_route(body: CrossSessionMemoryRequest) -> dict[str, str]:
    from src.preferences_storage import save_cross_session_memory_enabled

    return save_cross_session_memory_enabled(body.enabled)


@router.post("/api/preferences/cross-session-memory/clear")
async def clear_cross_session_memory_route() -> dict[str, Any]:
    from src.cross_session_memory import clear_all, list_entries

    removed = clear_all()
    return {"cleared": removed, "entries": list_entries()}


@router.get("/api/preferences/default-workspace")
async def get_default_workspace() -> dict[str, str]:
    from src.preferences_storage import load_default_workspace_id

    return {"workspace_id": load_default_workspace_id()}


@router.post("/api/preferences/default-workspace")
async def save_default_workspace_route(body: DefaultWorkspaceRequest) -> dict[str, str]:
    from src.preferences_storage import save_default_workspace_id

    return save_default_workspace_id(body.workspace_id)


@router.get("/api/preferences/high-risk-confirm")
async def get_high_risk_confirm() -> dict[str, bool]:
    from src.preferences_storage import load_high_risk_confirm

    return {"high_risk_confirm": load_high_risk_confirm()}


@router.post("/api/preferences/high-risk-confirm")
async def save_high_risk_confirm_route(body: HighRiskConfirmRequest) -> dict[str, str]:
    from src.preferences_storage import save_high_risk_confirm

    return save_high_risk_confirm(body.enabled)


@router.get("/api/preferences/local-trust")
async def get_local_trust() -> dict[str, Any]:
    from src.preferences_storage import load_trusted_ids, load_untrusted_confirm

    return {
        "untrusted_confirm": load_untrusted_confirm(),
        "trusted_mcp_ids": load_trusted_ids("mcp"),
        "trusted_workflow_ids": load_trusted_ids("workflow"),
    }


@router.post("/api/preferences/untrusted-confirm")
async def save_untrusted_confirm_route(body: HighRiskConfirmRequest) -> dict[str, str]:
    from src.preferences_storage import save_untrusted_confirm

    return save_untrusted_confirm(body.enabled)


@router.post("/api/preferences/local-trust")
async def save_local_trust_route(body: TrustItemRequest) -> dict[str, str]:
    from src.preferences_storage import save_trusted_id

    kind = body.kind.strip().lower()
    if kind not in {"mcp", "workflow"}:
        raise HTTPException(status_code=400, detail={"message": "kind must be mcp or workflow"})
    return save_trusted_id(kind, body.item_id)


@router.get("/api/memory/search")
async def search_workspace_memory(q: str = "") -> dict[str, Any]:
    from src.workspace_memory import search_memory

    return {"hits": search_memory(q)}


@router.post("/api/preferences/permission-mode")
async def save_permission_mode_route(body: PermissionModeRequest) -> dict[str, str]:
    from src.preferences_storage import save_permission_mode

    try:
        return save_permission_mode(body.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@router.post("/api/preferences/font-size")
async def save_font_size_preference(body: FontSizePreferenceRequest) -> dict[str, str]:
    from src.preferences_storage import save_font_size

    try:
        return save_font_size(body.font_size)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@router.post("/api/preferences/avatar")
async def save_avatar_preference(body: AvatarPreferenceRequest) -> dict[str, str]:
    from src.preferences_storage import save_avatar

    try:
        return save_avatar(body.avatar)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@router.post("/api/preferences/name")
async def save_user_name_preference(body: UserNamePreferenceRequest) -> dict[str, str]:
    from src.preferences_storage import save_user_name

    try:
        return save_user_name(body.user_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@router.get("/api/capability-packs")
async def list_capability_packs() -> dict[str, Any]:
    from src.capability_pack import list_installed_packs

    return {"packs": list_installed_packs()}


@router.post("/api/capability-packs/import")
async def import_capability_pack(body: CapabilityPackImportRequest) -> dict[str, Any]:
    from src.capability_pack import import_pack

    try:
        return await asyncio.to_thread(import_pack, body.path.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@router.post("/api/capability-packs/uninstall")
async def uninstall_capability_pack(body: CapabilityPackIdRequest) -> dict[str, Any]:
    from src.capability_pack import uninstall_pack

    try:
        return await asyncio.to_thread(uninstall_pack, body.pack_id.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
