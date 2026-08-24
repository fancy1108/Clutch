"""Tests for agent system prompt composition."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from src.agent_prompt import _format_local_time, compose_agent_system_prompt


def test_format_local_time_includes_clock_and_offset() -> None:
    now = datetime(2026, 8, 1, 15, 13, 6, tzinfo=timezone(timedelta(hours=8)))
    text = _format_local_time(now)
    assert "2026-08-01 15:13:06" in text
    assert "UTC+08:00" in text


def test_compose_agent_system_prompt_keeps_clock_out_of_prefix() -> None:
    from src.agent_prompt import attach_trailing_status, compose_agent_prompt_assembly

    agent = {
        "id": "clutch-agent",
        "name": "Clutch Agent",
        "agentType": "clutch",
    }
    assembly = compose_agent_prompt_assembly(
        agent,
        model_name="ornith:9b",
        model_api="ollama",
    )
    prompt = assembly.as_system_prompt()
    status = assembly.agent_status_text()
    assert "## Environment" in prompt
    assert "Local time:" not in prompt
    assert "<agent_status>" in status
    assert "Local time:" in status
    once = attach_trailing_status([{"role": "user", "content": "hi"}], status)
    assert sum(1 for item in once if "<agent_status>" in str(item.get("content"))) == 1
    assert once[-1]["content"] == "hi"


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
