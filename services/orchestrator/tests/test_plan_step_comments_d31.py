"""D31 — plan step inline comments."""

from __future__ import annotations

import json

from src.plan_revise import (
    align_step_comments,
    format_plan_feedback,
    parse_plan_revise_instructions,
)


def test_parse_plan_revise_json() -> None:
    payload = json.dumps(
        {
            "note": "Please shorten",
            "stepComments": [
                {"step": 2, "text": "Wire auth", "comment": "Use OAuth only"},
            ],
        }
    )
    note, annotations = parse_plan_revise_instructions(payload)
    assert note == "Please shorten"
    assert len(annotations) == 1
    assert annotations[0]["comment"] == "Use OAuth only"


def test_align_step_comments() -> None:
    aligned = align_step_comments(
        ["Add route", "Wire auth"],
        [{"step": 2, "comment": "OAuth only"}],
    )
    assert aligned == ["", "OAuth only"]


def test_format_plan_feedback() -> None:
    text = format_plan_feedback(
        "Overall shorter",
        [{"step": 1, "text": "Add route", "comment": "Skip docs"}],
    )
    assert "Overall shorter" in text
    assert "Step 1" in text
    assert "Skip docs" in text
