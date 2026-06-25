"""Tests for video_core.config — VideoConfig dataclass and helpers."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.video_core.config import VideoConfig


class TestVideoConfigDefaults:
    """Verify default values match the spec."""

    def test_default_resolution(self):
        cfg = VideoConfig()
        assert cfg.resolution == "1080p"

    def test_default_codec(self):
        cfg = VideoConfig()
        assert cfg.codec == "h264"

    def test_default_output_format(self):
        cfg = VideoConfig()
        assert cfg.output_format == "mp4"

    def test_default_fps(self):
        cfg = VideoConfig()
        assert cfg.fps == 30

    def test_default_bitrate(self):
        cfg = VideoConfig()
        assert cfg.bitrate_mbps == 8.0

    def test_default_output_dir(self):
        cfg = VideoConfig()
        assert cfg.output_dir.name == "videos"
        assert cfg.output_dir.parent.name == "outputs"

    def test_default_assets_dir(self):
        cfg = VideoConfig()
        assert "video_core" in str(cfg.assets_dir)
        assert "assets" in str(cfg.assets_dir)

    def test_default_work_dir(self):
        cfg = VideoConfig()
        assert ".clutch_tmp" in str(cfg.work_dir)
        assert "video_core" in str(cfg.work_dir)


class TestVideoConfigProperties:
    """Test computed properties."""

    @pytest.mark.parametrize("fmt,ext", [
        ("mp4", ".mp4"),
        ("mov", ".mov"),
        ("gif", ".gif"),
        ("webm", ".webm"),
    ])
    def test_extension_maps_format(self, fmt, ext):
        cfg = VideoConfig(output_format=fmt)
        assert cfg.extension == ext

    @pytest.mark.parametrize("bitrate,preset", [
        (8.0, "fast"),
        (4.0, "fast"),
        (10.0, "medium"),
        (20.0, "medium"),
    ])
    def test_preset_scales_with_bitrate(self, bitrate, preset):
        cfg = VideoConfig(bitrate_mbps=bitrate)
        assert cfg.preset == preset


class TestVideoConfigFromEnv:
    """Test environment-variable driven construction."""

    def test_from_env_uses_defaults_when_no_vars(self, monkeypatch):
        # Clear any VIDEO_* vars
        for key in list(os.environ.keys()):
            if key.startswith("VIDEO_"):
                monkeypatch.delenv(key, raising=False)
        cfg = VideoConfig.from_env()
        assert cfg.resolution == "1080p"
        assert cfg.codec == "h264"
        assert cfg.fps == 30

    def test_from_env_reads_resolution(self, monkeypatch):
        monkeypatch.setenv("VIDEO_RESOLUTION", "4k")
        cfg = VideoConfig.from_env()
        assert cfg.resolution == "4k"

    def test_from_env_reads_fps(self, monkeypatch):
        monkeypatch.setenv("VIDEO_FPS", "60")
        cfg = VideoConfig.from_env()
        assert cfg.fps == 60

    def test_from_env_reads_bitrate(self, monkeypatch):
        monkeypatch.setenv("VIDEO_BITRATE_MBPS", "16.0")
        cfg = VideoConfig.from_env()
        assert cfg.bitrate_mbps == 16.0

    def test_from_env_reads_output_dir(self, monkeypatch, tmp_path):
        monkeypatch.setenv("VIDEO_OUTPUT_DIR", str(tmp_path / "out"))
        cfg = VideoConfig.from_env()
        assert cfg.output_dir == tmp_path / "out"


class TestVideoConfigCustomValues:
    """Test that custom constructor values are respected."""

    def test_custom_values_stick(self):
        cfg = VideoConfig(
            resolution="4k",
            codec="av1",
            output_format="webm",
            fps=60,
            bitrate_mbps=20.0,
        )
        assert cfg.resolution == "4k"
        assert cfg.codec == "av1"
        assert cfg.output_format == "webm"
        assert cfg.fps == 60
        assert cfg.bitrate_mbps == 20.0
