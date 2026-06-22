#!/usr/bin/env bash
# Machine-checkable governance invariants (v1).
# Intent-level drift: use .claude/workflows/truth-alignment.md (on demand).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

errors=0
warns=0

err() {
  echo "ERROR: $*" >&2
  errors=$((errors + 1))
}

warn() {
  echo "WARN:  $*" >&2
  warns=$((warns + 1))
}

ok() {
  echo "OK: $1"
}

# INV-001: Legacy product naming in source (CLAUDE.md §架构红线)
check_legacy_naming() {
  local hits
  hits=$(grep -rEl 'VibeState|Vibe Workspace' \
    apps/desktop/src services/orchestrator/src packages 2>/dev/null || true)
  if [[ -n "$hits" ]]; then
    err "INV-001 legacy naming in source — $hits"
    return
  fi
  ok "INV-001 no legacy product naming in source"
}

# INV-002: Sidecar must use 8123 — flag wrong service ports in orchestrator src
check_sidecar_port() {
  local hits
  hits=$(grep -rEn 'localhost:(8000|3000|8080)' services/orchestrator/src 2>/dev/null || true)
  if [[ -n "$hits" ]]; then
    err "INV-002 unexpected localhost port in orchestrator src — $hits"
    return
  fi
  ok "INV-002 orchestrator src has no wrong localhost ports"
}

# INV-003: mock orchestration setTimeout in App.tsx (tasks.md M0-03)
# Prototype phase: warn. Post-M0: set CLUTCH_STRICT_MOCK=1 in CI to enforce.
check_mock_orchestration() {
  local app="apps/desktop/src/App.tsx"
  if [[ ! -f "$app" ]]; then
    ok "INV-003 App.tsx not found (skip)"
    return
  fi
  if grep -q 'setTimeout' "$app"; then
    if [[ "${CLUTCH_STRICT_MOCK:-}" == "1" ]]; then
      err "INV-003 setTimeout in App.tsx — mock orchestration banned post-M0"
    else
      warn "INV-003 setTimeout in App.tsx (expected until M0-03; set CLUTCH_STRICT_MOCK=1 after)"
    fi
    return
  fi
  ok "INV-003 no setTimeout in App.tsx"
}

# INV-004: Layer 4 playbooks must declare subordination (CLAUDE.md §Layer 4)
check_layer4_headers() {
  local f missing=0
  shopt -s nullglob
  for f in .claude/workflows/*.md; do
    if ! head -5 "$f" | grep -qE 'Layer 4|不扩权'; then
      err "INV-004 missing Layer 4 header in $f"
      missing=1
    fi
  done
  shopt -u nullglob
  if [[ $missing -eq 0 ]]; then
    ok "INV-004 Layer 4 playbook headers present"
  fi
}

main() {
  echo "== check-doc-drift.sh =="
  check_legacy_naming
  check_sidecar_port
  check_mock_orchestration
  check_layer4_headers
  echo "== done: ${errors} error(s), ${warns} warning(s) =="
  [[ "$errors" -eq 0 ]]
}

main
