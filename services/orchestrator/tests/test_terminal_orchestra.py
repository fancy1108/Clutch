"""Tests for terminal_orchestra dispatch + lane state (D34)."""

from src.terminal_orchestra import (
    confirm_dispatch,
    ensure_primary_lane,
    patch_lane_complete,
    patch_lane_focus,
    preview_dispatch,
)


def _base_state(**overrides):
    state = {
        "run_id": "run_test",
        "pty_lanes": [],
        "dispatch_log": [],
        "dispatch_edges": [],
        "pending_handoff_drafts": [],
        "focused_lane_id": None,
    }
    state.update(overrides)
    return state


def test_ensure_primary_lane_creates_lane():
    patch = ensure_primary_lane(_base_state(), cli_tool="claude-cli")
    assert patch["focused_lane_id"] == "lane_primary"
    assert len(patch["pty_lanes"]) == 1


def test_preview_dispatch_with_focused_lane():
    state = _base_state(
        pty_lanes=[
            {
                "lane_id": "lane_primary",
                "agent_type": "claude-cli",
                "label": "Main",
                "status": "running",
                "focused": True,
                "collapsed": False,
                "run_id": "run_test",
            }
        ],
        focused_lane_id="lane_primary",
    )
    preview = preview_dispatch(state, "@OpenCode 实现 API")
    assert preview is not None
    assert preview.target == "OpenCode"
    assert "Claude Code" in preview.sources
    assert preview.dispatch_mode == "switch"


def test_confirm_switch_stores_configured_agent_identity(tmp_path):
    preview = preview_dispatch(_base_state(), "@OpenCode 总结项目")
    assert preview is not None
    patch = confirm_dispatch(
        _base_state(),
        preview=preview,
        prompt="@OpenCode 总结项目",
        workspace_path=str(tmp_path),
        target_configured_agent_id="agent-opencode-1",
        target_configured_agent_name="Opencode",
    )
    lane = patch["pty_lanes"][0]
    assert lane["configured_agent_id"] == "agent-opencode-1"
    assert lane["configured_agent_name"] == "Opencode"
    entry = patch["dispatch_log"][-1]
    sessions = entry.get("lane_sessions") or []
    assert len(sessions) == 1
    assert sessions[0]["workspace_path"] == str(tmp_path)


def test_find_lane_for_agent_without_configured_id_reuses_first_scoped_lane():
    from src.terminal_orchestra import _find_lane_for_agent

    lanes = [
        {
            "lane_id": "lane_b",
            "agent_type": "opencode-cli",
            "configured_agent_id": "oc-2",
            "status": "running",
        },
        {
            "lane_id": "lane_a",
            "agent_type": "opencode-cli",
            "configured_agent_id": "oc-1",
            "status": "running",
        },
    ]
    assert _find_lane_for_agent(lanes, "OpenCode")["lane_id"] == "lane_b"


def test_find_lane_for_agent_respects_configured_agent_id():
    from src.terminal_orchestra import _find_lane_for_agent

    lanes = [
        {
            "lane_id": "lane_a",
            "agent_type": "opencode-cli",
            "configured_agent_id": "oc-1",
            "status": "running",
        },
        {
            "lane_id": "lane_b",
            "agent_type": "opencode-cli",
            "configured_agent_id": "oc-2",
            "status": "running",
        },
    ]
    assert _find_lane_for_agent(lanes, "OpenCode", configured_agent_id="oc-2")["lane_id"] == "lane_b"
    assert _find_lane_for_agent(lanes, "OpenCode", configured_agent_id="oc-1")["lane_id"] == "lane_a"


