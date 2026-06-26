"""Tests for human_input kinds."""

from __future__ import annotations

from src.human_input import HumanInputKind, human_required_payload


def test_human_required_payload_shape() -> None:
    payload = human_required_payload(
        run_id="run-1",
        kind=HumanInputKind.TOOL_CONFIRM,
        message="Allow tool?",
    )
    assert payload["kind"] == "tool_confirm"
    assert payload["run_id"] == "run-1"
