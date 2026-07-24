"""D13 — permission rules allow/ask/deny + dangerous force-ask + clear memory."""

from __future__ import annotations

from src.mcp_pending import clear_mcp_approval_state, get_approved_mcp_keys, record_mcp_approval
from src.permission_rules import (
    is_dangerous_command,
    load_permission_rules,
    match_rule,
    resolve_tool_gate,
    save_permission_rules,
)


def test_dangerous_rm_force_ask_even_in_full() -> None:
    assert is_dangerous_command("rm -rf /tmp/foo")
    gate = resolve_tool_gate(
        tool_name="run_terminal_cmd",
        func_args={"command": "rm -rf ./build"},
        permission_mode="full",
    )
    assert gate == "ask"


def test_deny_rule_blocks(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_PREFERENCES_DIR", str(tmp_path))
    save_permission_rules([{"pattern": r"npm\s+publish", "action": "deny"}])
    assert match_rule("npm publish --access public") == "deny"
    gate = resolve_tool_gate(
        tool_name="run_terminal_cmd",
        func_args={"command": "npm publish"},
        permission_mode="full",
    )
    assert gate == "deny"
    assert load_permission_rules()[0]["action"] == "deny"


def test_allow_rule_skips_pause(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_PREFERENCES_DIR", str(tmp_path))
    save_permission_rules([{"pattern": r"^echo\b", "action": "allow"}])
    gate = resolve_tool_gate(
        tool_name="run_terminal_cmd",
        func_args={"command": "echo hi"},
        permission_mode="ask",
    )
    assert gate == "allow"


def test_clear_mcp_approval_state() -> None:
    run_id = "run_d13_clear"
    clear_mcp_approval_state(run_id)
    record_mcp_approval(run_id, "run_terminal_cmd", {"command": "ls"})
    assert get_approved_mcp_keys(run_id)
    clear_mcp_approval_state(run_id)
    assert not get_approved_mcp_keys(run_id)
