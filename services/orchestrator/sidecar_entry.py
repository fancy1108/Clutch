"""PyInstaller entrypoint — bundled Clutch orchestrator sidecar."""

from __future__ import annotations

import uvicorn

from src.main import app


def main() -> None:
    # Pass app object directly so PyInstaller onefile keeps _MEIPASS / bundled datas.
    uvicorn.run(app, host="127.0.0.1", port=8123, log_level="info")


if __name__ == "__main__":
    main()