def test_confirm_switch_replaces_lane(tmp_path):
    state = _base_state(
        pty_lanes=[
            {
                "lane_id": "lane_primary",
                "agent_type": "opencode-cli",
                "label": "Main",
                "status": "running",
                "focused": True,
                "collapsed": False,
                "run_id": "run_test",
            }
        ],
        focused_lane_id="lane_primary",
    )
    preview = preview_dispatch(state, "@Claude Code 实现 API")
    assert preview is not None
    assert preview.dispatch_mode == "switch"
    patch = confirm_dispatch(
        state,
        preview=preview,
        prompt="@Claude Code 实现 API",
        workspace_path=str(tmp_path),
    )
    assert len(patch["pty_lanes"]) == 1
    assert patch["pty_lanes"][0]["agent_type"] == "claude-cli"
    assert patch.get("dispatch_edges") is None
    assert len(patch["dispatch_log"]) == 1
    assert patch["dispatch_log"][0]["sources_label"] == "User"
    assert patch["dispatch_log"][0]["dispatch_mode"] == "switch"
    assert patch["pty_sessions_to_close"] == ["run_test::lane_primary"]
    assert patch["pending_pty_inject"] == {
        "lane_id": "lane_primary",
        "prompt": "实现 API",
    }


def test_first_natural_dispatch_same_agent_is_switch(tmp_path):
    """Preview attach creates a lane; first @SameAgent task is User → agent, not self-handoff."""
    state = _base_state(
        pty_lanes=[
            {
                "lane_id": "lane_primary",
                "agent_type": "opencode-cli",
                "label": "Main",
                "status": "running",
                "focused": True,
                "collapsed": False,
                "run_id": "run_test",
            }
        ],
        focused_lane_id="lane_primary",
    )
    preview = preview_dispatch(state, "@OpenCode 总结项目")
    assert preview is not None
    assert preview.dispatch_mode == "switch"
    patch = confirm_dispatch(
        state,
        preview=preview,
        prompt="@OpenCode 总结项目",
        workspace_path=str(tmp_path),
    )
    assert patch["dispatch_log"][0]["sources_label"] == "User"
    assert patch["dispatch_log"][0]["target"] == "OpenCode"
    assert patch.get("dispatch_edges") is None


def test_confirm_handoff_keeps_source_lane(tmp_path):
    state = _base_state(
        pty_lanes=[
            {
                "lane_id": "lane_primary",
                "agent_type": "claude-cli",
                "label": "Main",
                "status": "running",
                "focused": True,
                "collapsed": False,
                "run_id": "run_test",
            }
        ],
        focused_lane_id="lane_primary",
        dispatch_log=[{"id": "prior"}],
    )
    preview = preview_dispatch(state, "@Codex CLI from @Claude Code：继续")
    assert preview is not None
    assert preview.dispatch_mode == "handoff"
    patch = confirm_dispatch(
        state,
        preview=preview,
        prompt="@Codex CLI from @Claude Code：继续",
        workspace_path=str(tmp_path),
        target_configured_agent_id="codex-1",
        target_configured_agent_name="Codex CLI",
    )
    assert len(patch["dispatch_log"]) == 2
    entry = patch["dispatch_log"][-1]
    assert entry["sources_label"] == "Claude Code"
    assert entry["target"] == "Codex CLI"
    assert len(patch["dispatch_edges"]) == 1
    assert any(l["agent_type"] == "claude-cli" for l in patch["pty_lanes"])
    assert any(l["agent_type"] == "codex-cli" for l in patch["pty_lanes"])
    claude = next(l for l in patch["pty_lanes"] if l["agent_type"] == "claude-cli")
    codex = next(l for l in patch["pty_lanes"] if l["agent_type"] == "codex-cli")
    assert claude["collapsed"] is True
    assert codex["collapsed"] is False
    assert codex["configured_agent_name"] == "Codex CLI"
    assert patch["focused_lane_id"] == codex["lane_id"]
    assert claude.get("cli_session_id")
    assert codex.get("cli_session_id")
    sessions = entry.get("lane_sessions") or []
    assert len(sessions) >= 2
    labels = {item["label"] for item in sessions}
    assert "Claude Code" in labels or "Main" in labels
    assert "Codex CLI" in labels
    for item in sessions:
        assert item.get("cli_session_id")
        assert item.get("workspace_path") == str(tmp_path)


