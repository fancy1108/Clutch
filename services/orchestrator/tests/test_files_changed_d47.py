"""D47: seal filesChanged onto assistant chat messages."""

from __future__ import annotations

from src.chat_runner import _chat_message


def test_chat_message_seals_files_changed() -> None:
    payload = _chat_message(
        "Clutch Agent",
        "Wrote notes.",
        files_changed=["notes.md", "docs/a.md", "notes.md"],
    )
    assert payload["filesChanged"] == ["notes.md", "docs/a.md"]
    assert "toolSteps" not in payload


def test_chat_message_omits_empty_files_changed() -> None:
    payload = _chat_message("Clutch Agent", "ok", files_changed=[])
    assert "filesChanged" not in payload
    payload_none = _chat_message("Clutch Agent", "ok", files_changed=None)
    assert "filesChanged" not in payload_none
