"""D6/D50 submit_diff_summary helpers."""

from __future__ import annotations

from src.builtin_tools import (
    build_diff_summary_from_paths,
    execute_builtin_tool,
    is_submit_diff_summary_tool,
    list_builtin_tools,
    normalize_diff_summary,
    _parse_unified_diff_lines,
)
from src.chat_runner import _chat_message, _diff_summary_for_seal
from src.mcp_risk import is_risky_mcp_tool


def test_submit_diff_summary_listed() -> None:
    assert "submit_diff_summary" in {t["name"] for t in list_builtin_tools()}
    assert is_submit_diff_summary_tool("clutch-tools__submit_diff_summary")
    assert not is_risky_mcp_tool("submit_diff_summary")


def test_normalize_and_execute_with_patch() -> None:
    patch = "@@ -1,2 +1,3 @@\n line\n-old\n+new\n+extra\n"
    card = normalize_diff_summary(
        {
            "title": "Cache layer",
            "summary": "Switched to Redis",
            "files": [
                {
                    "path": "cache.py",
                    "status": "M",
                    "summary": "Use Redis client",
                    "patch": patch,
                },
                {"path": "README.md", "status": "A", "patch": "+hello\n"},
            ],
        },
        enrich=False,
    )
    assert card["title"] == "Cache layer"
    assert len(card["files"]) == 2
    assert card["files"][0]["path"] == "cache.py"
    assert card["files"][0]["diffs"]
    out = execute_builtin_tool("submit_diff_summary", card)
    assert "Diff summary published" in out
    assert "cache.py" in out


def test_parse_unified_diff_lines() -> None:
    lines = _parse_unified_diff_lines("@@ -1 +1,2 @@\n-a\n+b\n+c\n")
    types = [row["type"] for row in lines]
    assert "deletion" in types
    assert types.count("addition") == 2


def test_build_from_paths_empty() -> None:
    assert build_diff_summary_from_paths([]) is None
    assert build_diff_summary_from_paths(None) is None


def test_seal_helper_skips_inline_and_auto() -> None:
    """Final reply must not re-attach inline/auto aggregate cards."""
    sealed = _diff_summary_for_seal(
        {},  # type: ignore[arg-type]
        files_changed=["notes.md", "a.py"],
    )
    assert sealed is None

    inline_state = {
        "diff_summary": {
            "title": "a.py",
            "inline": True,
            "files": [{"path": "a.py", "status": "M", "summary": "", "patch": "+x", "diffs": []}],
        }
    }
    assert _diff_summary_for_seal(inline_state) is None  # type: ignore[arg-type]


def test_seal_prefers_explicit_review_card() -> None:
    state = {
        "diff_summary": {
            "title": "Review",
            "files": [{"path": "x.py", "status": "M", "summary": "", "patch": "", "diffs": []}],
        }
    }
    sealed = _diff_summary_for_seal(state, files_changed=["y.py"])  # type: ignore[arg-type]
    assert sealed is not None
    assert sealed["title"] == "Review"
    assert sealed["files"][0]["path"] == "x.py"
    msg = _chat_message("Clutch Agent", "done", diff_summary=sealed)
    assert msg["diffSummary"]["title"] == "Review"


def test_inline_edit_card_from_search_replace() -> None:
    from src.builtin_tools import build_inline_edit_diff_cards

    cards = build_inline_edit_diff_cards(
        tool_name="search_replace",
        func_args={
            "path": "d6-diff-demo/alpha.py",
            "old_string": 'VERSION = "0.0.0"',
            "new_string": 'VERSION = "d6-1"',
        },
        result_str='{"ok": true, "path": "d6-diff-demo/alpha.py", "changed_paths": ["d6-diff-demo/alpha.py"]}',
    )
    assert len(cards) == 1
    assert cards[0]["inline"] is True
    assert cards[0]["title"] == "alpha.py"
    assert cards[0]["files"][0]["path"] == "d6-diff-demo/alpha.py"
    patch = cards[0]["files"][0]["patch"]
    assert 'VERSION = "0.0.0"' in patch
    assert 'VERSION = "d6-1"' in patch
    assert any(d["type"] == "deletion" for d in cards[0]["files"][0]["diffs"])
    assert any(d["type"] == "addition" for d in cards[0]["files"][0]["diffs"])


def test_append_hunk_keeps_unchanged_line_as_context() -> None:
    """Appending should not paint the unchanged prefix as deleted+re-added."""
    from src.builtin_tools import _hunk_from_old_new, _parse_unified_diff_lines

    patch = _hunk_from_old_new("D6 reviewed", "D6 reviewed\n\nD7 reviewed")
    lines = _parse_unified_diff_lines(patch)
    types = [row["type"] for row in lines]
    # Unchanged "D6 reviewed" must be context (normal), not deletion+addition.
    assert types.count("deletion") == 0
    assert any(row["type"] == "addition" and "D7 reviewed" in row["text"] for row in lines)
