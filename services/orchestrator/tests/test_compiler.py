"""WorkflowCompiler tests — M1-02."""

from __future__ import annotations

from src.compiler import WorkflowCompiler, compile_workflow, initial_compiler_state, workflow_run_config
from src.compiler.compiler import NODE_HANDLERS
from src.workflow_validator import load_and_validate_workflow

VIDEO_PRODUCTION = load_and_validate_workflow("video-production")


def test_all_five_node_type_handlers_registered() -> None:
    assert set(NODE_HANDLERS) == {"start", "agent_task", "check", "human_gate", "end"}


def test_compiled_node_types_match_workflow_json() -> None:
    compiler = WorkflowCompiler()
    compiler.compile(VIDEO_PRODUCTION)

    json_types = {node["id"]: node["type"] for node in VIDEO_PRODUCTION["nodes"]}
    compiled_types = {meta.id: meta.type for meta in compiler.node_metas}

    assert compiled_types["start"] == "start"
    for node_id, node_type in json_types.items():
        assert compiled_types[node_id] == node_type


def test_compiled_node_count_includes_virtual_start() -> None:
    compiler = WorkflowCompiler()
    compiler.compile(VIDEO_PRODUCTION)

    json_node_count = len(VIDEO_PRODUCTION["nodes"])
    assert len(compiler.node_metas) == json_node_count + 1
    assert {meta.id for meta in compiler.node_metas} == {"start", "n1", "n2", "n3", "end"}


def test_compiled_edges_match_workflow_json() -> None:
    compiler = WorkflowCompiler()
    compiler.compile(VIDEO_PRODUCTION)

    assert len(compiler.edge_metas) == len(VIDEO_PRODUCTION["edges"])

    for edge in VIDEO_PRODUCTION["edges"]:
        when = edge.get("data", {}).get("when")
        match = next(
            (
                compiled
                for compiled in compiler.edge_metas
                if compiled.id == edge["id"]
                and compiled.source == edge["source"]
                and compiled.target == edge["target"]
                and compiled.when == when
            ),
            None,
        )
        assert match is not None, f"missing edge {edge['id']}"


def test_invoke_happy_path_reaches_end_node() -> None:
    compiled = compile_workflow(VIDEO_PRODUCTION)
    run_id = "run_compiler_happy"
    result = compiled.invoke(initial_compiler_state(run_id), workflow_run_config(run_id))

    assert result["active_node_id"] == "end"
    assert result["status"] == "passed"
    assert result["active_agent"] == "Orchestrator"


def test_invoke_failed_check_pauses_at_human_gate() -> None:
    compiled = compile_workflow(VIDEO_PRODUCTION)
    run_id = "run_compiler_failed"
    state = initial_compiler_state(run_id)
    state["check_result"] = "failed"

    result = compiled.invoke(state, workflow_run_config(run_id))

    assert result["active_node_id"] == "n2"
    assert result["check_result"] == "failed"
    assert compiled.get_state(workflow_run_config(run_id)).next == ("n3",)
