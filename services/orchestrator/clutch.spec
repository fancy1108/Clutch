# -*- mode: python ; coding: utf-8 -*-
import importlib.util
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas: list = []
binaries: list = []
hiddenimports: list = []

_spec_dir = Path(SPEC).resolve().parent
_assets = _spec_dir / "src" / "workflow_assets"
if _assets.is_dir() and any(_assets.glob("*.json")):
    datas.append((str(_assets), "src/workflow_assets"))

_presets = _spec_dir / "src" / "design" / "presets"
if _presets.is_dir():
    datas.append((str(_presets), "src/design/presets"))


def _sidecar_console() -> bool:
    """Windows: hide console unless debugging (OSR-17).

    macOS/Linux: use the console bootloader so Tauri-spawned sidecar does not
    register as a GUI app and show a second Dock icon.
    """
    if os.environ.get("CLUTCH_SIDECAR_CONSOLE") == "1":
        return True
    if os.name == "nt":
        return False
    return True

for package in (
    "uvicorn",
    "fastapi",
    "starlette",
    "pydantic",
    "anyio",
    "langgraph",
    "langchain_core",
    "httptools",
    "uvloop",
    "watchfiles",
    "websockets",
    "keyring",
    "winpty",
    "tzdata",
):
    if importlib.util.find_spec(package) is None:
        continue
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

a = Analysis(
    ["sidecar_entry.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ["src.main", "src.state", "src.compiler.compiler"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="orchestrator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=_sidecar_console(),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
