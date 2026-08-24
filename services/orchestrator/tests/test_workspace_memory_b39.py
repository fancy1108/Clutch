"""B-39 workspace MEMORY.md."""

from __future__ import annotations

from src.workspace_memory import (
    MEMORY_REL,
    append_note,
    format_workspace_memory_block,
    harvest_user_remember,
    read_notes,
)


def _ws(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.workspace.get_workspace",
        lambda: {"workspace_path": str(tmp_path)},
    )


def test_append_and_prompt_block(tmp_path, monkeypatch) -> None:
    _ws(tmp_path, monkeypatch)
    assert append_note("commit messages in Chinese") == MEMORY_REL
    assert append_note("commit messages in Chinese") == MEMORY_REL
    assert read_notes() == ["commit messages in Chinese"]
    block = format_workspace_memory_block()
    assert "MEMORY.md" in block
    assert "commit messages in Chinese" in block
    assert (tmp_path / MEMORY_REL).is_file()


def test_harvest_remember_phrase(tmp_path, monkeypatch) -> None:
    _ws(tmp_path, monkeypatch)
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path / "store"))
    from src.preferences_storage import save_cross_session_memory_enabled

    save_cross_session_memory_enabled(True)
    assert harvest_user_remember("记住：提交说明用中文") == [MEMORY_REL]
    assert "提交说明用中文" in read_notes()
    assert harvest_user_remember("what's the weather") == []


def test_harvest_skips_when_memory_off(tmp_path, monkeypatch) -> None:
    _ws(tmp_path, monkeypatch)
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path / "store"))
    from src.preferences_storage import save_cross_session_memory_enabled

    save_cross_session_memory_enabled(False)
    assert harvest_user_remember("记住：不该写入") == []
    assert read_notes() == []


def test_compact_keeps_last_notes(tmp_path, monkeypatch) -> None:
    _ws(tmp_path, monkeypatch)
    for i in range(45):
        append_note(f"note-{i}")
    notes = read_notes()
    assert len(notes) == 40
    assert notes[0] == "note-5"
    assert notes[-1] == "note-44"


def test_remember_outcome_passed_and_failed(tmp_path, monkeypatch) -> None:
    _ws(tmp_path, monkeypatch)
    from src.workspace_memory import remember_outcome

    assert remember_outcome({"conclusion": "passed", "title": "login form"}) == MEMORY_REL
    assert any(item.startswith("Worked:") for item in read_notes())
    assert remember_outcome(
        {"conclusion": "failed", "title": "tests", "summary": "pytest boom"}
    ) == MEMORY_REL
    assert any("Failed: tests" in item for item in read_notes())
