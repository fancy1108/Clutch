"""P2-01 — skills registry persistence and SKILL.md scanning."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.skills_scanner import scan_mounted_directories
from src.skills_storage import load_registry, save_registry, skills_dir

client = TestClient(app)


@pytest.fixture
def skills_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "skills"
    monkeypatch.setenv("CLUTCH_SKILLS_DIR", str(target))
    return target


def _write_skill(root: Path, folder: str, title: str, body: str) -> None:
    skill_dir = root / folder
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"# {title}\n\n{body}\n", encoding="utf-8")


def test_scan_finds_skill_md_and_preserves_active_flag(tmp_path: Path) -> None:
    mount = tmp_path / "cursor-skills"
    _write_skill(mount, "commit", "Commit Skill", "Create atomic git commits.")
    existing = [{"key": "cursor-skills/commit", "isActiveGlobally": True}]
    found = scan_mounted_directories([str(mount)], existing_skills=existing)
    assert len(found) == 1
    assert found[0]["key"] == "cursor-skills/commit"
    assert found[0]["label"] == "Commit Skill"
    assert found[0]["isActiveGlobally"] is True


def test_api_mount_scan_and_toggle(skills_data_dir: Path, tmp_path: Path) -> None:
    mount = tmp_path / "my-skills"
    _write_skill(mount, "lint", "Lint Rules", "Enforce eslint on save.")

    mount_resp = client.post(
        "/api/skills/mount",
        json={"path": str(mount)},
    )
    assert mount_resp.status_code == 200
    body = mount_resp.json()
    assert str(mount.resolve()) in body["mounted_directories"]
    assert any(s["key"] == "my-skills/lint" for s in body["skills"])

    toggle_resp = client.post(
        "/api/skills/toggle",
        json={"key": "my-skills/lint", "is_active": True},
    )
    assert toggle_resp.status_code == 200
    active = [s for s in toggle_resp.json()["skills"] if s["key"] == "my-skills/lint"]
    assert active and active[0]["isActiveGlobally"] is True

    stored = load_registry()
    assert skills_dir() == skills_data_dir
    assert stored["skills"][0]["isActiveGlobally"] is True


def test_api_unmount_removes_skills_from_source(skills_data_dir: Path, tmp_path: Path) -> None:
    mount = tmp_path / "pack"
    _write_skill(mount, "a", "A", "Alpha skill.")
    client.post("/api/skills/mount", json={"path": str(mount)})
    unmount_resp = client.post(
        "/api/skills/unmount",
        json={"path": str(mount)},
    )
    assert unmount_resp.status_code == 200
    body = unmount_resp.json()
    assert str(mount.resolve()) not in body["mounted_directories"]
    assert not any(s.get("source") == str(mount.resolve()) for s in body["skills"])

    save_registry(mounted_directories=[], skills=[])
    assert load_registry()["skills"] == []


def test_ensure_default_skill_mounts_cursor_and_workspace(
    skills_data_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.skills_storage import ensure_default_skill_mounts, load_registry

    cursor_skills = tmp_path / "skills-cursor"
    _write_skill(cursor_skills, "automate", "Automate", "Run automations.")
    ws = tmp_path / "hyperframes"
    _write_skill(ws / "skills", "hyperframes", "Hyperframes", "Project skill.")

    monkeypatch.setattr(
        "src.skills_storage.discover_default_skill_directories",
        lambda **_: [str(cursor_skills.resolve()), str((ws / "skills").resolve())],
    )

    added = ensure_default_skill_mounts(workspace_path=str(ws))
    assert len(added) == 2
    stored = load_registry()
    assert str(cursor_skills.resolve()) in stored["mounted_directories"]
    assert str((ws / "skills").resolve()) in stored["mounted_directories"]

    # Idempotent on second call
    assert ensure_default_skill_mounts(workspace_path=str(ws)) == []


def test_api_get_auto_mounts_defaults(skills_data_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mount = tmp_path / "skills-cursor"
    _write_skill(mount, "canvas", "Canvas", "Canvas layouts.")
    monkeypatch.setattr(
        "src.skills_storage.discover_default_skill_directories",
        lambda **_: [str(mount.resolve())],
    )

    body = client.get("/api/skills").json()
    assert str(mount.resolve()) in body["mounted_directories"]
    assert any(s["key"] == "skills-cursor/canvas" for s in body["skills"])
