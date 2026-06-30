#!/usr/bin/env bash
# Compatibility wrapper for the cross-platform Python builder.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
orch="$root/services/orchestrator"
exec uv run --project "$orch" python "$root/scripts/build-sidecar.py"
