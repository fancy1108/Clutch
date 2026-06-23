#!/usr/bin/env bash
# E2E Smoke + MVP closed-loop (requires Sidecar on :8123).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

sidecar_pid=""
cleanup() {
  if [[ -n "$sidecar_pid" ]] && kill -0 "$sidecar_pid" 2>/dev/null; then
    kill "$sidecar_pid" 2>/dev/null || true
    wait "$sidecar_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if ! curl -sf http://127.0.0.1:8123/health >/dev/null; then
  (cd services/orchestrator && uv run uvicorn src.main:app --host 127.0.0.1 --port 8123) &
  sidecar_pid=$!
  for _ in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8123/health >/dev/null; then
      break
    fi
    sleep 0.5
  done
  curl -sf http://127.0.0.1:8123/health >/dev/null
fi

mkdir -p runs/verification
log="runs/verification/$(date +%Y-%m-%d)-e2e-smoke.log"
(cd e2e && pnpm test 2>&1 | tee "$root/$log")
