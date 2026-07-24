"""D3/D49 todo_write normalization and sealing helpers."""

from __future__ import annotations

from src.builtin_tools import (
    execute_builtin_tool,
    is_todo_write_tool,
    list_builtin_tools,
    normalize_todo_items,
)
from src.chat_runner import _chat_message


def test_todo_write_listed() -> None:
    assert "todo_write" in {t["name"] for t in list_builtin_tools()}
    assert is_todo_write_tool("clutch-tools__todo_write")


def test_normalize_todo_items_replace_and_merge() -> None:
    todos = normalize_todo_items(
        {
            "todos": [
                {"id": "1", "content": "A", "status": "completed"},
                {"content": "B", "status": "in_progress"},
                "C",
            ]
        }
    )
    assert len(todos) == 3
    assert todos[0]["status"] == "completed"
    assert todos[1]["status"] == "in_progress"
    assert todos[2]["content"] == "C"
    merged = normalize_todo_items(
        {"todos": [{"id": "1", "content": "A2", "status": "pending"}], "merge": True},
        existing=todos,
        merge=True,
    )
    assert merged[0]["content"] == "A2"
    assert len(merged) == 3


def test_execute_todo_write() -> None:
    out = execute_builtin_tool(
        "todo_write",
        {"todos": [{"content": "One", "status": "pending"}, {"content": "Two", "status": "in_progress"}]},
    )
    assert "Updated 2" in out
    assert "in_progress" in out


def test_chat_message_seals_todo_list() -> None:
    payload = _chat_message(
        "Clutch Agent",
        "Working",
        todo_list=[{"id": "1", "content": "A", "status": "pending"}],
    )
    assert payload["todoList"][0]["content"] == "A"