def test_handoff_targets_configured_opencode_lane_not_existing_other(tmp_path):
    state = _base_state(
        pty_lanes=[
            {
                "lane_id": "lane_oc2",
                "agent_type": "opencode-cli",
                "configured_agent_id": "oc-2",
                "configured_agent_name": "Opencode2",
                "label": "Other",
                "status": "running",
                "focused": True,
                "collapsed": False,
                "run_id": "run_test",
            },
        ],
        focused_lane_id="lane_oc2",
        dispatch_log=[{"id": "prior"}],
    )
    preview = preview_dispatch(state, "@OpenCode 总结项目")
    assert preview is not None
    assert preview.dispatch_mode == "switch"
    patch = confirm_dispatch(
        state,
        preview=preview,
        prompt="@OpenCode 总结项目",
        workspace_path=str(tmp_path),
        target_configured_agent_id="oc-1",
        target_configured_agent_name="Opencode",
    )
    entry = patch["dispatch_log"][-1]
    assert entry["sources_label"] == "User"
    assert entry["target"] == "Opencode"
    assert entry["dispatch_mode"] == "switch"
    assert not entry["handoff_file"]
    assert not entry["handoff_path"]
    opencode_lanes = [l for l in patch["pty_lanes"] if l["agent_type"] == "opencode-cli"]
    assert len(opencode_lanes) == 2
    target = next(l for l in opencode_lanes if l["configured_agent_id"] == "oc-1")
    assert target["lane_id"] != "lane_oc2"
    assert patch["focused_lane_id"] == target["lane_id"]
    assert patch["pending_pty_inject"]["lane_id"] == target["lane_id"]
    assert "handoff file" not in patch["pending_pty_inject"]["prompt"]


def test_switch_keeps_claude_lane_when_direct_mention_rivet(tmp_path):
    state = _base_state(
        pty_lanes=[
            {
                "lane_id": "lane_claude",
                "agent_type": "claude-cli",
                "label": "Main",
                "status": "running",
                "focused": True,
                "collapsed": False,
                "run_id": "run_test",
            },
        ],
        focused_lane_id="lane_claude",
        dispatch_log=[{"id": "prior", "sources_label": "User", "target": "Claude Code"}],
    )
    preview = preview_dispatch(state, "@Rivet CLI 项目目的")
    assert preview is not None
    assert preview.dispatch_mode == "switch"
    patch = confirm_dispatch(
        state,
        preview=preview,
        prompt="@Rivet CLI 项目目的",
        workspace_path=str(tmp_path),
    )
    entry = patch["dispatch_log"][-1]
    assert entry["sources_label"] == "User"
    assert entry["target"] == "Rivet CLI"
    assert entry["dispatch_mode"] == "switch"
    assert not entry["handoff_path"]
    assert patch.get("pty_sessions_to_close") is None
    assert len(patch["pty_lanes"]) == 2
    claude = next(l for l in patch["pty_lanes"] if l["lane_id"] == "lane_claude")
    rivet = next(l for l in patch["pty_lanes"] if l["agent_type"] == "rivet-cli")
    assert claude["status"] == "running"
    assert rivet["lane_id"] != "lane_claude"
    assert patch["focused_lane_id"] == rivet["lane_id"]
    assert patch["pending_pty_inject"]["lane_id"] == rivet["lane_id"]
    assert "handoff file" not in patch["pending_pty_inject"]["prompt"]


