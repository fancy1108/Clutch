"""Tests for claude_hybrid_output_parser."""

from __future__ import annotations

from src.claude_hybrid_output_parser import (
    ClaudeHybridOutputParser,
    parse_hybrid_claude_output,
    strip_ansi,
)

_ROUTE_C_ROUND1 = (
    "CLUTCH_P='Reply with exactly: OK'; /Users/fancy/.nvm/versions/node/v24.16.0/bin/"
    "claude -p \"$CLUTCH_P\" --dangerously-skip-permissions; echo __CLUTCH_HYBRID_DONE_1__\r\n"
    "OK\r\n"
    "\x1b(B\x0f\x1b[>4m\x1b[<u\x1b7\x1b8\x1b]0;\x07"
    "__CLUTCH_HYBRID_DONE_1__\r\nclutch$ "
)

_SYSTEM_PROMPT_LEAK = (
    "CLUTCH_P='你是谁'; /Users/fancy/.nvm/versions/node/v24.16.0/bin/claude -p \"$CLUTCH_P\" "
    "--session-id sess-abc --append-system-prompt 'You are Claude test Session, the active agent "
    "in the user\\'s Clutch workspace. Runtime model: Gemini 2.0 Flash.' "
    "--dangerously-skip-permissions; echo __CLUTCH_DONE_8df63c6__\r\n"
    "我是 Claude test Session，你的 Claude Code 助手。\r\n"
    "\x1b(B\x0f\x1b[>4m\x1b[\r\n"
    "__CLUTCH_DONE_8df63c6__\r\nclutch$ "
)


def test_strip_ansi_removes_control_sequences() -> None:
    assert strip_ansi("\x1b[31mOK\x1b[0m") == "OK"
    assert strip_ansi("\x1b(B\x0f\x1b[>4m") == ""


def test_parse_route_c_sample() -> None:
    out = parse_hybrid_claude_output(_ROUTE_C_ROUND1, marker="__CLUTCH_HYBRID_DONE_1__")
    assert out == "OK"


def test_parse_hides_system_prompt_and_shell_echo() -> None:
    out = parse_hybrid_claude_output(_SYSTEM_PROMPT_LEAK, marker="__CLUTCH_DONE_8df63c6__")
    assert out == "我是 Claude test Session，你的 Claude Code 助手。"
    assert "You are Claude test Session" not in out
    assert "claude -p" not in out


def test_marker_in_command_echo_does_not_truncate_response() -> None:
    """First marker occurrence is in shell echo; response follows it."""
    raw = (
        "CLUTCH_P='hi'; claude -p \"$CLUTCH_P\" --dangerously-skip-permissions; "
        "echo __CLUTCH_DONE_ab12__\n"
        "real answer\n"
        "__CLUTCH_DONE_ab12__\n"
    )
    assert ClaudeHybridOutputParser().parse(raw, marker="__CLUTCH_DONE_ab12__") == "real answer"


def test_parse_structured_preserves_debug_events() -> None:
    parsed = ClaudeHybridOutputParser().parse_structured(
        _SYSTEM_PROMPT_LEAK,
        marker="__CLUTCH_DONE_8df63c6__",
        shell_command="claude -p \"$CLUTCH_P\"",
        system_prompt="You are Claude test Session",
    )
    assert parsed.raw == _SYSTEM_PROMPT_LEAK
    assert parsed.assistant == "我是 Claude test Session，你的 Claude Code 助手。"
    types = [event.type for event in parsed.events]
    assert types == ["shell_echo", "system_prompt", "boundary_marker", "assistant"]
    assert parsed.events[0].visible is False
    assert "claude" in parsed.events[0].content
    assert "You are Claude test Session" in parsed.events[1].content
    assert parsed.events[-1].visible is True
    assert "--append-system-prompt '<see System prompt>'" in parsed.events[0].content


def test_parse_filters_agent_placeholder_line() -> None:
    raw = (
        "CLUTCH_P='说你爱我'; claude -p \"$CLUTCH_P\" --dangerously-skip-permissions; "
        "echo __CLUTCH_DONE_y__\n"
        "Define custom parameters or directives for this agent here.\n"
        "我爱你 ❤️\n"
        "__CLUTCH_DONE_y__\n"
    )
    out = ClaudeHybridOutputParser().parse(raw, marker="__CLUTCH_DONE_y__")
    assert out == "我爱你 ❤️"
    assert "Define custom parameters" not in out


def test_parse_filters_blockquote_protocol_lines() -> None:
    raw = (
        "CLUTCH_P='hi'; claude -p \"$CLUTCH_P\" --dangerously-skip-permissions; "
        "echo __CLUTCH_DONE_x__\n"
        "> Runtime model: Gemini 2.0 Flash (gemini-2.0-flash). # Custom Agent Prompt\n"
        "> ## Protocol\n"
        "ENTJ 很果断。\n"
        "__CLUTCH_DONE_x__\n"
    )
    out = ClaudeHybridOutputParser().parse(raw, marker="__CLUTCH_DONE_x__")
    assert out == "ENTJ 很果断。"
    raw = (
        "CLUTCH_P='hi'; claude -p \"$CLUTCH_P\" --dangerously-skip-permissions; "
        "echo __CLUTCH_DONE_x__\n"
        "When asked who you are, identify yourself as Claude test Session.\n"
        "Runtime model: Gemini 2.0 Flash (gemini-2.0-flash).\n"
        "INTJ 是一种理性、独立的性格类型。\n"
        "__CLUTCH_DONE_x__\n"
    )
    out = ClaudeHybridOutputParser().parse(raw, marker="__CLUTCH_DONE_x__")
    assert out == "INTJ 是一种理性、独立的性格类型。"
