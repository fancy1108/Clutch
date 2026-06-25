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


def test_save_agents_persists_builtin_override(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_AGENTS_DIR", str(tmp_path))
    customized = {
        **get_builtin_agent(),
        "markdownDoc": "# Custom builtin prompt",
        "lastModified": "2026-06-25",
    }
    save_agents([customized, {"id": "custom-1", "name": "Custom", "description": "x"}])
    stored = list_agents()
    assert stored[0]["markdownDoc"] == "# Custom builtin prompt"
    assert stored[0]["builtin"] is True
    assert stored[0]["aiEngine"] == "Configured LLM"
    assert any(agent["id"] == "custom-1" for agent in stored)
    assert len([agent for agent in stored if agent["id"] == BUILTIN_AGENT_ID]) == 1


def test_save_agents_strips_builtin_ai_engine_override(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_AGENTS_DIR", str(tmp_path))
    customized = {
        **get_builtin_agent(),
        "aiEngine": "Claude Code (Local CLI)",
    }
    save_agents([customized])
    stored = list_agents()
    assert stored[0]["aiEngine"] == "Configured LLM"


def test_get_agent_by_id_returns_builtin_agent() -> None:
    from src.agent_storage import BUILTIN_AGENT_ID, get_agent_by_id

    agent = get_agent_by_id(BUILTIN_AGENT_ID)
    assert agent is not None
    assert agent["name"] == "Clutch Agent"
    assert agent["builtin"] is True

    client = TestClient(app)
    response = client.get("/api/agents")
    assert response.status_code == 200
    agents = response.json()["agents"]
    assert agents[0]["id"] == BUILTIN_AGENT_ID
    assert agents[0]["builtin"] is True


def test_generate_agent_prompt_requires_name(monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_E2E_FAKE_LLM", "1")
    client = TestClient(app)
    response = client.post("/api/agents/generate-prompt", json={"name": "  ", "description": "x"})
    assert response.status_code == 400


def test_generate_agent_prompt_returns_skeleton(monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_E2E_FAKE_LLM", "1")
    client = TestClient(app)
    response = client.post(
        "/api/agents/generate-prompt",
        json={"name": "Security Auditor", "description": "Review code for vulnerabilities."},
    )
    assert response.status_code == 200
    body = response.json()
    assert "Security Auditor" in body["prompt"]
    assert body["source"] in {"llm", "template"}
