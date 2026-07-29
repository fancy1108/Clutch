"""D18 — POST /api/runs/{run_id}/compact."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("CLUTCH_PREFERENCES_DIR", str(tmp_path / "prefs"))
    from src.main import app

    return TestClient(app)


def _seed_run(run_id: str, n_messages: int) -> None:
    from src.chat_runner import _commit_run_state, _get_or_create_run

    state = _get_or_create_run(run_id)
    msgs: list[dict[str, Any]] = []
    for i in range(n_messages):
        msgs.append(
            {
                "id": f"m{i}",
                "agent": "User" if i % 2 == 0 else "Assistant",
                "text": f"message {i} " + ("x" * 20),
                "time": "2026-01-01 00:00:00",
                "status": "COMPLETED",
            }
        )
    state["messages"] = msgs
    state["session_tokens"] = 20000
    _commit_run_state(run_id, state)


def test_compact_too_short(client: TestClient) -> None:
    _seed_run("run_d18_short", 3)
    res = client.post("/api/runs/run_d18_short/compact")
    assert res.status_code == 200
    body = res.json()
    assert body["compacted"] is False
    assert "Not enough" in (body.get("detail") or "")


def test_compact_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_compact(
        run_id: str,
        state: dict,
        model_id: str | None = None,
        *,
        record_slash_command: bool = False,
    ):
        msgs = list(state.get("messages") or [])
        out = dict(state)
        tail = list(msgs[-2:])
        if record_slash_command:
            tail.append({"id": "user_compact", "agent": "User", "text": "/compact"})
        out["messages"] = [
            msgs[0],
            *tail,
            {"id": "digest", "agent": "System", "text": "digest", "status": "COMPLETED"},
        ]
        out["session_tokens"] = 100
        return out

    monkeypatch.setattr("src.compaction.compact_run_messages", fake_compact)
    _seed_run("run_d18_ok", 8)
    res = client.post("/api/runs/run_d18_ok/compact")
    assert res.status_code == 200
    body = res.json()
    assert body["compacted"] is True
    assert body["message_count"] < 8
