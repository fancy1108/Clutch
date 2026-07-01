#!/usr/bin/env bash
# Real desktop acceptance E2E — genuine CLI / API / Flow (no fake LLM).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

chmod +x scripts/e2e-preflight.sh scripts/e2e-sandbox-setup.sh
./scripts/e2e-preflight.sh

E2E_ROOT="$(./scripts/e2e-sandbox-setup.sh --real)"
# shellcheck disable=SC1091
source runs/verification/.e2e-env

export CLUTCH_RUNTIME_MODE="${CLUTCH_RUNTIME_MODE:-hybrid}"

sidecar_pid=""
tauri_pid=""
vite_pid=""

# Belt-and-suspenders: pnpm/tauri spawn clutch-desktop + uvicorn children that survive kill $tauri_pid.
e2e_kill_stacks() {
  "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/e2e-teardown.sh" >/dev/null
}

cleanup() {
  if [[ -n "${tauri_pid:-}" ]]; then
    kill -9 "$tauri_pid" 2>/dev/null || true
    tauri_pid=""
  fi
  if [[ -n "${vite_pid:-}" ]] && kill -0 "$vite_pid" 2>/dev/null; then
    kill -9 "$vite_pid" 2>/dev/null || true
    wait "$vite_pid" 2>/dev/null || true
    vite_pid=""
  fi
  if [[ -n "${sidecar_pid:-}" ]] && kill -0 "$sidecar_pid" 2>/dev/null; then
    kill -9 "$sidecar_pid" 2>/dev/null || true
    wait "$sidecar_pid" 2>/dev/null || true
  fi
  e2e_kill_stacks
  if [[ -n "${E2E_ROOT:-}" && -d "${E2E_ROOT}" && "${E2E_ROOT}" == *"clutch-e2e"* ]]; then
    rm -rf "${E2E_ROOT}"
  fi
}
trap cleanup EXIT

for port in 8124 8123 3000; do
  if lsof -ti "tcp:${port}" >/dev/null 2>&1; then
    lsof -ti "tcp:${port}" | xargs kill -9 2>/dev/null || true
    sleep 0.5
  fi
done

mkdir -p runs/verification
log="runs/verification/$(date +%Y-%m-%d)-e2e-real.log"

wait_vite() {
  for _ in $(seq 1 60); do
    if curl -sf http://127.0.0.1:3000 >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  echo "Vite dev server not ready on :3000" >&2
  return 1
}

wait_tauri_ready() {
  local boot_ms="${CLUTCH_E2E_TAURI_BOOT_MS:-120000}"
  local attempts=$((boot_ms / 1000))
  for _ in $(seq 1 "$attempts"); do
    if curl -sf http://127.0.0.1:3000 >/dev/null 2>&1 \
      && curl -sf "http://127.0.0.1:${CLUTCH_E2E_SIDECAR_PORT:-8124}/health" >/dev/null \
      && [[ -S /tmp/clutch-tauri-playwright.sock ]]; then
      return 0
    fi
    sleep 1
  done
  echo "Tauri app + sidecar + playwright socket not ready (${boot_ms}ms)" >&2
  return 1
}

{
  echo "=== Real Desktop Acceptance E2E ==="
  (cd e2e && pnpm exec playwright install chromium)

  (cd apps/desktop && pnpm dev) &
  vite_pid=$!
  wait_vite

  set +e
  (cd apps/desktop && env CLUTCH_E2E_SANDBOX="${CLUTCH_E2E_SANDBOX:-}" \
    CLUTCH_E2E_REAL=1 \
    CLUTCH_RUNTIME_MODE="${CLUTCH_RUNTIME_MODE}" \
    CLUTCH_WORKSPACES_FILE="${CLUTCH_WORKSPACES_FILE:-}" \
    CLUTCH_RUN_HISTORY_DIR="${CLUTCH_RUN_HISTORY_DIR:-}" \
    CLUTCH_TOOLS_CONFIG="${CLUTCH_TOOLS_CONFIG:-}" \
    CLUTCH_MODELS_CONFIG="${CLUTCH_MODELS_CONFIG:-}" \
    CLUTCH_AGENTS_DIR="${CLUTCH_AGENTS_DIR:-}" \
    CLUTCH_STORAGE_DIR="${CLUTCH_STORAGE_DIR:-}" \
    CLUTCH_USER_WORKFLOWS_DIR="${CLUTCH_USER_WORKFLOWS_DIR:-}" \
    pnpm tauri:e2e) &
  tauri_pid=$!
  wait_tauri_ready
  desktop_status=0
  (cd e2e && env CLUTCH_E2E_SANDBOX="${CLUTCH_E2E_SANDBOX:-}" \
    CLUTCH_E2E_SIDECAR_PORT="${CLUTCH_E2E_SIDECAR_PORT:-8124}" \
    CLUTCH_E2E_ACCEPTANCE_MANIFEST="${CLUTCH_E2E_ACCEPTANCE_MANIFEST:-}" \
    pnpm exec playwright test -c playwright.acceptance.config.ts --project=desktop tests/desktop/acceptance.spec.ts) || desktop_status=$?

  exit "$desktop_status"
} 2>&1 | tee "$root/$log"
exit "${PIPESTATUS[0]:-0}"
