#!/usr/bin/env python3
"""One-shot WS verification for hybrid execution details (no live Claude required)."""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch

ORCH_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ORCH_ROOT not in sys.path:
    sys.path.insert(0, ORCH_ROOT)

os.environ["CLUTCH_RUNTIME_MODE"] = "hybrid"

from fastapi.testclient import TestClient  # noqa: E402

from src.engine_router import EngineResult  # noqa: E402
from src.main import app  # noqa: E402

client = TestClient(app)

AGENT = {
    "id": "agent-claude-test",
    "name": "Claude test Session",
    "agentType": "claude-cli",
    "aiEngine": "Claude Code (Local CLI)",
    "markdownDoc": "## Protocol\n- Task validation",
}
WORKSPACE = {
    "id": "ws_hybrid_verify",
    "name": "penpot",
    "workspace_path": "/tmp/clutch-hybrid-verify",
}


def fake_hybrid(**_kwargs: object) -> EngineResult:
    return EngineResult(
        engine="Claude CLI (Hybrid)",
        output="天蝎女很深情。",
        logs=["[HYBRID] ok"],
        cli_session_id="sess-verify-1",
        raw_output="CLUTCH_P='hi'; claude -p ...",
        output_events=[
            {"type": "shell_echo", "visible": False, "content": 'claude -p "$CLUTCH_P"'},
            {"type": "system_prompt", "visible": False, "content": "You are Claude test Session"},
            {"type": "boundary_marker", "visible": False, "content": "__CLUTCH_DONE_x__"},
            {"type": "assistant", "visible": True, "content": "天蝎女很深情。"},
        ],
    )


def main() -> int:
    patches = [
        patch("src.engine_router.list_agents", return_value=[AGENT]),
        patch("src.agent_storage.get_agent_by_id", return_value=AGENT),
        patch("src.engine_router.tool_available_for_routing", return_value=True),
        patch("src.workspace.get_workspace", return_value=WORKSPACE),
        patch("src.engine_router.get_workspace", return_value=WORKSPACE),
        patch("src.run_state_store.save_run_state"),
        patch("src.engine_router._route_claude_hybrid", side_effect=fake_hybrid),
        patch("src.engine_router.route_engine", side_effect=fake_hybrid),
    ]
    for item in patches:
        item.start()
    try:
        events: list[dict] = []
        with client.websocket_connect("/ws/runs/run_hybrid_verify") as ws:
            ws.receive_json()
            ws.send_json({"text": "天蝎女怎么样", "agent_id": "agent-claude-test"})
            while True:
                event = ws.receive_json()
                events.append(event)
                if (
                    event.get("event") == "state_patch"
                    and event.get("data", {}).get("patch", {}).get("status") == "idle"
                ):
                    break

        hybrid_events = [e for e in events if e.get("event") == "hybrid_execution"]
        idle_patch = next(
            e["data"]["patch"]
            for e in events
            if e.get("event") == "state_patch"
            and e.get("data", {}).get("patch", {}).get("status") == "idle"
        )
        reply = next(
            e["data"]["message"]
            for e in events
            if e.get("event") == "message" and e["data"]["message"]["agent"] == "Claude test Session"
        )
        agent_messages = [
            m for m in idle_patch["messages"] if m.get("agent") == "Claude test Session"
        ]
        message_id = str(agent_messages[-1]["id"])
        hybrid_map = idle_patch.get("hybrid_executions") or {}
        entry = hybrid_map.get(message_id) or {}

        detail_log = next(
            (
                log
                for log in idle_patch.get("terminal_logs", [])
                if "[HYBRID] execution_details" in str(log)
            ),
            None,
        )

        checks = {
            "hybrid_execution_event": len(hybrid_events) == 1,
            "reply_outputEvents": bool(reply.get("outputEvents")),
            "reply_rawOutput": bool(reply.get("rawOutput")),
            "state_hybrid_executions": bool(hybrid_map),
            "state_entry_events": len(entry.get("outputEvents") or []) >= 3,
            "terminal_detail_log": detail_log is not None,
        }

        print("=== Hybrid execution WS verification ===")
        print(
            json.dumps(
                {
                    "checks": checks,
                    "message_id": message_id,
                    "outputEvents_count": len(entry.get("outputEvents") or []),
                    "raw_bytes": len(str(entry.get("rawOutput") or "")),
                    "terminal_detail_log": detail_log,
                    "hidden_event_types": [
                        e.get("type")
                        for e in (entry.get("outputEvents") or [])
                        if not e.get("visible")
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        failed = [name for name, ok in checks.items() if not ok]
        if failed:
            print(f"FAILED: {', '.join(failed)}", file=sys.stderr)
            return 1
        print("PASSED")
        return 0
    finally:
        for item in reversed(patches):
            item.stop()


if __name__ == "__main__":
    raise SystemExit(main())
