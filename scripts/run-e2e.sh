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
  if [[ -n "${tauri_pid:-}" ]] && kill -0 "$tauri_pid" 2>/dev/null; then
    kill "$tauri_pid" 2>/dev/null || true
    wait "$tauri_pid" 2>/dev/null || true
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

for port in 8123 3000; do
  if lsof -ti "tcp:${port}" >/dev/null 2>&1; then
    lsof -ti "tcp:${port}" | xargs kill -9 2>/dev/null || true
    sleep 0.5
  fi
done

mkdir -p runs/verification
log="runs/verification/$(date +%Y-%m-%d)-e2e-full.log"

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
  for _ in $(seq 1 180); do
    if curl -sf http://127.0.0.1:3000 >/dev/null 2>&1 \
      && curl -sf http://127.0.0.1:8123/health >/dev/null \
      && [[ -S /tmp/clutch-tauri-playwright.sock ]]; then
      return 0
    fi
    sleep 1
  done
  echo "Tauri app + sidecar + playwright socket not ready" >&2
  return 1
}

{
  echo "=== API E2E ==="
  (cd services/orchestrator && env CLUTCH_E2E_FAKE_LLM="${CLUTCH_E2E_FAKE_LLM:-}" \
    CLUTCH_E2E_SANDBOX="${CLUTCH_E2E_SANDBOX:-}" \
    CLUTCH_WORKSPACES_FILE="${CLUTCH_WORKSPACES_FILE:-}" \
    CLUTCH_RUN_HISTORY_DIR="${CLUTCH_RUN_HISTORY_DIR:-}" \
    CLUTCH_TOOLS_CONFIG="${CLUTCH_TOOLS_CONFIG:-}" \
    CLUTCH_MODELS_CONFIG="${CLUTCH_MODELS_CONFIG:-}" \
    uv run uvicorn src.main:app --host 127.0.0.1 --port 8123) &
  sidecar_pid=$!
  wait_sidecar
  (cd e2e && env CLUTCH_E2E_SANDBOX="${CLUTCH_E2E_SANDBOX:-}" pnpm test:api)

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
  (cd apps/desktop && env CLUTCH_E2E_SANDBOX="${CLUTCH_E2E_SANDBOX:-}" \
    CLUTCH_E2E_FAKE_LLM="${CLUTCH_E2E_FAKE_LLM:-}" \
    CLUTCH_WORKSPACES_FILE="${CLUTCH_WORKSPACES_FILE:-}" \
    CLUTCH_RUN_HISTORY_DIR="${CLUTCH_RUN_HISTORY_DIR:-}" \
    CLUTCH_TOOLS_CONFIG="${CLUTCH_TOOLS_CONFIG:-}" \
    CLUTCH_MODELS_CONFIG="${CLUTCH_MODELS_CONFIG:-}" \
    pnpm tauri:e2e) &
  tauri_pid=$!
  wait_tauri_ready
  (cd e2e && env CLUTCH_E2E_SANDBOX="${CLUTCH_E2E_SANDBOX:-}" pnpm test:desktop)
} 2>&1 | tee "$root/$log"
