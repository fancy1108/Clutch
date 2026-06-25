"""Tests for the engine router."""

from __future__ import annotations

from types import SimpleNamespace
import pytest

from src.engine_router import find_agent, route_engine, EngineResult


@pytest.fixture
def mock_agents(monkeypatch) -> list[dict[str, str]]:
    agents = [
        {
            "id": "agent-builder",
            "name": "Builder Module (JSX VibeCoder)",
            "aiEngine": "Claude Code (Local CLI)",
        },
        {
            "id": "agent-auditor",
            "name": "Auditor Agent (Pipeline Quality Audit)",
            "aiEngine": "Cursor Workspace Node",
        },
        {
            "id": "agent-evaluator",
            "name": "Evaluator Module",
            "aiEngine": "DeepSeek API",
        },
    ]
    monkeypatch.setattr("src.engine_router.list_agents", lambda: agents)
    return agents


def test_find_agent(mock_agents) -> None:
    # Exact name match
    assert find_agent("Builder Module (JSX VibeCoder)")["id"] == "agent-builder"
    # Exact id match
    assert find_agent("agent-auditor")["id"] == "agent-auditor"
    # Case-insensitive match
    assert find_agent("builder module (jsx vibecoder)")["id"] == "agent-builder"
    # Substring match
    assert find_agent("Auditor")["id"] == "agent-auditor"
    assert find_agent("evaluator")["id"] == "agent-evaluator"
    # None match
    assert find_agent("Unknown Agent") is None


class FakeRouter:
    def get_active_model(self) -> SimpleNamespace:
        return SimpleNamespace(name="Fake Model")

    def chat(self, history: list[dict[str, str]]) -> str:
        return f"Fake response for: {history[-1]['content']}"


def test_route_engine_fallback_no_agent(monkeypatch) -> None:
    monkeypatch.setattr("src.engine_router.list_agents", lambda: [])
    monkeypatch.setattr("src.engine_router.load_connected_ids", lambda: set())
    monkeypatch.setattr("src.models_config.get_router", lambda: FakeRouter())

    res = route_engine(agent_name="Builder", prompt="test prompt")
    assert res.engine == "Fake Model"
    assert "test prompt" in res.output
    assert any("Routing task to global LLM provider" in log for log in res.logs)


def test_route_engine_claude_cli_not_connected(monkeypatch, mock_agents) -> None:
    monkeypatch.setattr("src.engine_router.load_connected_ids", lambda: set())
    monkeypatch.setattr("src.models_config.get_router", lambda: FakeRouter())

    res = route_engine(agent_name="Builder Module (JSX VibeCoder)", prompt="hello")
    assert res.engine == "Fake Model"
    assert "hello" in res.output


def test_route_engine_claude_cli_connected(monkeypatch, mock_agents) -> None:
    monkeypatch.setattr("src.engine_router.load_connected_ids", lambda: {"claude-cli"})
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})

    called_prompt = None
    called_cwd = None
    called_system_prompt = None

    def fake_chat_claude(prompt, *, cwd, system_prompt, **kwargs):
        nonlocal called_prompt, called_cwd, called_system_prompt
        called_prompt = prompt
        called_cwd = cwd
        called_system_prompt = system_prompt
        return "Claude CLI output"

    monkeypatch.setattr("src.engine_router.chat_claude_cli", fake_chat_claude)

    res = route_engine(
        agent_name="Builder Module (JSX VibeCoder)",
        prompt="hello",
        system_prompt="sys prompt",
    )
    assert res.engine == "Claude CLI"
    assert res.output == "Claude CLI output"
    assert called_prompt == "hello"
    assert called_cwd == "/workspace"
    assert called_system_prompt == "sys prompt"
    assert any("Routing task to Claude Code" in log for log in res.logs)


def test_route_engine_cursor_connected(monkeypatch, mock_agents) -> None:
    monkeypatch.setattr("src.engine_router.load_connected_ids", lambda: {"cursor-app"})
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})

    called_path = None

    def fake_open_cursor(path):
        nonlocal called_path
        called_path = path

    monkeypatch.setattr("src.engine_router.open_workspace_in_cursor", fake_open_cursor)

    res = route_engine(
        agent_name="Auditor Agent (Pipeline Quality Audit)",
        prompt="open code",
    )
    assert res.engine == "Cursor"
    assert "打开工作区" in res.output or "opened in Cursor" in res.output
    assert called_path == "/workspace"
    assert any("Routing task to Cursor" in log for log in res.logs)


def test_route_engine_fallback_tool_claude_cli(monkeypatch) -> None:
    # No agent profile, but node has fallback_tool="claude-cli" and it is connected
    monkeypatch.setattr("src.engine_router.list_agents", lambda: [])
    monkeypatch.setattr("src.engine_router.load_connected_ids", lambda: {"claude-cli"})
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})
    monkeypatch.setattr("src.engine_router.chat_claude_cli", lambda **k: "fallback claude output")

    res = route_engine(
        agent_name="Builder",
        prompt="hello",
        fallback_tool="claude-cli",
    )
    assert res.engine == "Claude CLI"
    assert res.output == "fallback claude output"
