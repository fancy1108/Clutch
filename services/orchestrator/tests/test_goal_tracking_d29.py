"""D29 — goal_write live state + Chat goal bar."""

from __future__ import annotations

from types import SimpleNamespace

from src.builtin_tools import execute_builtin_tool, is_goal_write_tool, normalize_goal_args
from src.mcp_react import McpRunOutcome, run_mcp_react_loop


def test_normalize_goal_args_clamps_progress() -> None:
    goal = normalize_goal_args({"title": "修登录", "progress": 150})
    assert goal["title"] == "修登录"
    assert goal["progress"] == 100
    assert goal["done"] is True


def test_goal_write_tool_updates_payload() -> None:
    out = execute_builtin_tool(
        "goal_write",
        {"title": "修登录", "progress": 40},
    )
    assert "修登录" in out
    assert "40%" in out


def test_goal_write_streams_via_mcp_react(monkeypatch) -> None:
    goals: list[dict] = []

    class _Router:
        def get_active_model(self) -> SimpleNamespace:
            return SimpleNamespace(name="Test Model")

        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Test Model"), model_id

        def chat(self, messages, tools=None, model_id=None, tool_choice=None):
            if any(message.get("role") == "tool" for message in messages):
                return "Working on login fix"
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "tc1",
                        "type": "function",
                        "function": {
                            "name": "clutch_tools__goal_write",
                            "arguments": '{"title":"修登录","progress":60}',
                        },
                    }
                ],
            }

    class _FakeClient:
        def __init__(self, name: str, endpoint: str, env=None) -> None:
            self.name = name

        def start(self) -> bool:
            return True

        def list_tools(self) -> list[dict]:
            return []

        def call_tool(self, name: str, arguments: dict) -> dict:
            return {"content": [{"type": "text", "text": "ok"}]}

        def close(self) -> None:
            return None

    monkeypatch.setattr("src.mcp_react.McpClient", _FakeClient)
    monkeypatch.setattr("src.models_config.get_router", lambda: _Router())

    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "fix login"}],
        servers=[{"id": "clutch-tools", "virtual": True}],
        on_goal=lambda goal: goals.append(dict(goal)),
    )
    assert outcome.goal is not None
    assert outcome.goal["title"] == "修登录"
    assert outcome.goal["progress"] == 60
    assert goals and goals[-1]["title"] == "修登录"
    assert is_goal_write_tool("goal_write")
