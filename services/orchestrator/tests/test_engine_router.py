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
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: False)
    monkeypatch.setattr("src.models_config.get_router", lambda: FakeRouter())

    res = route_engine(
        agent_name="Builder Module (JSX VibeCoder)",
        prompt="hello",
    )
    assert res.engine == "Fake Model"
    assert "hello" in res.output
    assert any("回退到 LLM" in log or "falling back to LLM" in log for log in res.logs)


def test_route_engine_claude_cli_passes_conversation_history(monkeypatch, mock_agents) -> None:
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})

    captured: dict[str, object] = {}

    def fake_chat_claude(prompt, *, cwd, system_prompt, session_id=None, resume_session_id=None, **kwargs):
        captured["prompt"] = prompt
        captured["system_prompt"] = system_prompt or ""
        captured["session_id"] = session_id
        captured["resume_session_id"] = resume_session_id
        return "Claude CLI output"

    monkeypatch.setattr("src.engine_router.chat_claude_cli", fake_chat_claude)
    monkeypatch.setattr("src.engine_router.uuid.uuid4", lambda: "550e8400-e29b-41d4-a716-446655440000")

    history = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first answer"},
        {"role": "user", "content": "follow up"},
    ]
    res = route_engine(
        agent_name="Builder Module (JSX VibeCoder)",
        prompt="follow up",
        system_prompt="sys",
        history=history,
    )
    assert res.engine == "Claude CLI"
    assert res.claude_session_id == "550e8400-e29b-41d4-a716-446655440000"
    assert "User: first question" in str(captured["prompt"])
    assert "Assistant: first answer" in str(captured["prompt"])
    assert "User: follow up" in str(captured["prompt"])
    assert captured["session_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert captured["resume_session_id"] is None


def test_route_engine_claude_cli_resumes_existing_session(monkeypatch, mock_agents) -> None:
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})

    captured: dict[str, object] = {}

    def fake_chat_claude(prompt, *, cwd, system_prompt, session_id=None, resume_session_id=None, **kwargs):
        captured["prompt"] = prompt
        captured["system_prompt"] = system_prompt
        captured["session_id"] = session_id
        captured["resume_session_id"] = resume_session_id
        return "Claude CLI output"

    monkeypatch.setattr("src.engine_router.chat_claude_cli", fake_chat_claude)

    history = [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first answer"},
        {"role": "user", "content": "follow up"},
    ]
    res = route_engine(
        agent_name="Builder Module (JSX VibeCoder)",
        prompt="follow up",
        system_prompt="sys",
        history=history,
        claude_session_id="550e8400-e29b-41d4-a716-446655440000",
    )
    assert res.engine == "Claude CLI"
    assert res.claude_session_id == "550e8400-e29b-41d4-a716-446655440000"
    assert captured["prompt"] == "follow up"
    assert captured["system_prompt"] is None
    assert captured["resume_session_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert captured["session_id"] is None


def test_route_engine_claude_cli_connected(monkeypatch, mock_agents) -> None:
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
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


def test_route_engine_claude_cli_streams_router_logs(monkeypatch, mock_agents) -> None:
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})
    monkeypatch.setattr("src.engine_router.chat_claude_cli", lambda **kwargs: "ok")

    streamed: list[str] = []
    res = route_engine(agent_name="Builder Module (JSX VibeCoder)", prompt="hi", on_log=streamed.append)

    assert res.output == "ok"
    assert any(line.startswith("[ROUTER]") for line in streamed)
    assert any("Starting new Claude CLI session" in line for line in streamed)
    assert streamed == res.logs


def test_route_engine_cursor_connected(monkeypatch, mock_agents) -> None:
    monkeypatch.setattr(
        "src.engine_router.tool_available_for_routing",
        lambda tool_id: tool_id == "cursor-app",
    )
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
    monkeypatch.setattr("src.engine_router.list_agents", lambda: [])
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})
    monkeypatch.setattr("src.engine_router.chat_claude_cli", lambda **k: "fallback claude output")

    res = route_engine(
        agent_name="Builder",
        prompt="hello",
        fallback_tool="claude-cli",
    )
    assert res.engine == "Claude CLI"
    assert res.output == "fallback claude output"


def test_route_engine_normalizes_claude_code_cli_alias(monkeypatch, mock_agents) -> None:
    monkeypatch.setattr(
        "src.engine_router.list_agents",
        lambda: [
            {
                "id": "agent-cc",
                "name": "Claude Code Agent",
                "aiEngine": "Claude Code CLI",
            }
        ],
    )
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: True)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: {"workspace_path": "/workspace"})
    monkeypatch.setattr("src.engine_router.chat_claude_cli", lambda **k: "alias routed")

    res = route_engine(agent_name="Claude Code Agent", prompt="hi")
    assert res.engine == "Claude CLI"
    assert res.output == "alias routed"
    assert any("Claude Code (Local CLI)" in log for log in res.logs)
