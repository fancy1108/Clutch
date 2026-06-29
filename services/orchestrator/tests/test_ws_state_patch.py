from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["api_version"] == "2"


def test_ws_state_patch_on_connect() -> None:
    with client.websocket_connect("/ws/runs/run_m0_test") as ws:
        envelope = ws.receive_json()
        assert envelope["event"] == "state_patch"
        assert envelope["data"]["run_id"] == "run_m0_test"
        patch = envelope["data"]["patch"]
        assert patch["status"] == "idle"
        assert patch["active_node_id"] == ""
        assert patch["terminal_logs"] == []


def test_ws_state_patch_on_message(monkeypatch) -> None:
    monkeypatch.setattr("src.engine_router.tool_available_for_routing", lambda _tool_id: False)
    monkeypatch.setattr(
        "src.models_config.get_router",
        lambda: type(
            "_R",
            (),
            {
                "get_active_model": lambda self: type(
                    "M",
                    (),
                    {"id": "test-model", "name": "Test Model", "model_kind": "chat"},
                )(),
                "chat": lambda self, history: "pong",
            },
        )(),
    )

    with client.websocket_connect("/ws/runs/run_m0_ping") as ws:
        ws.receive_json()  # initial state_patch
        ws.send_json({"text": "Hello sidecar!"})
        events: list[dict] = []
        while True:
            event = ws.receive_json()
            events.append(event)
            if (
                event.get("event") == "state_patch"
                and event.get("data", {}).get("patch", {}).get("status") == "idle"
            ):
                break
        patch_events = [e for e in events if e["event"] == "state_patch"]
        assert len(patch_events) == 2
        
        patch1 = patch_events[0]["data"]["patch"]
        assert patch1["status"] == "running"
        assert any("Hello sidecar!" in m["text"] for m in patch1["messages"])
        
        patch2 = patch_events[1]["data"]["patch"]
        assert patch2["status"] == "idle"
        assert patch2.get("active_node_id", "") == ""


def test_ws_clear_workflow(monkeypatch) -> None:
    from src.main import _get_or_create_run, _commit_run_state
    run_id = "run_clear_wf_test"
    state = _get_or_create_run(run_id)
    state["workflow_id"] = "test-workflow-id"
    _commit_run_state(run_id, state)

    with client.websocket_connect(f"/ws/runs/{run_id}") as ws:
        envelope = ws.receive_json()
        assert envelope["event"] == "state_patch"
        assert envelope["data"]["patch"]["workflow_id"] == "test-workflow-id"

        ws.send_json({"action": "clear_workflow"})
        
        event = ws.receive_json()
        assert event["event"] == "state_patch"
        assert event["data"]["patch"]["workflow_id"] == ""
        
        # Verify it was persisted
        updated_state = _get_or_create_run(run_id)
        assert updated_state["workflow_id"] == ""
