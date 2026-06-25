"""Placeholder — video_core build env tests."""

from pathlib import Path

import pytest

from src.video_core.env import prepare_build_env


class TestPrepareBuildEnv:
    def test_creates_missing_dirs(self, tmp_path: Path) -> None:
        result = prepare_build_env(tmp_path)
        assert result["status"] == "ok"
        assert (tmp_path / "src" / "video_core").exists()
        assert (tmp_path / "src" / "video_core" / "assets").exists()
        assert (tmp_path / "tests" / "test_video_core").exists()

    def test_skips_existing_dirs(self, tmp_path: Path) -> None:
        # Pre-create all dirs
        for d in [
            tmp_path / "src" / "video_core",
            tmp_path / "src" / "video_core" / "assets",
            tmp_path / "tests" / "test_video_core",
        ]:
            d.mkdir(parents=True)

        result = prepare_build_env(tmp_path)
        assert result["created_dirs"] == []
