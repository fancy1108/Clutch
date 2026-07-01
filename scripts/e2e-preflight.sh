#!/usr/bin/env bash
# Preflight for real desktop acceptance E2E — fails fast when engines are missing.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
failures=0
warnings=0

ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; warnings=$((warnings + 1)); }
fail() { echo -e "${RED}✗${NC} $*"; failures=$((failures + 1)); }

if [[ ! -f "${root}/e2e/acceptance.config.json" ]]; then
  fail "Missing e2e/acceptance.config.json"
  exit 1
fi

PREFLIGHT_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/clutch-e2e-preflight.XXXXXX")"
export CLUTCH_E2E_ROOT="${PREFLIGHT_ROOT}"
"${root}/scripts/e2e-sandbox-setup.sh" --real "${root}/runs/verification/.e2e-preflight-env" >/dev/null
manifest="${PREFLIGHT_ROOT}/clutch-state/acceptance-manifest.json"

if [[ ! -f "${manifest}" ]]; then
  fail "Bootstrap manifest missing"
  rm -rf "${PREFLIGHT_ROOT}"
  exit 1
fi

eval "$(uv run --directory "${root}/services/orchestrator" python - <<PY
import json
from pathlib import Path
data = json.loads(Path("${manifest}").read_text(encoding="utf-8"))
print(f'text_key_present={1 if data.get("text_key_present") else 0}')
print(f'image_key_present={1 if data.get("image_key_present") else 0}')
print(f'cli_count={len(data.get("cli_tools") or [])}')
skipped = data.get("cli_skipped") or []
for i, line in enumerate(skipped):
    esc = str(line).replace("'", "'\\''")
    print(f"skip_{i}='{esc}'")
PY
)"

if [[ "${text_key_present}" == "1" ]]; then
  ok "Text API key available (env or host models.json)"
else
  fail "Text API key missing — set CLUTCH_E2E_DEEPSEEK_KEY or save DeepSeek key in Clutch Settings"
fi

if [[ "${image_key_present}" == "1" ]]; then
  ok "Image API key available (env or host models.json)"
else
  fail "Image API key missing — set CLUTCH_E2E_AGNES_KEY or save custom provider key in Clutch Settings"
fi

if curl -sf --connect-timeout 2 --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  ok "Ollama daemon reachable"
else
  fail "Ollama not reachable on :11434 — start Ollama for local model tests"
fi

if (( cli_count > 0 )); then
  ok "CLI matrix: ${cli_count} connected+routable tool(s) (agy excluded)"
else
  warn "No connected+routable CLIs found on host — CLI suite will be empty"
fi

while IFS= read -r line; do
  [[ -z "${line}" ]] && continue
  warn "${line}"
done < <(uv run --directory "${root}/services/orchestrator" python - <<PY
import json
from pathlib import Path
data = json.loads(Path("${manifest}").read_text(encoding="utf-8"))
for line in data.get("cli_skipped") or []:
    print(line)
PY
)

rm -rf "${PREFLIGHT_ROOT}"

echo ""
if (( failures > 0 )); then
  echo -e "${RED}Preflight failed (${failures} required check(s)).${NC}"
  exit 1
fi
if (( warnings > 0 )); then
  echo -e "${YELLOW}Preflight passed with ${warnings} warning(s).${NC}"
else
  echo -e "${GREEN}Preflight OK.${NC}"
fi
