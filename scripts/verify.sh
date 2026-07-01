#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

pnpm build
pnpm test
(cd services/orchestrator && uv sync --extra dev && uv run pytest)
./scripts/check-doc-drift.sh

# E2E tests are heavy. Run only when explicitly requested.
if [[ "${1:-}" == "--e2e" ]]; then
  ./scripts/run-e2e.sh
elif [[ "${1:-}" == "--e2e-real" ]]; then
  chmod +x ./scripts/run-e2e-real.sh ./scripts/e2e-preflight.sh
  ./scripts/run-e2e-real.sh
fi
