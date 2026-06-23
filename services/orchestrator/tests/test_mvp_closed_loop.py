"""MVP closed-loop API test — proposal §10.1 (T-03 backend)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.main import _run_states, app

client = TestClient(app)


def test_mvp_closed_loop_check_fail_human_approve(tmp_path: Path) -> None:
    """模板运行 → 检查失败 → 人工审批 → 通过。"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    ws = client.post("/api/workspace", json={"path": str(workspace)})
    assert ws.status_code == 200

    start = client.post("/api/runs/start", json={"workflow_id": "video-production"})
    assert start.status_code == 200
    body = start.json()
    assert body["status"] == "awaiting_human"
    run_id = body["run_id"]

    state = _run_states[run_id]
    assert state["active_node_id"] == "n3"
    assert state["active_agent"] == "Supervisor"

    approve = client.post(
        f"/api/runs/{run_id}/human-decision",
        json={"decision": "approve"},
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "passed"
    assert _run_states[run_id]["status"] == "passed"
