"""Hybrid concurrency rejection handlers (HRT-08)."""

from __future__ import annotations

import threading
import time

import pytest
from fastapi import WebSocketDisconnect
from unittest.mock import AsyncMock, MagicMock

from src.hybrid_audit_log import read_hybrid_audit_lines, get_hybrid_audit_dir
from src.main import _apply_hybrid_plain_chat_rejection, _handle_plain_chat
from src.hybrid_concurrency import HybridPlainChatRejected, plain_chat_turn_in_progress
from src.shell_session import ShellSessionError
from src.state import initial_state
from src.workspace_cli_lock import workspace_cli_turn


def test_plain_chat_turn_in_progress_when_task_active() -> None:
    state = initial_state("run-queue")
    state["status"] = "idle"
    assert plain_chat_turn_in_progress(
        plain_chat_task_done=False,
        state=state,
        hybrid_runtime=True,
    )


def test_plain_chat_turn_in_progress_when_hybrid_running() -> None:
    state = initial_state("run-queue")
    state["status"] = "running"
    assert plain_chat_turn_in_progress(
        plain_chat_task_done=True,
        state=state,
        hybrid_runtime=True,
    )


def test_plain_chat_turn_not_in_progress_when_idle() -> None:
    state = initial_state("run-queue")
    state["status"] = "idle"
    assert not plain_chat_turn_in_progress(
        plain_chat_task_done=True,
        state=state,
        hybrid_runtime=True,
    )


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
async def test_handle_plain_chat_noop_when_already_running(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """While a turn is active, duplicate WS calls noop; queue layer sends next turn."""
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
        raise AssertionError("llm should not run when status already running")

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
    assert "rejected_run_in_progress" not in str(result.get("shell_session_status", ""))


@pytest.mark.asyncio
async def test_handle_plain_chat_session_busy_keeps_running(
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
            "Shell session is busy.",
        )

    monkeypatch.setattr("src.main._llm_chat_reply", raise_busy)

    websocket = MagicMock()
    websocket.send_text = AsyncMock()

    state = initial_state("run_busy_guard")
    state["messages"] = [
        {"id": "u1", "agent": "User", "avatar": "", "time": "12:00", "text": "first"},
    ]

    result = await _handle_plain_chat(
        websocket,
        "run_busy_guard",
        state,
        "second",
        agent_id="agent-claude-test",
    )

    assert result["status"] == "running"
    assert result["shell_session_status"] == "rejected_session_busy"
    assert any(message.get("agent") == "User" and message.get("text") == "second" for message in result["messages"])
    assert any(message.get("agent") == "Supervisor" for message in result["messages"])


@pytest.mark.asyncio
async def test_handle_plain_chat_queues_hybrid_pool_full(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.plain_chat_pool_queue import pool_queue_depth, reset_for_tests

    reset_for_tests()
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

    drain = AsyncMock()
    monkeypatch.setattr("src.main._llm_chat_reply", raise_pool_full)
    monkeypatch.setattr("src.plain_chat_pool_queue.schedule_pool_drain", drain)

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

    assert result["status"] == "running"
    assert result["shell_session_status"] == "queued_pool"
    assert result.get("shell_pool_queue_position") == 1
    assert result.get("shell_pool_queue_depth") == 1
    assert isinstance(result.get("shell_pool_blocker_run_ids"), list)
    assert pool_queue_depth() == 1
    assert not any(message.get("agent") == "Supervisor" for message in result["messages"])
    drain.assert_awaited_once()
    reset_for_tests()


def test_history_for_llm_excludes_supervisor_rejection() -> None:
    from src.main import _history_for_llm

    history = _history_for_llm(
        [
            {
                "agent": "Supervisor",
                "text": "All Hybrid shell sessions are busy. Wait for another chat to finish or try again shortly.",
            },
            {"agent": "User", "text": "你好"},
        ]
    )

    assert history == [{"role": "user", "content": "你好"}]


@pytest.mark.asyncio
async def test_handle_plain_chat_commits_idle_before_ws_disconnect(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")

    saved: dict[str, object] = {}

    def capture_save(state) -> None:
        saved["state"] = dict(state)

    monkeypatch.setattr("src.run_state_store.save_run_state", capture_save)
    monkeypatch.setattr("src.main._touch_session", lambda *_args, **_kwargs: None)

    agent_record = {
        "id": "agent-claude-test",
        "name": "Claude test Session",
        "agentType": "claude-cli",
    }
    monkeypatch.setattr("src.agent_storage.get_agent_by_id", lambda _agent_id: agent_record)

    async def fake_llm(*_args, **_kwargs):
        return (
            "Claude test Session",
            "Claude CLI (Hybrid)",
            "assistant reply",
            [],
            "cli-session-1",
            None,
            [],
            None,
            None,
            False,
        )

    monkeypatch.setattr("src.main._llm_chat_reply", fake_llm)

    websocket = MagicMock()
    llm_done = {"ok": False}

    async def flaky_send_text(payload: str) -> None:
        if llm_done["ok"]:
            raise WebSocketDisconnect()
        if '"event": "message"' in payload and '"agent": "User"' in payload:
            return
        if '"event": "state_patch"' in payload and '"status": "running"' in payload:
            return

    async def send_text_after_llm(payload: str) -> None:
        if not llm_done["ok"]:
            await flaky_send_text(payload)
            return
        raise WebSocketDisconnect()

    original_llm = fake_llm

    async def llm_then_flag(*args, **kwargs):
        result = await original_llm(*args, **kwargs)
        llm_done["ok"] = True
        return result

    monkeypatch.setattr("src.main._llm_chat_reply", llm_then_flag)
    websocket.send_text = AsyncMock(side_effect=send_text_after_llm)

    state = initial_state("run_ws_disconnect")
    state["messages"] = []

    result = await _handle_plain_chat(
        websocket,
        "run_ws_disconnect",
        state,
        "hello",
        agent_id="agent-claude-test",
    )

    assert result["status"] == "idle"
    persisted = saved.get("state")
    assert persisted is not None
    assert persisted["status"] == "idle"
    assert any(
        message.get("agent") == "Claude test Session"
        and message.get("text") == "assistant reply"
        for message in persisted["messages"]
    )


def test_workspace_cli_lock_serializes() -> None:
    workspace = "/tmp/clutch-lock-test"
    order: list[str] = []
    gate = threading.Event()

    def worker_a() -> None:
        with workspace_cli_turn(workspace, timeout_s=2.0):
            order.append("a-start")
            gate.set()
            time.sleep(0.2)
            order.append("a-end")

    def worker_b() -> None:
        gate.wait(timeout=2.0)
        time.sleep(0.05)
        with workspace_cli_turn(workspace, timeout_s=2.0):
            order.append("b-start")
            order.append("b-end")

    t1 = threading.Thread(target=worker_a)
    t2 = threading.Thread(target=worker_b)
    t1.start()
    t2.start()
    t1.join(timeout=5.0)
    t2.join(timeout=5.0)

    assert not t1.is_alive() and not t2.is_alive()
    assert order == ["a-start", "a-end", "b-start", "b-end"]


def test_workspace_cli_lock_timeout_raises() -> None:
    workspace = "/tmp/clutch-lock-timeout-test"
    with workspace_cli_turn(workspace, timeout_s=5.0):
        with pytest.raises(ShellSessionError, match="workspace CLI lock timeout"):
            with workspace_cli_turn(workspace, timeout_s=0.05):
                pass
