"""RuntimeStrategy dispatch helpers (Step 4)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from src.provider_registry import ProviderSpec, resolve_provider_spec
from src.runtime_config import hybrid_eligible
from src.runtime_strategy import RuntimeStrategy

T = TypeVar("T")


def try_shell_exec_hybrid(
    *,
    agent_type: str,
    source: str,
    run_id: str | None,
    workspace_path: str | None,
    provider_spec: ProviderSpec | None,
    hybrid_route: Callable[[], T],
    legacy_route: Callable[[], T],
    logs: list[str],
    on_log: Callable[[str], None] | None,
    emit_log: Callable[[list[str], Callable[[str], None] | None, str], None],
) -> T:
    """Run SHELL_EXEC hybrid when eligible; fall back to legacy subprocess on failure."""
    spec = provider_spec or resolve_provider_spec(agent_type)
    if (
        spec.runtime_strategy == RuntimeStrategy.SHELL_EXEC
        and hybrid_eligible(source=source, agent_type=agent_type)
        and run_id
        and workspace_path
    ):
        try:
            return hybrid_route()
        except Exception as exc:
            emit_log(
                logs,
                on_log,
                f"[HYBRID] fallback to legacy compatible mode: {exc}",
            )
    return legacy_route()
