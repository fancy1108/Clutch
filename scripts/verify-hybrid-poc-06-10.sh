#!/usr/bin/env bash
# Layer 4 操作剧本 · 不扩权。铁律见 CLAUDE.md；决策见 memory/DECISIONS.md。
# Run automated POC acceptance #6 and #10 (HRT-10).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root/services/orchestrator"
exec uv run pytest tests/test_hybrid_poc_acceptance.py -v "$@"
