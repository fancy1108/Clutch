"""D24 — diagnostics tool MVP."""

from __future__ import annotations

from pathlib import Path


def test_run_py_compile_finds_syntax_error(tmp_path: Path) -> None:
    from src.code_diagnostics import format_diagnostics_for_prompt, run_code_diagnostics

    bad = tmp_path / "bad.py"
    bad.write_text("def oops(\n", encoding="utf-8")
    issues = run_code_diagnostics(tmp_path, ["bad.py"])
    assert issues
    assert any(item.get("tool") == "py_compile" for item in issues)
    prompt = format_diagnostics_for_prompt(issues)
    assert "bad.py" in prompt or "diagnostics" in prompt.lower()


def test_builtin_diagnostics_tool_stores_pending(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "err.py").write_text("syntax (\n", encoding="utf-8")
    workspace_mod.add_workspace(str(ws))

    from src.bg_jobs import bind_bg_job_context, release_bg_job_context
    from src.builtin_tools import execute_builtin_tool
    from src.code_diagnostics import peek_pending_diagnostics

    token = bind_bg_job_context({"run_id": "run_d24"})
    try:
        out = execute_builtin_tool("diagnostics", {"paths": ["err.py"]})
        assert "count" in out
        pending = peek_pending_diagnostics("run_d24")
        assert pending
    finally:
        release_bg_job_context(token)
