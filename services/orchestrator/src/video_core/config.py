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
        """Build config from environment variables (for CI / containerised builds)."""
        return cls(
            resolution=os.getenv("VIDEO_RESOLUTION", cls.resolution),  # type: ignore[arg-type]
            codec=os.getenv("VIDEO_CODEC", cls.codec),  # type: ignore[arg-type]
            output_format=os.getenv("VIDEO_FORMAT", cls.output_format),  # type: ignore[arg-type]
            fps=int(os.getenv("VIDEO_FPS", str(cls.fps))),
            bitrate_mbps=float(os.getenv("VIDEO_BITRATE_MBPS", str(cls.bitrate_mbps))),
            output_dir=Path(os.getenv("VIDEO_OUTPUT_DIR", str(cls.output_dir))),
        )
