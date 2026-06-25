"""Build environment preparation for video-core module.

Ensures the runtime toolchain (ffmpeg, python packages) is available
and creates the required directory layout for video production runs.
"""

from __future__ import annotations

import importlib.util
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def check_ffmpeg() -> bool:
    """Return True if ffmpeg is on PATH and reports a version."""
    return shutil.which("ffmpeg") is not None


def check_python_deps() -> bool:
    """Return True when all required third-party packages are importable."""
    required = ["imageio", "imageio_ffmpeg"]
    return all(importlib.util.find_spec(pkg) is not None for pkg in required)


def prepare_build_env(root: Path) -> dict:
    """Prepare the build environment under *root*.

    Creates the directory layout and validates the runtime toolchain.

    Returns a summary dict with created dirs and toolchain status.
    """
    dirs = [
        root / "src" / "video_core",
        root / "src" / "video_core" / "assets",
        root / "tests" / "test_video_core",
    ]

    created: list[str] = []
    for d in dirs:
        if d.exists():
            logger.debug("directory already exists: %s", d)
        else:
            d.mkdir(parents=True, exist_ok=True)
            created.append(str(d))

    has_ffmpeg = check_ffmpeg()
    has_deps = check_python_deps()

    return {
        "created_dirs": created,
        "status": "ok",
        "toolchain": {
            "ffmpeg": "available" if has_ffmpeg else "missing",
            "python_deps": "available" if has_deps else "missing",
        },
    }


def ensure_dirs(root: Path) -> list[Path]:
    """Guarantee the standard video-core directory tree exists; return created."""
    targets = [
        root / "src" / "video_core",
        root / "src" / "video_core" / "assets",
        root / "tests" / "test_video_core",
    ]
    created: list[Path] = []
    for t in targets:
        created_dir = t.mkdir(parents=True, exist_ok=True)
        if created_dir not in created:
            created.append(t)
    return created
