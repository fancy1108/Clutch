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
    # SERP policy / auto-redirect must not burn the loop fuse.
    assert not is_tool_failure_result(
        "Error executing tool: web_fetch cannot be used on search-engine result pages "
        "(Google/Bing/…). Call web_search with query='AI短剧'"
    )
    assert not is_tool_failure_result(
        '{"query":"x","redirected_from_web_fetch":true,"results":[]}'
    )
    assert not is_tool_failure_result(
        "Error: tool failure budget exhausted for `generate_image` (3/3)."
    )


def test_meta_tool_success_does_not_reset_consecutive_failures() -> None:
    from src.run_control import next_consecutive_failures

    assert next_consecutive_failures(2, result="Error executing tool: x") == 3
    assert next_consecutive_failures(2, result="todos updated", tool_name="todo_write") == 2
    assert next_consecutive_failures(2, result="ok", tool_name="list_dir") == 0
    assert next_consecutive_failures(1, result="ok", tool_name="clutch-tools__todo_write") == 1


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

        def start(self, *args, **kwargs) -> bool:
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


def test_loop_fuse_not_reset_by_todo_write_between_failures(monkeypatch) -> None:
    """todo_write success must not launder generate_image failure streaks (D9 gap)."""
    monkeypatch.setenv("CLUTCH_LOOP_FUSE_FAILURES", "3")
    calls = {"n": 0}

    class _Router:
        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Local 9B"), model_id

        def chat(self, messages, tools=None, model_id=None, tool_choice=None):
            calls["n"] += 1
            # Alternate failing generate_image with successful todo_write.
            if calls["n"] % 2 == 1:
                return {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": f"img_{calls['n']}",
                            "type": "function",
                            "function": {
                                "name": "clutch-tools__generate_image",
                                "arguments": {"prompt": "poster"},
                            },
                        }
                    ],
                }
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": f"todo_{calls['n']}",
                        "type": "function",
                        "function": {
                            "name": "clutch-tools__todo_write",
                            "arguments": {
                                "todos": [
                                    {
                                        "id": "1",
                                        "content": "retry image",
                                        "status": "in_progress",
                                    }
                                ]
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
                "name": "generate_image",
                "description": "image",
                "inputSchema": {
                    "type": "object",
                    "properties": {"prompt": {"type": "string"}},
                    "required": ["prompt"],
                },
            },
            {
                "name": "todo_write",
                "description": "todos",
                "inputSchema": {
                    "type": "object",
                    "properties": {"todos": {"type": "array"}},
                    "required": ["todos"],
                },
            },
        ],
    )

    def _exec(name: str, args: dict) -> str:
        if name == "generate_image":
            return (
                "Error executing tool: image generation failed "
                "(Failed to reach Agnes Image API: Remote end closed connection)."
            )
        return '{"ok": true, "todos": 1}'

    monkeypatch.setattr("src.builtin_tools.execute_builtin_tool", _exec)

    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "金华旅游攻略，要图和HTML"}],
        servers=[
            {
                "id": "clutch-tools",
                "name": "Clutch Builtin Tools",
                "virtual": True,
            }
        ],
        log_prefix="D9META",
        max_steps=12,
        pause_on_risky=False,
        permission_mode="full",
    )
    assert outcome.fuse_triggered is True
    assert outcome.consecutive_failures >= 3
    assert any("LOOP FUSE" in line for line in outcome.logs)


def test_same_tool_hard_cap_blocks_generate_image_thrash(monkeypatch) -> None:
    """After N generate_image failures, further calls are blocked (Cursor-style)."""
    monkeypatch.setenv("CLUTCH_SAME_TOOL_SOFT_FAILURES", "2")
    monkeypatch.setenv("CLUTCH_SAME_TOOL_HARD_FAILURES", "3")
    # Keep consecutive fuse high so same-tool budget is what stops thrash.
    monkeypatch.setenv("CLUTCH_LOOP_FUSE_FAILURES", "99")
    calls = {"n": 0}

    class _Router:
        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Local 9B"), model_id

        def chat(self, messages, tools=None, model_id=None, tool_choice=None):
            blob = " ".join(
                str(m.get("content") or "") for m in messages if isinstance(m, dict)
            )
            # Keep thrashing until hard-cap tool result appears, then answer.
            if "tool failure budget exhausted" in blob.lower():
                return "Image API unreachable; I'll finish without the poster."
            calls["n"] += 1
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": f"img_{calls['n']}",
                        "type": "function",
                        "function": {
                            "name": "clutch-tools__generate_image",
                            "arguments": {"prompt": f"poster {calls['n']}"},
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
                "name": "generate_image",
                "description": "image",
                "inputSchema": {
                    "type": "object",
                    "properties": {"prompt": {"type": "string"}},
                    "required": ["prompt"],
                },
            }
        ],
    )
    monkeypatch.setattr(
        "src.builtin_tools.execute_builtin_tool",
        lambda name, args: (
            "Error executing tool: image generation failed (connection closed)"
        ),
    )

    outcome = run_mcp_react_loop(
        messages=[{"role": "user", "content": "生成一张金华宣传图"}],
        servers=[
            {
                "id": "clutch-tools",
                "name": "Clutch Builtin Tools",
                "virtual": True,
            }
        ],
        log_prefix="SAMETOOL",
        max_steps=10,
        pause_on_risky=False,
        permission_mode="full",
    )
    assert any("Same-tool soft-cap" in line for line in outcome.logs)
    assert any("Same-tool hard-cap" in line for line in outcome.logs)
    # 3 real executes + ≥1 blocked attempt — must not burn the full step budget.
    assert calls["n"] <= 6
