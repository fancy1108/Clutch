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

# INV-R5: CHANGELOG must document the release version before tagging
tag="${CLUTCH_RELEASE_TAG:-${GITHUB_REF_NAME:-}}"
if [[ -z "$tag" && -n "${1:-}" ]]; then
  tag="$1"
fi
if [[ -n "$tag" ]]; then
  version="${tag#v}"
  changelog="$root/CHANGELOG.md"
  if [[ ! -f "$changelog" ]]; then
    err "INV-R5 missing CHANGELOG.md"
  elif ! grep -qE "^## \\[${version//./\\.}\\]" "$changelog"; then
    err "INV-R5 CHANGELOG.md has no section ## [${version}] — update before tag ${tag}"
  else
    ok "INV-R5 CHANGELOG.md documents version ${version}"
  fi
else
  ok "INV-R5 skipped (set CLUTCH_RELEASE_TAG or pass version as arg to enforce)"
fi

# INV-R6: version consistency across all version-bearing files
if [[ -n "${tag:-}" ]]; then
  version="${tag#v}"
  inv_r6_errors=0

  check_version_file() {
    local label="$1" file="$2" pattern="$3"
    if [[ ! -f "$file" ]]; then
      err "INV-R6 missing $label: $file"
      inv_r6_errors=1
      return 0
    fi
    if grep -qE "$pattern" "$file"; then
      return 0
    fi
    err "INV-R6 $label version mismatch (expected ${version}) in $file"
    inv_r6_errors=1
  }

  check_version_file "root package.json" "$root/package.json" "\"version\": \"${version}\""
  check_version_file "desktop package.json" "$root/apps/desktop/package.json" "\"version\": \"${version}\""
  check_version_file "tauri.conf.json" "$root/apps/desktop/src-tauri/tauri.conf.json" "\"version\": \"${version}\""
  check_version_file "Cargo.toml" "$root/apps/desktop/src-tauri/Cargo.toml" "^version = \"${version}\""
  # Cargo.lock has name + version on adjacent lines — check separately
  if awk '/name = "clutch-desktop"/{getline; if(/version = "'"${version}"'"/){f=1}} END{exit !f}' "$root/apps/desktop/src-tauri/Cargo.lock" 2>/dev/null; then
    ok "INV-R6 Cargo.lock clutch-desktop version ${version}"
  else
    err "INV-R6 Cargo.lock clutch-desktop version mismatch (expected ${version})"
    inv_r6_errors=1
  fi
  check_version_file "README.md" "$root/README.md" "v${version}]"
  check_version_file "README.zh-CN.md" "$root/README.zh-CN.md" "v${version}]"

  # Check that release snapshot exists and index has a row
  if [[ ! -f "$root/docs/releases/v${version}.md" ]]; then
    err "INV-R6 missing release snapshot docs/releases/v${version}.md"
    inv_r6_errors=1
  fi
  if ! grep -q "^| ${version} " "$root/docs/releases/README.md"; then
    err "INV-R6 missing ${version} row in docs/releases/README.md index"
    inv_r6_errors=1
  fi

  if [[ $inv_r6_errors -eq 0 ]]; then
    ok "INV-R6 version ${version} consistent across all files, snapshot + index row present"
  fi
else
  ok "INV-R6 skipped (set CLUTCH_RELEASE_TAG or pass version as arg to enforce)"
fi

if [[ $errors -gt 0 ]]; then
  echo "== release-preflight: $errors error(s) — aborting release ==" >&2
  exit 1
fi

echo "== release-preflight: passed =="
