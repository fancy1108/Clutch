#!/usr/bin/env bash
# Release gate: block DMG builds if secrets or user-runtime data paths are in git.
# OSR-12 · see docs/OPEN_SOURCE_RELEASE.md §4.2.2
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

errors=0

err() {
  echo "ERROR: $*" >&2
  errors=$((errors + 1))
}

ok() {
  echo "OK: $1"
}

# INV-R1: tracked credential / env files
while IFS= read -r f; do
  case "$f" in
    .env.example) continue ;;
    *) err "INV-R1 tracked env file: $f" ;;
  esac
done < <(git ls-files '.env' '.env.*' 2>/dev/null || true)

if git ls-files | grep -qE '(^|/)models\.json$'; then
  err "INV-R1 models.json must not be tracked (API keys belong in Application Support only)"
else
  ok "INV-R1 no tracked models.json"
fi

# INV-R2: machine-local runtime trees must not be in git
if git ls-files | grep -qiE 'application support|/clutch_dev/'; then
  err "INV-R2 Application Support / clutch_dev path in tracked files"
else
  ok "INV-R2 no Application Support paths in git"
fi

# INV-R3: sidecar bundle inputs are repo templates only
wf_dir="$root/workflows"
if [[ ! -d "$wf_dir" ]]; then
  err "INV-R3 missing workflows/ directory"
else
  wf_count=0
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    wf_count=$((wf_count + 1))
    if [[ $wf_count -eq 1 ]]; then
      ok "INV-R3 bundle will ship repo workflow template(s):"
    fi
    echo "      $(basename "$f")"
  done < <(find "$wf_dir" -maxdepth 1 -name '*.json' -type f | sort)
  if [[ $wf_count -eq 0 ]]; then
    err "INV-R3 no workflow templates under workflows/"
  fi
fi

# INV-R4: PyInstaller must not pick up ad-hoc workflow_assets leftovers
assets="$root/services/orchestrator/src/workflow_assets"
if [[ -d "$assets" ]]; then
  for f in "$assets"/*.json; do
    [[ -e "$f" ]] || continue
    base="$(basename "$f")"
    if [[ ! -f "$wf_dir/$base" ]]; then
      err "INV-R4 stray workflow_assets/$base (not in workflows/ — run build-sidecar clean)"
    fi
  done
fi
ok "INV-R4 workflow_assets consistent with workflows/ (or empty before build)"

if [[ $errors -gt 0 ]]; then
  echo "== release-preflight: $errors error(s) — aborting release ==" >&2
  exit 1
fi

echo "== release-preflight: passed =="
