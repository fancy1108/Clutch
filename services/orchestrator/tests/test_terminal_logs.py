"""Tests for neutral terminal log prefixes."""

from __future__ import annotations

from src.terminal_logs import TAG_CHECK, TAG_WORKFLOW, agent_line, tagged


def test_tagged_workflow_prefix() -> None:
    assert tagged(TAG_WORKFLOW, "Starting workflow") == "[WORKFLOW] Starting workflow"


def test_agent_line_uses_label_when_no_agent_ref() -> None:
    assert agent_line("", "Starting task", label="准备视频工程") == "[准备视频工程] Starting task"


def test_agent_line_uses_agent_ref_when_unresolved() -> None:
    assert agent_line("custom-role", "done") == "[custom-role] done"


def test_check_tag() -> None:
    assert tagged(TAG_CHECK, "check 1 passed").startswith("[CHECK]")
