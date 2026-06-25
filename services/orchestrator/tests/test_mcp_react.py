"""Tests for shared MCP ReAct loop (P2-15)."""

from __future__ import annotations

from types import SimpleNamespace

from src.mcp_react import McpRunOutcome, run_mcp_react_loop


class _FakeRouter:
    def get_active_model(self) -> SimpleNamespace:
        return SimpleNamespace(name="Test Model")

    def chat(self, messages, tools=None):
        if tools:
            return "Used tools path"
        return "Plain answer"


class _FakeClient:
    def __init__(self, name: str, endpoint: str, env=None) -> None:
        self.name = name
        self.endpoint = endpoint

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
        return {"content": [{"type": "text", "text": "ok"}]}

    def close(self) -> None:
        return None


def test_run_mcp_react_loop_returns_engine_label(monkeypatch) -> None:
    monkeypatch.setattr("src.mcp_react.McpClient", _FakeClient)
    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeRouter())

    outcome = run_mcp_react_loop(
        messages=[
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
        ],
        servers=[
            {
                "id": "mcp_test",
                "name": "Test MCP",
                "endpoint": "echo mcp",
            }
        ],
        log_prefix="TEST",
    )
    assert outcome.output == "Used tools path"
    assert "MCP (1 tools)" in outcome.engine_label
    assert any("Connected MCP server" in line for line in outcome.logs)


def test_run_mcp_react_pause_on_risky_tool(monkeypatch) -> None:
    captured: list[str] = []

    class _RiskyRouter:
        def get_active_model(self) -> SimpleNamespace:
            return SimpleNamespace(name="Test Model")

        def chat(self, messages, tools=None):
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "tc1",
                        "type": "function",
                        "function": {
                            "name": "mcp_test::write_file",
                            "arguments": "{\"path\":\"a.txt\"}",
                        },
                    }
                ],
            }

    monkeypatch.setattr("src.mcp_react.McpClient", _FakeClient)
    monkeypatch.setattr("src.models_config.get_router", lambda: _RiskyRouter())

    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "write file"}],
        servers=[{"id": "mcp_test", "name": "Test MCP", "endpoint": "echo mcp"}],
        pause_on_risky=True,
        on_log=captured.append,
    )
    assert isinstance(outcome, McpRunOutcome)
    assert outcome.approval_required is not None
    assert outcome.approval_required["func_name"] == "mcp_test::write_file"
    assert any("Approval required" in line for line in captured)
