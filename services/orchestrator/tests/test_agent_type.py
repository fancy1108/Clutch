"""Agent type normalization and model resolution."""

from __future__ import annotations

from types import SimpleNamespace

from src.agent_type import (
    agent_type_from_record,
    is_clutch_agent,
    migrate_agent_record,
    resolve_model_for_agent,
)
from src.llm.router import LLMProviderRouter


def test_migrate_legacy_ai_engine_to_agent_type() -> None:
    migrated = migrate_agent_record({"id": "a1", "aiEngine": "Configured LLM"})
    assert migrated["agentType"] == "clutch"
    assert "aiEngine" not in migrated


def test_agent_type_from_record_prefers_explicit_agent_type() -> None:
    assert agent_type_from_record({"agentType": "ollama-cli", "aiEngine": "Configured LLM"}) == "ollama-cli"


def test_builtin_agent_ignores_bound_model_id() -> None:
    router = LLMProviderRouter()
    router._chat = lambda **_kwargs: "ok"  # type: ignore[method-assign]
    router.set_active_model("deepseek-v4pro")
    agent = {
        "id": "clutch-agent",
        "agentType": "clutch",
        "builtin": True,
        "modelId": "agnes-image-2.1-flash",
    }
    spec, model_id = resolve_model_for_agent(router, agent)
    assert model_id == "deepseek-v4pro"
    assert spec.id == "deepseek-v4pro"


def test_resolve_model_for_agent_uses_session_model_id() -> None:
    router = LLMProviderRouter()
    router._chat = lambda **_kwargs: "ok"  # type: ignore[method-assign]
    router.set_active_model("deepseek-v4pro")
    agent = {
        "id": "clutch-agent",
        "agentType": "clutch",
        "builtin": True,
        "modelId": "agnes-image-2.1-flash",
    }
    spec, model_id = resolve_model_for_agent(
        router, agent, session_model_id="qwen2.5vl-7b"
    )
    assert model_id == "qwen2.5vl-7b"
    assert spec.id == "qwen2.5vl-7b"


def test_resolve_model_for_agent_uses_bound_model_id() -> None:
    router = LLMProviderRouter()
    router._chat = lambda **_kwargs: "ok"  # type: ignore[method-assign]
    router.set_active_model("deepseek-v4pro")
    agent = {"id": "custom-agent", "agentType": "clutch", "modelId": "agnes-image-2.1-flash"}
    spec, model_id = resolve_model_for_agent(router, agent)
    assert model_id == "agnes-image-2.1-flash"
    assert spec.id == "agnes-image-2.1-flash"


def test_resolve_model_for_agent_falls_back_to_active_model() -> None:
    router = LLMProviderRouter()
    router._chat = lambda **_kwargs: "ok"  # type: ignore[method-assign]
    router.set_active_model("deepseek-v4pro")
    spec, model_id = resolve_model_for_agent(router, {"agentType": "clutch"})
    assert model_id == "deepseek-v4pro"
    assert spec.id == "deepseek-v4pro"


def test_is_clutch_agent_false_for_ollama_cli() -> None:
    assert not is_clutch_agent({"agentType": "ollama-cli"})
