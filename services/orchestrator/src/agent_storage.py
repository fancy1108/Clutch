"""Agent configuration persistence (M4-02)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.agent_type import migrate_agent_record, normalize_agent_type_strict

AGENTS_ENV = "CLUTCH_AGENTS_DIR"
BUILTIN_AGENT_ID = "clutch-agent"


class AgentValidationError(ValueError):
    """Raised when a user-submitted agent record fails validation.

    Kept separate from generic ValueError so callers (e.g. the FastAPI layer)
    can format a targeted 400 response instead of a 500.
    """



def get_builtin_agent() -> dict[str, Any]:
    return {
        "id": BUILTIN_AGENT_ID,
        "name": "Clutch Agent",
        "description": "System built-in general-purpose agent for supervised workspace tasks.",
        "markdownDoc": (
            "# Protocol\n\n"
            "Editable agent protocol segment (D53) — not the full runtime system prompt.\n\n"
            "- Understand the user's goal in the active workspace.\n"
            "- Use clutch-tools (`read_file`, `list_dir`, `grep`, `search_replace`, "
            "`run_terminal_cmd`, `apply_patch`, `propose_plan`, `todo_write`, "
            "`ask_user_question`, `submit_verification`) to inspect and change the workspace.\n"
            "- For multi-step or feature work (e.g. add login), call `propose_plan` before "
            "any write/shell mutation and wait for Chat approval; skip for trivial Q&A.\n"
            "- Prefer incremental edits (`search_replace` / `apply_patch`) over rewriting whole files.\n"
            "- Propose clear steps for ambiguous or risky work; wait for approval when required.\n"
            "- After meaningful changes, verify when practical (tests or a focused check).\n"
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


def _validate_user_agent(agent: dict[str, Any]) -> None:
    """Reject user-submitted agent records with an unrecognized `agentType`.

    Prior behavior: `migrate_agent_record` → `normalize_agent_type` silently
    fell back to 'clutch' on typos (e.g. 'zcode' missing the '-cli' suffix),
    which then caused the persisted agent to route to the built-in Clutch
    engine instead of the CLI the user intended. See #54.
    """
    raw = str(agent.get("agentType", "")).strip()
    if not raw:
        return  # No agentType → defaults to 'clutch', that's fine.
    try:
        normalize_agent_type_strict(raw)
    except ValueError as exc:
        agent_id = agent.get("id") or "<no-id>"
        raise AgentValidationError(
            f"Agent {agent_id!r} has invalid agentType {raw!r}: {exc}"
        ) from exc


def save_agents(agents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    path = _agents_file()
    builtin_override = next(
        (agent for agent in agents if agent.get("id") == BUILTIN_AGENT_ID),
        None,
    )
    user_agent_inputs = [
        agent
        for agent in agents
        if agent.get("id") != BUILTIN_AGENT_ID and not agent.get("builtin")
    ]
    for agent in user_agent_inputs:
        _validate_user_agent(agent)
    user_agents = [migrate_agent_record(agent) for agent in user_agent_inputs]
    stored: list[dict[str, Any]] = []
    if builtin_override:
        stored.append(_effective_builtin(builtin_override))
    stored.extend(user_agents)
    path.write_text(json.dumps(stored, indent=2, ensure_ascii=False), encoding="utf-8")
    return list_agents()
