"""D36 — headless Clutch Agent runner (CI / CLI, same core as Chat)."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from src.preferences_storage import tr

logger = logging.getLogger(__name__)


@dataclass
class HeadlessRunResult:
    exit_code: int
    output: str
    run_id: str
    logs: list[str]


class _NullWebSocket:
    async def send_json(self, payload: dict[str, Any]) -> None:
        return None


async def run_headless_agent(
    *,
    prompt: str,
    workspace_path: str = "",
    agent_id: str = "",
) -> HeadlessRunResult:
    from src.chat_runner import _get_or_create_run, _handle_plain_chat, _merge_patch
    from src.state import initial_state
    from src.workspace import WorkspaceError, add_workspace, get_workspace, set_workspace

    stripped = prompt.strip()
    if not stripped:
        return HeadlessRunResult(exit_code=2, output="prompt required", run_id="", logs=[])

    prior = get_workspace()
    restored = False
    if workspace_path.strip():
        try:
            set_workspace(workspace_path.strip())
            restored = True
        except WorkspaceError:
            add_workspace(workspace_path.strip())
            restored = True
    elif get_workspace() is None:
        return HeadlessRunResult(
            exit_code=2,
            output=tr("workspace_path required when no active workspace", "无活动工作区时必须提供 workspace_path"),
            run_id="",
            logs=[],
        )

    run_id = f"headless_{uuid.uuid4().hex[:12]}"
    state = initial_state(run_id)
    state = _merge_patch(state, {"status": "idle"})
    _get_or_create_run(run_id)  # register

    ws = _NullWebSocket()
    try:
        final = await _handle_plain_chat(
            ws,
            run_id,
            state,
            stripped,
            agent_id=agent_id or None,
            user_persisted=True,
        )
        messages = list(final.get("messages") or [])
        reply = ""
        for item in reversed(messages):
            if str(item.get("agent", "")) not in {"User", "Supervisor"}:
                reply = str(item.get("text", "")).strip()
                break
        status = str(final.get("status") or "idle")
        exit_code = 0 if status in {"idle", "passed"} else 1
        logs = [str(line) for line in final.get("terminal_logs") or []]
        return HeadlessRunResult(exit_code=exit_code, output=reply, run_id=run_id, logs=logs)
    except Exception as exc:
        logger.exception("headless agent failed run_id=%s", run_id)
        return HeadlessRunResult(exit_code=1, output=str(exc), run_id=run_id, logs=[str(exc)])
    finally:
        if restored and prior and prior.get("workspace_path"):
            try:
                set_workspace(prior["workspace_path"])
            except Exception:
                pass


def run_headless_agent_sync(
    *,
    prompt: str,
    workspace_path: str = "",
    agent_id: str = "",
) -> HeadlessRunResult:
    return asyncio.run(
        run_headless_agent(prompt=prompt, workspace_path=workspace_path, agent_id=agent_id)
    )
