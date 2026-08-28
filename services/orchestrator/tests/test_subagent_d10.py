"""D10∥D48 — delegate_subtask + nested subtask cards."""

from __future__ import annotations

import json
from types import SimpleNamespace

from src.builtin_tools import execute_builtin_tool, is_delegate_subtask_tool
from src.subagent_runner import (
    DEFAULT_EXPLORE_MAX_STEPS,
    DEFAULT_IMPLEMENT_MAX_STEPS,
    bind_delegate_context,
    default_subtask_max_steps,
    initial_subtask_card,
    normalize_delegate_args,
    release_delegate_context,
    run_subagent,
    upsert_subtask,
)


def test_default_subtask_max_steps_by_type() -> None:
    assert default_subtask_max_steps("explore") == DEFAULT_EXPLORE_MAX_STEPS
    assert default_subtask_max_steps("implement") == DEFAULT_IMPLEMENT_MAX_STEPS
    assert DEFAULT_EXPLORE_MAX_STEPS > 8


def test_normalize_and_upsert_subtask() -> None:
    args = normalize_delegate_args(
        {"type": "explore", "prompt": "Find auth entrypoints", "title": "Auth scan"}
    )
    assert args["type"] == "explore"
    card = initial_subtask_card(args, subtask_id="sub_a")
    assert card["status"] == "running"
    merged = upsert_subtask([], card)
    merged = upsert_subtask(merged, {**card, "status": "done", "summary": "ok"})
    assert len(merged) == 1
    assert merged[0]["status"] == "done"
    assert is_delegate_subtask_tool("clutch-tools__delegate_subtask")


def test_delegate_requires_context() -> None:
    out = execute_builtin_tool(
        "delegate_subtask",
        {"type": "explore", "prompt": "look around"},
    )
    assert out.startswith("Error executing tool:")


def test_run_subagent_explore_marks_done(monkeypatch) -> None:
    class _Router:
        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Test", id="t"), "t"

        def chat(self, messages, tools=None, model_id=None):
            return "Exploration complete: found src/main.py"

    monkeypatch.setattr("src.models_config.get_router", lambda: _Router())
    monkeypatch.setattr(
        "src.adapters.ollama_adapter.model_supports_tool_calling",
        lambda spec: True,
    )

    class _Client:
        def __init__(self, name: str, endpoint: str, env=None) -> None:
            self.name = name

        def start(self, *args, **kwargs) -> bool:
            return True

        def list_tools(self) -> list[dict]:
            return []

        def close(self) -> None:
            return None

    monkeypatch.setattr("src.mcp_react.McpClient", _Client)

    updates: list[dict] = []
    card = run_subagent(
        task_type="explore",
        prompt="Survey the repo layout",
        title="Survey",
        servers=[{"id": "mcp_test", "name": "T", "endpoint": "echo"}],
        on_subtask_update=updates.append,
        max_steps=4,
        pause_on_risky=False,
        permission_mode="plan",
    )
    assert card["status"] == "done"
    assert "Exploration complete" in card["summary"]
    assert updates and updates[0]["status"] == "running"
    assert updates[-1]["status"] == "done"


def test_delegate_tool_with_context(monkeypatch) -> None:
    def fake_run_subagent(**kwargs):
        return {
            "id": "sub_x",
            "type": "implement",
            "title": "Patch",
            "status": "failed",
            "summary": "edit failed",
            "error": "edit failed",
            "toolSteps": [{"name": "search_replace", "status": "failed"}],
        }

    monkeypatch.setattr("src.subagent_runner.run_subagent", fake_run_subagent)
    token = bind_delegate_context(
        {
            "servers": [{"id": "clutch-tools", "name": "Builtin", "virtual": True}],
            "model_id": None,
            "max_steps": 8,
        }
    )
    try:
        raw = execute_builtin_tool(
            "delegate_subtask",
            {"type": "implement", "prompt": "fix bug", "title": "Patch"},
        )
    finally:
        release_delegate_context(token)
    payload = json.loads(raw)
    assert payload["status"] == "failed"
    assert payload["id"] == "sub_x"
    assert "edit failed" in payload["summary"]
