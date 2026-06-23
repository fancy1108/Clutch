"""Start workflow on an existing session run_id."""

from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.main import _run_states, app

client = TestClient(app)


class _FakeRouter:
    def get_active_model(self) -> SimpleNamespace:
        return SimpleNamespace(name="Test Model")

    def chat(self, history: list[dict[str, str]]) -> str:
        return "builder output"


def test_start_workflow_on_existing_run_id(monkeypatch) -> None:
    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeRouter())
    run_id = "run_session_start"

    response = client.post(
        f"/api/runs/{run_id}/start",
        json={"workflow_id": "video-production", "instruction": "ship it"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id
    assert body["status"] in {"passed", "awaiting_human"}
    assert body["state"]["workflow_id"] == "video-production"
    assert any(msg["agent"] == "User" for msg in body["state"]["messages"])
    assert any(msg["agent"] == "Builder" for msg in body["state"]["messages"])

    state = _run_states[run_id]
    assert state["workflow_id"] == "video-production"
    assert state["current_instruction"] == "ship it"
