"""D5/D50 submit_verification report helpers."""

from __future__ import annotations

from src.builtin_tools import (
    execute_builtin_tool,
    is_submit_verification_tool,
    list_builtin_tools,
    normalize_verification_report,
)
from src.chat_runner import _chat_message, _verification_report_for_seal
from src.mcp_risk import is_risky_mcp_tool


def test_submit_verification_listed() -> None:
    assert "submit_verification" in {t["name"] for t in list_builtin_tools()}
    assert is_submit_verification_tool("clutch-tools__submit_verification")
    assert not is_risky_mcp_tool("submit_verification")


def test_normalize_and_execute_passed() -> None:
    report = normalize_verification_report(
        {
            "title": "Health cache check",
            "conclusion": "passed",
            "steps": [
                {"name": "Import cache_service", "status": "passed"},
                {"name": "health.check returns ok", "status": "passed"},
            ],
            "summary": "All green",
            "changed_files": ["health.py"],
        }
    )
    assert report["conclusion"] == "passed"
    assert len(report["steps"]) == 2
    assert report["changedFiles"] == ["health.py"]
    out = execute_builtin_tool("submit_verification", report)
    assert "Verification PASSED" in out
    assert "Import cache_service" in out


def test_force_failed_when_todos_incomplete() -> None:
    report = normalize_verification_report(
        {
            "title": "Done?",
            "conclusion": "passed",
            "steps": [{"name": "lint", "status": "passed"}],
        },
        existing_todos=[
            {"id": "1", "content": "Write tests", "status": "pending"},
            {"id": "2", "content": "Update README", "status": "completed"},
        ],
    )
    assert report["conclusion"] == "failed"
    assert report["steps"][0]["id"] == "todos_incomplete"
    assert any("todos" in a.lower() for a in report["nextActions"])
    out = execute_builtin_tool(
        "submit_verification",
        {
            "title": report["title"],
            "conclusion": report["conclusion"],
            "steps": report["steps"],
            "next_actions": report["nextActions"],
            "summary": report["summary"],
        },
    )
    assert "Verification FAILED" in out


def test_failed_step_forces_failed_conclusion() -> None:
    report = normalize_verification_report(
        {
            "title": "Import check",
            "conclusion": "passed",
            "steps": [
                {"name": "import missing_mod", "status": "failed", "detail": "ModuleNotFound"},
            ],
            "next_actions": ["Install dependency"],
        }
    )
    assert report["conclusion"] == "failed"


def test_seal_helper_merges_files_changed() -> None:
    state = {
        "verification_report": {
            "title": "T",
            "conclusion": "failed",
            "steps": [],
            "changedFiles": ["a.py"],
        }
    }
    sealed = _verification_report_for_seal(state, files_changed=["b.py", "a.py"])  # type: ignore[arg-type]
    assert sealed is not None
    assert sealed["changedFiles"] == ["a.py", "b.py"]
    msg = _chat_message("Clutch Agent", "done", verification_report=sealed)
    assert msg["verificationReport"]["conclusion"] == "failed"
