"""D12 — git_status / git_diff / git_commit + web_fetch."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from src.builtin_tools import execute_builtin_tool, list_builtin_tools
from src.mcp_risk import is_risky_mcp_tool
from src.web_fetch_util import fetch_url_text


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "d12@clutch.test"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "D12 Test"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    (path / "hello.txt").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "hello.txt"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def _activate_workspace(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    ws = tmp_path / "repo"
    ws.mkdir()
    _init_repo(ws)
    workspace_mod.add_workspace(str(ws))
    return ws


def test_tool_names_registered() -> None:
    names = {t["name"] for t in list_builtin_tools()}
    assert {"git_status", "git_diff", "git_commit", "web_fetch"} <= names
    assert is_risky_mcp_tool("git_commit")
    assert not is_risky_mcp_tool("git_status")
    assert not is_risky_mcp_tool("web_fetch")


def test_git_status_diff_commit(tmp_path: Path, monkeypatch) -> None:
    ws = _activate_workspace(tmp_path, monkeypatch)
    (ws / "hello.txt").write_text("hello\nworld\n", encoding="utf-8")
    status = execute_builtin_tool("git_status", {})
    assert "hello.txt" in status
    diff = execute_builtin_tool("git_diff", {"paths": ["hello.txt"]})
    assert "world" in diff or "+world" in diff
    committed = execute_builtin_tool(
        "git_commit",
        {"message": "d12 test commit", "paths": ["hello.txt"]},
    )
    assert not committed.startswith("Error"), committed
    payload = json.loads(committed)
    assert payload["ok"] is True
    assert payload.get("sha")


def test_web_fetch_util_html(monkeypatch) -> None:
    html = b"<html><body><h1>Clutch Docs</h1><p>Token budget tip</p><script>x()</script></body></html>"

    class _Resp:
        status = 200
        headers = {"Content-Type": "text/html; charset=utf-8"}

        def read(self, n: int = -1) -> bytes:
            return html

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("src.web_fetch_util.urlopen", lambda *a, **k: _Resp())
    payload = fetch_url_text("https://example.com/docs")
    assert payload["status"] == 200
    assert "Clutch Docs" in payload["text"]
    assert "Token budget tip" in payload["text"]
    assert "x()" not in payload["text"]


def test_web_fetch_tool_rejects_bad_url(tmp_path: Path, monkeypatch) -> None:
    _activate_workspace(tmp_path, monkeypatch)
    out = execute_builtin_tool("web_fetch", {"url": "not-a-url"})
    assert out.startswith("Error executing tool:")
