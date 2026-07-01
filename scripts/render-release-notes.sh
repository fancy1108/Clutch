#!/usr/bin/env bash
# Assemble GitHub Release body: CHANGELOG section first, then install/upgrade fragments.
# Usage: ./scripts/render-release-notes.sh v1.0.3 [-o path.md]
# Exits non-zero if CHANGELOG has no ## [x.y.z] section (INV-R5 alignment).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
changelog="${root}/CHANGELOG.md"
fragments="${root}/.github/release-notes"
output=""

usage() {
  echo "Usage: $0 <version-tag> [-o output.md]" >&2
  echo "  version-tag: v1.0.3 or 1.0.3" >&2
  exit 2
}

tag="${1:-}"
[[ -n "$tag" ]] || usage
shift || true

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o)
      [[ $# -ge 2 ]] || usage
      output="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      ;;
  esac
done

version="${tag#v}"
version_escaped="${version//./\\.}"

if [[ ! -f "$changelog" ]]; then
  echo "ERROR: missing CHANGELOG.md" >&2
  exit 1
fi

if ! grep -qE "^## \\[${version_escaped}\\]" "$changelog"; then
  echo "ERROR: CHANGELOG.md has no section ## [${version}] (INV-R5)" >&2
  exit 1
fi

read_fragment() {
  local name="$1"
  local path="${fragments}/${name}.md"
  if [[ ! -f "$path" ]]; then
    echo "ERROR: missing fragment ${path}" >&2
    exit 1
  fi
  cat "$path"
}

tagline=""
changelog_body=""
in_section=0
content=0

while IFS= read -r line || [[ -n "$line" ]]; do
  if [[ "$line" =~ ^##\ \[ ]]; then
    if [[ $in_section -eq 1 ]]; then
      break
    fi
    if [[ "$line" =~ ^##\ \[${version}\] ]]; then
      in_section=1
      continue
    fi
  fi

  if [[ $in_section -eq 0 ]]; then
    continue
  fi

  if [[ "$line" =~ ^###\  ]]; then
    content=1
    changelog_body+="${line}"$'\n'
    continue
  fi

  if [[ $content -eq 1 ]]; then
    changelog_body+="${line}"$'\n'
    continue
  fi

  if [[ "$line" =~ ^\> ]]; then
    continue
  fi

  if [[ -z "${line//[[:space:]]/}" ]]; then
    continue
  fi

  if [[ -z "$tagline" ]]; then
    tagline="$line"
  fi
done < "$changelog"

if [[ -z "$changelog_body" ]]; then
  echo "ERROR: CHANGELOG section ## [${version}] has no ### subsections" >&2
  exit 1
fi

render() {
  echo "## What's in this release"
  echo
  if [[ -n "$tagline" ]]; then
    echo "$tagline"
    echo
  fi
  printf '%s' "$changelog_body"
  if [[ "$changelog_body" != *$'\n' ]]; then
    echo
  fi
  echo
  echo "---"
  echo
  echo "## Install"
  echo
  read_fragment install
  echo
  echo "## Upgrade"
  echo
  read_fragment upgrade
  echo
  echo "## macOS: first launch (unsigned app)"
  echo
  read_fragment macos-first-launch
  echo
  echo "## Windows"
  echo
  read_fragment windows
  echo
  echo "## Verify download"
  echo
  read_fragment verify-download
}

if [[ -n "$output" ]]; then
  render > "$output"
  echo "Wrote release notes to ${output}"
else
  render
fi
