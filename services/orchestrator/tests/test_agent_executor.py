"""Tests for agent_task execution."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from src.agent_executor import execute_agent_task
from src.llm.router import BUILTIN_MODELS


class _FakeRouter:
    _models = BUILTIN_MODELS

    def get_active_model(self) -> SimpleNamespace:
        return SimpleNamespace(
            id="deepseek-v4pro",
            name="Test Model",
            api_model="test-api-model",
            model_kind="chat",
        )

    @property
    def active_model_id(self) -> str:
        return "deepseek-v4pro"

    def chat(self, history: list[dict[str, str]], model_id: str | None = None) -> str:
        return f"Done: {history[-1]['content'][:40]}"


class _FakeImageRouter:
    _models = BUILTIN_MODELS

    def get_active_model(self):
        return BUILTIN_MODELS["agnes-image-2.1-flash"]

    @property
    def active_model_id(self) -> str:
        return "agnes-image-2.1-flash"

    def resolve_for_model(self, model_id: str | None = None):
        return BUILTIN_MODELS["agnes-image-2.1-flash"], "sk-test"

    def _require_api_key(self, _provider_id: str, api_key: str | None) -> str:
        return api_key or "sk-test"


def test_execute_agent_task_uses_llm(monkeypatch) -> None:
    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeRouter())
    result = execute_agent_task(
        {"agent": "Builder", "label": "Setup", "instruction": "Create README"},
        instruction="",
    )
    assert result.agent == "Builder"
    assert "Done:" in result.output
    assert any("Starting:" in line for line in result.logs)
    assert result.message["agent"] == "Builder"


def test_clutch_agent_injects_markdown_protocol(monkeypatch) -> None:
    captured: list[list[dict[str, str]]] = []

    class _CapturingRouter(_FakeRouter):
        def chat(self, history: list[dict[str, str]], model_id: str | None = None) -> str:
            captured.append(history)
            return "Clutch reply"

    monkeypatch.setattr("src.models_config.get_router", lambda: _CapturingRouter())
    monkeypatch.setattr("src.agent_mcp.resolve_agent_mcp_servers", lambda _agent: [])
    monkeypatch.setattr(
        "src.engine_router.find_agent",
        lambda _ref: {
            "id": "researcher",
            "name": "The Researcher",
            "agentType": "clutch",
            "modelId": "deepseek-v4pro",
            "markdownDoc": "Always describe weather scenes for illustrators.",
        },
    )

    result = execute_agent_task(
        {"agent": "The Researcher", "label": "Research", "tool": "llm"},
        instruction="Shanghai skyline at dusk.",
    )

    assert result.agent == "The Researcher"
    assert captured
    system = captured[0][0]["content"]
    assert "The Researcher" in system
    assert "Always describe weather scenes for illustrators." in system
    assert captured[0][-1]["content"] == "Shanghai skyline at dusk."


def test_flow_image_uses_upstream_output(monkeypatch) -> None:
    upstream = (
        "Golden hour over the Huangpu River: warm orange sky, "
        "Lujiazui towers silhouetted, light haze on the water."
    )
    seen_prompts: list[str] = []

    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeImageRouter())
    monkeypatch.setattr(
        "src.engine_router.find_agent",
        lambda _ref: {
            "id": "artist",
            "name": "The Artist",
            "agentType": "clutch",
            "modelId": "agnes-image-2.1-flash",
        },
    )

    def fake_generate(spec, prompt, **kwargs):
        seen_prompts.append(prompt)
        return {"url": "https://example.com/shanghai.png"}

    with patch("src.image_router.generate_image_for_model", side_effect=fake_generate):
        result = execute_agent_task(
            {
                "agent": "The Artist",
                "label": "Artist",
                "tool": "llm",
                "instruction": "Paint this scene.",
            },
            instruction=f"Paint this scene.\n\n{upstream}",
        )

    assert seen_prompts
    assert upstream in seen_prompts[0]
    assert "https://example.com/shanghai.png" in result.output
    assert result.agent == "The Artist"
