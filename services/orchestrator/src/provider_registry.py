"""Provider registry: agent_type -> RuntimeStrategy (Step 4)."""

from __future__ import annotations

from dataclasses import dataclass

from src.runtime_strategy import RuntimeStrategy


@dataclass(frozen=True)
class ProviderSpec:
    agent_type: str
    runtime_strategy: RuntimeStrategy
    exec_template: str | None = None


_REGISTRY: dict[str, ProviderSpec] = {
    "clutch": ProviderSpec("clutch", RuntimeStrategy.SDK_NATIVE),
    "claude-cli": ProviderSpec(
        "claude-cli",
        RuntimeStrategy.SHELL_EXEC,
        exec_template='claude -p "{prompt}"',
    ),
    "antigravity-cli": ProviderSpec(
        "antigravity-cli",
        RuntimeStrategy.SHELL_EXEC,
        exec_template='agy -p "{prompt}"',
    ),
    "ollama-cli": ProviderSpec("ollama-cli", RuntimeStrategy.HTTP_DAEMON),
}


def resolve_provider_spec(agent_type: str) -> ProviderSpec:
    key = agent_type.strip().lower()
    if key in _REGISTRY:
        return _REGISTRY[key]
    return ProviderSpec(key, RuntimeStrategy.SHELL_EXEC)
