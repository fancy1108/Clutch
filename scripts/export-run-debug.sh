#!/usr/bin/env bash
# Layer 4 操作剧本 · 不扩权。铁律见 CLAUDE.md；决策见 memory/DECISIONS.md。
# 导出单个 run 的 Hybrid 诊断摘要（HRT-07）；不含密钥。
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: export-run-debug.sh RUN_ID [--base-url URL] [--out PATH]

Fetch GET /api/runs/{run_id}/debug from the Sidecar and print or save JSON.
Requires Sidecar on localhost:8123 (or --base-url).

Examples:
  ./scripts/export-run-debug.sh run_abc123
  ./scripts/export-run-debug.sh run_abc123 --out runs/verification/run_abc123-debug.json
EOF
}

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 1
fi

run_id="$1"
shift
base_url="http://127.0.0.1:8123"
out_path=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      base_url="${2:?missing value for --base-url}"
      shift 2
      ;;
    --out)
      out_path="${2:?missing value for --out}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! [[ "$run_id" =~ ^[a-zA-Z0-9_-]{1,128}$ ]]; then
  echo "Invalid run_id: $run_id" >&2
  exit 1
fi

base_url="${base_url%/}"
url="${base_url}/api/runs/${run_id}/debug?logs_limit=20&audit_limit=50"

if ! curl -sf "$url" -o /tmp/clutch-export-debug.json; then
  echo "Failed to fetch $url (is Sidecar running?)" >&2
  exit 1
fi

if [[ -n "$out_path" ]]; then
  mkdir -p "$(dirname "$out_path")"
  python3 -m json.tool /tmp/clutch-export-debug.json >"$out_path"
  echo "Wrote $out_path"
else
  python3 -m json.tool /tmp/clutch-export-debug.json
fi
