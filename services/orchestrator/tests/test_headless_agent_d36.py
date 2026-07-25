"""D36 — headless Clutch Agent."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_agent_run_api_requires_prompt() -> None:
    from src.main import app

    paths = {getattr(route, "path", "") for route in app.routes}
    if "/api/agent/run" not in paths:
        import pytest

        pytest.skip("D36 agent run route not registered")
    client = TestClient(app)
    res = client.post("/api/agent/run", json={"prompt": "   "})
    assert res.status_code == 200
    body = res.json()
    assert body["exit_code"] == 2


@pytest.mark.asyncio
async def test_headless_missing_workspace(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("CLUTCH_WORKSPACES_FILE", str(tmp_path / "ws.json"))
    from src import workspace as workspace_mod

    workspace_mod._loaded = False
    workspace_mod._workspaces = {}
    workspace_mod._active_id = None

    from src.headless_agent import run_headless_agent

    result = await run_headless_agent(prompt="hi", workspace_path="")
    assert result.exit_code == 2
