"""Flow integration: Claude CLI hybrid node then Clutch built-in agent node."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.agent_executor import execute_agent_task
from src.compiler.compiler import resolve_agent_task_input
from src.compiler import compile_workflow, initial_compiler_state, workflow_run_config
from src.run_state_store import load_run_state, save_run_state
from src.state import cli_session_patch, initial_state


WORKFLOW = {
    "id": "mixed-hybrid-flow",
    "name": "Mixed Hybrid Flow",
    "version": 1,
    "nodes": [
        {
            "id": "builder",
            "type": "agent_task",
            "data": {
                "label": "Builder",
                "agent": "agent-claude",
                "tool": "claude-cli",
                "instruction": "Scaffold the feature.",
            },
        },
        {
            "id": "reviewer",
            "type": "agent_task",
            "data": {
                "label": "Reviewer",
                "agent": "agent-clutch",
                "tool": "llm",
                "instruction": "Review the builder output.",
            },
        },
        {"id": "end", "type": "end", "data": {"label": "Done"}},
    ],
    "edges": [
        {"id": "e1", "source": "start", "target": "builder"},
        {"id": "e2", "source": "builder", "target": "reviewer"},
        {"id": "e3", "source": "reviewer", "target": "end"},
    ],
}


@pytest.fixture
def hybrid_flow_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> dict[str, object]:
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("CLUTCH_E2E_FAKE_HYBRID", "1")

    route_calls: list[dict[str, object]] = []
    clutch_calls: list[list[dict[str, str]]] = []
    persisted_patches: list[dict[str, object]] = []

    def fake_route_engine(**kwargs):
        route_calls.append(dict(kwargs))
        from src.engine_router import EngineResult

        return EngineResult(
            engine="Claude CLI (Hybrid)",
            output="Built files: src/feature.ts",
            logs=["[HYBRID] flow claude turn"],
            cli_session_id="sess-builder-1",
        )

    from src.llm.router import BUILTIN_MODELS

    class _CapturingRouter:
        _models = BUILTIN_MODELS
        def get_active_model(self) -> SimpleNamespace:
            return SimpleNamespace(
                id="deepseek-v4pro",
                name="Test Model",
                api_model="test-api-model",
                model_kind="chat",
            )

        @property
        def active_model_id(self) -> str:
            return "deepseek-v4pro"

        def chat(self, history: list[dict[str, str]], model_id: str | None = None) -> str:
            clutch_calls.append(history)
            return f"Review OK: {history[-1]['content'][:60]}"

    monkeypatch.setattr("src.engine_router.route_engine", fake_route_engine)
    monkeypatch.setattr(
        "src.engine_router.find_agent",
        lambda ref: {
            "agent-claude": {
                "id": "agent-claude",
                "name": "Builder",
                "agentType": "claude-cli",
            },
            "agent-clutch": {
                "id": "agent-clutch",
                "name": "Reviewer",
                "agentType": "clutch",
                "modelId": "deepseek-v4pro",
            },
        }.get(str(ref), {"id": ref, "name": ref, "agentType": "clutch"}),
    )
    monkeypatch.setattr("src.workspace.get_workspace", lambda: {"workspace_path": "/workspace/ecc"})
    monkeypatch.setattr("src.agent_mcp.resolve_agent_mcp_servers", lambda _agent: [])
    monkeypatch.setattr("src.models_config.get_router", lambda: _CapturingRouter())

    def capture_emit(run_id: str, patch: dict) -> None:
        persisted_patches.append({"run_id": run_id, **patch})
        state = load_run_state(run_id) or initial_state(run_id)
        save_run_state({**state, **{k: v for k, v in patch.items() if k != "new_messages"}})

    monkeypatch.setattr("src.workflow_runtime.emit_workflow_agent_step", capture_emit)

    save_run_state(initial_state("run-mixed-hybrid"))

    return {
        "route_calls": route_calls,
        "clutch_calls": clutch_calls,
        "persisted_patches": persisted_patches,
    }


def test_claude_node_then_clutch_node_sequential(hybrid_flow_env) -> None:
    env = hybrid_flow_env
    run_id = "run-mixed-hybrid"

    builder = execute_agent_task(
        WORKFLOW["nodes"][0]["data"],
        instruction="Scaffold the feature.",
        run_id=run_id,
        node_id="builder",
    )
    assert builder.output == "Built files: src/feature.ts"
    assert len(env["route_calls"]) == 1
    assert env["route_calls"][0]["source"] == "flow"
    assert env["route_calls"][0]["cli_session_id"] is None

    state_after_builder = load_run_state(run_id)
    assert state_after_builder is not None
    assert state_after_builder["cli_session_id"] == "sess-builder-1"
    assert state_after_builder["cli_session_agent_id"] == "agent-claude"

    compiler_state = {
        **initial_compiler_state(run_id, instruction="Ship feature"),
        "node_outputs": {"builder": builder.output},
    }
    reviewer_input = resolve_agent_task_input(compiler_state, WORKFLOW["nodes"][1], WORKFLOW)
    assert "Built files: src/feature.ts" in reviewer_input

    reviewer = execute_agent_task(
        WORKFLOW["nodes"][1]["data"],
        instruction=reviewer_input,
        run_id=run_id,
        node_id="reviewer",
    )
    assert reviewer.output.startswith("Review OK:")
    assert "Built files: src/feature.ts" in reviewer.output
    assert len(env["route_calls"]) == 1
    assert len(env["clutch_calls"]) == 1
    assert "Built files: src/feature.ts" in env["clutch_calls"][0][-1]["content"]

    state_after_reviewer = load_run_state(run_id)
    assert state_after_reviewer is not None
    assert state_after_reviewer["cli_session_id"] == "sess-builder-1"
    assert state_after_reviewer["cli_session_agent_id"] == "agent-claude"


def test_full_workflow_compile_invocation(hybrid_flow_env) -> None:
    compiled = compile_workflow(WORKFLOW)
    result = compiled.invoke(
        initial_compiler_state("run-mixed-hybrid", instruction="Ship feature"),
        workflow_run_config("run-mixed-hybrid"),
    )

    assert result["status"] == "passed"
    assert result["node_outputs"]["builder"] == "Built files: src/feature.ts"
    assert result["node_outputs"]["reviewer"].startswith("Review OK:")

    state = load_run_state("run-mixed-hybrid")
    assert state is not None
    assert state["cli_session_id"] == "sess-builder-1"
