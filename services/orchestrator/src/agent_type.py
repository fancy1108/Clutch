"""Agent runtime type (Clutch / CLI) and per-agent model resolution."""

from __future__ import annotations

from typing import Any

from src.llm.router import LLMProviderRouter, ModelSpec

_BUILTIN_AGENT_ID = "clutch-agent"

AGENT_TYPES = frozenset({"clutch", "claude-cli", "ollama-cli", "antigravity-cli", "codex-cli", "aider-cli", "rivet-cli", "opencode-cli"})

_LEGACY_AI_ENGINE_TO_TYPE: dict[str, str] = {
    "configured llm": "clutch",
    "clutch": "clutch",
    "claude code (local cli)": "claude-cli",
    "claude code cli": "claude-cli",
    "claude-cli": "claude-cli",
    "claude cli": "claude-cli",
    "antigravity cli": "antigravity-cli",
    "antigravity-cli": "antigravity-cli",
    "agy-cli": "antigravity-cli",
    "agy cli": "antigravity-cli",
    "codex cli": "codex-cli",
    "codex-cli": "codex-cli",
    "openai codex cli": "codex-cli",
    "ollama": "ollama-cli",
    "ollama-cli": "ollama-cli",
    "ollama (cli)": "ollama-cli",
    "deepseek api": "clutch",
    "aider": "aider-cli",
    "aider-cli": "aider-cli",
    "aider (cli)": "aider-cli",
    "rivet cli": "rivet-cli",
    "rivet-cli": "rivet-cli",
    "tianshu": "rivet-cli",
    "t9-cli": "rivet-cli",
    "opencode cli": "opencode-cli",
    "opencode-cli": "opencode-cli",
    "open code cli": "opencode-cli",
}


def normalize_agent_type(raw: str) -> str:
    key = raw.strip().lower()
    if key in AGENT_TYPES:
        return key
    legacy = _LEGACY_AI_ENGINE_TO_TYPE.get(key)
    if legacy:
        return legacy
    try:
        from src.engine_router import CLI_ROUTING_CONFIGS

        if key in CLI_ROUTING_CONFIGS:
            return key
        for agent_type, cfg in CLI_ROUTING_CONFIGS.items():
            if isinstance(cfg, dict) and str(cfg.get("tool_id", "")).lower() == key:
                return agent_type
    except Exception:
        pass
    return "clutch"


def agent_type_from_record(agent: dict[str, Any] | None) -> str:
    if not agent:
        return "clutch"
    explicit = str(agent.get("agentType", "")).strip()
    if explicit:
        return normalize_agent_type(explicit)
    legacy = str(agent.get("aiEngine", "")).strip()
    if legacy:
        return normalize_agent_type(legacy)
    return "clutch"


def is_clutch_agent(agent: dict[str, Any] | None) -> bool:
    return agent_type_from_record(agent) == "clutch"


def agent_model_id(agent: dict[str, Any] | None) -> str:
    if not agent or not is_clutch_agent(agent):
        return ""
    if agent.get("builtin") or str(agent.get("id", "")).strip() == _BUILTIN_AGENT_ID:
        return ""
    return str(agent.get("modelId") or agent.get("model_id") or "").strip()


def resolve_model_for_agent(
    router: LLMProviderRouter,
    agent: dict[str, Any] | None,
    *,
    session_model_id: str | None = None,
) -> tuple[ModelSpec, str]:
    if session_model_id and session_model_id in router._models:
        return router._models[session_model_id], session_model_id
    model_id = agent_model_id(agent)
    if model_id and model_id in router._models:
        return router._models[model_id], model_id
    active = router.get_active_model()
    fallback_id = getattr(router, "active_model_id", None) or getattr(active, "id", "")
    return active, fallback_id


def migrate_agent_record(agent: dict[str, Any]) -> dict[str, Any]:
    """Normalize persisted agent dict to agentType + modelId; drop legacy aiEngine."""
    out = dict(agent)
    out["agentType"] = agent_type_from_record(agent)
    out.pop("aiEngine", None)
    model_id = agent_model_id(agent)
    if model_id:
        out["modelId"] = model_id
    elif "modelId" in out and not str(out.get("modelId", "")).strip():
        out.pop("modelId", None)
    agent_type = out["agentType"]
    if agent_type != "ollama-cli":
        out.pop("ollamaModel", None)
    return out
