#!/usr/bin/env bash
# Bump fancy1108/homebrew-clutch after a GitHub Release (macOS aarch64 DMG).
# Usage: CLUTCH_VERSION=v1.0.2 ./scripts/sync-homebrew-tap.sh
# Requires: gh, git, shasum; tap cloned at ../homebrew-clutch (or set HOMEBREW_TAP_DIR)
set -euo pipefail

REPO="${CLUTCH_REPO:-fancy1108/Clutch}"
TAP_REPO="${HOMEBREW_TAP_REPO:-fancy1108/homebrew-clutch}"
TAP_DIR="${HOMEBREW_TAP_DIR:-$(cd "$(dirname "$0")/../.." && pwd)/homebrew-clutch}"

version="${CLUTCH_VERSION:-}"
if [[ -z "$version" ]]; then
  version="$(gh release view --repo "$REPO" --json tagName -q .tagName)"
fi
version="${version#v}"
asset="Clutch_${version//./_}_aarch64.dmg"

sums="$(gh release download "v${version}" --repo "$REPO" --pattern SHA256SUMS.txt -O -)"
sha256="$(echo "$sums" | awk -v f="$asset" '$2 == f {print $1; exit}')"
[[ -n "$sha256" ]] || { echo "SHA256 not found for $asset" >&2; exit 1; }

if [[ ! -d "$TAP_DIR/.git" ]]; then
  echo "Cloning tap to $TAP_DIR"
  git clone "https://github.com/${TAP_REPO}.git" "$TAP_DIR"
fi

cask="$TAP_DIR/Casks/clutch.rb"
ruby - "$cask" "$version" "$sha256" <<'RUBY'
path, ver, sha = ARGV
text = File.read(path)
text.sub!(/version "[^"]+"/, %(version "#{ver}"))
text.sub!(/sha256 "[^"]+"/, %(sha256 "#{sha}"))
File.write(path, text)
RUBY

cd "$TAP_DIR"
git add Casks/clutch.rb
if git diff --staged --quiet; then
  echo "Tap already at v${version}"
  exit 0
fi
git commit -m "chore(cask): bump Clutch to ${version}"
git push origin HEAD
echo "==> Updated ${TAP_REPO} to v${version}"
