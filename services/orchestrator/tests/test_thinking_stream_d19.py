"""D19 — thinking stream + shell output snippets."""

from __future__ import annotations

from src.mcp_react import _accumulate_model_reasoning
from src.tool_steps import append_execute_output_detail, make_tool_step


def test_append_execute_output_detail_for_shell() -> None:
    step = make_tool_step(
        tool_alias="run_terminal_cmd",
        func_args={"command": "echo hello"},
        status="completed",
        step_idx=0,
    )
    merged = append_execute_output_detail(
        step,
        "run_terminal_cmd",
        "exit_code=0\nhello\nworld\n",
    )
    assert "hello" in merged["detail"]
    assert merged["detail"].startswith("exit_code=0")


def test_accumulate_model_reasoning_joins_chunks() -> None:
    chunks: list[str] = []
    seen: list[str] = []

    def on_reasoning(text: str) -> None:
        seen.append(text)

    _accumulate_model_reasoning(
        {"content": "ok", "reasoning_content": "step one"},
        chunks,
        on_reasoning,
    )
    _accumulate_model_reasoning(
        {"content": "ok", "reasoning_content": "step two"},
        chunks,
        on_reasoning,
    )
    assert seen[-1] == "step one\n\nstep two"
