"""Integration test for visual-narrative-automation workflow shape."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.compiler import compile_workflow, initial_compiler_state, workflow_run_config
from src.engine_router import EngineResult


WORKFLOW_PATH = (
    Path.home()
    / "Library/Application Support/clutch_dev/workflows/visual-narrative-automation.json"
)


@pytest.fixture
def visual_narrative_workflow() -> dict:
    if not WORKFLOW_PATH.is_file():
        pytest.skip("visual-narrative-automation workflow not installed locally")
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def visual_narrative_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> dict[str, list[dict[str, object]]]:
    monkeypatch.setenv("CLUTCH_RUNTIME_MODE", "hybrid")
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))

    agents = {
        "agent-1782646023679": {
            "id": "agent-1782646023679",
            "name": "1-Concept Architect",
            "agentType": "antigravity-cli",
            "markdownDoc": 'Return JSON: {"world_background":"x","protagonist_design":"y","core_conflict":"z"}',
        },
        "agent-1782646075477": {
            "id": "agent-1782646075477",
            "name": "2-Scriptwriter",
            "agentType": "claude-cli",
            "markdownDoc": 'Return JSON: {"climax_script":"scene"}',
        },
        "agent-1782646111028": {
            "id": "agent-1782646111028",
            "name": "3-Storyboard Director",
            "agentType": "codex-cli",
            "markdownDoc": 'Return JSON: {"main_subject":"hero","environment_and_lighting":"night","camera_language":"wide"}',
        },
        "agent-1782646148750": {
            "id": "agent-1782646148750",
            "name": "4-Prompt Engineer",
            "agentType": "ollama-cli",
            "ollamaModel": "qwen3.6:35b",
            "markdownDoc": 'Return JSON: {"final_image_prompt":"dragon boat festival, cinematic"}',
        },
        "agent-1782646188905": {
            "id": "agent-1782646188905",
            "name": "5-Visual Rendering Engine",
            "agentType": "clutch",
            "modelId": "agnes-image-2.1-flash",
            "markdownDoc": "Render the final_image_prompt.",
        },
    }

    route_calls: list[dict[str, object]] = []

    outputs_by_agent = {
        "agent-1782646023679": '{"world_background":"mystic river","protagonist_design":"young paddler","core_conflict":"race against tide"}',
        "agent-1782646075477": '{"climax_script":"The dragon boats surge through mist as zongzi steam rises."}',
        "agent-1782646111028": '{"main_subject":"hero paddling","environment_and_lighting":"night lanterns","camera_language":"wide"}',
    }

    def fake_route_engine(**kwargs):
        route_calls.append(dict(kwargs))
        agent_name = str(kwargs.get("agent_name", ""))
        agent = agents.get(agent_name)
        if agent and agent.get("agentType") == "ollama-cli":
            return EngineResult(
                engine="Ollama (qwen3.6:35b)",
                output='{"final_image_prompt":"dragon boat festival, cinematic"}',
                logs=[],
            )
        if agent and agent.get("agentType") == "clutch":
            raise AssertionError("image node should use generate_image_for_model path")
        engine = "Antigravity CLI (Hybrid)" if agent_name == "agent-1782646023679" else "CLI (Hybrid)"
        return EngineResult(
            engine=engine,
            output=outputs_by_agent.get(agent_name, "ok"),
            logs=["[HYBRID] ok"],
            cli_session_id=f"sess-{agent_name}",
        )

    monkeypatch.setattr("src.engine_router.route_engine", fake_route_engine)
    monkeypatch.setattr("src.engine_router.find_agent", lambda ref: agents.get(str(ref)))
    monkeypatch.setattr("src.workspace.get_workspace", lambda: {"workspace_path": str(tmp_path / "penpot")})
    (tmp_path / "penpot").mkdir()

    from src.llm.router import BUILTIN_MODELS

    class _ImageRouter:
        _models = BUILTIN_MODELS

        def get_active_model(self):
            return BUILTIN_MODELS["agnes-image-2.1-flash"]

        @property
        def active_model_id(self) -> str:
            return "agnes-image-2.1-flash"

        def resolve_for_model(self, model_id: str | None = None):
            return BUILTIN_MODELS["agnes-image-2.1-flash"], "sk-test"

        def _require_api_key(self, _provider_id: str, api_key: str | None) -> str:
            return api_key or "sk-test"

    monkeypatch.setattr("src.models_config.get_router", lambda: _ImageRouter())

    def fake_generate_image(spec, prompt, **kwargs):
        assert "dragon boat" in prompt.lower() or "festival" in prompt.lower()
        return {"url": "https://example.com/frame.png"}

    monkeypatch.setattr("src.image_router.generate_image_for_model", fake_generate_image)

    from src.run_state_store import save_run_state
    from src.state import initial_state

    save_run_state(initial_state("run-visual-narrative"))

    return {"route_calls": route_calls}


def test_visual_narrative_workflow_runs_end_to_end(
    visual_narrative_workflow,
    visual_narrative_env,
) -> None:
    compiled = compile_workflow(visual_narrative_workflow)
    user_prompt = (
        "3D动画电影风格的端午节奇幻冒险，包含包粽子、赛龙舟和佩戴香囊的传统元素。"
    )
    result = compiled.invoke(
        initial_compiler_state("run-visual-narrative", instruction=user_prompt),
        workflow_run_config("run-visual-narrative"),
    )

    assert result["status"] == "passed"
    outputs = result["node_outputs"]
    assert len(outputs) == 5
    assert "world_background" in outputs["step-1782647878227"]
    assert "climax_script" in outputs["step-1782647888698"]
    assert "main_subject" in outputs["step-1782647901402"]
    assert "final_image_prompt" in outputs["step-1782647908169"]
    assert "example.com/frame.png" in outputs["step-1782647915010"]

    first_call = visual_narrative_env["route_calls"][0]
    assert first_call["source"] == "flow"
    assert user_prompt in str(first_call["prompt"])
    assert "world_background" in str(first_call["system_prompt"])
