"""B-36 layered context: offload → noise → batch; L4 stays in compaction."""

from __future__ import annotations

from pathlib import Path

from src.compaction import should_compact
from src.context_layers import POINTER, apply_layered_context
from src.state import initial_state


def _tool(content: str, *, call_id: str = "c1") -> dict:
    return {"role": "tool", "tool_call_id": call_id, "content": content}


def test_offload_large_tool_result_writes_pointer(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_TOOL_OFFLOAD_CHARS", "80")
    monkeypatch.setenv("CLUTCH_TOOL_BATCH_CHARS", "99999")
    body = "x" * 200
    messages = [
        {"role": "user", "content": "read it"},
        _tool(body),
    ]
    stats = apply_layered_context(messages, archive_dir=tmp_path)
    assert stats.offloaded == 1
    assert messages[0]["content"] == "read it"
    assert messages[1]["content"].startswith(POINTER)
    assert "chars=200" in messages[1]["content"]
    assert "source=tool" in messages[1]["content"]
    assert "truncated=yes" in messages[1]["content"]
    files = list(tmp_path.glob("*.txt"))
    assert len(files) == 1
    assert files[0].read_text(encoding="utf-8") == body


def test_small_tool_result_stays_inline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_TOOL_OFFLOAD_CHARS", "4000")
    messages = [_tool("hello")]
    stats = apply_layered_context(messages, archive_dir=tmp_path)
    assert stats.offloaded == 0
    assert messages[0]["content"] == "hello"
    assert list(tmp_path.glob("*.txt")) == []


def test_noise_drops_duplicate_older_tool(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_TOOL_OFFLOAD_CHARS", "4000")
    monkeypatch.setenv("CLUTCH_TOOL_BATCH_CHARS", "99999")
    blob = "same listing\n" + "file.txt\n"
    messages = [
        _tool(blob, call_id="old"),
        _tool("unique later result", call_id="mid"),
        _tool(blob, call_id="new"),
    ]
    stats = apply_layered_context(messages, archive_dir=tmp_path)
    assert stats.noise_dropped >= 1
    assert messages[0]["content"].startswith("[dropped as noise]")
    assert messages[2]["content"] == blob


def test_batch_offloads_older_tools_keeps_recent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_TOOL_OFFLOAD_CHARS", "4000")
    monkeypatch.setenv("CLUTCH_TOOL_BATCH_CHARS", "400")
    older = "alpha " * 80
    recent_a = "beta keep"
    recent_b = "gamma keep"
    messages = [
        {"role": "assistant", "content": "calling"},
        _tool(older, call_id="old"),
        _tool(recent_a, call_id="a"),
        _tool(recent_b, call_id="b"),
    ]
    stats = apply_layered_context(messages, archive_dir=tmp_path)
    assert stats.batched == 1
    assert messages[1]["content"].startswith(POINTER)
    assert messages[2]["content"] == recent_a
    assert messages[3]["content"] == recent_b


def test_emergency_compact_threshold_unchanged() -> None:
    state = initial_state("run_b36")
    state["messages"] = [{"agent": "User", "text": f"m{i}"} for i in range(6)]
    state["session_tokens"] = 14_999
    assert should_compact(state) is False
    state["session_tokens"] = 15_001
    assert should_compact(state) is True
