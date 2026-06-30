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
    console=os.environ.get("CLUTCH_SIDECAR_CONSOLE") == "1",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
