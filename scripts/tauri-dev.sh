#!/usr/bin/env bash
# Layer 4 操作剧本 · 不扩权。铁律见 CLAUDE.md
# Start Vite in a new session (double-fork), then run tauri without managing the dev server.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP="$REPO_ROOT/apps/desktop"
VITE_URL="http://127.0.0.1:3000/"
VITE_LOG="${REPO_ROOT}/.clutch-vite-dev.log"
VITE_PID_FILE="${REPO_ROOT}/.clutch-vite.pid"

start_vite_daemon() {
  : >"$VITE_LOG"
  DESKTOP="$DESKTOP" VITE_LOG="$VITE_LOG" VITE_PID_FILE="$VITE_PID_FILE" python3 <<'PY'
import os
import sys

desktop = os.environ["DESKTOP"]
log_path = os.environ["VITE_LOG"]
pid_path = os.environ["VITE_PID_FILE"]

# Fully detach from the interactive shell (macOS has no setsid binary).
if os.fork() > 0:
    sys.exit(0)
os.setsid()
if os.fork() > 0:
    sys.exit(0)

with open(pid_path, "w", encoding="utf-8") as pid_file:
    pid_file.write(str(os.getpid()))

os.chdir(desktop)
log_fd = os.open(log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT)
os.dup2(log_fd, 1)
os.dup2(log_fd, 2)
os.execvp("pnpm", ["pnpm", "run", "dev"])
PY
}

if ! curl -sf "$VITE_URL" >/dev/null 2>&1; then
  start_vite_daemon
  for _ in $(seq 1 120); do
    if curl -sf "$VITE_URL" >/dev/null 2>&1; then
      break
    fi
    if [[ -f "$VITE_PID_FILE" ]]; then
      VITE_PID="$(cat "$VITE_PID_FILE")"
      if ! kill -0 "$VITE_PID" 2>/dev/null; then
        echo "[tauri-dev] Vite exited before :3000 became ready. Log:" >&2
        tail -30 "$VITE_LOG" >&2 || true
        exit 1
      fi
    fi
    sleep 0.25
  done
  if ! curl -sf "$VITE_URL" >/dev/null 2>&1; then
    echo "[tauri-dev] Timed out waiting for Vite on :3000. Log:" >&2
    tail -30 "$VITE_LOG" >&2 || true
    exit 1
  fi
  echo "[tauri-dev] Vite ready at $VITE_URL (pid $(cat "$VITE_PID_FILE"), log $VITE_LOG)"
else
  echo "[tauri-dev] Reusing existing Vite on :3000"
fi

export CLUTCH_RUNTIME_MODE="${CLUTCH_RUNTIME_MODE:-hybrid}"
cd "$DESKTOP"
exec pnpm tauri dev --no-dev-server-wait
