"""Global plain-chat pool queue drain (cross-session)."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.plain_chat_pool_queue import pool_queue_depth, reset_for_tests
from src.shell_session import get_shell_session_manager

client = TestClient(app)

AGENT_ID = "agent-e2e-hybrid"


@pytest.fixture
def pool_queue_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    reset_for_tests()
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")
    monkeypatch.setenv("CLUTCH_E2E_FAKE_HYBRID", "1")
    monkeypatch.setenv("CLUTCH_E2E_FAKE_SHELL", "1")
    monkeypatch.setenv("CLUTCH_E2E_FAKE_HYBRID_DELAY", "0.35")
    monkeypatch.setenv("CLUTCH_SHELL_MAX_SESSIONS", "1")
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("CLUTCH_AGENTS_DIR", str(tmp_path / "agents"))
    monkeypatch.setenv("CLUTCH_RUN_HISTORY_DIR", str(tmp_path / "sessions"))
    (tmp_path / "agents").mkdir()
    (tmp_path / "storage").mkdir()
    (tmp_path / "sessions").mkdir()

    from src.agent_storage import save_agents

    save_agents(
        [
            {
                "id": AGENT_ID,
                "name": "Claude E2E Hybrid",
                "agentType": "claude-cli",
                "aiEngine": "Claude Code (Local CLI)",
                "markdownDoc": "# E2E\n",
            }
        ]
    )
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool: True)
    workspace = {"id": "ws-e2e", "name": "e2e", "workspace_path": str(tmp_path / "workspace")}
    (tmp_path / "workspace").mkdir()
    monkeypatch.setattr("src.workspace.get_workspace", lambda: workspace)
    monkeypatch.setattr("src.engine_router.get_workspace", lambda: workspace)
    monkeypatch.setattr("src.main._touch_session", lambda *_args, **_kwargs: None)
    yield
    manager = get_shell_session_manager()
    manager.release("run_pool_a")
    manager.release("run_pool_b")
    reset_for_tests()


def _run_state(run_id: str) -> dict[str, object]:
    response = client.get(f"/api/runs/{run_id}/state")
    assert response.status_code == 200
    return response.json()["state"]


def _wait_until(run_id: str, predicate, *, timeout_s: float = 20.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        state = _run_state(run_id)
        if predicate(state):
            return state
        time.sleep(0.05)
    raise TimeoutError(f"run {run_id} condition not met within {timeout_s}s")


@pytest.mark.real_route_engine
def test_pool_full_queues_second_session_then_drains(pool_queue_env: None, tmp_path) -> None:
    workspace_path = str(tmp_path / "workspace")
    manager = get_shell_session_manager()
    manager.get_or_create("run_pool_a", workspace_path=workspace_path)

    with client.websocket_connect("/ws/runs/run_pool_b") as ws:
        ws.receive_json()
        ws.send_json({"text": "queued-turn", "agent_id": AGENT_ID})

        queued_state = _wait_until(
            "run_pool_b",
            lambda state: state.get("shell_session_status") == "queued_pool"
            or any(
                "queued waiting for shell pool" in str(line)
                for line in (state.get("terminal_logs") or [])
            ),
            timeout_s=15.0,
        )
        manager.mark_idle("run_pool_a")
        idle_state = _wait_until(
            "run_pool_b",
            lambda state: state.get("status") == "idle",
            timeout_s=20.0,
        )

    log_blob = "\n".join(str(line) for line in queued_state.get("terminal_logs") or [])
    assert "queued waiting for shell pool" in log_blob or queued_state.get("shell_session_status") == "queued_pool"
    assert "rejected (pool_full)" not in log_blob
    messages = idle_state.get("messages") or []
    reply_blob = " ".join(
        str(message.get("text", ""))
        for message in messages
        if message.get("agent") not in {None, "User", "Supervisor"}
    )
    assert "queued-turn" in reply_blob
    assert pool_queue_depth() == 0
