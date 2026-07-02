"""WebSocket interactive PTY attach/detach events."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.interactive_pty_runtime import InteractivePtySession, InteractivePtyStatus
from src.main import app

client = TestClient(app)


def test_ws_pty_attach_blocked_without_workspace() -> None:
    with patch("src.workspace.get_workspace", return_value=None):
        with client.websocket_connect("/ws/runs/run_pty_blocked") as ws:
            ws.receive_json()  # initial state_patch
            ws.send_json({"action": "pty_attach", "cli_tool": "claude-cli"})
            status = ws.receive_json()
    assert status["event"] == "pty_session_status"
    assert status["data"]["status"] == "blocked"


def test_ws_pty_attach_and_detach(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = InteractivePtySession(
        run_id="run_pty_ok",
        workspace_path="/tmp",
        cli_tool="claude-cli",
        binary="/usr/bin/claude",
        status=InteractivePtyStatus.READY,
    )

    with patch("src.workspace.get_workspace", return_value={"workspace_path": "/tmp"}):
        with patch(
            "src.interactive_pty_runtime.interactive_pty_manager.attach",
            return_value=fake_session,
        ):
            with client.websocket_connect("/ws/runs/run_pty_ok") as ws:
                ws.receive_json()
                ws.send_json({"action": "pty_attach", "cli_tool": "claude-cli"})
                attach_status = ws.receive_json()
                ws.send_json({"action": "pty_detach"})
                detach_status = ws.receive_json()

    assert attach_status["event"] == "pty_session_status"
    assert attach_status["data"]["status"] == "ready"
    assert detach_status["event"] == "pty_session_status"
    assert detach_status["data"]["status"] == "detached"
