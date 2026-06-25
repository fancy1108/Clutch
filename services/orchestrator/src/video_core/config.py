"""Video core configuration — dataclasses and defaults for the pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

OutputFormat = Literal["mp4", "mov", "gif", "webm"]
Resolution = Literal["720p", "1080p", "4k"]
Codec = Literal["h264", "hevc", "vp9", "av1"]


@dataclass(slots=True)
class VideoConfig:
    """Immutable configuration for a single video production run."""

    resolution: Resolution = "1080p"
    codec: Codec = "h264"
    output_format: OutputFormat = "mp4"
    fps: int = 30
    bitrate_mbps: float = 8.0
    output_dir: Path = field(default_factory=lambda: Path.cwd() / "outputs" / "videos")
    assets_dir: Path = field(default_factory=lambda: Path.cwd() / "src" / "video_core" / "assets")
    work_dir: Path = field(default_factory=lambda: Path.cwd() / ".clutch_tmp" / "video_core")

    @property
    def extension(self) -> str:
        return {
            "mp4": ".mp4",
            "mov": ".mov",
            "gif": ".gif",
            "webm": ".webm",
        }[self.output_format]

    @property
    def preset(self) -> str:
        """FFmpeg preset — faster for dev, slower for release."""
        return "fast" if self.bitrate_mbps <= 8 else "medium"

    @classmethod
    def from_env(cls) -> VideoConfig:
        """Build config from environment variables (for CI / containerised builds).

        Starts from a blank instance (which picks up dataclass defaults),
        then overrides any fields whose VIDEO_* env vars are set.
        """
        cfg = cls()  # picks up all dataclass defaults
        if (v := os.getenv("VIDEO_RESOLUTION")):
            cfg.resolution = v  # type: ignore[assignment]
        if (v := os.getenv("VIDEO_CODEC")):
            cfg.codec = v  # type: ignore[assignment]
        if (v := os.getenv("VIDEO_FORMAT")):
            cfg.output_format = v  # type: ignore[assignment]
        if (v := os.getenv("VIDEO_FPS")):
            cfg.fps = int(v)
        if (v := os.getenv("VIDEO_BITRATE_MBPS")):
            cfg.bitrate_mbps = float(v)
        if (v := os.getenv("VIDEO_OUTPUT_DIR")):
            cfg.output_dir = Path(v)
        return cfg
