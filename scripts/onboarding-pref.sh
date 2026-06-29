#!/usr/bin/env bash
# Toggle onboarding_completed in Sidecar preferences (dev/prod storage via storage_helper).
# Usage: ./scripts/onboarding-pref.sh reset|complete|status
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
action="${1:-}"

if [[ "$action" != "reset" && "$action" != "complete" && "$action" != "status" ]]; then
  echo "Usage: $0 reset|complete|status" >&2
  exit 1
fi

cd "$root/services/orchestrator"
uv run python - "$action" <<'PY'
import sys
from src.preferences_storage import (
    is_onboarding_completed,
    preferences_dir,
    reset_onboarding_completed,
    save_onboarding_completed,
)

action = sys.argv[1]
if action == "reset":
    reset_onboarding_completed()
elif action == "complete":
    save_onboarding_completed()
done = is_onboarding_completed()
print(f"onboarding_completed={'true' if done else 'false'}  ({preferences_dir() / 'preferences.json'})")
PY
