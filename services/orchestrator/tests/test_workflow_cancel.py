"""Workflow cooperative cancellation (stop during in-flight LangGraph + hybrid shell)."""

import pytest

from src.compiler.compiler import _handle_agent_task
from src.workflow_cancel import WorkflowCancelled, clear_workflow_cancel, is_workflow_cancelled, request_workflow_cancel
from src.workflow_runtime import (
    clear_workflow_step_callback,
    emit_workflow_agent_step,
    register_workflow_step_callback,
)


def test_workflow_cancel_flag_lifecycle() -> None:
    clear_workflow_cancel("run_flag")
    assert not is_workflow_cancelled("run_flag")
    request_workflow_cancel("run_flag")
    assert is_workflow_cancelled("run_flag")
    clear_workflow_cancel("run_flag")
    assert not is_workflow_cancelled("run_flag")


def test_handle_agent_task_raises_when_cancelled() -> None:
    request_workflow_cancel("run_cancel")
    state = {"run_id": "run_cancel", "task_logs": [], "task_messages": [], "node_outputs": {}}
    node = {"id": "n1", "data": {"agent": "Builder", "tool": "clutch"}}
    workflow = {"id": "wf", "nodes": [node], "edges": []}
    try:
        with pytest.raises(WorkflowCancelled):
            _handle_agent_task(state, node, workflow)
    finally:
        clear_workflow_cancel("run_cancel")


def test_emit_workflow_agent_step_skips_when_cancelled() -> None:
    calls: list[dict] = []
    register_workflow_step_callback("run_emit", calls.append)
    try:
        request_workflow_cancel("run_emit")
        emit_workflow_agent_step("run_emit", {"new_messages": [{"id": "m1"}]})
        assert calls == []
    finally:
        clear_workflow_cancel("run_emit")
        clear_workflow_step_callback("run_emit")


def test_stop_workflow_requests_cancel_and_releases_shell(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from src.main import _commit_run_state, _get_or_create_run, app

    cancelled: list[str] = []
    released: list[str] = []
    monkeypatch.setattr(
        "src.workflow_cancel.request_workflow_cancel",
        lambda run_id: cancelled.append(run_id),
    )
    monkeypatch.setattr(
        "src.main._interrupt_plain_chat_shell",
        lambda run_id: released.append(run_id),
    )

    run_id = "run_stop_workflow"
    _commit_run_state(
        run_id,
        {
            **_get_or_create_run(run_id),
            "workflow_id": "video-production",
            "status": "running",
        },
    )

    client = TestClient(app)
    response = client.post(f"/api/runs/{run_id}/stop")
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert cancelled == [run_id]
    assert released == [run_id]
