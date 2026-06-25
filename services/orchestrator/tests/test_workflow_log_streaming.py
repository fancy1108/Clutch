"""Workflow execution streams terminal logs via run log forwarder."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.main import _run_states, app
from src.run_log_forwarder import clear_forwarder

client = TestClient(app)


class _FakeRouter:
    def get_active_model(self) -> SimpleNamespace:
        return SimpleNamespace(name="Test Model")

    def chat(self, history: list[dict[str, str]]) -> str:
        return "builder streamed output"


@pytest.fixture(autouse=True)
def _clear_forwarders() -> None:
    clear_forwarder("run_wf_stream")


def test_workflow_start_streams_orchestrator_and_builder_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeRouter())

    response = client.post(
        "/api/runs/run_wf_stream/start",
        json={"workflow_id": "video-production", "instruction": "stream logs"},
    )
    assert response.status_code == 200

    logs = _run_states["run_wf_stream"]["terminal_logs"]
    assert any("Starting workflow" in line for line in logs)
    assert any("Workflow graph entered" in line for line in logs)
    assert any("Starting:" in line for line in logs)
    assert any("Active node" in line for line in logs)
    assert logs == response.json()["state"]["terminal_logs"]
