"""PyInstaller entrypoint — bundled Clutch orchestrator sidecar."""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("src.main:app", host="127.0.0.1", port=8123, log_level="info")


if __name__ == "__main__":
    main()