def test_handoff_collapses_other_lanes_when_target_already_exists(tmp_path):
    state = _base_state(
        pty_lanes=[
            {
                "lane_id": "lane_claude",
                "agent_type": "claude-cli",
                "label": "Main",
                "status": "running",
                "focused": True,
                "collapsed": False,
                "run_id": "run_test",
            },
            {
                "lane_id": "lane_oc",
                "agent_type": "opencode-cli",
                "configured_agent_id": "oc-1",
                "configured_agent_name": "Opencode",
                "label": "Sub",
                "status": "running",
                "focused": False,
                "collapsed": False,
                "run_id": "run_test",
            },
        ],
        focused_lane_id="lane_claude",
        dispatch_log=[{"id": "prior"}],
    )
    preview = preview_dispatch(state, "@OpenCode from @Claude Code：生成 HTML")
    patch = confirm_dispatch(
        state,
        preview=preview,
        prompt="@OpenCode from @Claude Code：生成 HTML",
        workspace_path=str(tmp_path),
        target_configured_agent_id="oc-1",
        target_configured_agent_name="Opencode",
    )
    claude = next(l for l in patch["pty_lanes"] if l["lane_id"] == "lane_claude")
    opencode = next(l for l in patch["pty_lanes"] if l["lane_id"] == "lane_oc")
    assert claude["collapsed"] is True
    assert opencode["collapsed"] is False
    assert opencode["status"] == "running"
    assert patch["focused_lane_id"] == "lane_oc"


def test_confirm_dispatch_appends_log_and_lane(tmp_path):
    state = _base_state(
        pty_lanes=[
            {
                "lane_id": "lane_primary",
                "agent_type": "claude-cli",
                "label": "Main",
                "status": "running",
                "focused": True,
                "collapsed": False,
                "run_id": "run_test",
            }
        ],
        focused_lane_id="lane_primary",
        dispatch_log=[{"id": "prior"}],
    )
    preview = preview_dispatch(state, "@OpenCode 实现 API")
    assert preview is not None
    assert preview.dispatch_mode == "switch"
    patch = confirm_dispatch(
        state,
        preview=preview,
        prompt="@OpenCode 实现 API",
        workspace_path=str(tmp_path),
    )
    assert len(patch["dispatch_log"]) == 2
    entry = patch["dispatch_log"][-1]
    assert entry["sources_label"] == "User"
    assert entry["dispatch_mode"] == "switch"
    assert not entry["handoff_file"]
    assert not entry["handoff_path"]
    assert patch.get("dispatch_edges") is None
    assert len(patch["pty_lanes"]) == 2
    assert any(l["agent_type"] == "opencode-cli" for l in patch["pty_lanes"])
    inject = patch["pending_pty_inject"]
    assert inject["lane_id"]
    assert "handoff file" not in inject["prompt"]
    assert not inject.get("handoff_path")


def test_handoff_file_includes_dispatch_history(tmp_path):
    state = _base_state(
        pty_lanes=[
            {
                "lane_id": "lane_primary",
                "agent_type": "claude-cli",
                "label": "Main",
                "status": "running",
                "focused": True,
                "collapsed": False,
                "run_id": "run_test",
            }
        ],
        focused_lane_id="lane_primary",
        dispatch_log=[
            {
                "id": "prior",
                "sources_label": "User",
                "target": "Claude Code",
                "time": "20:26",
                "prompt": "@Claude Code 总结项目",
            }
        ],
    )
    preview = preview_dispatch(state, "@OpenCode from @Claude Code：基于总结生成 HTML")
    patch = confirm_dispatch(
        state,
        preview=preview,
        prompt="@OpenCode from @Claude Code：基于总结生成 HTML",
        workspace_path=str(tmp_path),
    )
    rel_path = patch["dispatch_log"][-1]["handoff_path"]
    content = (tmp_path / rel_path).read_text(encoding="utf-8")
    assert "## Dispatch history" in content
    assert "总结项目" in content
    assert "## Goal" in content


