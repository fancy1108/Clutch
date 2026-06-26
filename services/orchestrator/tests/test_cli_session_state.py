"""CLI session id fields on ClutchState (cli_session_id migration)."""

from __future__ import annotations

from src.state import (
    cli_session_patch,
    initial_state,
    read_cli_session_agent_id,
    read_cli_session_id,
)


def test_read_cli_session_id_prefers_new_field() -> None:
    state = {"cli_session_id": "new-id", "claude_session_id": "legacy-id"}
    assert read_cli_session_id(state) == "new-id"


def test_read_cli_session_id_falls_back_to_legacy() -> None:
    state = {"claude_session_id": "legacy-id"}
    assert read_cli_session_id(state) == "legacy-id"


def test_cli_session_patch_clears_when_no_session() -> None:
    assert cli_session_patch(None, "") == {"cli_session_id": "", "cli_session_agent_id": ""}


def test_initial_state_uses_cli_session_fields() -> None:
    state = initial_state("run_test")
    assert state["cli_session_id"] == ""
    assert state["cli_session_agent_id"] == ""
    assert read_cli_session_agent_id(state) == ""
