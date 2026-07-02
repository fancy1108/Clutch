"""Run history persistence tests — M2-07."""

from __future__ import annotations

import pytest

from src import run_history


@pytest.fixture(autouse=True)
def isolated_history_dir(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_RUN_HISTORY_DIR", str(tmp_path))


def _persist_session_state(
    run_id: str,
    *,
    messages: list[dict[str, str]] | None = None,
    dispatch_log: list[dict[str, str]] | None = None,
) -> None:
    from src.run_state_store import save_run_state
    from src.state import initial_state

    state = initial_state(run_id, "")
    if messages is not None:
        state["messages"] = messages
    if dispatch_log is not None:
        state["dispatch_log"] = dispatch_log
    save_run_state(state)


def test_append_and_list_run_records() -> None:
    _persist_session_state("run_abc123", messages=[{"id": "m1", "text": "hello"}])
    run_history.append_run_record(
        {
            "run_id": "run_abc123",
            "workspace_id": "ws_test",
            "title": "Video production",
            "workflow_id": "video-production",
            "status": "passed",
            "started_at": "2026-06-23T10:00:00+00:00",
        }
    )

    records = run_history.list_runs()
    assert len(records) == 1
    assert records[0]["run_id"] == "run_abc123"
    assert records[0]["workspace_id"] == "ws_test"


def test_update_run_record_status() -> None:
    _persist_session_state("run_update_me", messages=[{"id": "m1", "text": "hello"}])
    run_history.append_run_record(
        {
            "run_id": "run_update_me",
            "workspace_id": "ws_test",
            "title": "Retry flow",
            "workflow_id": "video-production",
            "status": "running",
            "started_at": "2026-06-23T10:00:00+00:00",
        }
    )

    updated = run_history.update_run_record("run_update_me", {"status": "failed"})
    assert updated is not None
    assert updated["status"] == "failed"
    assert run_history.list_runs()[0]["status"] == "failed"


def test_list_runs_filters_by_workspace() -> None:
    _persist_session_state("run_a", messages=[{"id": "m1", "text": "ecc"}])
    _persist_session_state("run_b", messages=[{"id": "m2", "text": "other"}])
    run_history.upsert_session(
        {
            "run_id": "run_a",
            "workspace_id": "ws_ecc",
            "title": "ECC chat",
            "workflow_id": "",
            "status": "idle",
            "started_at": "2026-06-23T10:00:00+00:00",
        }
    )
    run_history.upsert_session(
        {
            "run_id": "run_b",
            "workspace_id": "ws_other",
            "title": "Other",
            "workflow_id": "",
            "status": "idle",
            "started_at": "2026-06-23T10:00:00+00:00",
        }
    )

    ecc_runs = run_history.list_runs(workspace_id="ws_ecc")
    assert len(ecc_runs) == 1
    assert ecc_runs[0]["run_id"] == "run_a"


def test_list_runs_prunes_empty_sessions() -> None:
    run_history.upsert_session(
        {
            "run_id": "run_empty",
            "workspace_id": "ws_ecc",
            "title": "New session",
            "workflow_id": "",
            "status": "idle",
            "started_at": "2026-06-23T10:00:00+00:00",
        }
    )
    _persist_session_state("run_with_chat", messages=[{"id": "m1", "text": "hello"}])
    run_history.upsert_session(
        {
            "run_id": "run_with_chat",
            "workspace_id": "ws_ecc",
            "title": "Real chat",
            "workflow_id": "",
            "status": "idle",
            "started_at": "2026-06-23T10:00:00+00:00",
        }
    )

    records = run_history.list_runs()
    assert [record["run_id"] for record in records] == ["run_with_chat"]


def test_create_session_api_requires_workspace(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from src.main import app
    from src import workspace

    monkeypatch.setenv("CLUTCH_RUN_HISTORY_DIR", str(tmp_path))
    workspace.clear_workspace_for_tests()
    client = TestClient(app)

    denied = client.post("/api/sessions", json={"run_id": "run_new", "title": "Hello"})
    assert denied.status_code == 400

    project = tmp_path / "ecc"
    project.mkdir()
    workspace.add_workspace(str(project))

    created = client.post("/api/sessions", json={"run_id": "run_new", "title": "Hello"})
    assert created.status_code == 200
    body = created.json()
    assert body["workspace_id"]
    assert body["title"] == "Hello"
    assert run_history.list_runs() == []


def test_history_api_returns_records() -> None:
    from fastapi.testclient import TestClient

    from src.main import app

    _persist_session_state("run_api", messages=[{"id": "m1", "text": "hello"}])
    run_history.append_run_record(
        {
            "run_id": "run_api",
            "workspace_id": "ws_api",
            "title": "API session",
            "workflow_id": "video-production",
            "status": "passed",
            "started_at": "2026-06-23T11:00:00+00:00",
        }
    )

    response = TestClient(app).get("/api/runs/history")
    assert response.status_code == 200
    body = response.json()
    assert body["runs"][0]["run_id"] == "run_api"


def test_delete_session_api(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient
    from src.main import app
    from src import run_history

    monkeypatch.setenv("CLUTCH_RUN_HISTORY_DIR", str(tmp_path))
    client = TestClient(app)

    _persist_session_state("run_delete_api", messages=[{"id": "m1", "text": "hello"}])
    run_history.append_run_record(
        {
            "run_id": "run_delete_api",
            "workspace_id": "ws_api",
            "title": "API session to delete",
            "workflow_id": "video-production",
            "status": "passed",
            "started_at": "2026-06-23T11:00:00+00:00",
        }
    )

    assert len(run_history.list_runs()) == 1

    response = client.delete("/api/runs/run_delete_api")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    assert len(run_history.list_runs()) == 0


def test_delete_session_releases_shell_session(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient
    from src.main import app
    from src.shell_session import get_shell_session_manager

    manager = get_shell_session_manager()
    released: list[str] = []

    def fake_release(run_id: str) -> None:
        released.append(run_id)

    monkeypatch.setattr(manager, "release", fake_release)
    client = TestClient(app)

    response = client.delete("/api/runs/run_shell_release")
    assert response.status_code == 200
    assert released == ["run_shell_release"]
