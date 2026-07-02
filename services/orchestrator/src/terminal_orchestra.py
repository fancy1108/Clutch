"""Terminal Orchestra state + dispatch (D34)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from src.dispatch_parse import DispatchPreview, parse_dispatch_mentions
from src.handoff_writer import parse_handoff_meta_from_name, write_handoff_markdown

MAX_PTY_LANES = 4
WORKSPACE_SOURCE = "工作区"

CLI_TO_DISPLAY: dict[str, str] = {
    "claude-cli": "Claude Code",
    "opencode-cli": "OpenCode",
}
DISPLAY_TO_CLI: dict[str, str] = {v: k for k, v in CLI_TO_DISPLAY.items()}


def pty_session_key(run_id: str, lane_id: str) -> str:
    return f"{run_id}::{lane_id}"


def parse_pty_session_key(session_key: str) -> tuple[str, str]:
    if "::" in session_key:
        parent, lane_id = session_key.split("::", 1)
        return parent, lane_id
    return session_key, "primary"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M")


def _lane_list(state: dict[str, Any]) -> list[dict[str, Any]]:
    lanes = state.get("pty_lanes")
    return list(lanes) if isinstance(lanes, list) else []


def _dispatch_log(state: dict[str, Any]) -> list[dict[str, Any]]:
    log = state.get("dispatch_log")
    return list(log) if isinstance(log, list) else []


def _dispatch_edges(state: dict[str, Any]) -> list[dict[str, Any]]:
    edges = state.get("dispatch_edges")
    return list(edges) if isinstance(edges, list) else []


def _drafts(state: dict[str, Any]) -> list[dict[str, Any]]:
    drafts = state.get("pending_handoff_drafts")
    return list(drafts) if isinstance(drafts, list) else []


def focused_lane(state: dict[str, Any]) -> dict[str, Any] | None:
    lanes = _lane_list(state)
    focus_id = state.get("focused_lane_id")
    if focus_id:
        for lane in lanes:
            if lane.get("lane_id") == focus_id:
                return lane
    for lane in lanes:
        if lane.get("focused"):
            return lane
    return lanes[0] if lanes else None


def focused_agent_name(state: dict[str, Any]) -> str | None:
    lane = focused_lane(state)
    if not lane:
        return None
    agent_type = str(lane.get("agent_type", ""))
    return CLI_TO_DISPLAY.get(agent_type) or agent_type


def ensure_primary_lane(state: dict[str, Any], *, cli_tool: str, label: str = "主任务") -> dict[str, Any]:
    lanes = _lane_list(state)
    if lanes:
        return {}
    lane_id = "lane_primary"
    lane = {
        "lane_id": lane_id,
        "agent_type": cli_tool,
        "label": label,
        "status": "running",
        "focused": True,
        "collapsed": False,
        "run_id": state.get("run_id", ""),
    }
    return {"pty_lanes": [lane], "focused_lane_id": lane_id}


def file_meta_resolver(file_name: str) -> dict[str, Any]:
    return parse_handoff_meta_from_name(file_name)


def preview_dispatch(state: dict[str, Any], text: str) -> DispatchPreview | None:
    return parse_dispatch_mentions(
        text,
        focused_agent=focused_agent_name(state),
        file_meta_resolver=file_meta_resolver,
    )


def _agent_type_for_target(target: str) -> str:
    return DISPLAY_TO_CLI.get(target, "claude-cli")


def _find_lane_for_agent(lanes: list[dict[str, Any]], target: str) -> dict[str, Any] | None:
    cli = _agent_type_for_target(target)
    for lane in lanes:
        if lane.get("agent_type") == cli and lane.get("status") != "completed":
            return lane
    return None


def _source_lane_ids(lanes: list[dict[str, Any]], sources: list[str]) -> list[str]:
    ids: list[str] = []
    for src in sources:
        if src == WORKSPACE_SOURCE:
            continue
        cli = _agent_type_for_target(src)
        for lane in lanes:
            if lane.get("agent_type") == cli and lane.get("lane_id") not in ids:
                ids.append(str(lane.get("lane_id")))
                break
    return ids


def confirm_dispatch(
    state: dict[str, Any],
    *,
    preview: DispatchPreview,
    prompt: str,
    workspace_path: str,
    active_chips: list[str] | None = None,
) -> dict[str, Any]:
    sources = list(active_chips if active_chips is not None else preview.sources)
    if not sources:
        sources = [WORKSPACE_SOURCE]

    rel_path, file_name = write_handoff_markdown(
        workspace_path,
        sources=sources,
        target=preview.target,
        task=preview.task,
        prompt=prompt,
        file_refs=preview.file_refs,
    )

    lanes = _lane_list(state)
    expanded = [l for l in lanes if not l.get("collapsed")]
    if len(expanded) >= MAX_PTY_LANES and not _find_lane_for_agent(lanes, preview.target):
        queued_lane = {
            "lane_id": f"lane_q_{uuid.uuid4().hex[:8]}",
            "agent_type": _agent_type_for_target(preview.target),
            "label": preview.task[:40] or preview.target,
            "status": "queued",
            "focused": False,
            "collapsed": True,
            "run_id": state.get("run_id", ""),
        }
        lanes.append(queued_lane)
    else:
        existing = _find_lane_for_agent(lanes, preview.target)
        if existing:
            existing["status"] = "booting"
            existing["label"] = preview.task[:40] or existing.get("label", preview.target)
            existing["focused"] = True
            for lane in lanes:
                lane["focused"] = lane.get("lane_id") == existing.get("lane_id")
        else:
            lane_id = f"lane_{uuid.uuid4().hex[:8]}"
            lanes.append(
                {
                    "lane_id": lane_id,
                    "agent_type": _agent_type_for_target(preview.target),
                    "label": preview.task[:40] or preview.target,
                    "status": "booting",
                    "focused": True,
                    "collapsed": False,
                    "run_id": state.get("run_id", ""),
                }
            )
            for lane in lanes:
                lane["focused"] = lane.get("lane_id") == lane_id

    target_lane = focused_lane({"pty_lanes": lanes}) or {}
    target_lane_id = str(target_lane.get("lane_id", ""))
    source_lane_ids = _source_lane_ids(lanes, sources)

    sources_label = " + ".join(sources) if sources else WORKSPACE_SOURCE
    entry = {
        "id": f"dispatch_{uuid.uuid4().hex[:12]}",
        "time": _iso_now(),
        "sources_label": sources_label,
        "target": preview.target,
        "prompt": prompt,
        "handoff_file": file_name,
        "handoff_path": rel_path,
        "input_mode": preview.input_mode,
        "file_refs": preview.file_refs,
    }
    edge = {
        "sources": sources,
        "target": preview.target,
        "handoff_file": file_name,
        "source_lane_ids": source_lane_ids,
        "target_lane_id": target_lane_id,
    }

    log = _dispatch_log(state)
    log.append(entry)
    edges = _dispatch_edges(state)
    edges.append(edge)

    return {
        "pty_lanes": lanes,
        "focused_lane_id": target_lane_id,
        "dispatch_log": log,
        "dispatch_edges": edges,
    }


def patch_lane_focus(state: dict[str, Any], lane_id: str) -> dict[str, Any]:
    lanes = _lane_list(state)
    for lane in lanes:
        lane["focused"] = lane.get("lane_id") == lane_id
    return {"pty_lanes": lanes, "focused_lane_id": lane_id}


def patch_lane_collapse(state: dict[str, Any], lane_id: str, *, collapsed: bool) -> dict[str, Any]:
    lanes = _lane_list(state)
    for lane in lanes:
        if lane.get("lane_id") == lane_id:
            lane["collapsed"] = collapsed
    return {"pty_lanes": lanes}


def patch_lane_complete(state: dict[str, Any], lane_id: str) -> dict[str, Any]:
    lanes = _lane_list(state)
    completed_lane: dict[str, Any] | None = None
    for lane in lanes:
        if lane.get("lane_id") == lane_id:
            lane["status"] = "completed"
            completed_lane = lane
    drafts = _drafts(state)
    if completed_lane:
        agent = CLI_TO_DISPLAY.get(str(completed_lane.get("agent_type", "")), "Agent")
        drafts.append(
            {
                "id": f"draft_{uuid.uuid4().hex[:8]}",
                "label": f"回传草稿 · {completed_lane.get('label', agent)}",
                "text": f"@Claude Code {agent} 已完成「{completed_lane.get('label', '')}」。请继续联调。",
                "suggested_target": "Claude Code",
            }
        )
    return {"pty_lanes": lanes, "pending_handoff_drafts": drafts}


def serialize_preview(preview: DispatchPreview) -> dict[str, Any]:
    return {
        "sources": preview.sources,
        "target": preview.target,
        "task": preview.task,
        "handoff_path": preview.handoff_path,
        "handoff_file": preview.handoff_file,
        "file_refs": preview.file_refs,
        "input_mode": preview.input_mode,
        "chips": [
            {
                "id": c.id,
                "label": c.label,
                "on": c.on,
                "source_name": c.source_name,
            }
            for c in preview.chips
        ],
    }
