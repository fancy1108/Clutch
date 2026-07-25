"""Harness tool-use policy (all tool families) + ReAct skip retry."""

from __future__ import annotations

from types import SimpleNamespace

from src.mcp_react import run_mcp_react_loop
from src.tool_use_policy import (
    NETWORK_HARD_BUDGET,
    NETWORK_SOFT_BUDGET,
    classify_tool_expectation,
    is_network_tool,
    network_budget_exhausted_result,
    network_budget_stop_nudge,
    should_nudge_for_skipped_tools,
    turn_expects_network_tools,
)


def test_classify_covers_network_workspace_git_shell() -> None:
    assert classify_tool_expectation(
        "今天上海天气怎么样",
        available_tools={"web_fetch"},
    ).kind == "network"
    assert classify_tool_expectation(
        "看看项目里有哪些文件",
        available_tools={"list_dir", "read_file"},
    ).kind == "workspace_read"
    assert classify_tool_expectation(
        "把 README 标题改一下",
        available_tools={"search_replace", "read_file"},
    ).kind == "workspace_write"
    assert classify_tool_expectation(
        "看一下 git status",
        available_tools={"git_status", "git_diff"},
    ).kind == "git"
    assert classify_tool_expectation(
        "跑一下 pytest",
        available_tools={"run_terminal_cmd"},
    ).kind == "shell"
    assert (
        classify_tool_expectation(
            "你好",
            available_tools={"web_fetch", "list_dir"},
        )
        is None
    )


def test_weather_turn_expects_network_tools() -> None:
    assert turn_expects_network_tools(
        "今天上海天气怎么样",
        has_web_search=False,
        has_web_fetch=True,
    )
    assert turn_expects_network_tools(
        "上海迪士尼最近有什么活动不",
        has_web_search=True,
        has_web_fetch=True,
    )
    assert not turn_expects_network_tools(
        "把 README 里的标题改一下",
        has_web_search=True,
        has_web_fetch=True,
    )


def test_network_budget_helpers() -> None:
    assert is_network_tool("clutch-tools__web_fetch")
    assert is_network_tool("web_search")
    assert not is_network_tool("list_dir")
    assert NETWORK_SOFT_BUDGET == 3
    assert NETWORK_HARD_BUDGET == 5
    assert "stop searching" in network_budget_stop_nudge(used=3).lower()
    assert "exhausted" in network_budget_exhausted_result(used=5).lower()


def test_should_nudge_once_per_turn() -> None:
    first = should_nudge_for_skipped_tools(
        user_text="今天上海天气怎么样",
        assistant_text="I cannot directly obtain real-time weather data.",
        available_tools={"web_fetch"},
        already_nudged=False,
    )
    assert first is not None and first.kind == "network"
    assert (
        should_nudge_for_skipped_tools(
            user_text="今天上海天气怎么样",
            assistant_text="…",
            available_tools={"web_fetch"},
            already_nudged=True,
        )
        is None
    )


def test_refusal_prose_gets_generic_nudge() -> None:
    nudge = should_nudge_for_skipped_tools(
        user_text="随便聊聊",
        assistant_text="I don't have access to your files or workspace.",
        available_tools={"read_file", "list_dir"},
        already_nudged=False,
    )
    assert nudge is not None and nudge.kind == "available"


def test_react_nudges_when_model_skips_weather_tools(monkeypatch) -> None:
    calls: list[dict] = []

    class _Router:
        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Agnes 2.0 Flash"), model_id

        def chat(self, messages, tools=None, model_id=None, tool_choice=None):
            calls.append({"tools": bool(tools), "tool_choice": tool_choice, "n": len(messages)})
            if tool_choice == "required":
                return {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "tc_weather",
                            "type": "function",
                            "function": {
                                "name": "clutch-tools__web_fetch",
                                "arguments": {"url": "https://wttr.in/Shanghai?format=3"},
                            },
                        }
                    ],
                }
            if any(m.get("role") == "tool" for m in messages):
                return "Shanghai weather: sunny, 31°C."
            return "I cannot directly obtain real-time weather data. Check your phone."

    monkeypatch.setattr("src.models_config.get_router", lambda: _Router())
    monkeypatch.setattr(
        "src.adapters.ollama_adapter.model_supports_tool_calling",
        lambda spec: True,
    )
    monkeypatch.setattr(
        "src.builtin_tools.list_builtin_tools",
        lambda: [
            {
                "name": "web_fetch",
                "description": "fetch",
                "inputSchema": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
            }
        ],
    )
    monkeypatch.setattr(
        "src.builtin_tools.execute_builtin_tool",
        lambda name, args: '{"text":"Shanghai: sunny"}',
    )

    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "今天上海天气怎么样"}],
        servers=[
            {
                "id": "clutch-tools",
                "name": "Clutch Builtin Tools",
                "virtual": True,
                "transport": "virtual",
            }
        ],
        log_prefix="TEST",
    )
    assert any(c.get("tool_choice") == "required" for c in calls)
    assert any("Tool-skip nudge (network)" in line for line in outcome.logs)
    assert "sunny" in outcome.output.lower() or "31" in outcome.output


