"""Tests for hybrid_audit_log (HRT-05)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.hybrid_audit_log import (
    append_hybrid_turn_audit,
    build_turn_audit_line,
    get_hybrid_audit_dir,
    hybrid_audit_path_for_date,
    read_hybrid_audit_lines,
    summarize_shell_command,
)


def test_summarize_shell_command_redacts_prompt_and_system() -> None:
    cmd = (
        "CLUTCH_P='secret user prompt'; /usr/bin/claude -p \"$CLUTCH_P\" "
        "--session-id sess-1 --append-system-prompt 'You are secret agent' "
        "--dangerously-skip-permissions; echo __CLUTCH_DONE_x__"
    )
    summary = summarize_shell_command(cmd)
    assert "secret user prompt" not in summary
    assert "secret agent" not in summary
    assert "CLUTCH_P='[redacted]'" in summary
    assert "--append-system-prompt '[redacted]'" in summary
    assert "--session-id sess-1" in summary


def test_append_and_read_audit_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    when = datetime(2026, 6, 27, 12, 0, 0, tzinfo=UTC)
    audit_path = hybrid_audit_path_for_date(when)
    line = build_turn_audit_line(
        run_id="run_audit_1",
        turn_id="abcd1234",
        marker="__CLUTCH_DONE_abcd1234__",
        duration_ms=1200,
        result="ok",
        cli_session_id="sess-abc",
        agent="claude",
        command_summary="claude -p [redacted]",
        node_id="plain_chat",
        message="hybrid claude turn ok",
        timestamp=when,
    )
    append_hybrid_turn_audit(line, path=audit_path)

    assert audit_path.exists()
    raw = json.loads(audit_path.read_text(encoding="utf-8").strip())
    assert raw["run_id"] == "run_audit_1"
    assert raw["turn_id"] == "abcd1234"
    assert raw["marker"] == "__CLUTCH_DONE_abcd1234__"
    assert raw["duration_ms"] == 1200
    assert raw["result"] == "ok"
    assert raw["cli_session_id"] == "sess-abc"
    assert raw["agent"] == "claude"
    assert raw["source"] == "shell_exec_runtime"
    assert raw["level"] == "info"
    assert raw["timestamp"] == when.isoformat()

    filtered = read_hybrid_audit_lines(run_id="run_audit_1", audit_dir=get_hybrid_audit_dir())
    assert len(filtered) == 1
    assert filtered[0]["result"] == "ok"

    missing = read_hybrid_audit_lines(run_id="run_other", audit_dir=get_hybrid_audit_dir())
    assert missing == []


def test_read_hybrid_audit_lines_respects_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    audit_dir = get_hybrid_audit_dir()
    audit_dir.mkdir(parents=True)
    audit_file = audit_dir / "2026-06-27.jsonl"
    for idx in range(5):
        append_hybrid_turn_audit(
            build_turn_audit_line(
                run_id=f"run_{idx}",
                turn_id=f"t{idx}",
                marker=f"__CLUTCH_DONE_t{idx}__",
                duration_ms=idx,
                result="ok",
                cli_session_id=None,
                agent="claude",
                command_summary="claude -p [redacted]",
                node_id="plain_chat",
                message="ok",
            ),
            path=audit_file,
        )

    recent = read_hybrid_audit_lines(limit=2, audit_dir=audit_dir)
    assert len(recent) == 2
    assert recent[0]["run_id"] == "run_3"
    assert recent[1]["run_id"] == "run_4"
