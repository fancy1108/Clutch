"""E2E fake hybrid + concurrent plain-chat WebSocket integration."""

from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

AGENT_ID = "agent-e2e-hybrid"


@pytest.fixture
def hybrid_e2e_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")
    monkeypatch.setenv("CLUTCH_E2E_FAKE_HYBRID", "1")
    monkeypatch.setenv("CLUTCH_E2E_FAKE_SHELL", "1")
    monkeypatch.setenv("CLUTCH_E2E_FAKE_HYBRID_DELAY", "0.1")
    monkeypatch.setenv("CLUTCH_SHELL_MAX_SESSIONS", "8")
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


def _chat_until_idle(run_id: str, text: str) -> dict[str, object]:
    logs: list[str] = []
    reply = ""
    with client.websocket_connect(f"/ws/runs/{run_id}") as ws:
        ws.receive_json()
        ws.send_json({"text": text, "agent_id": AGENT_ID})
        while True:
            event = ws.receive_json()
            if event.get("event") == "log":
                logs.append(str(event.get("data", {}).get("message", "")))
            if event.get("event") == "message":
                message = event.get("data", {}).get("message", {})
                if message.get("agent") not in {None, "User", "Supervisor"}:
                    reply = str(message.get("text", ""))
            if (
                event.get("event") == "state_patch"
                and event.get("data", {}).get("patch", {}).get("status") == "idle"
            ):
                break
    return {"logs": logs, "reply": reply}


@pytest.mark.real_route_engine
def test_concurrent_hybrid_plain_chat_ws(hybrid_e2e_env: None) -> None:
    results: dict[str, dict[str, object]] = {}
    errors: list[BaseException] = []

    def worker(run_id: str, text: str) -> None:
        try:
            results[run_id] = _chat_until_idle(run_id, text)
        except BaseException as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=worker, args=("run_conc_a", "这是对话1")),
        threading.Thread(target=worker, args=("run_conc_b", "这是对话2")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30.0)
        assert not thread.is_alive()

    assert not errors
    log_a = "\n".join(str(line) for line in results["run_conc_a"]["logs"])
    log_b = "\n".join(str(line) for line in results["run_conc_b"]["logs"])
    assert "[HYBRID] acquiring shell" in log_a
    assert "[HYBRID] shell ready" in log_a
    assert "[HYBRID] acquiring shell" in log_b
    assert "[HYBRID] shell ready" in log_b
    assert "pool_full" not in log_a
    assert "pool_full" not in log_b
    assert "这是对话1" in str(results["run_conc_a"]["reply"])
    assert "这是对话2" in str(results["run_conc_b"]["reply"])
