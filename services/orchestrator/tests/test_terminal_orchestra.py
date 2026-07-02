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
    )
    preview = preview_dispatch(state, "@OpenCode 实现 API")
    assert preview is not None
    patch = confirm_dispatch(
        state,
        preview=preview,
        prompt="@OpenCode 实现 API",
        workspace_path=str(tmp_path),
    )
    assert len(patch["dispatch_log"]) == 1
    assert len(patch["dispatch_edges"]) == 1
    assert any(l["agent_type"] == "opencode-cli" for l in patch["pty_lanes"])


def test_patch_lane_focus():
    lanes = [
        {"lane_id": "a", "focused": True},
        {"lane_id": "b", "focused": False},
    ]
    patch = patch_lane_focus({"pty_lanes": lanes}, "b")
    assert patch["focused_lane_id"] == "b"
    assert patch["pty_lanes"][1]["focused"] is True


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
