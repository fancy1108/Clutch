"""Release hardening gates for frozen PyInstaller sidecar (OSR-16)."""

from __future__ import annotations

import importlib
import sys

import pytest
from fastapi.testclient import TestClient

from src.run_state_store import save_run_state
from src.state import initial_state


def _set_sys_frozen(frozen: bool) -> None:
    if frozen:
        sys.frozen = True  # type: ignore[attr-defined]
    elif hasattr(sys, "frozen"):
        delattr(sys, "frozen")


def _reload_orchestrator_modules() -> None:
    import src.main
    import src.release_hardening
    import src.sidecar_auth

    importlib.reload(src.release_hardening)
    importlib.reload(src.sidecar_auth)
    importlib.reload(src.main)


def _reload_orchestrator_app(monkeypatch: pytest.MonkeyPatch, *, frozen: bool, debug_api: bool) -> TestClient:
    _set_sys_frozen(frozen)
    if debug_api:
        monkeypatch.setenv("CLUTCH_DEBUG_API", "1")
    else:
        monkeypatch.delenv("CLUTCH_DEBUG_API", raising=False)

    _reload_orchestrator_modules()
    import src.main

    return TestClient(src.main.app)


@pytest.fixture
def restore_unfrozen_app(monkeypatch: pytest.MonkeyPatch) -> None:
    had_frozen = hasattr(sys, "frozen")
    original_frozen = getattr(sys, "frozen", False)
    yield
    if had_frozen:
        sys.frozen = original_frozen  # type: ignore[attr-defined]
    elif hasattr(sys, "frozen"):
        delattr(sys, "frozen")
    monkeypatch.delenv("CLUTCH_DEBUG_API", raising=False)
    _reload_orchestrator_modules()


def test_frozen_release_hides_debug_and_docs(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    restore_unfrozen_app: None,
) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    client = _reload_orchestrator_app(monkeypatch, frozen=True, debug_api=False)

    save_run_state(initial_state("run_frozen"))
    assert client.get("/api/runs/run_frozen/debug").status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/health").status_code == 200


def test_frozen_release_debug_opt_in(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    restore_unfrozen_app: None,
) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    client = _reload_orchestrator_app(monkeypatch, frozen=True, debug_api=True)

    run_id = "run_frozen_debug"
    save_run_state(initial_state(run_id))
    assert client.get(f"/api/runs/{run_id}/debug").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
