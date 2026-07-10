#!/usr/bin/env python3
"""Build the PyInstaller sidecar for the current Tauri host target."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def resolve_pyinstaller_python(orchestrator: Path) -> str:
    """Prefer the orchestrator uv-managed venv (where PyInstaller lives).

    Falls back to `sys.executable`, but that only works if the caller already
    activated the orchestrator venv or installed PyInstaller globally — which
    is not how the project is set up (see services/orchestrator/pyproject.toml).
    """
    if os.name == "nt":
        candidate = orchestrator / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = orchestrator / ".venv" / "bin" / "python"
    if candidate.is_file():
        return str(candidate)
    return sys.executable


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    orchestrator = root / "services" / "orchestrator"
    assets = orchestrator / "src" / "workflow_assets"
    tauri_bin = root / "apps" / "desktop" / "src-tauri" / "binaries"

    shutil.rmtree(assets, ignore_errors=True)
    assets.mkdir(parents=True)
    for workflow in (root / "workflows").glob("*.json"):
        shutil.copy2(workflow, assets / workflow.name)

    triple = subprocess.check_output(
        ["rustc", "--print", "host-tuple"], text=True
    ).strip()
    python = resolve_pyinstaller_python(orchestrator)
    subprocess.run(
        [python, "-m", "PyInstaller", "clutch.spec", "--noconfirm", "--clean"],
        cwd=orchestrator,
        check=True,
    )

    suffix = ".exe" if os.name == "nt" else ""
    source = orchestrator / "dist" / f"orchestrator{suffix}"
    destination = tauri_bin / f"orchestrator-{triple}{suffix}"
    tauri_bin.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if os.name != "nt":
        destination.chmod(0o755)
    print(f"sidecar -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
