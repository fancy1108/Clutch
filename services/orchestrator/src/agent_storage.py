"""Agent configuration persistence (M4-02)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.agent_type import migrate_agent_record

AGENTS_ENV = "CLUTCH_AGENTS_DIR"
BUILTIN_AGENT_ID = "clutch-agent"


def get_builtin_agent() -> dict[str, Any]:
    return {
        "id": BUILTIN_AGENT_ID,
        "name": "Clutch Agent",
        "description": "System built-in general-purpose agent for supervised workspace tasks.",
        "markdownDoc": (
            "# Clutch Agent\n\n"
            "You are Clutch Agent, the default system agent for single-agent sessions.\n\n"
            "## Protocol\n"
            "- Understand the user's goal in the active workspace.\n"
            "- Propose clear, incremental steps before making changes.\n"
            "- Ask for approval when execution is risky or ambiguous.\n"
        ),
        "lastModified": "Built-in",
        "avatar": "",
        "deliverables": [],
        "mcpTools": [],
        "mcpServerIds": [],
        "agentType": "clutch",
        "skills": [],
        "builtin": True,
    }


def agents_dir() -> Path:
    override = os.environ.get(AGENTS_ENV)
    if override:
        return Path(override)
    from src.storage_helper import get_storage_dir
    return get_storage_dir() / "agents"


def _ensure_dir() -> Path:
    path = agents_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _agents_file() -> Path:
    return _ensure_dir() / "agents.json"


def _read_file_agents() -> list[dict[str, Any]]:
    path = _agents_file()
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _effective_builtin(override: dict[str, Any] | None = None) -> dict[str, Any]:
    agent = get_builtin_agent()
    if override and override.get("id") == BUILTIN_AGENT_ID:
        agent = {**agent, **override, "id": BUILTIN_AGENT_ID, "builtin": True}
    agent["agentType"] = "clutch"
    agent.pop("aiEngine", None)
    agent.pop("modelId", None)
    agent.pop("model_id", None)
    return migrate_agent_record(agent)


def get_agent_by_id(agent_id: str) -> dict[str, Any] | None:
    for agent in list_agents():
        if agent.get("id") == agent_id:
            return agent
    return None


def list_agents() -> list[dict[str, Any]]:
    file_agents = _read_file_agents()
    builtin_override = next(
        (agent for agent in file_agents if agent.get("id") == BUILTIN_AGENT_ID),
        None,
    )
    user_agents = [
        migrate_agent_record(agent)
        for agent in file_agents
        if agent.get("id") != BUILTIN_AGENT_ID
    ]
    return [_effective_builtin(builtin_override), *user_agents]


def save_agents(agents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    path = _agents_file()
    builtin_override = next(
        (agent for agent in agents if agent.get("id") == BUILTIN_AGENT_ID),
        None,
    )
    user_agents = [
        migrate_agent_record(agent)
        for agent in agents
        if agent.get("id") != BUILTIN_AGENT_ID and not agent.get("builtin")
    ]
    stored: list[dict[str, Any]] = []
    if builtin_override:
        stored.append(_effective_builtin(builtin_override))
    stored.extend(user_agents)
    path.write_text(json.dumps(stored, indent=2, ensure_ascii=False), encoding="utf-8")
    return list_agents()
