"""Repro: reconnect between turns must not drop the first assistant reply."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _force_llm_plain_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: False)


class _FakeRouter:
    def get_active_model(self) -> SimpleNamespace:
        return SimpleNamespace(
            id="test-model", name="Test Model",
            api_model="test-api-model", model_kind="chat",
        )

    @property
    def active_model_id(self) -> str:
        return "test-model"

    def chat(self, history):
        last = history[-1]["content"]
        if isinstance(last, list):
            last = " ".join(str(p.get("text", "")) for p in last if isinstance(p, dict))
        return f"Echo: {last}"


def _collect_until_idle(ws) -> list[dict]:
    events: list[dict] = []
    while True:
        event = ws.receive_json()
        events.append(event)
        if (
            event.get("event") == "state_patch"
            and event.get("data", {}).get("patch", {}).get("status") == "idle"
        ):
            break
    return events


def test_reconnect_then_second_turn_keeps_first_reply(monkeypatch) -> None:
    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeRouter())
    run_id = "run_reconnect_repro"

    with client.websocket_connect(f"/ws/runs/{run_id}") as ws1:
        ws1.receive_json()
        ws1.send_json({"text": "question one", "client_message_id": "user_q1"})
        turn1 = _collect_until_idle(ws1)
        assistant1 = next(
            e["data"]["message"]
            for e in turn1
            if e["event"] == "message" and e["data"]["message"]["agent"] != "User"
        )

    # reconnect (simulates sidecar WS drop / page reload)
    with client.websocket_connect(f"/ws/runs/{run_id}") as ws2:
        init = ws2.receive_json()  # full state patch on connect
        init_msgs = init["data"]["patch"].get("messages", [])
        print("\nINIT PATCH message ids:", [m["id"] for m in init_msgs])
        assert assistant1["id"] in {m["id"] for m in init_msgs}, "reconnect full-state lost assistant1"

        ws2.send_json({"text": "question two", "client_message_id": "user_q2"})
        turn2 = _collect_until_idle(ws2)

    for event in turn2:
        if event.get("event") != "state_patch":
            continue
        messages = event["data"].get("patch", {}).get("messages")
        if messages is None:
            continue
        ids = {m["id"] for m in messages}
        assert assistant1["id"] in ids, f"turn2 patch dropped assistant1: {ids}"
