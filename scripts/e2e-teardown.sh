#!/usr/bin/env bash
# Kill orphaned Clutch desktop E2E stacks (Tauri + Vite + sidecar).
set -euo pipefail

echo "Stopping Clutch E2E processes..."
pkill -9 -f "clutch-desktop" 2>/dev/null || true
pkill -9 -f "tauri dev --features e2e-testing" 2>/dev/null || true
pkill -9 -f "vite --port=3000" 2>/dev/null || true
pkill -9 -f "uvicorn src.main:app.*--port 8124" 2>/dev/null || true
for port in 8124 8123 3000; do
  if lsof -ti "tcp:${port}" >/dev/null 2>&1; then
    lsof -ti "tcp:${port}" | xargs kill -9 2>/dev/null || true
  fi
done
rm -f /tmp/clutch-tauri-playwright.sock 2>/dev/null || true
echo "Done. Ports 3000/8124/8123 should be free."