def test_react_nudges_workspace_read(monkeypatch) -> None:
    calls: list[dict] = []

    class _Router:
        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Agnes 2.0 Flash"), model_id

        def chat(self, messages, tools=None, model_id=None, tool_choice=None):
            calls.append({"tool_choice": tool_choice})
            if tool_choice == "required":
                return {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "tc_ls",
                            "type": "function",
                            "function": {
                                "name": "clutch-tools__list_dir",
                                "arguments": {"path": "."},
                            },
                        }
                    ],
                }
            if any(m.get("role") == "tool" for m in messages):
                return "Workspace has README.md and src/."
            return "I don't have access to your files."

    monkeypatch.setattr("src.models_config.get_router", lambda: _Router())
    monkeypatch.setattr(
        "src.adapters.ollama_adapter.model_supports_tool_calling",
        lambda spec: True,
    )
    monkeypatch.setattr(
        "src.builtin_tools.list_builtin_tools",
        lambda: [
            {
                "name": "list_dir",
                "description": "list",
                "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}},
            }
        ],
    )
    monkeypatch.setattr(
        "src.builtin_tools.execute_builtin_tool",
        lambda name, args: '["README.md", "src/"]',
    )

    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "看看项目里有哪些文件"}],
        servers=[
            {
                "id": "clutch-tools",
                "name": "Clutch Builtin Tools",
                "virtual": True,
                "transport": "virtual",
            }
        ],
        log_prefix="TEST",
    )
    assert any(c.get("tool_choice") == "required" for c in calls)
    assert any("Tool-skip nudge (workspace_read)" in line for line in outcome.logs)
    assert "README" in outcome.output


def test_react_network_soft_cap_stops_thrash(monkeypatch) -> None:
    """Open-web Q&A must not burn 24 fetches — soft-cap nudges stop-and-answer."""
    fetch_count = {"n": 0}

    class _Router:
        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Agnes 2.0 Flash"), model_id

        def chat(self, messages, tools=None, model_id=None, tool_choice=None):
            if any(
                isinstance(m.get("content"), str)
                and "stop searching" in m.get("content", "").lower()
                for m in messages
            ):
                return "Shanghai Disney: 10th anniversary events through summer."
            fetch_count["n"] += 1
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": f"tc_{fetch_count['n']}",
                        "type": "function",
                        "function": {
                            "name": "clutch-tools__web_fetch",
                            "arguments": {
                                "url": f"https://example.com/disney-{fetch_count['n']}"
                            },
                        },
                    }
                ],
            }

    monkeypatch.setattr("src.models_config.get_router", lambda: _Router())
    monkeypatch.setattr(
        "src.adapters.ollama_adapter.model_supports_tool_calling",
        lambda spec: True,
    )
    monkeypatch.setattr(
        "src.builtin_tools.list_builtin_tools",
        lambda: [
            {
                "name": "web_fetch",
                "description": "fetch",
                "inputSchema": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
            },
            {
                "name": "web_search",
                "description": "search",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        ],
    )
    monkeypatch.setattr(
        "src.builtin_tools.execute_builtin_tool",
        lambda name, args: '{"text":"snippet about disney events"}',
    )

    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "上海迪士尼最近有什么活动不"}],
        servers=[
            {
                "id": "clutch-tools",
                "name": "Clutch Builtin Tools",
                "virtual": True,
                "transport": "virtual",
            }
        ],
        log_prefix="TEST",
        max_steps=24,
    )
    assert any("Network budget soft-cap" in line for line in outcome.logs)
    assert fetch_count["n"] <= NETWORK_HARD_BUDGET + 1
    assert "disney" in outcome.output.lower() or "anniversary" in outcome.output.lower()
