"""Incremental workflow step state patches (M3-F07)."""

from __future__ import annotations

from src.chat_events import chat_message
from src.main import _apply_workflow_step_patch, _run_states, initial_state


def test_apply_workflow_step_patch_appends_and_dedupes() -> None:
    run_id = "run_step_patch"
    _run_states[run_id] = initial_state(run_id)
    first = chat_message("The Researcher", "Scene description.", msg_id="step_msg_1")

    _apply_workflow_step_patch(
        run_id,
        {
            "new_messages": [first],
            "active_node_id": "researcher",
            "active_agent": "The Researcher",
            "status": "running",
        },
    )
    assert len(_run_states[run_id]["messages"]) == 1
    assert _run_states[run_id]["active_agent"] == "The Researcher"

    duplicate = chat_message("The Researcher", "Scene description.", msg_id="step_msg_1")
    second = chat_message("The Artist", "![img](https://example.com/x.png)", msg_id="step_msg_2")
    _apply_workflow_step_patch(
        run_id,
        {
            "new_messages": [duplicate, second],
            "active_node_id": "artist",
            "active_agent": "The Artist",
            "status": "running",
        },
    )

    ids = [str(item.get("id", "")) for item in _run_states[run_id]["messages"]]
    assert ids == ["step_msg_1", "step_msg_2"]
    assert _run_states[run_id]["active_node_id"] == "artist"
    _run_states.pop(run_id, None)
