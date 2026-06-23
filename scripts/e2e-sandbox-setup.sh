#!/usr/bin/env bash
# Create isolated E2E sandbox — never touches user projects or Application Support.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
E2E_ROOT="${CLUTCH_E2E_ROOT:-$(mktemp -d "${TMPDIR:-/tmp}/clutch-e2e.XXXXXX")}"
SANDBOX="${E2E_ROOT}/sandbox-project"
STATE="${E2E_ROOT}/clutch-state"

mkdir -p "${SANDBOX}/src" "${STATE}"
# Intentionally omit docs/verify.md for MVP check-fail scenario.
cat > "${SANDBOX}/package.json" <<'EOF'
{
  "name": "clutch-e2e-sandbox",
  "private": true,
  "scripts": {
    "lint": "node -e \"process.exit(0)\""
  }
}
EOF
echo "# Clutch E2E sandbox — safe to delete" > "${SANDBOX}/README.md"
mkdir -p "${SANDBOX}/.clutch-skills"
printf '%s\n' '---' 'name: e2e-skill' '---' '# E2E skill fixture' > "${SANDBOX}/.clutch-skills/e2e-skill.md"

ENV_FILE="${1:-${root}/runs/verification/.e2e-env}"
mkdir -p "$(dirname "${ENV_FILE}")"
cat > "${ENV_FILE}" <<EOF
export CLUTCH_E2E_ROOT='${E2E_ROOT}'
export CLUTCH_E2E_SANDBOX='${SANDBOX}'
export CLUTCH_WORKSPACES_FILE='${STATE}/workspaces.json'
export CLUTCH_RUN_HISTORY_DIR='${STATE}/sessions'
export CLUTCH_TOOLS_CONFIG='${STATE}/tools.json'
export CLUTCH_E2E_FAKE_LLM='1'
export CLUTCH_MODELS_CONFIG='${STATE}/models.json'
EOF

echo "${E2E_ROOT}"
