"""Agent runtime type (Clutch / CLI) and per-agent model resolution."""

from __future__ import annotations

from typing import Any

from src.llm.router import LLMProviderRouter, ModelSpec

_BUILTIN_AGENT_ID = "clutch-agent"

AGENT_TYPES = frozenset({"clutch", "claude-cli", "ollama-cli", "antigravity-cli", "codex-cli", "aider-cli", "rivet-cli", "opencode-cli", "mimo-cli", "codebuddy-cli", "cursor-cli", "zcode-cli", "qoder-cli", "comate-cli", "devin-cli", "copilot-cli"})

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
    "mimo code cli": "mimo-cli",
    "mimo-cli": "mimo-cli",
    "mimo cli": "mimo-cli",
    "mimocode": "mimo-cli",
    "codebuddy cli": "codebuddy-cli",
    "codebuddy-cli": "codebuddy-cli",
    "workbuddy cli": "codebuddy-cli",
    "cbc": "codebuddy-cli",
    "cursor": "cursor-cli",
    "cursor cli": "cursor-cli",
    "cursor-cli": "cursor-cli",
    "cursor agent cli": "cursor-cli",
    "cursor-agent": "cursor-cli",
    "zcode": "zcode-cli",
    "zcode cli": "zcode-cli",
    "zcode-cli": "zcode-cli",
    "z.ai zcode": "zcode-cli",
    "z.ai zcode cli": "zcode-cli",
    "qoder cli": "qoder-cli",
    "qoder-cli": "qoder-cli",
    "qodercli": "qoder-cli",
    "comate": "comate-cli",
    "comate-cli": "comate-cli",
    "baidu comate": "comate-cli",
    "devin": "devin-cli",
    "devin-cli": "devin-cli",
    "devin cli": "devin-cli",
    "copilot": "copilot-cli",
    "copilot-cli": "copilot-cli",
    "github copilot cli": "copilot-cli",
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


def normalize_agent_type_strict(raw: str) -> str:
    """Same as normalize_agent_type, but raises ValueError instead of silently
    falling back to 'clutch' when the input maps to nothing recognizable.

    Use at trust boundaries where an unrecognized `agentType` should surface as
    a config error, not be papered over. Notably: user-submitted agent records
    persisted via `save_agents` (see #54).

    Legacy aliases (e.g. 'ZCode CLI', 'Claude Code CLI') are still accepted
    exactly like in the lenient version; only genuinely unknown inputs (typos
    like 'zcod' or made-up names) raise.

    Empty / whitespace-only input still returns 'clutch' — this matches the
    documented default when no `agentType` is specified.
    """
    if not raw or not raw.strip():
        return "clutch"
    normalized = normalize_agent_type(raw)
    key = raw.strip().lower()
    if normalized == "clutch" and key not in AGENT_TYPES and key not in _LEGACY_AI_ENGINE_TO_TYPE:
        raise ValueError(
            f"Unrecognized agentType {raw!r}. "
            f"Expected one of {sorted(AGENT_TYPES)}, or a documented alias."
        )
    return normalized


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
