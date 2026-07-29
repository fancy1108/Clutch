"""D21 — gitignore/clutchignore filtering and strict sandbox."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.builtin_tools import execute_builtin_tool
from src.ignore_rules import clear_ignore_cache, is_ignored_path
from src.workspace import WorkspaceError, clear_workspace_for_tests, set_workspace


@pytest.fixture(autouse=True)
def _reset_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clear_ignore_cache()
    clear_workspace_for_tests()
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("CLUTCH_PREFERENCES_DIR", str(tmp_path / "prefs"))
    (tmp_path / "prefs").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".gitignore").write_text("secrets/\n*.env\n", encoding="utf-8")
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "key.env").write_text("TOKEN=secret\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "public.env").write_text("PUBLIC=1\n", encoding="utf-8")
    set_workspace(str(tmp_path))


def test_ignored_paths_not_listed_or_grepped() -> None:
    from src.workspace import require_workspace

    ws = require_workspace()
    assert is_ignored_path(ws, "secrets/key.env")
    assert is_ignored_path(ws, "public.env")

    listed = execute_builtin_tool("list_dir", {"path": "."})
    assert "secrets/" not in listed
    assert "public.env" not in listed
    assert "src/" in listed

    grep_out = execute_builtin_tool("grep", {"pattern": "TOKEN", "path": "."})
    assert "secrets" not in grep_out
    assert grep_out == "(no matches)"


def test_read_ignored_file_rejected() -> None:
    out = execute_builtin_tool("read_file", {"path": "secrets/key.env"})
    assert out.startswith("Error executing tool:")
    assert "ignored" in out.lower() or "忽略" in out


def test_strict_sandbox_rejects_escape_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.preferences_storage import save_strict_sandbox

    save_strict_sandbox(True)
    out = execute_builtin_tool("run_terminal_cmd", {"command": "cd ../outside && pwd"})
    assert out.startswith("Error executing tool:")
    assert "sandbox" in out.lower() or "沙箱" in out


def test_strict_sandbox_rejects_outside_absolute_path(tmp_path: Path) -> None:
    from src.preferences_storage import save_strict_sandbox

    save_strict_sandbox(True)
    out = execute_builtin_tool("run_terminal_cmd", {"command": "cat /etc/passwd"})
    assert out.startswith("Error executing tool:")
    assert "sandbox" in out.lower() or "沙箱" in out
