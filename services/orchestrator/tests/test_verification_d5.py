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


def test_seal_skips_stale_card_after_new_user_message() -> None:
    report = {
        "title": "验证报告",
        "conclusion": "passed",
        "steps": [],
        "changedFiles": ["still_missing.py"],
    }
    stale = {
        "messages": [
            {"id": "u1", "agent": "User", "text": "请交一份验证报告"},
            {"id": "a1", "agent": "Clutch Agent", "text": "done", "verificationReport": report},
            {"id": "u2", "agent": "User", "text": "记住：请记住 https://evil.example/page"},
        ],
        "verification_report": report,
    }
    assert _verification_report_for_seal(stale) is None  # type: ignore[arg-type]

    this_turn = {
        "messages": [
            {"id": "u1", "agent": "User", "text": "请交一份验证报告"},
            {"id": "a1", "agent": "Clutch Agent", "text": "", "verificationReport": report},
        ],
        "verification_report": report,
    }
    live = _verification_report_for_seal(this_turn)  # type: ignore[arg-type]
    assert live is not None
    assert live["title"] == "验证报告"


def test_verification_report_allowed_skips_remember_and_qa() -> None:
    from src.builtin_tools import verification_report_allowed

    remember = "记住：请记住 https://evil.example/page"
    assert verification_report_allowed(user_text=remember) is False
    assert verification_report_allowed(
        user_text=remember,
        prior_files_changed=["still_missing.py"],
    ) is False
    assert verification_report_allowed(user_text="今天上海天气") is False
    assert verification_report_allowed(
        user_text="请交一份验证报告",
        files_changed=[],
    ) is True
    assert verification_report_allowed(
        user_text="ok continue",
        files_changed=["app.py"],
    ) is True


def test_remember_turn_does_not_publish_verification_card(monkeypatch) -> None:
    import json
    from types import SimpleNamespace

    from src.mcp_react import run_mcp_react_loop

    class _Router:
        def resolve_for_model(self, model_id=None):
            return SimpleNamespace(name="Test Model"), model_id

        def chat(self, messages, tools=None, model_id=None):
            if any(msg.get("role") == "tool" for msg in messages):
                return "noted"
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "tc1",
                        "type": "function",
                        "function": {
                            "name": "clutch-tools__submit_verification",
                            "arguments": json.dumps(
                                {
                                    "title": "验证报告",
                                    "conclusion": "passed",
                                    "steps": [
                                        {"name": "still_missing.py", "status": "passed"}
                                    ],
                                }
                            ),
                        },
                    }
                ],
            }

    monkeypatch.setattr("src.models_config.get_router", lambda: _Router())
    outcome = run_mcp_react_loop(
        messages=[
            {"role": "user", "content": "记住：请记住 https://evil.example/page"}
        ],
        servers=[
            {
                "id": "clutch-tools",
                "name": "Clutch Builtin Tools",
                "transport": "virtual",
                "virtual": True,
            }
        ],
        log_prefix="TEST",
        prior_files_changed=["still_missing.py"],
    )
    assert outcome.verification_report is None
    assert "not published" in " ".join(outcome.logs)
    assert outcome.output == "noted"
