"""Harness tool-use policy (all tool families) + ReAct skip retry."""

from __future__ import annotations

from types import SimpleNamespace

from src.mcp_react import run_mcp_react_loop
from src.deliverable_intent import (
    html_deliverable_wrapup_nudge,
    is_html_deliverable_path,
    wants_browser_preview,
)
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


def test_plan_approval_expects_todo_then_execute() -> None:
    from src.tool_use_policy import looks_like_plan_approval

    assert looks_like_plan_approval("确认")
    assert looks_like_plan_approval("批准，你按照你自己的计划来")
    assert looks_like_plan_approval("那你按照你说的，去帮我优化")
    assert classify_tool_expectation(
        "确认",
        available_tools={"todo_write", "apply_patch", "search_replace"},
    ).kind == "plan_execute"
    assert classify_tool_expectation(
        "批准，你按照你自己的计划来",
        available_tools={"todo_write", "run_terminal_cmd"},
    ).kind == "plan_execute"
    nudge = should_nudge_for_skipped_tools(
        user_text="确认",
        assistant_text="让我再确认一下执行计划……",
        available_tools={"todo_write", "apply_patch"},
        already_nudged=False,
    )
    assert nudge is not None and nudge.kind == "plan_execute"
    assert "todo_write" in nudge.nudge


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
    nudge = network_budget_stop_nudge(used=3).lower()
    assert "stop searching" in nudge
    assert "search_replace" in nudge or "apply_patch" in nudge
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


def test_html_deliverable_helpers() -> None:
    assert is_html_deliverable_path("ai_short_dramas.html")
    assert is_html_deliverable_path("dist/Index.HTM")
    assert not is_html_deliverable_path("readme.md")
    text = html_deliverable_wrapup_nudge(paths=["ai_short_dramas.html"])
    assert "ai_short_dramas.html" in text
    assert "todo_write" in text
    assert wants_browser_preview("生成一个 HTML 页面")
    assert not wants_browser_preview("搜索金华，总结一下，生成图片")
    assert not wants_browser_preview("写一段 Python 代码")


def test_react_html_write_triggers_wrapup_nudge(monkeypatch) -> None:
    """After writing HTML *when user asked for a page*, nudge once to close the turn."""
    phase = {"n": 0}

    class _Router:
        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Agnes 2.0 Flash"), model_id

        def chat(self, messages, tools=None, model_id=None, tool_choice=None):
            phase["n"] += 1
            if phase["n"] == 1:
                return {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "tc_write",
                            "type": "function",
                            "function": {
                                "name": "clutch-tools__search_replace",
                                "arguments": {
                                    "path": "page.html",
                                    "old_string": "",
                                    "new_string": "<html>ok</html>",
                                },
                            },
                        }
                    ],
                }
            assert any(
                isinstance(m.get("content"), str)
                and "HTML deliverable ready" in m.get("content", "")
                for m in messages
            )
            return "Done — wrote page.html"

    monkeypatch.setattr("src.models_config.get_router", lambda: _Router())
    monkeypatch.setattr(
        "src.adapters.ollama_adapter.model_supports_tool_calling",
        lambda spec: True,
    )
    monkeypatch.setattr(
        "src.builtin_tools.list_builtin_tools",
        lambda: [
            {
                "name": "search_replace",
                "description": "write",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "old_string": {"type": "string"},
                        "new_string": {"type": "string"},
                    },
                    "required": ["path", "new_string"],
                },
            }
        ],
    )
    monkeypatch.setattr(
        "src.builtin_tools.execute_builtin_tool",
        lambda name, args: '{"path":"page.html","changed_paths":["page.html"]}',
    )

    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "生成一个 HTML 页面"}],
        servers=[
            {
                "id": "clutch-tools",
                "name": "Clutch Builtin Tools",
                "virtual": True,
                "transport": "virtual",
            }
        ],
        log_prefix="TEST",
        max_steps=6,
    )
    assert any("HTML deliverable wrap-up nudge" in line for line in outcome.logs)
    assert "page.html" in outcome.output




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
