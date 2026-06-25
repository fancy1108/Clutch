"""FFmpeg-backed renderer using imageio-ffmpeg (already in dependencies)."""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


async def render(prompt: str, output_path: str, duration: float = 5.0) -> str:
    """Stub: generate a video at *output_path* from *prompt*.

    Current implementation writes a marker file so callers can verify
    the pipeline wires end-to-end. Replace with real ffmpeg / diffusion
    backend calls when the model provider is chosen.
    """
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(f"generated:{prompt}:{duration}s")
    logger.info("stub render → %s", dest)
    return str(dest)


def check_ffmpeg() -> bool:
    """Return True when ``ffmpeg`` binary is on PATH."""
    return shutil.which("ffmpeg") is not None
