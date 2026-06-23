"""M1-08 — LLM Provider Router tests."""

from __future__ import annotations

from src.llm import DEFAULT_MODEL_ID, LLMProviderRouter, ModelSpec
from src.orchestrator.routing import route_next


def test_default_model_is_deepseek_v4pro() -> None:
    router = LLMProviderRouter()
    assert router.active_model_id == DEFAULT_MODEL_ID
    model = router.get_active_model()
    assert model.name == "DeepSeek V4 Pro"
    assert model.provider_id == "deepseek"


def test_switch_active_model() -> None:
    router = LLMProviderRouter()
    router.set_active_model("claude-3-7-sonnet")
    assert router.get_active_model().provider_id == "anthropic"


def test_api_keys_stored_per_provider() -> None:
    router = LLMProviderRouter()
    router.set_api_key("deepseek", "sk-ds")
    router.set_api_key("anthropic", "sk-ant")
    assert router.get_api_key("deepseek") == "sk-ds"
    assert router.get_api_key("anthropic") == "sk-ant"
    assert router.get_api_key("openai") is None


def test_env_fallback_api_key(monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_DEEPSEEK_API_KEY", "from-env")
    router = LLMProviderRouter()
    assert router.get_api_key("deepseek") == "from-env"


def test_complete_uses_active_provider() -> None:
    calls: list[dict[str, str]] = []

    def fake_complete(**kwargs: str) -> str:
        calls.append(kwargs)
        return "ok"

    router = LLMProviderRouter()
    router.set_api_key("deepseek", "key-ds")
    router._complete = fake_complete  # type: ignore[method-assign]

    assert router.complete("hello") == "ok"
    assert calls[0]["api_model"] == "deepseek-chat"
    assert calls[0]["api_key"] == "key-ds"
    assert calls[0]["base_url"] == "https://api.deepseek.com/v1"


def test_complete_after_model_switch() -> None:
    calls: list[str] = []

    def fake_complete(**kwargs: str) -> str:
        calls.append(kwargs["api_model"])
        return "ok"

    router = LLMProviderRouter()
    router.set_api_key("anthropic", "key-ant")
    router._complete = fake_complete  # type: ignore[method-assign]
    router.set_active_model("claude-3-7-sonnet")

    router.complete("route me")
    assert calls[-1] == "claude-3-7-sonnet-latest"


def test_route_suggester_integrates_with_orchestrator() -> None:
    workflow = {
        "nodes": [{"id": "n1", "type": "check"}],
        "edges": [
            {"source": "n1", "target": "n2", "data": {"when": "passed"}},
            {"source": "n1", "target": "n3", "data": {"when": "failed"}},
        ],
    }
    state = {"check_result": "unknown_branch"}

    router = LLMProviderRouter()
    router.set_api_key("deepseek", "key-ds")
    router._complete = lambda **_kw: "failed"  # type: ignore[method-assign]

    target, method = route_next(
        workflow, "n1", state, llm_suggest=router.as_route_suggester()
    )
    assert method == "llm"
    assert target == "failed"
