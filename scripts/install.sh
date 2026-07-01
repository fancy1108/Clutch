#!/usr/bin/env bash
# Install Clutch from GitHub Releases (macOS · Apple Silicon DMG).
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/fancy1108/Clutch/main/scripts/install.sh | bash
#   CLUTCH_VERSION=v1.0.2 ./scripts/install.sh
#
# Options (env):
#   CLUTCH_VERSION   Release tag (default: latest)
#   CLUTCH_INSTALL_DIR  Target dir (default: /Applications)
set -euo pipefail

REPO="${CLUTCH_REPO:-fancy1108/Clutch}"
INSTALL_DIR="${CLUTCH_INSTALL_DIR:-/Applications}"
API="https://api.github.com/repos/${REPO}"

die() {
  echo "error: $*" >&2
  exit 1
}

info() {
  echo "==> $*"
}

if [[ "$(uname -s)" != "Darwin" ]]; then
  die "This installer is for macOS only. Windows: see scripts/install.ps1 or docs/INSTALL.md"
fi

arch="$(uname -m)"
case "$arch" in
  arm64) asset_suffix="_aarch64.dmg" ;;
  x86_64)
    die "No Intel DMG is published yet (latest releases are Apple Silicon aarch64 only). Use docs/BUILD_FROM_SOURCE.md or download from Releases manually."
    ;;
  *) die "Unsupported architecture: $arch" ;;
esac

if ! command -v curl >/dev/null 2>&1; then
  die "curl is required"
fi

resolve_release() {
  if [[ -n "${CLUTCH_VERSION:-}" ]]; then
    echo "${CLUTCH_VERSION#v}"
    return
  fi
  curl -fsSL "${API}/releases/latest" | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"].lstrip("v"))'
}

resolve_asset_name() {
  local version="$1"
  local tag="v${version}"
  curl -fsSL "${API}/releases/tags/${tag}" | python3 -c '
import json, sys
suffix = sys.argv[1]
data = json.load(sys.stdin)
for asset in data.get("assets", []):
    name = asset.get("name", "")
    if name.endswith(suffix) and name.startswith("Clutch_"):
        print(name)
        break
else:
    raise SystemExit(1)
' "$asset_suffix"
}

verify_checksum() {
  local dmg="$1" version="$2" asset_name="$3"
  local sums_url="${API}/releases/tags/v${version}"
  local sums
  sums="$(curl -fsSL "$sums_url" | python3 -c '
import json, sys
data = json.load(sys.stdin)
for asset in data.get("assets", []):
    if asset.get("name") == "SHA256SUMS.txt":
        print(asset["browser_download_url"])
        break
' )" || return 0
  [[ -z "$sums" ]] && return 0
  local expected
  expected="$(curl -fsSL "$sums" | awk -v f="$asset_name" '$2 == f {print $1; exit}')"
  [[ -z "$expected" ]] && return 0
  local actual
  if command -v shasum >/dev/null 2>&1; then
    actual="$(shasum -a 256 "$dmg" | awk '{print $1}')"
  else
    actual="$(openssl dgst -sha256 "$dmg" | awk '{print $NF}')"
  fi
  [[ "$actual" == "$expected" ]] || die "SHA256 mismatch for $asset_name"
  info "Checksum OK"
}

version="$(resolve_release)" || die "Could not resolve release version"
asset_name="$(resolve_asset_name "$version")" || die "No DMG asset matching *${asset_suffix} in v${version}"
download_url="https://github.com/${REPO}/releases/download/v${version}/${asset_name}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
dmg="${tmpdir}/${asset_name}"

info "Clutch v${version} · ${asset_name}"
info "Downloading…"
curl -fL --progress-bar -o "$dmg" "$download_url"
verify_checksum "$dmg" "$version" "$asset_name"

mount_out="$(hdiutil attach -nobrowse -quiet "$dmg")"
mount_point="$(echo "$mount_out" | awk 'END {print $3}')"
[[ -d "$mount_point" ]] || die "Could not mount DMG"

app_src=""
for candidate in "$mount_point/Clutch.app" "$mount_point"/*.app; do
  if [[ -d "$candidate" ]]; then
    app_src="$candidate"
    break
  fi
done
[[ -n "$app_src" ]] || die "Clutch.app not found inside DMG"

dest="${INSTALL_DIR}/Clutch.app"
info "Installing to ${dest}"
if [[ -d "$dest" ]]; then
  rm -rf "$dest"
fi
cp -R "$app_src" "$dest"
hdiutil detach "$mount_point" -quiet || true

xattr -cr "$dest" 2>/dev/null || true

echo ""
info "Installed Clutch v${version} → ${dest}"
echo "    open -a Clutch"
echo ""
echo "Note: unsigned build — if Gatekeeper blocks launch, run:"
echo "    xattr -cr ${dest} && open -a Clutch"
