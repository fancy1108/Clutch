"""Tests for video_core.env — build environment helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.video_core.env import (
    check_ffmpeg,
    check_python_deps,
    ensure_dirs,
    prepare_build_env,
)


class TestCheckFfmpeg:
    """Verify ffmpeg detection logic."""

    def test_ffmpeg_on_path(self):
        """ffmpeg should be available via system PATH or imageio-ffmpeg bundle."""
        assert check_ffmpeg() is True


class TestCheckPythonDeps:
    """Verify Python dependency detection."""

    def test_imageio_importable(self):
        assert check_python_deps() is True


class TestEnsureDirs:
    """Verify directory creation guarantees."""

    def test_creates_missing_dirs(self, tmp_path: Path):
        # Remove the target so mkdir is exercised
        targets = [
            tmp_path / "src" / "video_core",
            tmp_path / "src" / "video_core" / "assets",
            tmp_path / "tests" / "test_video_core",
        ]
        for t in targets:
            if t.exists():
                t.rmdir()

        created = ensure_dirs(tmp_path)

        for t in targets:
            assert t.exists(), f"{t} was not created"

    def test_returns_created_list(self, tmp_path: Path):
        created = ensure_dirs(tmp_path)
        # All three should be in the returned list
        assert len(created) == 3

    def test_idempotent_when_exists(self, tmp_path: Path):
        targets = [
            tmp_path / "src" / "video_core",
            tmp_path / "src" / "video_core" / "assets",
            tmp_path / "tests" / "test_video_core",
        ]
        created = ensure_dirs(tmp_path)
        # Should return empty or minimal — nothing newly created
        for t in targets:
            assert t.exists()


class TestPrepareBuildEnv:
    """Verify the full build-env preparation routine."""

    def test_returns_summary_dict(self, tmp_path: Path):
        result = prepare_build_env(tmp_path)
        assert isinstance(result, dict)
        assert "created_dirs" in result
        assert "status" in result
        assert "toolchain" in result

    def test_status_is_ok(self, tmp_path: Path):
        result = prepare_build_env(tmp_path)
        assert result["status"] == "ok"

    def test_toolchain_reports_ffmpeg(self, tmp_path: Path):
        result = prepare_build_env(tmp_path)
        assert result["toolchain"]["ffmpeg"] == "available"

    def test_toolchain_reports_python_deps(self, tmp_path: Path):
        result = prepare_build_env(tmp_path)
        assert result["toolchain"]["python_deps"] == "available"

    def test_creates_expected_dirs(self, tmp_path: Path):
        result = prepare_build_env(tmp_path)
        expected = [
            str(tmp_path / "src" / "video_core"),
            str(tmp_path / "src" / "video_core" / "assets"),
            str(tmp_path / "tests" / "test_video_core"),
        ]
        for exp in expected:
            assert exp in result["created_dirs"]
