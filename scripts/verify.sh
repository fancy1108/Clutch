#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

pnpm build
(cd services/orchestrator && uv run pytest)
./scripts/check-doc-drift.sh
