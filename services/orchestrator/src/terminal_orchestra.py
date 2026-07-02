"""Terminal Orchestra state + dispatch (D34)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from src.dispatch_parse import DispatchPreview, DispatchMode, DispatchChip, parse_dispatch_mentions
from src.handoff_writer import parse_handoff_meta_from_name, write_handoff_markdown
from src.terminal_cli_catalog import CLI_TO_DISPLAY, DISPLAY_TO_CLI

MAX_PTY_LANES = 4
WORKSPACE_SOURCE = "工作区"
USER_SOURCE = "User"


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


def normalize_lane_id(lane_id: str, state: dict[str, Any]) -> str:
    raw = (lane_id or "primary").strip() or "primary"
    if raw in {"primary", "lane_primary"}:
        focus = str(state.get("focused_lane_id") or "").strip()
        return focus or "lane_primary"
    return raw


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


def _lane_dispatch_label(lane: dict[str, Any]) -> str:
    """Human label for dispatch sources/targets; prefer configured agent name over CLI display."""
    configured = str(lane.get("configured_agent_name") or "").strip()
    if configured:
        return configured
    agent_type = str(lane.get("agent_type", ""))
    return CLI_TO_DISPLAY.get(agent_type) or agent_type


def focused_agent_name(state: dict[str, Any]) -> str | None:
    lane = focused_lane(state)
    if not lane:
        return None
    return _lane_dispatch_label(lane)


def ensure_primary_lane(state: dict[str, Any], *, cli_tool: str, label: str | None = None) -> dict[str, Any]:
    lanes = _lane_list(state)
    if lanes:
        return {}
    lane_id = "lane_primary"
    lane_label = label or CLI_TO_DISPLAY.get(cli_tool, cli_tool)
    lane = {
        "lane_id": lane_id,
        "agent_type": cli_tool,
        "label": lane_label,
        "status": "running",
        "focused": True,
        "collapsed": False,
        "run_id": state.get("run_id", ""),
    }
    _ensure_lane_cli_session_id(lane)
    return {"pty_lanes": [lane], "focused_lane_id": lane_id}


def file_meta_resolver(file_name: str) -> dict[str, Any]:
    return parse_handoff_meta_from_name(file_name)


def _infer_handoff_sources(state: dict[str, Any], target: str) -> list[str]:
    """Prefer upstream lanes / prior dispatch targets over the focused lane for handoff."""
    target_norm = target.strip().lower()
    sources: list[str] = []
    for lane in _lane_list(state):
        if lane.get("status") == "queued":
            continue
        display = _lane_dispatch_label(lane)
        if not display or display.strip().lower() == target_norm:
            continue
        if display not in sources:
            sources.append(display)
    if sources:
        return sources

    log = _dispatch_log(state)
    if log:
        last_target = str(log[-1].get("target") or "").strip()
        if (
            last_target
            and last_target.strip().lower() != target_norm
            and last_target not in sources
        ):
            return [last_target]

    focused = focused_agent_name(state)
    if focused and focused.strip().lower() != target_norm:
        return [focused]
    return []


def _with_handoff_sources(
    state: dict[str, Any],
    preview: DispatchPreview,
    *,
    mode: DispatchMode,
) -> DispatchPreview:
    if mode != "handoff" or preview.input_mode != "natural" or preview.file_refs:
        return preview

    inferred = _infer_handoff_sources(state, preview.target)
    if not inferred:
        return preview
    if preview.sources == inferred:
        return preview

    chips = [
        DispatchChip(
            id=f"src_{i}",
            label=f"Lane · {name}" if name != WORKSPACE_SOURCE else "工作区摘要",
            on=True,
            source_name=name,
        )
        for i, name in enumerate(inferred)
    ]

    return DispatchPreview(
        sources=inferred,
        target=preview.target,
        task=preview.task,
        handoff_path=preview.handoff_path,
        handoff_file=preview.handoff_file,
        chips=chips,
        file_refs=preview.file_refs,
        input_mode=preview.input_mode,
        dispatch_mode=mode,
    )


def preview_dispatch(state: dict[str, Any], text: str) -> DispatchPreview | None:
    preview = parse_dispatch_mentions(
        text,
        focused_agent=focused_agent_name(state),
        file_meta_resolver=file_meta_resolver,
    )
    if preview is None:
        return None
    mode = resolve_dispatch_mode(state, preview)
    adjusted = _with_handoff_sources(state, preview, mode=mode)
    return DispatchPreview(
        sources=adjusted.sources,
        target=adjusted.target,
        task=adjusted.task,
        handoff_path=adjusted.handoff_path,
        handoff_file=adjusted.handoff_file,
        chips=adjusted.chips,
        file_refs=adjusted.file_refs,
        input_mode=adjusted.input_mode,
        dispatch_mode=mode,
    )


def resolve_dispatch_mode(state: dict[str, Any], preview: DispatchPreview) -> DispatchMode:
    """Graph syntax or file attachments = handoff; natural @target = switch (User → agent)."""
    if preview.input_mode == "graph" or preview.file_refs:
        return "handoff"
    return "switch"


def _use_multi_lane_switch(state: dict[str, Any], lanes: list[dict[str, Any]]) -> bool:
    """Keep existing PTY lanes when orchestrating a new @-target beyond bootstrap replace."""
    active = [lane for lane in lanes if lane.get("status") != "completed"]
    if len(active) > 1:
        return True
    if len(active) == 1 and (_dispatch_log(state) or _dispatch_edges(state)):
        return True
    if len(active) == 1 and active[0].get("lane_id") != "lane_primary":
        return True
    return False


def _agent_type_for_target(target: str) -> str:
    return DISPLAY_TO_CLI.get(target, "claude-cli")


def _apply_configured_agent(
    lane: dict[str, Any],
    *,
    agent_id: str = "",
    agent_name: str = "",
) -> None:
    aid = agent_id.strip()
    aname = agent_name.strip()
    if aid:
        lane["configured_agent_id"] = aid
    if aname:
        lane["configured_agent_name"] = aname


def _display_labels_for_sources(
    lanes: list[dict[str, Any]],
    sources: list[str],
) -> list[str]:
    """Map canonical dispatch names (OpenCode) to configured lane labels (Opencode)."""
    out: list[str] = []
    for src in sources:
        if src == WORKSPACE_SOURCE:
            out.append(src)
            continue
        lane = _find_lane_for_agent(lanes, src)
        if not lane:
            src_norm = src.strip().lower()
            for candidate in lanes:
                if _lane_dispatch_label(candidate).strip().lower() == src_norm:
                    lane = candidate
                    break
        label = _lane_dispatch_label(lane) if lane else src
        if label not in out:
            out.append(label)
    return out


def _find_lane_for_agent(
    lanes: list[dict[str, Any]],
    target: str,
    *,
    configured_agent_id: str = "",
) -> dict[str, Any] | None:
    cli = _agent_type_for_target(target)
    cfg_id = configured_agent_id.strip()
    completed_fallback: dict[str, Any] | None = None
    unscoped_active: dict[str, Any] | None = None
    for lane in lanes:
        if lane.get("agent_type") != cli:
            continue
        if lane.get("status") == "completed":
            if completed_fallback is None:
                completed_fallback = lane
            continue
        lane_cfg = str(lane.get("configured_agent_id") or "").strip()
        if cfg_id:
            if lane_cfg == cfg_id:
                return lane
            continue
        if not lane_cfg:
            return lane
        if unscoped_active is None:
            unscoped_active = lane
    if cfg_id:
        return completed_fallback
    return unscoped_active or completed_fallback


def _ensure_lane_cli_session_id(lane: dict[str, Any]) -> str:
    sid = str(lane.get("cli_session_id") or "").strip()
    if not sid:
        sid = str(uuid.uuid4())
        lane["cli_session_id"] = sid
    return sid


def _lane_session_ref(lane: dict[str, Any], *, workspace_path: str = "") -> dict[str, str]:
    ref: dict[str, str] = {
        "lane_id": str(lane.get("lane_id") or ""),
        "label": _lane_dispatch_label(lane),
        "agent_type": str(lane.get("agent_type") or ""),
        "cli_session_id": _ensure_lane_cli_session_id(lane),
    }
    ws = workspace_path.strip()
    if ws:
        ref["workspace_path"] = ws
    return ref


def _collect_lane_sessions(
    lanes: list[dict[str, Any]],
    lane_ids: list[str],
    *,
    workspace_path: str = "",
) -> list[dict[str, str]]:
    by_id = {str(lane.get("lane_id") or ""): lane for lane in lanes}
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for lane_id in lane_ids:
        if not lane_id or lane_id in seen:
            continue
        lane = by_id.get(lane_id)
        if not lane:
            continue
        seen.add(lane_id)
        out.append(_lane_session_ref(lane, workspace_path=workspace_path))
    return out


def _source_lane_ids(lanes: list[dict[str, Any]], sources: list[str]) -> list[str]:
    ids: list[str] = []
    for src in sources:
        if src == WORKSPACE_SOURCE:
            continue
        src_norm = src.strip().lower()
        matched = False
        for lane in lanes:
            lane_name = str(lane.get("configured_agent_name") or "").strip()
            if lane_name and lane_name.lower() == src_norm:
                lane_id = str(lane.get("lane_id"))
                if lane_id not in ids:
                    ids.append(lane_id)
                matched = True
                break
        if matched:
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
    target_configured_agent_id: str = "",
    target_configured_agent_name: str = "",
    lane_transcripts: list[dict[str, object]] | None = None,
) -> dict[str, Any]:
    if preview.dispatch_mode == "switch":
        return _confirm_switch_dispatch(
            state,
            preview=preview,
            prompt=prompt,
            workspace_path=workspace_path,
            target_configured_agent_id=target_configured_agent_id,
            target_configured_agent_name=target_configured_agent_name,
        )
    return _confirm_handoff_dispatch(
        state,
        preview=preview,
        prompt=prompt,
        workspace_path=workspace_path,
        active_chips=active_chips,
        target_configured_agent_id=target_configured_agent_id,
        target_configured_agent_name=target_configured_agent_name,
        lane_transcripts=lane_transcripts,
    )


def _apply_dispatch_lane_layout(lanes: list[dict[str, Any]], target_lane_id: str) -> None:
    """Expand only the latest @-target lane; collapse other non-queued lanes."""
    tid = target_lane_id.strip()
    if not tid:
        return

    eligible = [lane for lane in lanes if lane.get("status") != "queued"]
    if len(eligible) <= 1:
        for lane in eligible:
            if str(lane.get("lane_id", "")) == tid:
                lane["collapsed"] = False
                lane["focused"] = True
        return

    for lane in lanes:
        if lane.get("status") == "queued":
            continue
        lid = str(lane.get("lane_id", ""))
        if lid == tid:
            lane["collapsed"] = False
            lane["focused"] = True
        else:
            lane["collapsed"] = True
            lane["focused"] = False


def _handoff_inject_prompt(preview: DispatchPreview, *, handoff_path: str) -> str:
    task = preview.task.strip() or preview.target
    return (
        f"Read the handoff file `{handoff_path}` for upstream agent context and conversation history. "
        f"Then complete this task: {task}"
    )


def _pending_inject_patch(
    preview: DispatchPreview,
    lane_id: str,
    *,
    prompt: str | None = None,
    handoff_path: str = "",
) -> dict[str, Any]:
    text = (prompt or preview.task).strip()
    if not text or not lane_id:
        return {}
    payload: dict[str, str] = {"lane_id": lane_id, "prompt": text}
    if handoff_path:
        payload["handoff_path"] = handoff_path
    return {"pending_pty_inject": payload}


def _append_target_lane_for_switch(
    lanes: list[dict[str, Any]],
    *,
    preview: DispatchPreview,
    run_id: str,
    target_configured_agent_id: str = "",
    target_configured_agent_name: str = "",
) -> str:
    """Find or create the @-target lane; return its lane_id."""
    expanded = [lane for lane in lanes if not lane.get("collapsed")]
    if len(expanded) >= MAX_PTY_LANES and not _find_lane_for_agent(
        lanes,
        preview.target,
        configured_agent_id=target_configured_agent_id,
    ):
        queued_lane = {
            "lane_id": f"lane_q_{uuid.uuid4().hex[:8]}",
            "agent_type": _agent_type_for_target(preview.target),
            "label": preview.task[:40] or preview.target,
            "status": "queued",
            "focused": False,
            "collapsed": True,
            "run_id": run_id,
        }
        lanes.append(queued_lane)
        _apply_configured_agent(
            queued_lane,
            agent_id=target_configured_agent_id,
            agent_name=target_configured_agent_name,
        )
        return str(queued_lane["lane_id"])

    existing = _find_lane_for_agent(
        lanes,
        preview.target,
        configured_agent_id=target_configured_agent_id,
    )
    if existing:
        existing["status"] = "running"
        existing["label"] = preview.task[:40] or existing.get("label", preview.target)
        _apply_configured_agent(
            existing,
            agent_id=target_configured_agent_id,
            agent_name=target_configured_agent_name,
        )
        _ensure_lane_cli_session_id(existing)
        return str(existing.get("lane_id", ""))

    lane_id = f"lane_{uuid.uuid4().hex[:8]}"
    lanes.append(
        {
            "lane_id": lane_id,
            "agent_type": _agent_type_for_target(preview.target),
            "label": preview.task[:40] or preview.target,
            "status": "booting",
            "focused": True,
            "collapsed": False,
            "run_id": run_id,
        }
    )
    _apply_configured_agent(
        lanes[-1],
        agent_id=target_configured_agent_id,
        agent_name=target_configured_agent_name,
    )
    _ensure_lane_cli_session_id(lanes[-1])
    return lane_id


def _confirm_switch_dispatch(
    state: dict[str, Any],
    *,
    preview: DispatchPreview,
    prompt: str,
    workspace_path: str = "",
    target_configured_agent_id: str = "",
    target_configured_agent_name: str = "",
) -> dict[str, Any]:
    run_id = str(state.get("run_id", ""))
    lanes = _lane_list(state)

    if _use_multi_lane_switch(state, lanes):
        target_lane_id = _append_target_lane_for_switch(
            lanes,
            preview=preview,
            run_id=run_id,
            target_configured_agent_id=target_configured_agent_id,
            target_configured_agent_name=target_configured_agent_name,
        )
        for lane in lanes:
            _ensure_lane_cli_session_id(lane)
        _apply_dispatch_lane_layout(lanes, target_lane_id)

        target_label = target_configured_agent_name.strip() or preview.target
        log = _dispatch_log(state)
        log.append(
            {
                "id": f"dispatch_{uuid.uuid4().hex[:12]}",
                "time": _iso_now(),
                "sources_label": USER_SOURCE,
                "target": target_label,
                "prompt": prompt,
                "handoff_file": "",
                "handoff_path": "",
                "input_mode": preview.input_mode,
                "dispatch_mode": "switch",
                "file_refs": preview.file_refs,
                "lane_sessions": _collect_lane_sessions(
                    lanes,
                    [target_lane_id],
                    workspace_path=workspace_path,
                ),
            }
        )
        return {
            "pty_lanes": lanes,
            "focused_lane_id": target_lane_id,
            "dispatch_log": log,
            **_pending_inject_patch(preview, target_lane_id),
        }

    sessions_to_close = [
        pty_session_key(run_id, str(lane.get("lane_id", "")))
        for lane in lanes
        if lane.get("lane_id")
    ]

    target_cli = _agent_type_for_target(preview.target)
    new_lane = {
        "lane_id": "lane_primary",
        "agent_type": target_cli,
        "label": preview.task[:40] or preview.target,
        "status": "booting",
        "focused": True,
        "collapsed": False,
        "run_id": run_id,
    }
    _apply_configured_agent(
        new_lane,
        agent_id=target_configured_agent_id,
        agent_name=target_configured_agent_name,
    )
    _ensure_lane_cli_session_id(new_lane)

    log = _dispatch_log(state)
    target_label = target_configured_agent_name.strip() or preview.target
    log.append(
        {
            "id": f"dispatch_{uuid.uuid4().hex[:12]}",
            "time": _iso_now(),
            "sources_label": USER_SOURCE,
            "target": target_label,
            "prompt": prompt,
            "handoff_file": "",
            "handoff_path": "",
            "input_mode": preview.input_mode,
            "dispatch_mode": "switch",
            "file_refs": preview.file_refs,
            "lane_sessions": _collect_lane_sessions(
                lanes + [new_lane],
                ["lane_primary"],
                workspace_path=workspace_path,
            ),
        }
    )

    return {
        "pty_lanes": [new_lane],
        "focused_lane_id": "lane_primary",
        "dispatch_log": log,
        "pty_sessions_to_close": sessions_to_close,
        **_pending_inject_patch(preview, "lane_primary"),
    }


def _confirm_handoff_dispatch(
    state: dict[str, Any],
    *,
    preview: DispatchPreview,
    prompt: str,
    workspace_path: str,
    active_chips: list[str] | None = None,
    target_configured_agent_id: str = "",
    target_configured_agent_name: str = "",
    lane_transcripts: list[dict[str, object]] | None = None,
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
        dispatch_history=_dispatch_log(state),
        lane_transcripts=lane_transcripts,
    )

    lanes = _lane_list(state)
    expanded = [l for l in lanes if not l.get("collapsed")]
    if len(expanded) >= MAX_PTY_LANES and not _find_lane_for_agent(
        lanes,
        preview.target,
        configured_agent_id=target_configured_agent_id,
    ):
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
        existing = _find_lane_for_agent(
            lanes,
            preview.target,
            configured_agent_id=target_configured_agent_id,
        )
        if existing:
            # Reuse live PTY — keep running so the lane pane injects without detach/respawn.
            existing["status"] = "running"
            existing["label"] = preview.task[:40] or existing.get("label", preview.target)
            existing["focused"] = True
            _apply_configured_agent(
                existing,
                agent_id=target_configured_agent_id,
                agent_name=target_configured_agent_name,
            )
            _ensure_lane_cli_session_id(existing)
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
            _apply_configured_agent(
                lanes[-1],
                agent_id=target_configured_agent_id,
                agent_name=target_configured_agent_name,
            )
            _ensure_lane_cli_session_id(lanes[-1])
            for lane in lanes:
                lane["focused"] = lane.get("lane_id") == lane_id

    for lane in lanes:
        _ensure_lane_cli_session_id(lane)

    target_lane = focused_lane({"pty_lanes": lanes}) or {}
    target_lane_id = str(target_lane.get("lane_id", ""))
    _apply_dispatch_lane_layout(lanes, target_lane_id)
    source_lane_ids = _source_lane_ids(lanes, sources)
    session_lane_ids = [*source_lane_ids]
    if target_lane_id and target_lane_id not in session_lane_ids:
        session_lane_ids.append(target_lane_id)

    target_label = target_configured_agent_name.strip() or preview.target
    if preview.input_mode == "graph":
        target_lane_for_label = _find_lane_for_agent(lanes, preview.target)
        target_label = (
            _lane_dispatch_label(target_lane_for_label)
            if target_lane_for_label
            else preview.target.strip() or target_label
        )
    display_sources = _display_labels_for_sources(lanes, sources)
    sources_label = " + ".join(display_sources) if display_sources else WORKSPACE_SOURCE
    entry = {
        "id": f"dispatch_{uuid.uuid4().hex[:12]}",
        "time": _iso_now(),
        "sources_label": sources_label,
        "target": target_label,
        "prompt": prompt,
        "handoff_file": file_name,
        "handoff_path": rel_path,
        "input_mode": preview.input_mode,
        "dispatch_mode": "handoff",
        "file_refs": preview.file_refs,
        "lane_sessions": _collect_lane_sessions(
            lanes,
            session_lane_ids,
            workspace_path=workspace_path,
        ),
    }
    edge = {
        "sources": sources,
        "target": target_label,
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
        **_pending_inject_patch(
            preview,
            target_lane_id,
            prompt=_handoff_inject_prompt(preview, handoff_path=rel_path),
            handoff_path=rel_path,
        ),
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


def patch_close_terminal_lanes(
    state: dict[str, Any],
    *,
    keep_lane_id: str | None = None,
) -> dict[str, Any]:
    """Close PTY sessions for lanes; keep_lane_id=None closes all active lanes."""
    run_id = str(state.get("run_id", ""))
    lanes = _lane_list(state)
    active = [lane for lane in lanes if lane.get("status") != "completed"]
    to_close: list[str] = []
    remaining: list[dict[str, Any]] = []

    for lane in active:
        lane_id = str(lane.get("lane_id", ""))
        if not lane_id:
            continue
        if keep_lane_id is None:
            to_close.append(pty_session_key(run_id, lane_id))
            continue
        if lane_id == keep_lane_id:
            remaining.append(lane)
        else:
            to_close.append(pty_session_key(run_id, lane_id))

    if keep_lane_id is None:
        remaining = []

    focused = keep_lane_id if remaining else None
    return {
        "pty_lanes": remaining,
        "focused_lane_id": focused,
        "pty_sessions_to_close": to_close,
    }


def serialize_preview(preview: DispatchPreview) -> dict[str, Any]:
    return {
        "sources": preview.sources,
        "target": preview.target,
        "task": preview.task,
        "handoff_path": preview.handoff_path,
        "handoff_file": preview.handoff_file,
        "file_refs": preview.file_refs,
        "input_mode": preview.input_mode,
        "dispatch_mode": preview.dispatch_mode,
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
