"""Tests for workspace attachments + path resolve."""

from __future__ import annotations

import base64
import os
import time
from pathlib import Path

import pytest

from src import workspace
from src.workspace_attachments import (
    ATTACHMENTS_REL,
    ensure_attachments_gitignore,
    maybe_gc_attachments,
    resolve_workspace_file_path,
    save_attachment_data_url,
)
import src.workspace_attachments as wa


@pytest.fixture(autouse=True)
def reset_workspace(tmp_path: Path) -> None:
    workspace.clear_workspace_for_tests()
    workspace.set_workspace(str(tmp_path))


def test_save_attachment_writes_gitignore_and_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "src.design.image_analysis.image_analysis_prompt_fragment_for_chat",
        lambda _url: "OCR: hi",
    )
    png = base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode("ascii")
    data_url = f"data:image/png;base64,{png}"
    result = save_attachment_data_url(data_url, analyze=True)
    assert result["path"].startswith(f"{ATTACHMENTS_REL}/")
    assert result["analysis_text"] == "OCR: hi"
    assert (tmp_path / result["path"]).is_file()
    gi = tmp_path / ATTACHMENTS_REL / ".gitignore"
    assert gi.is_file()
    assert gi.read_text(encoding="utf-8").strip() == "*"


def test_gc_deletes_old_files_when_large(tmp_path: Path) -> None:
    directory = tmp_path / ATTACHMENTS_REL
    ensure_attachments_gitignore(directory)
    old = directory / "old.png"
    old.write_bytes(b"x" * 1024)
    original = wa._dir_size_bytes
    wa._dir_size_bytes = lambda _d: wa._GC_SIZE_BYTES + 1  # type: ignore[assignment]
    try:
        old_mtime = time.time() - wa._GC_AGE_SECONDS - 10
        os.utime(old, (old_mtime, old_mtime))
        deleted = maybe_gc_attachments(directory)
        assert deleted >= 1
        assert not old.exists()
        assert (directory / ".gitignore").is_file()
    finally:
        wa._dir_size_bytes = original  # type: ignore[assignment]


def test_resolve_exact_and_basename(tmp_path: Path) -> None:
    nested = tmp_path / "src" / "components"
    nested.mkdir(parents=True)
    (nested / "Button.tsx").write_text("export {}", encoding="utf-8")

    exact = resolve_workspace_file_path("src/components/Button.tsx")
    assert exact == {"ok": True, "path": "src/components/Button.tsx", "match": "exact"}

    fuzzy = resolve_workspace_file_path("Button.tsx")
    assert fuzzy["ok"] is True
    assert fuzzy["path"] == "src/components/Button.tsx"
    assert fuzzy["match"] == "basename"

    missing = resolve_workspace_file_path("Missing.tsx")
    assert missing == {"ok": False, "reason": "not_found"}


def test_resolve_strips_trailing_punct(tmp_path: Path) -> None:
    (tmp_path / "foo.ts").write_text("x", encoding="utf-8")
    result = resolve_workspace_file_path("./foo.ts,")
    assert result["ok"] is True
    assert result["path"] == "foo.ts"


def test_resolve_ambiguous_basename(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "dup.ts").write_text("1", encoding="utf-8")
    (tmp_path / "b" / "dup.ts").write_text("2", encoding="utf-8")
    result = resolve_workspace_file_path("dup.ts")
    assert result == {"ok": False, "reason": "ambiguous"}


def test_attachments_and_resolve_http_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: running Sidecar must expose these routes (404 = stale process)."""
    from fastapi.testclient import TestClient

    from src.main import app

    workspace.clear_workspace_for_tests()
    workspace.set_workspace(str(tmp_path))
    monkeypatch.setattr(
        "src.design.image_analysis.image_analysis_prompt_fragment_for_chat",
        lambda _url: "colors: #abc",
    )

    client = TestClient(app)
    png = base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode("ascii")
    upload = client.post(
        "/api/workspace/attachments",
        json={"data_url": f"data:image/png;base64,{png}", "analyze": True},
    )
    assert upload.status_code == 200, upload.text
    body = upload.json()
    assert body["path"].startswith(f"{ATTACHMENTS_REL}/")
    assert "colors: #abc" in body.get("analysis_text", "")
    assert (tmp_path / body["path"]).is_file()
    assert (tmp_path / ATTACHMENTS_REL / ".gitignore").read_text(encoding="utf-8").strip() == "*"

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "OnlyOne.tsx").write_text("x", encoding="utf-8")
    resolved = client.get("/api/workspace/file/resolve", params={"path": "OnlyOne.tsx"})
    assert resolved.status_code == 200, resolved.text
    assert resolved.json() == {
        "ok": True,
        "path": "src/OnlyOne.tsx",
        "match": "basename",
    }

    missing = client.get("/api/workspace/file/resolve", params={"path": "Nope.tsx"})
    assert missing.status_code == 200
    assert missing.json()["ok"] is False

