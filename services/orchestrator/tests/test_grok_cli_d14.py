"""D14 — external grok CLI routing."""

from __future__ import annotations

from unittest.mock import patch


def test_grok_cli_in_candidates() -> None:
    from src.tools_status import CLI_CANDIDATES

    ids = {item["id"] for item in CLI_CANDIDATES}
    assert "grok-cli" in ids


def test_resolve_agent_type_grok() -> None:
    from src.tools_status import resolve_agent_type_for_tool

    assert resolve_agent_type_for_tool("grok-cli") == "grok-cli"
    assert resolve_agent_type_for_tool("grok") == "grok-cli"


def test_grok_cli_adapter_invokes_generic(monkeypatch) -> None:
    from src.adapters.grok_cli_adapter import chat_grok_cli

    captured: dict = {}

    def _fake(prompt: str, **kwargs):
        captured.update({"prompt": prompt, **kwargs})
        return "ok"

    monkeypatch.setattr("src.adapters.grok_cli_adapter.chat_generic_cli", _fake)
    out = chat_grok_cli("hello", cwd="/tmp")
    assert out == "ok"
    assert captured.get("binary") == "grok"
    assert captured.get("prompt_flag") == "-p"


def test_engine_router_grok_config() -> None:
    from src.engine_router import CLI_ROUTING_CONFIGS

    cfg = CLI_ROUTING_CONFIGS["grok-cli"]
    assert cfg["binary_name"] == "grok"
    assert cfg["prompt_flag"] == "-p"
