"""LLM Provider Router — D4 default DeepSeek V4 Pro, switchable per provider keys (M1-08)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Protocol

ProviderId = Literal["deepseek", "openai", "anthropic", "google", "ollama", "custom"]
ModelKind = Literal["chat", "image"]

DEFAULT_MODEL_ID = "deepseek-v4pro"
ENV_KEY_PREFIX = "CLUTCH_"


@dataclass(frozen=True)
class ModelSpec:
    id: str
    name: str
    provider_id: ProviderId
    api_model: str
    base_url: str
    model_kind: ModelKind = "chat"
    image_backend: str = ""


BUILTIN_MODELS: dict[str, ModelSpec] = {
    DEFAULT_MODEL_ID: ModelSpec(
        id="deepseek-v4pro",
        name="DeepSeek V4 Pro",
        provider_id="deepseek",
        api_model="deepseek-chat",
        base_url="https://api.deepseek.com",
    ),
    "claude-3-7-sonnet": ModelSpec(
        id="claude-3-7-sonnet",
        name="Claude 3.7 Sonnet",
        provider_id="anthropic",
        api_model="claude-3-7-sonnet-latest",
        base_url="https://api.anthropic.com/v1",
    ),
    "gpt-4o": ModelSpec(
        id="gpt-4o",
        name="GPT-4o",
        provider_id="openai",
        api_model="gpt-4o",
        base_url="https://api.openai.com/v1",
    ),
    "gemini-2.5-flash": ModelSpec(
        id="gemini-2.5-flash",
        name="Gemini 2.5 Flash",
        provider_id="google",
        api_model="gemini-2.5-flash",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    ),
    "qwen2.5vl-7b": ModelSpec(
        id="qwen2.5vl-7b",
        name="Qwen 2.5 VL 7B (Ollama)",
        provider_id="ollama",
        api_model="qwen2.5vl:7b",
        base_url="http://localhost:11434/v1",
    ),
    # Legacy id kept so existing models.json selections keep working.
    "qwen2.5-coder-7b": ModelSpec(
        id="qwen2.5-coder-7b",
        name="Qwen 2.5 VL 7B (Ollama)",
        provider_id="ollama",
        api_model="qwen2.5vl:7b",
        base_url="http://localhost:11434/v1",
    ),
    "agnes-2.0-flash": ModelSpec(
        id="agnes-2.0-flash",
        name="Agnes 2.0 Flash",
        provider_id="custom",
        api_model="agnes-2.0-flash",
        base_url="https://apihub.agnes-ai.com/v1",
    ),
    "agnes-image-2.1-flash": ModelSpec(
        id="agnes-image-2.1-flash",
        name="Agnes Image 2.1 Flash",
        provider_id="custom",
        api_model="agnes-image-2.1-flash",
        base_url="https://apihub.agnes-ai.com",
        model_kind="image",
        image_backend="agnes",
    ),
}


class CompletionFn(Protocol):
    def __call__(
        self, *, base_url: str, api_model: str, api_key: str, prompt: str
    ) -> str: ...


class ChatFn(Protocol):
    def __call__(
        self,
        *,
        provider_id: ProviderId,
        base_url: str,
        api_model: str,
        api_key: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | str: ...


def _env_key_for(provider_id: ProviderId) -> str:
    return f"{ENV_KEY_PREFIX}{provider_id.upper()}_API_KEY"


@dataclass
class LLMProviderRouter:
    """Route LLM calls to the active model's provider; keys stored per provider."""

    _models: dict[str, ModelSpec] = field(default_factory=lambda: dict(BUILTIN_MODELS))
    _api_keys: dict[ProviderId, str] = field(default_factory=dict)
    _active_model_id: str = DEFAULT_MODEL_ID
    _complete: CompletionFn | None = None
    _chat: ChatFn | None = None

    @property
    def active_model_id(self) -> str:
        return self._active_model_id

    def register_model(self, spec: ModelSpec) -> None:
        self._models[spec.id] = spec

    def list_models(self) -> list[ModelSpec]:
        return list(self._models.values())

    def set_active_model(self, model_id: str) -> None:
        if model_id not in self._models:
            raise KeyError(f"Unknown model: {model_id}")
        self._active_model_id = model_id

    def get_active_model(self) -> ModelSpec:
        return self._models[self._active_model_id]

    def set_api_key(self, provider_id: ProviderId, api_key: str) -> None:
        self._api_keys[provider_id] = api_key

    def get_api_key(self, provider_id: ProviderId) -> str | None:
        if provider_id in self._api_keys:
            return self._api_keys[provider_id]
        return os.environ.get(_env_key_for(provider_id))

    def resolve_for_model(self, model_id: str | None = None) -> tuple[ModelSpec, str | None]:
        spec = self._models[model_id or self._active_model_id]
        return spec, self.get_api_key(spec.provider_id)

    def _require_api_key(self, provider_id: ProviderId, api_key: str | None) -> str:
        if api_key:
            return api_key
        if provider_id == "ollama":
            return ""
        raise RuntimeError(f"No API key configured for provider {provider_id!r}")

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model_id: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | str:
        spec, api_key = self.resolve_for_model(model_id)
        key = self._require_api_key(spec.provider_id, api_key)
        if self._chat is None:
            raise RuntimeError("No chat backend configured")
        return self._chat(
            provider_id=spec.provider_id,
            base_url=spec.base_url,
            api_model=spec.api_model,
            api_key=key,
            messages=messages,
            tools=tools,
        )

    def complete(self, prompt: str, *, model_id: str | None = None) -> str:
        if self._chat is not None:
            return self.chat([{"role": "user", "content": prompt}], model_id=model_id)
        spec, api_key = self.resolve_for_model(model_id)
        key = self._require_api_key(spec.provider_id, api_key)
        if self._complete is None:
            raise RuntimeError("No completion backend configured")
        return self._complete(
            base_url=spec.base_url, api_model=spec.api_model, api_key=key, prompt=prompt
        )

    def as_route_suggester(self) -> Callable[[dict[str, Any], str, dict[str, Any]], str]:
        """Adapter for orchestrator routing LLM fallback (M1-04)."""

        def suggest(workflow: dict[str, Any], source: str, state: dict[str, Any]) -> str:
            edges = [edge for edge in workflow["edges"] if edge["source"] == source]
            options = [
                edge["data"]["when"]
                for edge in edges
                if edge.get("data", {}).get("when")
            ]
            if not options:
                return "passed"
            prompt = (
                f"Routing decision for workflow node {source!r}. "
                f"State keys: {sorted(state.keys())}. "
                f"Pick one branch: {options}. Reply with only the branch key."
            )
            choice = self.complete(prompt).strip().strip('"')
            return choice if choice in options else options[0]

        return suggest
