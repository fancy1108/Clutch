"""Workflow graph → ClutchState projection (M3-F03)."""

from __future__ import annotations

from src.chat_events import chat_message
from src.compiler.compiler import CompilerState
from src.state import initial_state
from src.workflow_projection import project_graph_to_clutch


def test_project_graph_dedupes_incremental_messages() -> None:
    researcher_msg = chat_message("The Researcher", "Shanghai is sunny.", msg_id="msg_researcher")
    artist_msg = chat_message("The Artist", "![img](https://example.com/a.png)", msg_id="msg_artist")
    state = initial_state("run_proj")
    state["messages"] = [
        chat_message("User", "上海天气"),
        researcher_msg,
    ]
    graph_result = CompilerState(
        run_id="run_proj",
        active_node_id="artist",
        active_agent="The Artist",
        status="passed",
        check_result="",
        human_decision="",
        current_instruction="上海天气",
        node_outputs={"researcher": "Shanghai is sunny.", "artist": "![img](https://example.com/a.png)"},
        task_logs=[],
        task_messages=[researcher_msg, artist_msg],
    )
    workflow = {"id": "weather-to-vision", "name": "Weather to Vision"}

    patch = project_graph_to_clutch(
        state,
        graph_result,
        workflow=workflow,
        instruction="上海天气",
        include_logs=False,
    )

    ids = [str(item.get("id", "")) for item in patch["messages"]]
    assert ids.count("msg_researcher") == 1
    assert ids.count("msg_artist") == 1
    assert patch["active_agent"] == "The Artist"
    assert patch["workflow_id"] == "weather-to-vision"
