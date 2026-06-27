"""D29 regression: concurrent rejection failure modes in audit JSONL + debug API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from src.hybrid_audit_log import (
    append_hybrid_rejection_audit,
    get_hybrid_audit_dir,
    read_hybrid_audit_lines,
)
from src.hybrid_concurrency import shell_session_status_for_rejection
from src.main import _apply_hybrid_plain_chat_rejection, _handle_plain_chat, app
from src.hybrid_concurrency import HybridPlainChatRejected
from src.run_state_store import save_run_state
from src.state import initial_state

client = TestClient(app)

REJECTION_CODES = ("run_in_progress", "session_busy", "pool_full")


@pytest.mark.parametrize("code", REJECTION_CODES)
@pytest.mark.asyncio
async def test_rejection_codes_write_audit_status_and_terminal_log(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    code: str,
) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")

    websocket = MagicMock()
    websocket.send_text = AsyncMock()

    run_id = f"run_d29_{code}"
    state = initial_state(run_id)
    state["status"] = "running"

    result = await _apply_hybrid_plain_chat_rejection(
        websocket,
        run_id,
        state,
        code=code,
        keep_running=code == "run_in_progress",
    )

    assert result["shell_session_status"] == shell_session_status_for_rejection(code)
    assert any("[HYBRID] rejected" in log and code in log for log in result["terminal_logs"])
    assert result["messages"][-1]["agent"] == "Supervisor"

    audit = read_hybrid_audit_lines(run_id=run_id, audit_dir=get_hybrid_audit_dir())
    assert len(audit) == 1
    assert audit[0]["result"] == "rejected"
    assert audit[0]["source"] == "orchestrator"
    assert audit[0]["level"] == "warn"
    assert code in audit[0]["message"]


@pytest.mark.parametrize("code", REJECTION_CODES)
def test_debug_api_surfaces_rejection_audit(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    code: str,
) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    run_id = f"run_debug_d29_{code}"
    save_run_state(initial_state(run_id))

    append_hybrid_rejection_audit(
        run_id=run_id,
        reason=code,
        message=f"Hybrid rejection test for {code}",
    )

    response = client.get(f"/api/runs/{run_id}/debug?audit_limit=10")
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id
    assert len(body["hybrid_audit"]) == 1
    assert body["hybrid_audit"][0]["result"] == "rejected"
    assert code in body["hybrid_audit"][0]["message"]


@pytest.mark.asyncio
async def test_handle_plain_chat_session_busy_audited(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")
    monkeypatch.setattr("src.run_state_store.save_run_state", lambda _state: None)
    monkeypatch.setattr("src.main._touch_session", lambda *_args, **_kwargs: None)

    agent_record = {
        "id": "agent-claude-test",
        "name": "Claude test Session",
        "agentType": "claude-cli",
    }
    monkeypatch.setattr("src.agent_storage.get_agent_by_id", lambda _agent_id: agent_record)

    async def raise_busy(*_args, **_kwargs):
        raise HybridPlainChatRejected(
            "session_busy",
            "This chat is still running a Hybrid shell turn.",
        )

    monkeypatch.setattr("src.main._llm_chat_reply", raise_busy)

    websocket = MagicMock()
    websocket.send_text = AsyncMock()

    run_id = "run_session_busy_d29"
    state = initial_state(run_id)

    result = await _handle_plain_chat(
        websocket,
        run_id,
        state,
        "hello while busy",
        agent_id="agent-claude-test",
    )

    assert result["status"] == "running"
    assert result["shell_session_status"] == "rejected_session_busy"
    audit = read_hybrid_audit_lines(run_id=run_id, audit_dir=get_hybrid_audit_dir())
    assert audit[-1]["result"] == "rejected"
    assert "session_busy" in audit[-1]["message"]
