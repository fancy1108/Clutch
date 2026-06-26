"""Tests for video_core.renderer — stub render and ffmpeg check."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.video_core.renderer import check_ffmpeg, render


class TestCheckFfmpeg:
    """Verify ffmpeg binary detection."""

    def test_ffmpeg_on_path(self):
        assert check_ffmpeg() is True


class TestRender:
    """Verify the stub renderer creates output and returns path."""

    def test_render_creates_file(self, tmp_path: Path):
        output = tmp_path / "renders" / "test.mp4"
        result = asyncio.run(render("hello world", str(output), duration=2.0))
        assert Path(result).exists()
        assert Path(result).read_text().startswith("generated:")

    def test_render_returns_absolute_path(self, tmp_path: Path):
        output = tmp_path / "renders" / "test.mp4"
        result = asyncio.run(render("hello world", str(output), duration=2.0))
        assert Path(result).resolve() == output.resolve()

    def test_render_parent_dir_created(self, tmp_path: Path):
        output = tmp_path / "deep" / "nested" / "dir" / "out.mp4"
        asyncio.run(render("test", str(output)))
        assert output.parent.exists()
