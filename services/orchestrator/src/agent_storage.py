"""Agent configuration persistence (M4-02)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

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
        "aiEngine": "Configured LLM",
        "skills": [],
        "builtin": True,
    }


def _is_persisted_agent(agent: dict[str, Any]) -> bool:
    return agent.get("id") != BUILTIN_AGENT_ID and not agent.get("builtin")


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


def list_agents() -> list[dict[str, Any]]:
    path = _agents_file()
    user_agents: list[dict[str, Any]] = []
    if path.is_file():
        user_agents = [
            agent for agent in json.loads(path.read_text(encoding="utf-8"))
            if _is_persisted_agent(agent)
        ]
    return [get_builtin_agent(), *user_agents]


def save_agents(agents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    path = _agents_file()
    user_agents = [agent for agent in agents if _is_persisted_agent(agent)]
    path.write_text(json.dumps(user_agents, indent=2, ensure_ascii=False), encoding="utf-8")
    return list_agents()
