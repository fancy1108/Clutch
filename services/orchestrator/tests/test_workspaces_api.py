"""Multi-workspace API — M2-09."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from src.main import app


def test_list_empty_workspaces() -> None:
    client = TestClient(app)
    response = client.get("/api/workspaces")
    assert response.status_code == 200
    body = response.json()
    assert body["workspaces"] == []
    assert body["active_id"] is None


def test_add_and_list_workspaces(tmp_path: Path) -> None:
    client = TestClient(app)
    first = tmp_path / "alpha"
    second = tmp_path / "beta"
    first.mkdir()
    second.mkdir()

    add_first = client.post("/api/workspaces", json={"path": str(first)})
    assert add_first.status_code == 200
    first_body = add_first.json()
    assert first_body["name"] == "alpha"

    add_second = client.post("/api/workspaces", json={"path": str(second)})
    assert add_second.status_code == 200

    listed = client.get("/api/workspaces").json()
    assert len(listed["workspaces"]) == 2
    assert listed["active_id"] == add_second.json()["id"]

    activate = client.post(f"/api/workspaces/{first_body['id']}/activate")
    assert activate.status_code == 200
    assert client.get("/api/workspaces").json()["active_id"] == first_body["id"]
    assert client.get("/api/workspace").json()["workspace_path"] == str(first)


def test_add_existing_path_activates_without_duplicate(tmp_path: Path) -> None:
    client = TestClient(app)
    project = tmp_path / "clutch"
    project.mkdir()

    first = client.post("/api/workspaces", json={"path": str(project)}).json()
    other = tmp_path / "other"
    other.mkdir()
    client.post("/api/workspaces", json={"path": str(other)})
    second = client.post("/api/workspaces", json={"path": str(project)}).json()

    assert first["id"] == second["id"]
    listed = client.get("/api/workspaces").json()
    assert len(listed["workspaces"]) == 2
    assert listed["active_id"] == first["id"]


def test_activate_workspace_rejects_missing_path(tmp_path: Path) -> None:
    from src.workspace import WorkspaceError, activate_workspace, add_workspace, remove_workspace

    project = tmp_path / "gone"
    project.mkdir()
    entry = add_workspace(str(project))
    project.rmdir()

    try:
        activate_workspace(entry["id"])
        raise AssertionError("expected WorkspaceError")
    except WorkspaceError as exc:
        assert "no longer exists" in str(exc).lower() or "不存在" in str(exc)

    remove_workspace(entry["id"])
    client = TestClient(app)
    project = tmp_path / "repo"
    project.mkdir()
    client.post("/api/workspaces", json={"path": str(project)})

    response = client.get("/api/workspace/git")
    assert response.status_code == 200
    assert response.json() == {"is_git_repo": False, "branch": None, "branches": []}


def test_get_git_info_for_local_repo() -> None:
    from src.workspace import get_git_info

    repo_root = Path(__file__).resolve().parents[3]
    info = get_git_info(repo_root)
    assert info["is_git_repo"] is True
    assert isinstance(info["branch"], str)
    assert info["branch"] in info["branches"]


def test_run_git_hides_windows_console(monkeypatch, tmp_path: Path) -> None:
    from src import workspace

    captured: dict[str, object] = {}
    flag = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, "true\n", "")

    monkeypatch.setattr(workspace.sys, "platform", "win32")
    monkeypatch.setattr(workspace.subprocess, "CREATE_NO_WINDOW", flag, raising=False)
    monkeypatch.setattr(workspace.subprocess, "run", fake_run)

    result = workspace._run_git(tmp_path, "rev-parse", "--is-inside-work-tree")

    assert result is not None
    assert captured["creationflags"] == flag


def test_workspace_git_without_workspace() -> None:
    client = TestClient(app)
    response = client.get("/api/workspace/git")
    assert response.status_code == 200
    assert response.json() == {"is_git_repo": False, "branch": None, "branches": []}


def test_stable_workspace_id_survives_remove_and_readd(tmp_path: Path) -> None:
    from src.workspace import add_workspace, remove_workspace, stable_workspace_id

    project = tmp_path / "stable-proj"
    project.mkdir()
    first = add_workspace(str(project))
    assert first["id"] == stable_workspace_id(project.resolve())
    remove_workspace(first["id"])
    second = add_workspace(str(project))
    assert second["id"] == first["id"]


def test_migrate_random_ids_remaps_run_history(tmp_path: Path, monkeypatch) -> None:
    from src import run_history, workspace

    store = tmp_path / "workspaces.json"
    project = tmp_path / "legacy-proj"
    project.mkdir()
    legacy_id = "ws_deadbeefcafe"
    store.write_text(
        json.dumps(
            {
                "workspaces": [
                    {
                        "id": legacy_id,
                        "workspace_path": str(project.resolve()),
                        "name": "legacy-proj",
                    }
                ],
                "active_id": legacy_id,
                "repository_groups": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(store))
    monkeypatch.setenv("CLUTCH_RUN_HISTORY_DIR", str(tmp_path / "sessions"))
    workspace._workspaces = {}
    workspace._repository_groups = {}
    workspace._active_id = None
    workspace._loaded = False
    workspace._persistence_disabled = False

    run_history.upsert_session(
        {
            "run_id": "run_legacy_1",
            "workspace_id": legacy_id,
            "workspace_name": "legacy-proj",
            "title": "kept",
            "mode": "coding",
            "status": "idle",
        }
    )

    listed = workspace.list_workspaces()
    expected = workspace.stable_workspace_id(project.resolve())
    assert listed["active_id"] == expected
    assert listed["workspaces"][0]["id"] == expected
    runs = run_history.list_runs(workspace_id=expected)
    assert len(runs) == 1
    assert runs[0]["workspace_id"] == expected


def test_refuse_temp_workspace_in_default_store(tmp_path: Path, monkeypatch) -> None:
    from src import workspace
    from src.workspace import WorkspaceError, add_workspace

    monkeypatch.delenv("CLUTCH_ALLOW_TEMP_WORKSPACE", raising=False)
    workspace._workspaces = {}
    workspace._repository_groups = {}
    workspace._active_id = None
    workspace._loaded = True
    workspace._persistence_disabled = False
    monkeypatch.setattr(workspace, "_using_isolated_store", lambda: False)
    monkeypatch.setattr(workspace, "_store_path", lambda: tmp_path / "default-workspaces.json")

    ephemeral = Path(tempfile.mkdtemp(prefix="tmp"))
    try:
        try:
            add_workspace(str(ephemeral))
            raise AssertionError("expected WorkspaceError for temp path")
        except WorkspaceError as exc:
            assert "temporary" in str(exc).lower() or "临时" in str(exc)
    finally:
        ephemeral.rmdir()
