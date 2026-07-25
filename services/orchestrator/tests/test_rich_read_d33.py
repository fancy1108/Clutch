"""D33 — rich read_file for images and PDF."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.builtin_tools import execute_builtin_tool
from src.rich_read_util import read_image_workspace_file, read_pdf_workspace_file


def _activate_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None
    ws = tmp_path / "repo"
    ws.mkdir()
    workspace_mod.add_workspace(str(ws))
    return ws


def test_read_image_uses_analysis(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ws = _activate_workspace(tmp_path, monkeypatch)
    img = ws / "shot.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setattr(
        "src.design.image_analysis.image_analysis_prompt_fragment_for_chat",
        lambda _url: "[Attached image — local analysis]\nVisible text (OCR): hello",
    )
    out = execute_builtin_tool("read_file", {"path": "shot.png"})
    assert "hello" in out


def test_read_pdf_without_pdftotext(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ws = _activate_workspace(tmp_path, monkeypatch)
    pdf = ws / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr("src.rich_read_util.shutil.which", lambda _name: None)
    out = execute_builtin_tool("read_file", {"path": "doc.pdf"})
    assert "pdftotext not found" in out


def test_read_pdf_with_pdftotext(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ws = _activate_workspace(tmp_path, monkeypatch)
    pdf = ws / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    class _Proc:
        returncode = 0
        stdout = "PDF body text"
        stderr = ""

    monkeypatch.setattr("src.rich_read_util.shutil.which", lambda _name: "/usr/bin/pdftotext")
    monkeypatch.setattr("src.rich_read_util.subprocess.run", lambda *a, **k: _Proc())
    out = read_pdf_workspace_file(pdf)
    assert "PDF body text" in out
