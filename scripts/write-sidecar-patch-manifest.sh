#!/usr/bin/env bash
# Write sidecar-patch.json for GitHub Releases (D37 hotpatch).
# Usage:
#   ./scripts/write-sidecar-patch-manifest.sh sidecar-patch.json \
#     2026.07.11.1 1.2.1 darwin-aarch64 \
#     https://github.com/fancy1108/Clutch/releases/download/v1.2.1/orchestrator-darwin-aarch64 \
#     path/to/orchestrator
set -euo pipefail

json_path="${1:?output path e.g. sidecar-patch.json}"
patch_id="${2:?patch_id e.g. 2026.07.11.1}"
min_app_version="${3:?min_app_version e.g. 1.2.1}"
platform_key="${4:?platform key e.g. darwin-aarch64}"
bundle_url="${5:?HTTPS URL to orchestrator binary}"
binary_path="${6:?local path to binary for sha256}"

if [[ ! -f "$binary_path" ]]; then
  echo "binary not found: $binary_path" >&2
  exit 1
fi

sha256="$(shasum -a 256 "$binary_path" | awk '{print $1}')"

python3 - "$json_path" "$patch_id" "$min_app_version" "$platform_key" "$bundle_url" "$sha256" <<'PY'
import json
import sys
from pathlib import Path

path, patch_id, min_app, platform_key, url, sha256 = sys.argv[1:7]
doc_path = Path(path)
doc = {}
if doc_path.is_file():
    doc = json.loads(doc_path.read_text(encoding="utf-8"))

doc["patch_id"] = patch_id
doc["min_app_version"] = min_app
doc.setdefault("severity", "normal")
doc.setdefault("notes", "")
platforms = doc.setdefault("platforms", {})
platforms[platform_key] = {"url": url, "sha256": sha256}

doc_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
print(f"updated {doc_path} -> {platform_key} sha256={sha256[:12]}…")
PY
