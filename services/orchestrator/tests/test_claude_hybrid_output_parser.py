"""Tests for claude_hybrid_output_parser."""

from __future__ import annotations

from src.claude_hybrid_output_parser import (
    ClaudeHybridOutputParser,
    extract_cli_issue_message,
    extract_codex_assistant_output,
    extract_tty_cli_output,
    marker_completed_in_output,
    parse_codex_jsonl_output,
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


def test_marker_completed_ignores_command_echo() -> None:
    marker = "__CLUTCH_DONE_ab12__"
    command_only = (
        f"CLUTCH_P='hi'; claude -p \"$CLUTCH_P\" --dangerously-skip-permissions; "
        f"echo {marker}\n"
    )
    assert marker_completed_in_output(command_only, marker=marker) is False
    completed = (
        f"{command_only}"
        "real answer\n"
        f"{marker}\n"
        "clutch$ "
    )
    assert marker_completed_in_output(completed, marker=marker) is True


def test_marker_completed_with_ansi_before_marker() -> None:
    marker = "__CLUTCH_DONE_debug01__"
    raw = (
        "OK\r\n"
        "\x1b(B\x0f\x1b[>4m\x1b[<u\x1b7\x1b8\x1b]0;\x07\x1b[?25h"
        f"{marker}\r\n"
        "clutch$ "
    )
    assert marker_completed_in_output(raw, marker=marker) is True
    out = ClaudeHybridOutputParser().parse(raw, marker=marker)
    assert out == "OK"


def test_parse_rejects_shell_fragment_assistant() -> None:
    raw = (
        "CLUTCH_P='One word: blue'; /opt/homebrew/bin/agy -p \"$CLUTCH_P\" "
        "--dangerously-skip-permissions; echo __CLUTCH_DONE_5__\n"
        "__CLUTCH_DONE_5__\n"
    )
    out = ClaudeHybridOutputParser().parse(raw, marker="__CLUTCH_DONE_5__")
    assert out == ""


def test_parse_filters_history_echo_and_wait_prompt() -> None:
    raw = (
        "CLUTCH_P='hi'; claude -p \"$CLUTCH_P\" --dangerously-skip-permissions; "
        "echo __CLUTCH_DONE_echo__\n"
        "Assistant: 你好！我是 Clutch Agent，由 Sapiens AI 开发。\n"
        "你好！有什么我可以帮你的吗？\n"
        "你好！有什么我可以帮你的吗？\n"
        "It's been 20 second(s) since the last assistant message, with the user via their main channel.\n"
        "If you were asked to wait / no-reply, and are reached via the main channel, you should take a look at the main channel for new messages, to assess whether the user is waiting or pinging you.\n"
        "你好！有什么我可以帮你的吗？\n"
        "__CLUTCH_DONE_echo__\n"
    )
    out = ClaudeHybridOutputParser().parse(raw, marker="__CLUTCH_DONE_echo__")
    assert out == "你好！有什么我可以帮你的吗？"
    assert "Clutch Agent" not in out
    assert "main channel" not in out


def test_parse_filters_snapshot_handoff_lines() -> None:
    raw = (
        "CLUTCH_P='hi'; claude -p \"$CLUTCH_P\" --dangerously-skip-permissions; "
        "echo __CLUTCH_DONE_h__\n"
        "[Clutch session context]\n"
        "Task summary: 你好\n"
        "Working directory: /Users/fancy/hyperframes\n"
        "我是 Agnes，没有年龄的概念。\n"
        "__CLUTCH_DONE_h__\n"
    )
    out = ClaudeHybridOutputParser().parse(raw, marker="__CLUTCH_DONE_h__")
    assert out == "我是 Agnes，没有年龄的概念。"
    assert "Task summary" not in out
    assert "Working directory" not in out


def test_extract_cli_issue_message_quota() -> None:
    raw = (
        "\x1b[31m⚠ Individual quota reached. Please upgrade your subscription to increase your limits. "
        "Resets in 2h17m22s.\x1b[0m\r\n"
        "How's the CLI experience so far?\r\n"
    )
    issue = extract_cli_issue_message(raw)
    assert issue is not None
    assert "Individual quota reached" in issue
    assert "Resets in 2h17m22s" in issue


def test_extract_tty_cli_output_surfaces_quota_when_no_assistant() -> None:
    raw = (
        "Individual quota reached. Please upgrade your subscription to increase your limits. "
        "Resets in 1h5m0s.\r\n"
    )
    out = extract_tty_cli_output(raw)
    assert "Individual quota reached" in out
    assert "Resets in 1h5m0s" in out


_CODEX_JSONL_HYBRID = (
    "CLUTCH_P='你好'; /Users/fancy/.local/bin/codex exec --skip-git-repo-check "
    "--dangerously-bypass-approvals-and-sandbox --json \"$CLUTCH_P\" </dev/null; "
    "echo __CLUTCH_DONE_codex1__\n"
    "Reading additional input from stdin...\n"
    '{"type":"thread.started","thread_id":"019f0cbe-bd02-75f3-a758-1004ad5cad64"}\n'
    '{"type":"item.completed","item":{"id":"item_0","type":"error","message":"Model metadata warning"}}\n'
    '{"type":"turn.started"}\n'
    '{"type":"item.completed","item":{"id":"item_1","type":"agent_message","text":"你好！有什么我可以帮你的吗？"}}\n'
    '{"type":"turn.completed","usage":{"input_tokens":16731,"output_tokens":12}}\n'
    "__CLUTCH_DONE_codex1__\n"
    "clutch$ "
)

_CODEX_TUI_FALLBACK = (
    "reasoning summaries: none\n"
    "session id: 019f0cbe-bd02-75f3-a758-1004ad5cad64\n"
    "user\n"
    "User Request:\n"
    "warning: Model metadata for gemini-2.0-flash not found.\n"
    "codex\n"
    "你好！有什么我可以帮你的吗？\n"
    "tokens used\n"
    "16,731\n"
)


def test_parse_codex_jsonl_output_extracts_agent_message() -> None:
    raw = (
        '{"type":"item.completed","item":{"type":"agent_message","text":"PONG"}}\n'
        '{"type":"turn.completed","usage":{"output_tokens":1}}\n'
    )
    assert parse_codex_jsonl_output(raw) == "PONG"


def test_extract_codex_assistant_output_from_hybrid_jsonl() -> None:
    out = extract_codex_assistant_output(_CODEX_JSONL_HYBRID, marker="__CLUTCH_DONE_codex1__")
    assert out == "你好！有什么我可以帮你的吗？"
    assert "session id" not in out
    assert "tokens used" not in out


def test_extract_codex_assistant_output_tui_fallback() -> None:
    out = extract_codex_assistant_output(_CODEX_TUI_FALLBACK)
    assert out == "你好！有什么我可以帮你的吗？"


def test_extract_codex_assistant_output_summarizes_skill_stderr() -> None:
    raw = (
        '2026-06-28T11:04:36.081477Z ERROR codex_core::session::session: failed to load skill '
        '/Users/fancy/skills/foo/SKILL.md: missing field description\n'
        '2026-06-28T11:04:36.081500Z ERROR codex_core::session::session: failed to load skill '
        '/Users/fancy/skills/bar/SKILL.md: missing field description\n'
    )
    out = extract_codex_assistant_output(raw)
    assert out == ""


def test_extract_codex_assistant_output_ignores_leaked_system_prompt_line() -> None:
    raw = (
        "User Request:\n"
        "For conversational questions (identity, recall, small talk), answer directly "
        "from the conversation and your role above. Do not scan or modify the workspace "
        "unless the user asks about code, files, or a task.\n"
        "codex\n"
        "你上句说的是「你好」。\n"
    )
    out = extract_codex_assistant_output(raw)
    assert out == "你上句说的是「你好」。"


def test_strip_leading_embedded_prompt_removes_system_protocol_echo() -> None:
    from src.claude_hybrid_output_parser import strip_leading_embedded_prompt

    system = (
        "你是一位资深的世界观架构师。\n\n"
        "工作流要求：\n\n必须且只能输出合法的 JSON 格式。"
    )
    answer = '{"world_background":"floating river","core_conflict":"race"}'
    echoed = f"{system}\n\n{answer}"
    out = strip_leading_embedded_prompt(echoed, system_prompt=system)
    assert out == answer


def test_strip_leading_embedded_prompt_removes_user_request_echo() -> None:
    from src.claude_hybrid_output_parser import strip_leading_embedded_prompt

    system = "You are the architect."
    user = "Dragon Boat Festival adventure"
    answer = '{"core_conflict":"tide"}'
    echoed = f"{system}\n\nUser Request:\n{user}\n\n{answer}"
    out = strip_leading_embedded_prompt(
        echoed,
        system_prompt=system,
        user_prompt=user,
    )
    assert out == answer


def test_extract_trailing_json_object_from_agy_echo() -> None:
    from src.claude_hybrid_output_parser import (
        ClaudeHybridOutputParser,
        extract_trailing_json_object,
    )

    marker = "__CLUTCH_DONE_f6af7427__"
    protocol = (
        "你是一位资深的世界观架构师。你的任务是接收用户输入的初始灵感，并将其转化为结构化的背景设定。\n"
        "工作流要求：必须且只能输出合法的 JSON 格式。"
    )
    payload = {
        "world_background": "端阳仙境",
        "protagonist_design": "艾小叶",
        "core_conflict": "赢得龙舟赛",
    }
    import json

    body = (
        f"{protocol}\n"
        "接收碎片化灵感，完成从 0 到 1 的标准化设定。\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n"
    )
    raw = (
        f"CLUTCH_P='{protocol}'; agy -p \"$CLUTCH_P\"; echo {marker}\n"
        f"{body}"
        f"{marker}\nclutch$ "
    )
    extracted = extract_trailing_json_object(body)
    assert extracted is not None
    assert "端阳仙境" in extracted
    assert "世界观架构师" not in extracted

    parsed = ClaudeHybridOutputParser().parse_structured(
        raw,
        marker=marker,
        system_prompt=protocol,
        user_prompt="接收碎片化灵感，完成从 0 到 1 的标准化设定。",
    )
    assert "端阳仙境" in parsed.assistant
    assert "世界观架构师" not in parsed.assistant
    assert parsed.events[-1].content == parsed.assistant
