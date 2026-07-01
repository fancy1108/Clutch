#!/usr/bin/env bash
# Layer 4 操作剧本 · 不扩权。铁律见 CLAUDE.md
# E2E Tauri dev: inject playwright capability only while e2e-testing feature is active.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP="$REPO_ROOT/apps/desktop"
CAP_DIR="$DESKTOP/src-tauri/capabilities"
E2E_CAP="$DESKTOP/src-tauri/e2e-capabilities/e2e.json"
E2E_LINK="$CAP_DIR/e2e.json"

cleanup() {
  rm -f "$E2E_LINK"
}
trap cleanup EXIT INT TERM

cp "$E2E_CAP" "$E2E_LINK"
cd "$DESKTOP"
exec pnpm tauri dev --features e2e-testing --config src-tauri/tauri.e2e.conf.json "$@"
