"""Tests for agent system prompt composition."""

from __future__ import annotations

from src.agent_prompt import compose_agent_system_prompt


def test_compose_agent_system_prompt_includes_runtime_model_for_clutch_agent() -> None:
    agent = {
        "id": "clutch-agent",
        "name": "Clutch Agent",
        "agentType": "clutch",
    }
    prompt = compose_agent_system_prompt(
        agent,
        model_name="Gemini 2.5 Flash",
        model_api="gemini-2.5-flash",
    )
    assert "Runtime model: Gemini 2.5 Flash (gemini-2.5-flash)." in prompt


def test_compose_agent_system_prompt_omits_runtime_model_for_cli_agent() -> None:
    agent = {
        "id": "agy-agent",
        "name": "Antigravity CLI",
        "agentType": "antigravity-cli",
    }
    prompt = compose_agent_system_prompt(
        agent,
        model_name="Gemini 2.5 Flash",
        model_api="gemini-2.5-flash",
    )
    assert "Runtime model" not in prompt
