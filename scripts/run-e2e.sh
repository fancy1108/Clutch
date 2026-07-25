#!/usr/bin/env bash
# E2E: API smoke + MVP closed-loop + desktop full UI (isolated sandbox).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

chmod +x scripts/e2e-sandbox-setup.sh
E2E_ROOT="$(./scripts/e2e-sandbox-setup.sh)"
# shellcheck disable=SC1091
source runs/verification/.e2e-env

sidecar_pid=""
tauri_pid=""
cleanup() {
  if [[ -n "${tauri_pid:-}" ]]; then
    kill -9 "$tauri_pid" 2>/dev/null || true
    tauri_pid=""
  fi
  if [[ -n "${sidecar_pid:-}" ]] && kill -0 "$sidecar_pid" 2>/dev/null; then
    kill "$sidecar_pid" 2>/dev/null || true
    wait "$sidecar_pid" 2>/dev/null || true
  fi
  if [[ -n "${E2E_ROOT:-}" && -d "${E2E_ROOT}" && "${E2E_ROOT}" == *"clutch-e2e"* ]]; then
    rm -rf "${E2E_ROOT}"
  fi
  rm -f /tmp/clutch-tauri-playwright.sock 2>/dev/null || true
}
trap cleanup EXIT

for port in 8124 8123 3000; do
  if lsof -ti "tcp:${port}" >/dev/null 2>&1; then
    lsof -ti "tcp:${port}" | xargs kill -9 2>/dev/null || true
    sleep 0.5
  fi
done

mkdir -p runs/verification
log="runs/verification/$(date +%Y-%m-%d)-e2e-full.log"
status_file="$(mktemp)"
echo 1 >"$status_file"

# Playwright browsers (desktop E2E); API tests use Node WebSocket only.
(cd e2e && pnpm exec playwright install chromium)

wait_sidecar() {
  for _ in $(seq 1 60); do
    curl -sf http://127.0.0.1:8123/health >/dev/null && return 0
    sleep 0.5
  done
  echo "Sidecar health check failed" >&2
  return 1
}