def test_handoff_file_includes_source_lane_transcripts(tmp_path):
    state = _base_state(
        pty_lanes=[
            {
                "lane_id": "lane_claude",
                "agent_type": "claude-cli",
                "label": "Main",
                "status": "running",
                "focused": True,
                "collapsed": False,
                "run_id": "run_test",
            }
        ],
        focused_lane_id="lane_claude",
        dispatch_log=[{"id": "prior"}],
    )
    preview = preview_dispatch(state, "@OpenCode from @Claude Code：生成 HTML")
    patch = confirm_dispatch(
        state,
        preview=preview,
        prompt="@OpenCode from @Claude Code：生成 HTML",
        workspace_path=str(tmp_path),
        lane_transcripts=[
            {
                "lane_id": "lane_claude",
                "agent": "Claude Code",
                "transcript": "User: 总结项目\nClaude: 项目总结如下…",
            }
        ],
    )
    rel_path = patch["dispatch_log"][-1]["handoff_path"]
    content = (tmp_path / rel_path).read_text(encoding="utf-8")
    assert "## Source output" in content
    assert "项目总结如下" in content
    assert "## From" in content
    assert "## To" in content
    assert "## Time" in content
    assert "## User prompt" in content
    assert "## Referenced files" in content
    assert "@session" not in content


def test_handoff_preview_infers_upstream_source_when_focus_is_target(tmp_path):
    state = _base_state(
        pty_lanes=[
            {
                "lane_id": "lane_claude",
                "agent_type": "claude-cli",
                "label": "Main",
                "status": "running",
                "focused": False,
                "collapsed": True,
                "run_id": "run_test",
            },
            {
                "lane_id": "lane_oc",
                "agent_type": "opencode-cli",
                "label": "Next",
                "status": "running",
                "focused": True,
                "collapsed": False,
                "run_id": "run_test",
            },
        ],
        focused_lane_id="lane_oc",
        dispatch_log=[
            {
                "id": "prior",
                "sources_label": "User",
                "target": "Claude Code",
                "time": "20:26",
                "prompt": "@Claude Code 总结项目",
            }
        ],
    )
    preview = preview_dispatch(state, "@OpenCode from @Claude Code：基于总结生成 HTML")
    assert preview is not None
    assert preview.dispatch_mode == "handoff"
    assert "Claude Code" in preview.sources
    patch = confirm_dispatch(
        state,
        preview=preview,
        prompt="@OpenCode from @Claude Code：基于总结生成 HTML",
        workspace_path=str(tmp_path),
        lane_transcripts=[
            {
                "lane_id": "lane_claude",
                "agent": "Claude Code",
                "transcript": "Claude: 项目总结如下…",
            }
        ],
    )
    content = (tmp_path / patch["dispatch_log"][-1]["handoff_path"]).read_text(encoding="utf-8")
    assert "项目总结如下" in content
    assert "## From" in content
    assert "Claude Code" in content
    assert "## To" in content
    assert "OpenCode" in content


def test_patch_lane_focus():
    lanes = [
        {"lane_id": "a", "focused": True},
        {"lane_id": "b", "focused": False},
    ]
    patch = patch_lane_focus({"pty_lanes": lanes}, "b")
    assert patch["focused_lane_id"] == "b"
    assert patch["pty_lanes"][1]["focused"] is True


def test_patch_close_terminal_lanes_keeps_current():
    state = _base_state(
        pty_lanes=[
            {
                "lane_id": "lane_a",
                "agent_type": "claude-cli",
                "status": "running",
                "focused": True,
                "collapsed": False,
                "run_id": "run_test",
            },
            {
                "lane_id": "lane_b",
                "agent_type": "opencode-cli",
                "status": "running",
                "focused": False,
                "collapsed": False,
                "run_id": "run_test",
            },
        ],
        focused_lane_id="lane_a",
    )
    from src.terminal_orchestra import patch_close_terminal_lanes

    patch = patch_close_terminal_lanes(state, keep_lane_id="lane_a")
    assert len(patch["pty_lanes"]) == 1
    assert patch["pty_lanes"][0]["lane_id"] == "lane_a"
    assert patch["pty_sessions_to_close"] == ["run_test::lane_b"]
    assert patch["focused_lane_id"] == "lane_a"


