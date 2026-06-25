import os
import sys
from pathlib import Path


def get_storage_dir() -> Path:
    """Returns the base storage directory for Clutch, isolating DEV vs PROD.

    - DEV/TEST (uvicorn / ``pnpm tauri dev``): ``clutch_dev``
    - PROD (PyInstaller sidecar in DMG): ``clutch``
    - Override: ``CLUTCH_STORAGE_DIR`` (absolute path)
    """
    override = os.environ.get("CLUTCH_STORAGE_DIR")
    if override:
        return Path(override).expanduser().resolve()

    sub_dir = "clutch" if getattr(sys, "frozen", False) else "clutch_dev"

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / sub_dir
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / sub_dir
    return Path.home() / ".local" / "share" / sub_dir
