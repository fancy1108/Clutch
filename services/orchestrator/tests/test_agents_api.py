"""Agent registry API — built-in Clutch Agent is always present."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.agent_storage import BUILTIN_AGENT_ID, get_builtin_agent, list_agents, save_agents
from src.main import app


def test_list_agents_includes_builtin_clutch_agent() -> None:
    agents = list_agents()
    assert agents
    assert agents[0]["id"] == BUILTIN_AGENT_ID
    assert agents[0]["builtin"] is True
    assert agents[0]["name"] == "Clutch Agent"


def test_save_agents_does_not_persist_builtin_agent(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_AGENTS_DIR", str(tmp_path))
    save_agents([get_builtin_agent(), {"id": "custom-1", "name": "Custom", "description": "x"}])
    stored = list_agents()
    assert stored[0]["id"] == BUILTIN_AGENT_ID
    assert any(agent["id"] == "custom-1" for agent in stored)
    assert not any(agent["id"] == BUILTIN_AGENT_ID for agent in stored[1:])


def test_agents_api_returns_builtin_agent() -> None:
    client = TestClient(app)
    response = client.get("/api/agents")
    assert response.status_code == 200
    agents = response.json()["agents"]
    assert agents[0]["id"] == BUILTIN_AGENT_ID
    assert agents[0]["builtin"] is True
