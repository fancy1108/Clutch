"""B-37: test suite + artifact review gate on submit_verification."""

from __future__ import annotations

from pathlib import Path

from src.builtin_tools import normalize_verification_report
from src.verify_harness import detect_test_command, review_artifacts


def _activate(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    ws = tmp_path / "proj"
    ws.mkdir()
    workspace_mod.add_workspace(str(ws))
    return ws


def _passed_payload(**extra):
    body = {
        "title": "Done",
        "conclusion": "passed",
        "steps": [{"name": "self check", "status": "passed"}],
    }
    body.update(extra)
    return body


def test_no_workspace_leaves_self_report(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "none.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    report = normalize_verification_report(_passed_payload())
    assert report["conclusion"] == "passed"
    assert all(s.get("id") != "harness_tests" for s in report["steps"])


def test_failed_tests_block_passed(tmp_path: Path, monkeypatch) -> None:
    ws = _activate(tmp_path, monkeypatch)
    (ws / "tests").mkdir()
    (ws / "tests" / "test_boom.py").write_text("def test_boom():\n    assert False\n", encoding="utf-8")
    monkeypatch.setenv("CLUTCH_VERIFY_TEST_TIMEOUT", "20")
    report = normalize_verification_report(_passed_payload())
    assert report["conclusion"] == "failed"
    assert report["steps"][0]["id"] == "harness_tests"
    assert report["steps"][0]["status"] == "failed"
    assert any("test suite" in a.lower() for a in report["nextActions"])
    assert "forced to failed" in (report.get("summary") or "").lower()


def test_passing_tests_and_missing_file_block(tmp_path: Path, monkeypatch) -> None:
    ws = _activate(tmp_path, monkeypatch)
    (ws / "tests").mkdir()
    (ws / "tests" / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    monkeypatch.setenv("CLUTCH_VERIFY_TEST_TIMEOUT", "20")
    report = normalize_verification_report(
        _passed_payload(changed_files=["src/missing.py"])
    )
    assert report["conclusion"] == "failed"
    ids = {s["id"] for s in report["steps"]}
    assert "harness_tests" in ids
    assert "harness_artifacts" in ids
    art = next(s for s in report["steps"] if s["id"] == "harness_artifacts")
    assert art["status"] == "failed"
    assert "missing" in (report.get("summary") or "").lower()


def test_detect_and_review_helpers(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    assert detect_test_command(tmp_path) is not None
    (tmp_path / "app.py").write_text("x\n", encoding="utf-8")
    ok, _ = review_artifacts(tmp_path, ["app.py"])
    assert ok
    ok, detail = review_artifacts(tmp_path, ["gone.py"])
    assert not ok
    assert "gone.py" in detail


def test_already_applied_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    _activate(tmp_path, monkeypatch)
    first = normalize_verification_report(_passed_payload())
    second = normalize_verification_report(
        {
            "title": first["title"],
            "conclusion": first["conclusion"],
            "steps": first["steps"],
            "changed_files": first.get("changedFiles") or [],
        }
    )
    assert [s.get("id") for s in second["steps"]].count("harness_tests") <= 1
