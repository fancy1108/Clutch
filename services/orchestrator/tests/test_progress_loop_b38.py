"""B-38 no-progress loop: same read/grep/list args."""

from __future__ import annotations

from src.progress_loop import ProgressTracker, fingerprint, progress_stop_result
from src.run_control import should_offer_continue


def test_fingerprint_ignores_writes() -> None:
    assert fingerprint("search_replace", {"path": "a.py"}) is None
    assert fingerprint("read_file", {"path": "a.py"}) == "read_file:a.py||"
    assert fingerprint("list_dir", {}) == "list_dir:."
    assert fingerprint("grep", {"pattern": "foo", "path": "src"}) == "grep:foo|src"


def test_third_identical_read_stops() -> None:
    tracker = ProgressTracker()
    args = {"path": "README.md"}
    assert tracker.peek("read_file", args) == "ok"
    assert tracker.observe("read_file", args) == "ok"
    assert tracker.peek("read_file", args) == "nudge"
    assert tracker.observe("read_file", args) == "nudge"
    assert tracker.peek("read_file", args) == "stop"
    assert tracker.observe("read_file", args) == "stop"
    assert tracker.peek("read_file", args) == "stop"


def test_different_paths_do_not_trip() -> None:
    tracker = ProgressTracker()
    assert tracker.observe("list_dir", {"path": "."}) == "ok"
    assert tracker.observe("list_dir", {"path": "src"}) == "ok"
    assert tracker.observe("list_dir", {"path": "."}) == "nudge"


def test_writes_never_count() -> None:
    tracker = ProgressTracker()
    args = {"path": "a.py", "old_string": "x", "new_string": "y"}
    assert tracker.observe("search_replace", args) == "ok"
    assert tracker.observe("search_replace", args) == "ok"
    assert tracker.observe("search_replace", args) == "ok"


def test_stop_message_offers_continue() -> None:
    text = progress_stop_result("read_file")
    assert should_offer_continue(text)
    assert "No-progress loop" in text or "无进展循环" in text
    assert should_offer_continue("[CHAT] No-progress loop: blocked repeat read_file")
