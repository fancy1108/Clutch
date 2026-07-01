#!/usr/bin/env bash
# Clutch environment doctor — checks toolchain and platform for local dev / DMG smoke.
# Exit 0 = all required checks pass; non-zero = at least one required failure.
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

required_fail=0
optional_fail=0

ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; optional_fail=$((optional_fail + 1)); }
fail() { echo -e "${RED}✗${NC} $*"; required_fail=$((required_fail + 1)); }

version_ge() {
  # version_ge <current> <minimum>  (semver numeric segments)
  local IFS=.
  local i cur=($1) min=($2)
  for ((i=0; i<${#min[@]}; i++)); do
    local c=${cur[i]:-0}
    local m=${min[i]:-0}
    if ((10#$c > 10#$m)); then return 0; fi
    if ((10#$c < 10#$m)); then return 1; fi
  done
  return 0
}

echo "== Clutch doctor =="
echo "Repo: $root"
echo ""

# --- Platform ---
echo "-- Platform --"
case "$(uname -s)" in
  Darwin)
    ok "OS: macOS ($(sw_vers -productVersion 2>/dev/null || uname -r))"
  if [[ "$(uname -m)" == "arm64" ]]; then
      ok "Arch: Apple Silicon (arm64) — primary target"
    else
      warn "Arch: Intel (x86_64) — Clutch does not ship Intel DMG; Apple Silicon only (source build optional)"
    fi
    ;;
  Linux)
    warn "OS: Linux — desktop packaging not officially supported yet"
    ;;
  MINGW*|MSYS*|CYGWIN*)
    warn "OS: Windows — MSI not officially supported yet"
    ;;
  *)
    warn "OS: $(uname -s) — unknown support level"
    ;;
esac
echo ""

# --- Toolchain (required for from-source dev) ---
echo "-- Required (from-source development) --"

if command -v node >/dev/null 2>&1; then
  nv=$(node -p "process.versions.node")
  if version_ge "$nv" "20.0.0"; then
    ok "Node.js $nv (need >= 20)"
  else
    fail "Node.js $nv — need >= 20 (see package.json engines)"
  fi
else
  fail "Node.js not found"
fi

if command -v pnpm >/dev/null 2>&1; then
  ok "pnpm in PATH (need >= 9 — see package.json engines)"
else
  fail "pnpm not found — corepack enable && corepack prepare pnpm@9.15.0 --activate"
fi

python_version() {
  if [[ -x "$root/services/orchestrator/.venv/bin/python" ]]; then
    "$root/services/orchestrator/.venv/bin/python" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))'
  elif command -v uv >/dev/null 2>&1; then
    (cd "$root/services/orchestrator" && uv run python -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
  elif command -v python3 >/dev/null 2>&1; then
    python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))'
  else
    echo ""
  fi
}

if pyv=$(python_version); [[ -n "$pyv" ]]; then
  if version_ge "$pyv" "3.11.0"; then
    ok "Python $pyv (need >= 3.11)"
  else
    fail "Python $pyv — need >= 3.11 (use uv sync in services/orchestrator)"
  fi
else
  fail "python3 not found — install Python 3.11+ or run: cd services/orchestrator && uv sync --extra dev"
fi

if command -v uv >/dev/null 2>&1; then
  uvv=$(uv --version 2>/dev/null | awk '{print $2}')
  ok "uv ${uvv:-unknown}"
else
  fail "uv not found — https://docs.astral.sh/uv/"
fi

echo ""
echo "-- Optional (Tauri DMG build) --"

if command -v rustc >/dev/null 2>&1; then
  rv=$(rustc --version | awk '{print $2}')
  ok "Rust $rv"
else
  warn "rustc not found — required for pnpm tauri build"
fi

if command -v cargo >/dev/null 2>&1; then
  ok "cargo $(cargo --version | awk '{print $2}')"
else
  warn "cargo not found"
fi

echo ""
echo "-- Dependencies --"

if [[ -d "$root/node_modules" ]]; then
  ok "node_modules present (run pnpm install if missing)"
else
  warn "node_modules missing — run: pnpm install"
fi

if [[ -d "$root/services/orchestrator/.venv" ]]; then
  ok "services/orchestrator/.venv present"
else
  warn "Orchestrator .venv missing — run: cd services/orchestrator && uv sync --extra dev"
fi

echo ""
echo "-- Sidecar smoke (optional) --"

check_sidecar() {
  local port=$1 label=$2
  if curl -sf --connect-timeout 1 --max-time 2 "http://127.0.0.1:${port}/health" >/dev/null 2>&1; then
    ok "Sidecar health on :${port} (${label})"
    return 0
  fi
  return 1
}

if ! check_sidecar 8124 "dev" && ! check_sidecar 8123 "prod/DMG"; then
  warn "No sidecar on 8124 or 8123 — start dev: cd services/orchestrator && uv run uvicorn src.main:app --reload --port 8124"
fi

echo ""
echo "== Summary =="
if (( required_fail > 0 )); then
  echo -e "${RED}Required checks failed: ${required_fail}${NC}"
  echo "Fix required items before from-source development."
  exit 1
fi

if (( optional_fail > 0 )); then
  echo -e "${YELLOW}Optional warnings: ${optional_fail}${NC}"
fi

echo -e "${GREEN}Required toolchain OK.${NC}"
echo "Next: pnpm install && see CLAUDE.md §核心命令"
exit 0
