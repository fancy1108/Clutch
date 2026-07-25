#!/usr/bin/env bash
# D52 — PRODUCT_INTRO must keep a Capability → Chat UI table (release / complete gate).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
doc="$root/docs/PRODUCT_INTRO.md"

if [[ ! -f "$doc" ]]; then
  echo "ERROR: missing $doc" >&2
  exit 1
fi

if ! grep -q 'capability-ui-table:start' "$doc"; then
  echo "ERROR: D52 marker capability-ui-table:start missing in PRODUCT_INTRO.md" >&2
  exit 1
fi
if ! grep -q 'capability-ui-table:end' "$doc"; then
  echo "ERROR: D52 marker capability-ui-table:end missing in PRODUCT_INTRO.md" >&2
  exit 1
fi

# Required spot-check rows (capability plan: D1 / D10 / D37 at minimum).
required=(
  '| D1 '
  '| D10 '
  '| D37 '
  '| D46 '
  '| D51 '
)

missing=0
for row in "${required[@]}"; do
  if ! grep -qF "$row" "$doc"; then
    echo "ERROR: D52 capability table missing row matching: $row" >&2
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

echo "OK: D52 Capability → Chat UI table present (D1/D10/D37/D46/D51)"
