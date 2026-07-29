"""Regression: optional ClutchState keys must survive _merge_patch (D3/D5)."""

from __future__ import annotations

from src.chat_runner import _merge_patch, _verification_report_for_seal
from src.state import initial_state


def test_merge_patch_keeps_agent_todos_and_verification_report() -> None:
    state = initial_state("run_merge_opt")
    report = {
        "title": "Import fail",
        "conclusion": "failed",
        "steps": [{"id": "1", "name": "import", "status": "failed", "detail": "missing"}],
        "nextActions": ["Fix import"],
        "changedFiles": ["test_import_fail.py"],
    }
    patched = _merge_patch(
        state,
        {
            "agent_todos": [
                {"id": "t1", "content": "A", "status": "pending"},
            ],
            "verification_report": report,
            "diff_summary": {
                "title": "Changes",
                "files": [{"path": "a.py", "status": "M", "summary": "", "patch": "", "diffs": []}],
            },
            "pending_tool_steps": [{"id": "s1", "title": "Verify"}],
        },
    )
    assert patched.get("agent_todos") and patched["agent_todos"][0]["id"] == "t1"
    assert patched.get("verification_report", {}).get("conclusion") == "failed"
    assert patched.get("diff_summary", {}).get("title") == "Changes"
    assert patched.get("pending_tool_steps")

    sealed = _verification_report_for_seal(patched, files_changed=["extra.py"])
    assert sealed is not None
    assert sealed["conclusion"] == "failed"
    assert "extra.py" in sealed["changedFiles"]