def test_patch_close_terminal_lanes_close_all():
    state = _base_state(
        pty_lanes=[
            {
                "lane_id": "lane_primary",
                "agent_type": "claude-cli",
                "status": "running",
                "focused": True,
                "collapsed": False,
                "run_id": "run_test",
            },
        ],
    )
    from src.terminal_orchestra import patch_close_terminal_lanes

    patch = patch_close_terminal_lanes(state, keep_lane_id=None)
    assert patch["pty_lanes"] == []
    assert patch["pty_sessions_to_close"] == ["run_test::lane_primary"]


def test_handoff_reuses_existing_target_lane(tmp_path):
    state = _base_state(
        pty_lanes=[
            {
                "lane_id": "lane_a",
                "agent_type": "claude-cli",
                "label": "Main",
                "status": "running",
                "focused": True,
                "collapsed": False,
                "run_id": "run_test",
            },
            {
                "lane_id": "lane_b",
                "agent_type": "opencode-cli",
                "label": "Sub task",
                "status": "running",
                "focused": False,
                "collapsed": False,
                "run_id": "run_test",
            },
        ],
        focused_lane_id="lane_b",
        dispatch_log=[{"id": "prior"}],
    )
    preview = preview_dispatch(state, "@Claude Code from @OpenCode：继续主任务")
    assert preview is not None
    assert preview.dispatch_mode == "handoff"
    patch = confirm_dispatch(
        state,
        preview=preview,
        prompt="@Claude Code from @OpenCode：继续主任务",
        workspace_path=str(tmp_path),
    )
    claude_lanes = [l for l in patch["pty_lanes"] if l["agent_type"] == "claude-cli"]
    opencode_lanes = [l for l in patch["pty_lanes"] if l["agent_type"] == "opencode-cli"]
    assert len(claude_lanes) == 1
    assert len(opencode_lanes) == 1
    assert claude_lanes[0]["lane_id"] == "lane_a"
    assert patch["focused_lane_id"] == "lane_a"


def test_handoff_log_uses_configured_lane_labels_for_graph_syntax(tmp_path):
    state = _base_state(
        pty_lanes=[
            {
                "lane_id": "lane_claude",
                "agent_type": "claude-cli",
                "configured_agent_name": "Claude Code",
                "label": "Main",
                "status": "running",
                "focused": False,
                "collapsed": False,
                "run_id": "run_test",
            },
            {
                "lane_id": "lane_oc",
                "agent_type": "opencode-cli",
                "configured_agent_name": "Opencode",
                "label": "Sub",
                "status": "running",
                "focused": True,
                "collapsed": False,
                "run_id": "run_test",
            },
        ],
        focused_lane_id="lane_oc",
        dispatch_log=[{"id": "prior"}],
    )
    preview = preview_dispatch(state, "@Claude Code from @OpenCode：总结成一句话")
    assert preview is not None
    patch = confirm_dispatch(
        state,
        preview=preview,
        prompt="@Claude Code from @OpenCode：总结成一句话",
        workspace_path=str(tmp_path),
        target_configured_agent_id="oc-1",
        target_configured_agent_name="Opencode",
    )
    entry = patch["dispatch_log"][-1]
    assert entry["sources_label"] == "Opencode"
    assert entry["target"] == "Claude Code"


def test_patch_lane_complete_adds_draft():
    state = _base_state(
        pty_lanes=[
            {
                "lane_id": "lane_primary",
                "agent_type": "claude-cli",
                "label": "API",
                "status": "running",
                "focused": True,
                "collapsed": False,
                "run_id": "run_test",
            }
        ]
    )
    patch = patch_lane_complete(state, "lane_primary")
    assert patch["pty_lanes"][0]["status"] == "completed"
    assert len(patch["pending_handoff_drafts"]) == 1
