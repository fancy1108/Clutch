"""D27 — explore permission mode blocks writes, allows reads."""

from __future__ import annotations

from types import SimpleNamespace

from src.agent_prompt import compose_agent_prompt_assembly
from src.mcp_react import McpRunOutcome, run_mcp_react_loop


def test_ask_mode_reminder_in_prompt() -> None:
    ask = compose_agent_prompt_assembly(
        {"id": "clutch-agent", "name": "Clutch Agent"},
        model_name="A",
        model_api="a",
        mcp_servers_bound=True,
        permission_mode="ask",
        clutch_mcp_path=True,
    )
    mode = next(layer for layer in ask.layers if layer.name == "mode")
    assert "Ask" in mode.content
    assert "read-only" in mode.content.lower()


def test_legacy_explore_mode_reminder_aliases_ask() -> None:
    explore = compose_agent_prompt_assembly(
        {"id": "clutch-agent", "name": "Clutch Agent"},
        model_name="A",
        model_api="a",
        mcp_servers_bound=True,
        permission_mode="explore",
        clutch_mcp_path=True,
    )
    mode = next(layer for layer in explore.layers if layer.name == "mode")
    assert "Ask" in mode.content


def test_explore_mode_blocks_write_tool(monkeypatch) -> None:
    captured: list[str] = []

    class _RiskyRouter:
        def get_active_model(self) -> SimpleNamespace:
            return SimpleNamespace(name="Test Model")

        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Test Model"), model_id

        def chat(self, messages, tools=None, model_id=None):
            # After blocked write, model answers without more tools.
            if any(message.get("role") == "tool" for message in messages):
                return "Would create notes.txt with hello"
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "tc1",
                        "type": "function",
                        "function": {
                            "name": "mcp_test__write_file",
                            "arguments": "{\"path\":\"notes.txt\",\"content\":\"hello\"}",
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
            return [
                {
                    "name": "write_file",
                    "description": "Write file",
                    "inputSchema": {"type": "object", "properties": {}},
                }
            ]

        def call_tool(self, name: str, arguments: dict) -> dict:
            return {"content": [{"type": "text", "text": "ok"}]}

        def close(self) -> None:
            return None

    monkeypatch.setattr("src.mcp_react.McpClient", _FakeClient)
    monkeypatch.setattr("src.models_config.get_router", lambda: _RiskyRouter())

    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "write a file"}],
        servers=[{"id": "mcp_test", "name": "Test MCP", "endpoint": "echo mcp"}],
        pause_on_risky=True,
        permission_mode="explore",
        on_log=captured.append,
    )
    assert isinstance(outcome, McpRunOutcome)
    assert outcome.approval_required is None
    assert any("Ask mode: blocked" in line for line in captured)
    assert "Would create" in outcome.output


def test_ask_mode_blocks_write_tool(monkeypatch) -> None:
    captured: list[str] = []

    class _RiskyRouter:
        def get_active_model(self) -> SimpleNamespace:
            return SimpleNamespace(name="Test Model")

        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Test Model"), model_id

        def chat(self, messages, tools=None, model_id=None):
            if any(message.get("role") == "tool" for message in messages):
                return "Would create notes.txt with hello"
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "tc1",
                        "type": "function",
                        "function": {
                            "name": "mcp_test__write_file",
                            "arguments": "{\"path\":\"notes.txt\",\"content\":\"hello\"}",
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
            return [
                {
                    "name": "write_file",
                    "description": "Write file",
                    "inputSchema": {"type": "object", "properties": {}},
                }
            ]

        def call_tool(self, name: str, arguments: dict) -> dict:
            return {"content": [{"type": "text", "text": "ok"}]}

        def close(self) -> None:
            return None

    monkeypatch.setattr("src.mcp_react.McpClient", _FakeClient)
    monkeypatch.setattr("src.models_config.get_router", lambda: _RiskyRouter())

    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "write a file"}],
        servers=[{"id": "mcp_test", "name": "Test MCP", "endpoint": "echo mcp"}],
        pause_on_risky=True,
        permission_mode="ask",
        on_log=captured.append,
    )
    assert isinstance(outcome, McpRunOutcome)
    assert outcome.approval_required is None
    assert any("Ask mode: blocked" in line for line in captured)
    assert "Would create" in outcome.output


def test_explore_mode_allows_read_tool(monkeypatch) -> None:
    class _ReadRouter:
        def get_active_model(self) -> SimpleNamespace:
            return SimpleNamespace(name="Test Model")

        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Test Model"), model_id

        def chat(self, messages, tools=None, model_id=None):
            if any(message.get("role") == "tool" for message in messages):
                return "Found README"
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "tc1",
                        "type": "function",
                        "function": {
                            "name": "clutch-tools__read_file",
                            "arguments": "{\"path\":\"README.md\"}",
                        },
                    }
                ],
            }

    class _ReadClient:
        def __init__(self, name: str, endpoint: str, env=None) -> None:
            self.name = name

        def start(self) -> bool:
            return True

        def list_tools(self) -> list[dict]:
            return [
                {
                    "name": "read_file",
                    "description": "Read file",
                    "inputSchema": {"type": "object", "properties": {}},
                }
            ]

        def call_tool(self, name: str, arguments: dict) -> dict:
            return {"content": [{"type": "text", "text": "# Hello"}]}

        def close(self) -> None:
            return None

    monkeypatch.setattr("src.mcp_react.McpClient", _ReadClient)
    monkeypatch.setattr("src.models_config.get_router", lambda: _ReadRouter())
    monkeypatch.setattr(
        "src.builtin_tools.execute_builtin_tool",
        lambda name, args: "# Hello",
    )

    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "read readme"}],
        servers=[
            {
                "id": "clutch-tools",
                "name": "Clutch Builtin Tools",
                "transport": "virtual",
                "virtual": True,
            }
        ],
        pause_on_risky=True,
        permission_mode="explore",
    )
    assert outcome.approval_required is None
    assert "Found README" in outcome.output
