"""Tests for neutral terminal log prefixes."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from src.terminal_logs import TAG_CHECK, TAG_WORKFLOW, agent_line, china_chat_time, stamp_log_line, tagged


def test_tagged_workflow_prefix() -> None:
    assert tagged(TAG_WORKFLOW, "Starting workflow") == "[WORKFLOW] Starting workflow"


def test_agent_line_uses_label_when_no_agent_ref() -> None:
    assert agent_line("", "Starting task", label="准备视频工程") == "[准备视频工程] Starting task"


def test_agent_line_uses_agent_ref_when_unresolved() -> None:
    assert agent_line("custom-role", "done") == "[custom-role] done"


def test_check_tag() -> None:
    assert tagged(TAG_CHECK, "check 1 passed").startswith("[CHECK]")


def test_stamp_log_line_adds_china_time() -> None:
    stamped = stamp_log_line("[WORKFLOW] Starting workflow")
    assert " CST] [WORKFLOW] Starting workflow" in stamped
    assert stamped == stamp_log_line(stamped)


def test_china_chat_time_uses_shanghai_timezone() -> None:
    fixed = datetime(2026, 6, 26, 17, 13, 9, tzinfo=ZoneInfo("Asia/Shanghai"))
    with patch("src.terminal_logs.datetime") as mock_dt:
        mock_dt.now.return_value = fixed
        assert china_chat_time() == "17:13"
