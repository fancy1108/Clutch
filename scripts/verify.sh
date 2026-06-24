#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

pnpm build
pnpm test
(cd services/orchestrator && uv run pytest)
./scripts/check-doc-drift.sh

# E2E tests are heavy. Run them only if --e2e flag is provided.
if [[ "${1:-}" == "--e2e" ]]; then
  ./scripts/run-e2e.sh
fi
