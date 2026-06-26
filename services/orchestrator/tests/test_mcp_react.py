"""Tests for shared MCP ReAct loop (P2-15)."""

from __future__ import annotations

from types import SimpleNamespace

from src.mcp_react import McpRunOutcome, run_mcp_react_loop


class _FakeRouter:
    def get_active_model(self) -> SimpleNamespace:
        return SimpleNamespace(name="Test Model")

    def resolve_for_model(self, model_id=None):
        return SimpleNamespace(name="Test Model"), model_id

    def chat(self, messages, tools=None, model_id=None):
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


def test_run_mcp_react_text_only_when_model_lacks_tools(monkeypatch) -> None:
    class _TextOnlyRouter:
        def resolve_for_model(self, model_id=None):
            from src.llm.router import BUILTIN_MODELS

            spec = BUILTIN_MODELS["qwen2.5vl-7b"]
            return spec, spec.id

        def chat(self, messages, tools=None, model_id=None):
            assert tools is None
            return "I am Qwen 2.5 VL"

    monkeypatch.setattr("src.models_config.get_router", lambda: _TextOnlyRouter())
    monkeypatch.setattr(
        "src.adapters.ollama_adapter.model_supports_tool_calling",
        lambda spec: False,
    )

    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "你是什么模型"}],
        servers=[{"id": "mcp_test", "name": "Test MCP", "endpoint": "echo mcp"}],
        log_prefix="TEST",
        model_id="qwen2.5vl-7b",
    )
    assert outcome.output == "I am Qwen 2.5 VL"
    assert outcome.engine_label.endswith("no tools")
    assert any("without MCP tools" in line for line in outcome.logs)


def test_run_mcp_react_loop_plain_answer_completes(monkeypatch) -> None:
    """Regression: plain LLM replies must not reference undefined `model`."""
    monkeypatch.setattr("src.mcp_react.McpClient", _FakeClient)
    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeRouter())

    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "hello"}],
        servers=[{"id": "mcp_test", "name": "Test MCP", "endpoint": "echo mcp"}],
        log_prefix="TEST",
    )
    assert outcome.output == "Used tools path"
    assert any("Completed via Test Model" in line for line in outcome.logs)


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

        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Test Model"), model_id

        def chat(self, messages, tools=None, model_id=None):
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "tc1",
                        "type": "function",
                        "function": {
                            "name": "mcp_test__write_file",
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
    assert outcome.approval_required["func_name"] == "mcp_test__write_file"


def test_run_mcp_react_auto_approves_duplicate_risky_tool(monkeypatch) -> None:
    calls = {"count": 0}

    class _RiskyRouter:
        def get_active_model(self) -> SimpleNamespace:
            return SimpleNamespace(name="Test Model")

        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Test Model"), model_id

        def chat(self, messages, tools=None, model_id=None):
            calls["count"] += 1
            if calls["count"] == 1:
                return {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "tc1",
                            "type": "function",
                            "function": {
                                "name": "mcp_test__write_file",
                                "arguments": "{\"path\":\"a.txt\",\"content\":\"\"}",
                            },
                        }
                    ],
                }
            return "done"

    class _WriteClient(_FakeClient):
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

    from src.mcp_risk import mcp_approval_key

    monkeypatch.setattr("src.mcp_react.McpClient", _WriteClient)
    monkeypatch.setattr("src.models_config.get_router", lambda: _RiskyRouter())
    monkeypatch.setattr("src.workspace.to_workspace_relative", lambda path: "a.txt")

    approved_key = mcp_approval_key(
        "mcp_test__write_file",
        {"path": "a.txt", "content": ""},
    )
    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "write file"}],
        servers=[{"id": "mcp_test", "name": "Test MCP", "endpoint": "echo mcp"}],
        pause_on_risky=True,
        approved_tool={
            "tool_call_id": "tc1",
            "func_name": "mcp_test__write_file",
            "func_args": {"path": "a.txt", "content": ""},
            "step_idx": 0,
        },
        approved_keys={approved_key},
    )
    assert outcome.approval_required is None
    assert outcome.output == "done"
    assert any("Auto-approved duplicate risky tool" in line for line in outcome.logs)


def test_tool_alias_matches_openai_name_pattern() -> None:
    import re

    from src.mcp_react import _tool_alias

    alias = _tool_alias("local-fs", "read_file")
    assert alias == "local-fs__read_file"
    assert re.fullmatch(r"[a-zA-Z0-9_-]+", alias)

    dotted = _tool_alias("my.server", "tool.name")
    assert re.fullmatch(r"[a-zA-Z0-9_-]+", dotted)
    assert dotted == "my_server__tool_name"


def test_run_mcp_react_registers_builtin_tools(monkeypatch) -> None:
    class _Router:
        def get_active_model(self) -> SimpleNamespace:
            return SimpleNamespace(name="Test Model")

        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Test Model"), model_id

        def chat(self, messages, tools=None, model_id=None):
            names = [tool["function"]["name"] for tool in tools or []]
            assert "clutch-tools__apply_patch" in names
            return "done"

    monkeypatch.setattr("src.models_config.get_router", lambda: _Router())

    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "patch"}],
        servers=[
            {
                "id": "clutch-tools",
                "name": "Clutch Builtin Tools",
                "transport": "virtual",
                "virtual": True,
            }
        ],
        log_prefix="TEST",
    )
    assert outcome.output == "done"
    assert any("Registered builtin server" in line for line in outcome.logs)


def test_run_mcp_react_builtin_apply_patch_records_files_changed(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    workspace_mod.add_workspace(str(tmp_path))

    class _Router:
        def get_active_model(self) -> SimpleNamespace:
            return SimpleNamespace(name="Test Model")

        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Test Model"), model_id

        def chat(self, messages, tools=None, model_id=None):
            return "done"

    monkeypatch.setattr("src.models_config.get_router", lambda: _Router())

    patch = "*** Begin Patch\n*** Add File: added.txt\n+hi\n*** End Patch"
    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "add"}],
        servers=[{"id": "clutch-tools", "name": "Clutch Builtin Tools", "virtual": True}],
        approved_tool={
            "tool_call_id": "tc1",
            "func_name": "clutch-tools__apply_patch",
            "func_args": {"patch": patch},
            "step_idx": 0,
        },
    )
    assert outcome.files_changed == ["added.txt"]


def test_run_mcp_react_records_files_changed(monkeypatch) -> None:
    class _WriteClient(_FakeClient):
        def list_tools(self) -> list[dict]:
            return [
                {
                    "name": "write_file",
                    "description": "Write file",
                    "inputSchema": {"type": "object", "properties": {}},
                }
            ]

    class _ResumeRouter:
        def get_active_model(self) -> SimpleNamespace:
            return SimpleNamespace(name="Test Model")

        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Test Model"), model_id

        def chat(self, messages, tools=None, model_id=None):
            return "done"

    monkeypatch.setattr("src.mcp_react.McpClient", _WriteClient)
    monkeypatch.setattr("src.models_config.get_router", lambda: _ResumeRouter())
    monkeypatch.setattr("src.workspace.to_workspace_relative", lambda path: "test.txt")

    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "write"}],
        servers=[{"id": "mcp_test", "name": "Test MCP", "endpoint": "echo mcp"}],
        approved_tool={
            "tool_call_id": "tc1",
            "func_name": "mcp_test__write_file",
            "func_args": {"path": "test.txt"},
            "step_idx": 0,
        },
    )
    assert outcome.files_changed == ["test.txt"]
