"""Tests for session persistable content gate."""

from __future__ import annotations

from src.session_content import session_has_persistable_content


def test_empty_state_is_not_persistable() -> None:
    assert session_has_persistable_content(None) is False
    assert session_has_persistable_content({}) is False
    assert session_has_persistable_content({"messages": [], "dispatch_log": []}) is False


def test_messages_make_session_persistable() -> None:
    assert session_has_persistable_content({"messages": [{"id": "m1", "text": "hi"}]}) is True


def test_dispatch_log_makes_session_persistable() -> None:
    assert session_has_persistable_content({"dispatch_log": [{"id": "d1"}]}) is True
