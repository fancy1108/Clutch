"""D17 — tool hook PreToolUse deny rules."""

from __future__ import annotations

import json
from pathlib import Path

from src.mcp_react import _execute_tool_call
from src.tool_hooks import evaluate_pretool


def test_pretool_deny_from_user_hooks(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_PREFERENCES_DIR", str(tmp_path / "prefs"))
    hooks = {
        "PreToolUse": [
            {
                "tool": "search_replace",
                "action": "deny",
                "reason": "Writes blocked by project hook",
            }
        ]
    }
    path = tmp_path / "prefs" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(hooks), encoding="utf-8")

    verdict = evaluate_pretool("search_replace", {"path": "foo.txt"})
    assert not verdict.allowed
    assert "Writes blocked" in verdict.reason

    logs: list[str] = []
    out = _execute_tool_call(
        func_name="clutch-tools__search_replace",
        func_args={"path": "foo.txt", "old_string": "a", "new_string": "b"},
        tool_routes={"clutch-tools__search_replace": ("clutch-tools", "search_replace")},
        clients={},
        builtin_servers={"clutch-tools"},
        log_prefix="TEST",
        logs=logs,
        on_log=None,
        step_idx=0,
    )
    assert out.startswith("Error executing tool:")
    assert "Hook PreToolUse blocked" in out