wait_tauri_ready() {
  # Dev/e2e Tauri spawns sidecar on 8124; packaged uses 8123.
  for _ in $(seq 1 240); do
    if curl -sf http://127.0.0.1:3000 >/dev/null 2>&1 \
      && { curl -sf http://127.0.0.1:8124/health >/dev/null 2>&1 \
        || curl -sf http://127.0.0.1:8123/health >/dev/null 2>&1; } \
      && [[ -S /tmp/clutch-tauri-playwright.sock ]]; then
      return 0
    fi
    sleep 1
  done
  echo "Tauri app + sidecar (8124/8123) + playwright socket not ready" >&2
  echo "  :3000=$(curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:3000 || echo down)" >&2
  echo "  :8124=$(curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:8124/health || echo down)" >&2
  echo "  :8123=$(curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:8123/health || echo down)" >&2
  echo "  sock=$([[ -S /tmp/clutch-tauri-playwright.sock ]] && echo yes || echo no)" >&2
  return 1
}

{
  echo "=== API E2E ==="
  (cd services/orchestrator && env CLUTCH_E2E_FAKE_LLM="${CLUTCH_E2E_FAKE_LLM:-}" \
    CLUTCH_STORAGE_DIR="${CLUTCH_STORAGE_DIR:-}" \
    CLUTCH_AGENTS_DIR="${CLUTCH_AGENTS_DIR:-}" \
    CLUTCH_E2E_SANDBOX="${CLUTCH_E2E_SANDBOX:-}" \
    CLUTCH_WORKSPACES_FILE="${CLUTCH_WORKSPACES_FILE:-}" \
    CLUTCH_RUN_HISTORY_DIR="${CLUTCH_RUN_HISTORY_DIR:-}" \
    CLUTCH_TOOLS_CONFIG="${CLUTCH_TOOLS_CONFIG:-}" \
    CLUTCH_MODELS_CONFIG="${CLUTCH_MODELS_CONFIG:-}" \
    uv run uvicorn src.main:app --host 127.0.0.1 --port 8123) &
  sidecar_pid=$!
  wait_sidecar
  (cd e2e && env CLUTCH_E2E_SANDBOX="${CLUTCH_E2E_SANDBOX:-}" \
    CLUTCH_E2E_SIDECAR_PORT=8123 \
    pnpm test:api)

  kill "$sidecar_pid" 2>/dev/null || true
  wait "$sidecar_pid" 2>/dev/null || true
  sidecar_pid=""
  sleep 2
  for port in 8123 3000; do
    if lsof -ti "tcp:${port}" >/dev/null 2>&1; then
      lsof -ti "tcp:${port}" | xargs kill -9 2>/dev/null || true
      sleep 0.5
    fi
  done

  echo "=== Hybrid concurrent sessions API E2E (real PTY spawn) ==="
  (cd services/orchestrator && env CLUTCH_E2E_FAKE_LLM="${CLUTCH_E2E_FAKE_LLM:-}" \
    CLUTCH_E2E_FAKE_HYBRID=1 \
    CLUTCH_RUNTIME_MODE=hybrid \
    CLUTCH_SHELL_MAX_SESSIONS=8 \
    CLUTCH_STORAGE_DIR="${CLUTCH_STORAGE_DIR:-}" \
    CLUTCH_AGENTS_DIR="${CLUTCH_AGENTS_DIR:-}" \
    CLUTCH_E2E_SANDBOX="${CLUTCH_E2E_SANDBOX:-}" \
    CLUTCH_WORKSPACES_FILE="${CLUTCH_WORKSPACES_FILE:-}" \
    CLUTCH_RUN_HISTORY_DIR="${CLUTCH_RUN_HISTORY_DIR:-}" \
    CLUTCH_TOOLS_CONFIG="${CLUTCH_TOOLS_CONFIG:-}" \
    CLUTCH_MODELS_CONFIG="${CLUTCH_MODELS_CONFIG:-}" \
    uv run uvicorn src.main:app --host 127.0.0.1 --port 8123) &
  sidecar_pid=$!
  wait_sidecar
  (cd e2e && env CLUTCH_E2E_SANDBOX="${CLUTCH_E2E_SANDBOX:-}" \
    CLUTCH_E2E_SIDECAR_PORT=8123 \
    CLUTCH_RUNTIME_MODE=hybrid \
    CLUTCH_E2E_FAKE_HYBRID=1 \
    pnpm test:hybrid-api)

  kill "$sidecar_pid" 2>/dev/null || true
  wait "$sidecar_pid" 2>/dev/null || true
  sidecar_pid=""
  sleep 2
  for port in 8123 3000; do
    if lsof -ti "tcp:${port}" >/dev/null 2>&1; then
      lsof -ti "tcp:${port}" | xargs kill -9 2>/dev/null || true
      sleep 0.5
    fi
  done
  rm -f /tmp/clutch-tauri-playwright.sock 2>/dev/null || true

  echo "=== Desktop E2E ==="
  set +e
  # Must pass CLUTCH_STORAGE_DIR so the Tauri-spawned sidecar never touches clutch_dev.
  (cd apps/desktop && env CLUTCH_E2E_SANDBOX="${CLUTCH_E2E_SANDBOX:-}" \
    CLUTCH_E2E_FAKE_LLM="${CLUTCH_E2E_FAKE_LLM:-}" \
    CLUTCH_STORAGE_DIR="${CLUTCH_STORAGE_DIR:-}" \
    CLUTCH_AGENTS_DIR="${CLUTCH_AGENTS_DIR:-}" \
    CLUTCH_WORKSPACES_FILE="${CLUTCH_WORKSPACES_FILE:-}" \
    CLUTCH_RUN_HISTORY_DIR="${CLUTCH_RUN_HISTORY_DIR:-}" \
    CLUTCH_TOOLS_CONFIG="${CLUTCH_TOOLS_CONFIG:-}" \
    CLUTCH_MODELS_CONFIG="${CLUTCH_MODELS_CONFIG:-}" \
    pnpm tauri:e2e) &
  tauri_pid=$!
  disown "$tauri_pid" 2>/dev/null || true
  if ! wait_tauri_ready; then
    kill -9 "$tauri_pid" 2>/dev/null || true
    tauri_pid=""
    exit 1
  fi
  desktop_status=0
  # Tauri-spawned sidecar listens on 8124 (dev); seed/WS helpers must match.
  (cd e2e && env CLUTCH_E2E_SANDBOX="${CLUTCH_E2E_SANDBOX:-}" \
    CLUTCH_E2E_SIDECAR_PORT=8124 \
    pnpm test:desktop) || desktop_status=$?
  # Kill Tauri/Vite/sidecar aggressively — port-only kills can leave Vite daemon hanging the script.
  if [[ -n "${tauri_pid:-}" ]]; then
    kill -9 "$tauri_pid" 2>/dev/null || true
    pkill -9 -P "$tauri_pid" 2>/dev/null || true
  fi
  if [[ -f "$root/.clutch-vite-e2e.pid" ]]; then
    kill -9 "$(cat "$root/.clutch-vite-e2e.pid")" 2>/dev/null || true
    rm -f "$root/.clutch-vite-e2e.pid"
  fi
  pkill -9 -f 'clutch-desktop|tauri.e2e|apps/desktop.*vite' 2>/dev/null || true
  for port in 8123 8124 3000; do
    if lsof -ti "tcp:${port}" >/dev/null 2>&1; then
      lsof -ti "tcp:${port}" | xargs kill -9 2>/dev/null || true
      sleep 0.5
    fi
  done
  tauri_pid=""
  rm -f /tmp/clutch-tauri-playwright.sock 2>/dev/null || true
  if [[ "$desktop_status" -ne 0 ]]; then
    echo "$desktop_status" >"$status_file"
    exit "$desktop_status"
  fi
  echo 0 >"$status_file"
  exit 0
} 2>&1 | tee "$root/$log"
status="$(cat "$status_file" 2>/dev/null || echo "${PIPESTATUS[0]:-1}")"
rm -f "$status_file"
exit "$status"
