"""D16 — cross-session memory tests."""

from __future__ import annotations

from src.agent_prompt import compose_agent_prompt_assembly
from src.builtin_tools import execute_builtin_tool
from src.cross_session_memory import add_entry, clear_all, format_memory_prompt_block, list_entries
from src.bg_jobs import bind_bg_job_context, release_bg_job_context
from src.preferences_storage import save_cross_session_memory_enabled


def test_memory_injected_when_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path / "storage"))
    save_cross_session_memory_enabled(True)
    add_entry("commit messages in Chinese")
    block = format_memory_prompt_block()
    assert "commit messages in Chinese" in block
    assembly = compose_agent_prompt_assembly(
        {"name": "Clutch Agent", "markdownDoc": "protocol"},
        model_name="test",
        model_api="builtin",
        clutch_mcp_path=True,
        mcp_servers_bound=True,
    )
    names = [layer.name for layer in assembly.layers]
    assert "memory" in names


def test_remember_preference_tool(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CLUTCH_STORAGE_DIR", str(tmp_path / "storage"))
    save_cross_session_memory_enabled(True)
    token = bind_bg_job_context({"run_id": "run_mem"})
    try:
        out = execute_builtin_tool("remember_preference", {"text": "use pytest for tests"})
        assert "ok" in out.lower()
        assert len(list_entries()) == 1
    finally:
        release_bg_job_context(token)
    clear_all()
    assert list_entries() == []
