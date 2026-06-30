#!/usr/bin/env bash
# Merge updater platform entries into latest.json for GitHub Releases (OSR-20).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
json_path="${1:-latest.json}"
platform_key="${2:?platform key e.g. darwin-aarch64}"
bundle_url="${3:?HTTPS URL to updater bundle}"
sig_path="${4:?path to .sig file}"
version="${5:?semver version without v prefix}"

signature="$(tr -d '\n' < "$sig_path")"
pub_date="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

python3 - "$json_path" "$platform_key" "$bundle_url" "$signature" "$version" "$pub_date" <<'PY'
import json
import sys
from pathlib import Path

path, platform_key, bundle_url, signature, version, pub_date = sys.argv[1:7]
doc_path = Path(path)
doc = {}
if doc_path.is_file():
    doc = json.loads(doc_path.read_text(encoding="utf-8"))

doc["version"] = version
doc.setdefault("notes", "")
doc["pub_date"] = pub_date
platforms = doc.setdefault("platforms", {})
platforms[platform_key] = {"url": bundle_url, "signature": signature}

doc_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
print(f"updated {doc_path} -> {platform_key}")
PY
