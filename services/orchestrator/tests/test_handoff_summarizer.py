"""Tests for handoff transcript cleaning and summarization."""

from src.handoff_summarizer import clean_pty_transcript, summarize_lane_transcripts, truncate_transcript_fallback


def test_clean_pty_transcript_strips_ansi_and_control_codes() -> None:
    raw = "\x1b[49m\x1b[K\x1b[18;2H\x1b[31mHello\x1b[0m world"
    assert clean_pty_transcript(raw) == "Hello world"


def test_clean_pty_transcript_erases_backspaces() -> None:
    assert clean_pty_transcript("hel\b\b\bOK") == "OK"


def test_truncate_transcript_fallback_preserves_head_and_tail() -> None:
    long_text = "line\n" * 800
    result = truncate_transcript_fallback(long_text, max_chars=200)
    assert "…" in result
    assert result.startswith("line")


def test_summarize_lane_transcripts_empty() -> None:
    assert summarize_lane_transcripts(None, sources_label="Claude Code", target="OpenCode") == (
        "(no upstream session captured)"
    )


def test_summarize_lane_transcripts_fallback_when_llm_unavailable(monkeypatch) -> None:
    def _boom(*_args, **_kwargs):
        raise RuntimeError("no llm")

    monkeypatch.setattr("src.handoff_summarizer.get_router", _boom, raising=False)
    monkeypatch.setattr("src.models_config.get_router", _boom)

    result = summarize_lane_transcripts(
        [{"agent": "Claude Code", "transcript": "\x1b[31m项目总结如下…\x1b[0m"}],
        sources_label="Claude Code",
        target="OpenCode",
    )
    assert "项目总结如下" in result
    assert "\x1b[" not in result


def test_summarize_lane_transcripts_uses_llm(monkeypatch) -> None:
    class _FakeRouter:
        def chat(self, messages, model_id=None):
            assert "Handoff context" in messages[1]["content"]
            return "• Summary bullet from LLM"

    monkeypatch.setattr("src.models_config.get_router", lambda: _FakeRouter())

    result = summarize_lane_transcripts(
        [{"agent": "Claude Code", "transcript": "User: summarize\nClaude: done"}],
        sources_label="Claude Code",
        target="OpenCode",
        task_focus="Build HTML page",
    )
    assert result == "• Summary bullet from LLM"
