"""Hybrid concurrency rejection handlers (HRT-08)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.hybrid_audit_log import read_hybrid_audit_lines, get_hybrid_audit_dir
from src.main import _apply_hybrid_plain_chat_rejection, _handle_plain_chat
from src.hybrid_concurrency import HybridPlainChatRejected
from src.state import initial_state


@pytest.mark.asyncio
async def test_apply_hybrid_rejection_keeps_running_and_audits(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")

    websocket = MagicMock()
    websocket.send_text = AsyncMock()

    state = initial_state("run_reject_keep")
    state["status"] = "running"

    result = await _apply_hybrid_plain_chat_rejection(
        websocket,
        "run_reject_keep",
        state,
        code="run_in_progress",
        keep_running=True,
    )

    assert result["status"] == "running"
    assert result["shell_session_status"] == "rejected_run_in_progress"
    assert result["messages"][-1]["agent"] == "Supervisor"
    audit = read_hybrid_audit_lines(run_id="run_reject_keep", audit_dir=get_hybrid_audit_dir())
    assert audit[-1]["result"] == "rejected"


@pytest.mark.asyncio
async def test_apply_hybrid_rejection_pool_full_returns_idle(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")

    websocket = MagicMock()
    websocket.send_text = AsyncMock()

    state = initial_state("run_reject_idle")
    state["status"] = "running"
    state["messages"] = [
        {"id": "u1", "agent": "User", "avatar": "", "time": "12:00", "text": "hello"},
    ]

    result = await _apply_hybrid_plain_chat_rejection(
        websocket,
        "run_reject_idle",
        state,
        code="pool_full",
        keep_running=False,
    )

    assert result["status"] == "idle"
    assert result["shell_session_status"] == "rejected_pool_full"


@pytest.mark.asyncio
async def test_handle_plain_chat_rejects_duplicate_hybrid_send(
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

    llm_called = {"ok": False}

    async def fail_llm(*_args, **_kwargs):
        llm_called["ok"] = True
        raise AssertionError("llm should not run when run_in_progress")

    monkeypatch.setattr("src.main._llm_chat_reply", fail_llm)

    websocket = MagicMock()
    websocket.send_text = AsyncMock()

    state = initial_state("run_dup_guard")
    state["status"] = "running"

    result = await _handle_plain_chat(
        websocket,
        "run_dup_guard",
        state,
        "second",
        agent_id="agent-claude-test",
    )

    assert llm_called["ok"] is False
    assert result["status"] == "running"
    assert result["shell_session_status"] == "rejected_run_in_progress"


@pytest.mark.asyncio
async def test_handle_plain_chat_catches_hybrid_pool_full(
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

    async def raise_pool_full(*_args, **_kwargs):
        raise HybridPlainChatRejected(
            "pool_full",
            "All Hybrid shell sessions are busy.",
        )

    monkeypatch.setattr("src.main._llm_chat_reply", raise_pool_full)

    websocket = MagicMock()
    websocket.send_text = AsyncMock()

    state = initial_state("run_pool_guard")

    result = await _handle_plain_chat(
        websocket,
        "run_pool_guard",
        state,
        "hello",
        agent_id="agent-claude-test",
    )

    assert result["status"] == "idle"
    assert result["shell_session_status"] == "rejected_pool_full"
    assert any(message.get("agent") == "Supervisor" for message in result["messages"])
