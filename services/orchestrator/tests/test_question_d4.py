"""D4/D49 ask_user_question pause and question card helpers."""

from __future__ import annotations

from src.builtin_tools import (
    execute_builtin_tool,
    is_ask_user_question_tool,
    list_builtin_tools,
    normalize_question_args,
    parse_question_selection,
)
from src.chat_runner import (
    _chat_message,
    _is_question_pause,
    _messages_for_mcp_pause,
    _patch_question_card_status,
)
from src.mcp_risk import is_risky_mcp_tool


def test_ask_user_question_listed() -> None:
    assert "ask_user_question" in {t["name"] for t in list_builtin_tools()}
    assert is_ask_user_question_tool("clutch-tools__ask_user_question")
    assert not is_ask_user_question_tool("propose_plan")


def test_ask_user_question_not_risky_gate() -> None:
    assert not is_risky_mcp_tool("ask_user_question")
    assert not is_risky_mcp_tool("clutch-tools__ask_user_question")


def test_normalize_question_args() -> None:
    q = normalize_question_args(
        {
            "question": "Which cache?",
            "options": [
                {"id": "redis", "label": "Redis"},
                "Memcached",
            ],
        }
    )
    assert q["question"] == "Which cache?"
    assert q["options"] == [
        {"id": "redis", "label": "Redis"},
        {"id": "opt_2", "label": "Memcached"},
    ]
    assert q["allow_custom"] is True


def test_notify_user_normalizes_send_cancel() -> None:
    q = normalize_question_args({"message": "Build finished"})
    assert q["kind"] == "notify"
    assert q["question"] == "Build finished"
    assert [o["id"] for o in q["options"]] == ["send", "cancel"]
    assert "notify_user" in {t["name"] for t in list_builtin_tools()}
    assert is_ask_user_question_tool("notify_user")


def test_parse_question_selection_json_and_custom() -> None:
    args = {
        "question": "Which cache?",
        "options": [
            {"id": "redis", "label": "Redis"},
            {"id": "mem", "label": "Memcached"},
        ],
    }
    assert parse_question_selection(
        '{"id":"redis","label":"Redis"}', args
    ) == {"id": "redis", "label": "Redis"}
    assert parse_question_selection("Memcached", args) == {
        "id": "mem",
        "label": "Memcached",
    }
    assert parse_question_selection("Something else", args) == {
        "id": "custom",
        "label": "Something else",
    }


def test_execute_with_selected() -> None:
    out = execute_builtin_tool(
        "ask_user_question",
        {
            "question": "Which?",
            "options": [{"id": "a", "label": "A"}],
            "selected": {"id": "a", "label": "A"},
        },
    )
    assert "User selected: A" in out


def test_question_pause_seals_card() -> None:
    pause = {
        "kind": "question",
        "func_name": "clutch-tools__ask_user_question",
        "func_args": {
            "question": "Which cache?",
            "options": [{"id": "redis", "label": "Redis"}, {"id": "mem", "label": "Memcached"}],
        },
        "tool_steps": [],
    }
    assert _is_question_pause(pause)
    messages, msg, created = _messages_for_mcp_pause([], pause, reply_label="Clutch Agent")
    assert created is True
    assert msg["text"] == ""
    assert msg["questionCard"]["question"] == "Which cache?"
    assert msg["questionCard"]["status"] == "pending"
    assert len(msg["questionCard"]["options"]) == 2
    assert "toolSteps" not in msg
    assert len(messages) == 1


def test_patch_question_card_answered() -> None:
    messages = [
        _chat_message(
            "Clutch Agent",
            "",
            question_card={
                "question": "Q?",
                "options": [{"id": "a", "label": "A"}],
                "status": "pending",
            },
        )
    ]
    updated = _patch_question_card_status(
        messages, status="answered", selected={"id": "a", "label": "A"}
    )
    card = updated[0]["questionCard"]
    assert card["status"] == "answered"
    assert card["selectedId"] == "a"
    assert card["selectedLabel"] == "A"
