"""Repro: previous assistant reply must survive the next turn's state_patch.

Bug: in Chat mode, after Q1 answered fine, sending Q2 made the FIRST answer
disappear from the feed. Suspect: a state_patch whose messages list is missing
the sealed assistant reply (shorter list, all ids known) triggers the
frontend's authoritative-replacement path and wipes the bubble.
"""

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
            id="test-model",
            name="Test Model",
            api_model="test-api-model",
            model_kind="chat",
        )

    @property
    def active_model_id(self) -> str:
        return "test-model"

    def chat(self, history: list[dict[str, str]]) -> str:
        last = history[-1]["content"]
        if isinstance(last, list):
            last = " ".join(str(part.get("text", "")) for part in last if isinstance(part, dict))
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


def _message_ids(events: list[dict]) -> set[str]:
    ids: set[str] = set()
    for event in events:
        if event.get("event") == "message":
            ids.add(event["data"]["message"]["id"])
    return ids


def test_second_turn_patches_keep_first_assistant_reply(monkeypatch) -> None:
    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeRouter())
    run_id = "run_turn_repro"

    with client.websocket_connect(f"/ws/runs/{run_id}") as ws:
        ws.receive_json()  # initial state_patch

        # Turn 1
        ws.send_json({"text": "question one", "client_message_id": "user_q1"})
        turn1_events = _collect_until_idle(ws)
        turn1_ids = _message_ids(turn1_events)
        assistant1 = next(
            e["data"]["message"]
            for e in turn1_events
            if e["event"] == "message" and e["data"]["message"]["agent"] != "User"
        )
        assert assistant1["text"] == "Echo: question one"
        assert "user_q1" in turn1_ids

        # Turn 2
        ws.send_json({"text": "question two", "client_message_id": "user_q2"})
        turn2_events = _collect_until_idle(ws)

    # No state_patch in turn 2 may project a messages list that DROPS the
    # first assistant reply while it is still part of the session.
    for event in turn2_events:
        if event.get("event") != "state_patch":
            continue
        patch = event["data"].get("patch", {})
        messages = patch.get("messages")
        if messages is None:
            continue
        ids = {m["id"] for m in messages}
        assert assistant1["id"] in ids, (
            f"state_patch dropped first assistant reply; patch messages={ids}"
        )
        assert "user_q1" in ids
