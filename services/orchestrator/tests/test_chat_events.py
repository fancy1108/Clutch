"""Chat event builder tests."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from src.chat_events import chat_message, chat_time


def test_chat_time_matches_terminal_timezone() -> None:
    fixed = datetime(2026, 6, 26, 17, 13, 9, tzinfo=ZoneInfo("Asia/Shanghai"))
    with patch("src.terminal_logs.datetime") as mock_dt:
        mock_dt.now.return_value = fixed
        assert chat_time() == "17:13"


def test_chat_message_includes_china_time() -> None:
    fixed = datetime(2026, 6, 26, 9, 13, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    with patch("src.terminal_logs.datetime") as mock_dt:
        mock_dt.now.return_value = fixed
        payload = chat_message("The Artist", "![img](https://example.com/a.png)")
    assert payload["time"] == "09:13"
    assert payload["agent"] == "The Artist"
