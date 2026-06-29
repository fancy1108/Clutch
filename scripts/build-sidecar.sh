#!/usr/bin/env bash
# Build PyInstaller sidecar and copy to Tauri externalBin path.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
orch="$root/services/orchestrator"
tauri_bin="$root/apps/desktop/src-tauri/binaries"
triple="$(rustc --print host-tuple)"

mkdir -p "$tauri_bin"
cd "$orch"

assets="$orch/src/workflow_assets"
rm -rf "$assets"
mkdir -p "$assets"
cp "$root/workflows/"*.json "$assets/"
echo "== workflow_assets (repo templates only; no Application Support data) =="
ls -1 "$assets/"

echo "== build-sidecar: PyInstaller ($triple) =="
uv run pyinstaller clutch.spec --noconfirm --clean

dest="$tauri_bin/orchestrator-$triple"
cp -f "$orch/dist/orchestrator" "$dest"
chmod +x "$dest"
echo "== sidecar -> $dest =="
