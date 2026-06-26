"""Linear Flow handoff between agent_task nodes."""

from __future__ import annotations

from src.compiler import compile_workflow, initial_compiler_state, workflow_run_config


def test_linear_flow_passes_first_agent_output_to_second(monkeypatch) -> None:
    workflow = {
        "id": "handoff-test",
        "name": "Handoff Test",
        "version": 1,
        "nodes": [
            {
                "id": "researcher",
                "type": "agent_task",
                "data": {
                    "label": "Researcher",
                    "agent": "Researcher",
                    "tool": "llm",
                    "instruction": "Describe the scene for an illustrator.",
                },
            },
            {
                "id": "artist",
                "type": "agent_task",
                "data": {
                    "label": "Artist",
                    "agent": "Artist",
                    "tool": "llm",
                    "instruction": "Generate an image from the description.",
                },
            },
            {"id": "end", "type": "end", "data": {"label": "Done"}},
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "researcher"},
            {"id": "e2", "source": "researcher", "target": "artist"},
            {"id": "e3", "source": "artist", "target": "end"},
        ],
    }

    seen_instructions: list[str] = []

    def fake_execute(node_data, *, instruction="", run_id="", node_id=""):
        from src.agent_executor import AgentTaskResult
        from src.chat_events import chat_message

        seen_instructions.append(instruction)
        agent = str(node_data.get("agent", "Agent"))
        if agent == "Researcher":
            output = "A white cat with an umbrella at West Lake in Hangzhou at dusk."
        else:
            output = f"image:{instruction[:40]}"
        return AgentTaskResult(
            agent=agent,
            output=output,
            logs=[],
            message=chat_message(agent, output),
        )

    monkeypatch.setattr("src.compiler.compiler.execute_agent_task", fake_execute)
    monkeypatch.setattr("src.compiler.compiler.emit_workflow_agent_step", lambda *_args, **_kwargs: None)

    compiled = compile_workflow(workflow)
    result = compiled.invoke(
        initial_compiler_state("run_handoff", instruction="画西湖的猫"),
        workflow_run_config("run_handoff"),
    )

    assert result["status"] == "passed"
    assert result["node_outputs"]["researcher"].startswith("A white cat")
    assert "A white cat with an umbrella" in seen_instructions[1]
    assert "画西湖的猫" in seen_instructions[0]
