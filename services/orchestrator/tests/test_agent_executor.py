"""Tests for agent_task execution."""

from __future__ import annotations

from types import SimpleNamespace

from src.agent_executor import execute_agent_task


class _FakeRouter:
    def get_active_model(self) -> SimpleNamespace:
        return SimpleNamespace(name="Test Model")

    def chat(self, history: list[dict[str, str]]) -> str:
        return f"Done: {history[-1]['content'][:40]}"


def test_execute_agent_task_uses_llm(monkeypatch) -> None:
    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeRouter())
    result = execute_agent_task(
        {"agent": "Builder", "label": "Setup", "instruction": "Create README"},
        instruction="",
    )
    assert result.agent == "Builder"
    assert "Done:" in result.output
    assert any("BUILDER" in line for line in result.logs)
    assert result.message["agent"] == "Builder"
