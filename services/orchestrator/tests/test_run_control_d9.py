"""D9 run control — loop fuse, continue helpers, chat-visible stats."""

from __future__ import annotations

from types import SimpleNamespace

from src.mcp_react import run_mcp_react_loop
from src.run_control import (
    build_run_stats,
    continue_user_prompt,
    fuse_message,
    is_tool_failure_result,
    max_consecutive_failures,
    should_offer_continue,
    stop_supervisor_message,
)


def test_is_tool_failure_result() -> None:
    assert is_tool_failure_result("Error executing tool: boom")
    assert is_tool_failure_result("MCP server not connected: x")
    assert not is_tool_failure_result('{"ok": true}')


def test_build_run_stats_and_continue_markers() -> None:
    stats = build_run_stats(tool_steps=3, max_steps=24, session_tokens=1200, fuse_triggered=True)
    assert stats["tool_steps"] == 3
    assert stats["fuse_triggered"] is True
    assert should_offer_continue(fuse_message(failures=3, max_failures=3))
    assert should_offer_continue(stop_supervisor_message(lang="en"))
    assert "Continue" in continue_user_prompt(lang="en") or "continue" in continue_user_prompt(
        lang="en"
    ).lower()


def test_loop_fuse_trips_after_consecutive_failures(monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_LOOP_FUSE_FAILURES", "3")
    assert max_consecutive_failures() == 3

    class _FailRouter:
        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Fail Model", id="fail"), "fail"

        def chat(self, messages, tools=None, model_id=None):
            # Always request the same failing tool.
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "tc1",
                        "type": "function",
                        "function": {
                            "name": "mcp_test__list_files",
                            "arguments": "{}",
                        },
                    }
                ],
            }

    class _FailClient:
        def __init__(self, name: str, endpoint: str, env=None) -> None:
            self.name = name

        def start(self) -> bool:
            return True

        def list_tools(self) -> list[dict]:
            return [
                {
                    "name": "list_files",
                    "description": "List files",
                    "inputSchema": {"type": "object", "properties": {}},
                }
            ]

        def call_tool(self, name: str, arguments: dict) -> dict:
            raise RuntimeError("always fails")

        def close(self) -> None:
            return None

    monkeypatch.setattr("src.mcp_react.McpClient", _FailClient)
    monkeypatch.setattr("src.models_config.get_router", lambda: _FailRouter())
    monkeypatch.setattr(
        "src.adapters.ollama_adapter.model_supports_tool_calling",
        lambda spec: True,
    )

    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "keep trying"}],
        servers=[{"id": "mcp_test", "name": "Test MCP", "endpoint": "echo mcp"}],
        log_prefix="D9",
        max_steps=10,
        pause_on_risky=False,
        permission_mode="full",
    )
    assert outcome.fuse_triggered is True
    assert outcome.consecutive_failures >= 3
    assert "Loop fuse" in outcome.output or "死循环熔断" in outcome.output
    assert any("LOOP FUSE" in line for line in outcome.logs)
