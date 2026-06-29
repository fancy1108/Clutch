#!/usr/bin/env bash
# Create isolated E2E sandbox — never touches user projects or Application Support.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
E2E_ROOT="${CLUTCH_E2E_ROOT:-$(mktemp -d "${TMPDIR:-/tmp}/clutch-e2e.XXXXXX")}"
SANDBOX="${E2E_ROOT}/sandbox-project"
STATE="${E2E_ROOT}/clutch-state"

mkdir -p "${SANDBOX}/src" "${STATE}" "${STATE}/storage" "${STATE}/agents" "${STATE}/storage/preferences"
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

# Git repo so footer branch menu and /api/workspace/git E2E reflect real branches.
if command -v git >/dev/null 2>&1; then
  if git -C "${SANDBOX}" init -b main >/dev/null 2>&1; then
    :
  else
    git -C "${SANDBOX}" init >/dev/null 2>&1
    git -C "${SANDBOX}" checkout -b main >/dev/null 2>&1 || true
  fi
  git -C "${SANDBOX}" config user.email "e2e@clutch.local"
  git -C "${SANDBOX}" config user.name "Clutch E2E"
  git -C "${SANDBOX}" add .
  git -C "${SANDBOX}" -c commit.gpgsign=false commit -m "e2e sandbox seed" >/dev/null 2>&1 || true
fi

ENV_FILE="${1:-${root}/runs/verification/.e2e-env}"
mkdir -p "$(dirname "${ENV_FILE}")"
cat > "${ENV_FILE}" <<EOF
export CLUTCH_E2E_ROOT='${E2E_ROOT}'
export CLUTCH_E2E_SANDBOX='${SANDBOX}'
export CLUTCH_WORKSPACES_FILE='${STATE}/workspaces.json'
export CLUTCH_RUN_HISTORY_DIR='${STATE}/sessions'
export CLUTCH_TOOLS_CONFIG='${STATE}/tools.json'
export CLUTCH_STORAGE_DIR='${STATE}/storage'
export CLUTCH_AGENTS_DIR='${STATE}/agents'
export CLUTCH_E2E_FAKE_LLM='1'
export CLUTCH_E2E_SKIP_ONBOARDING='1'
export CLUTCH_MODELS_CONFIG='${STATE}/models.json'
EOF

cat > "${STATE}/storage/preferences/preferences.json" <<'EOF'
{
  "active_theme_id": "pristine-light",
  "active_language": "en",
  "permission_mode": "ask",
  "user_avatar": "",
  "user_name": "User",
  "onboarding_completed": "true"
}
EOF

cat > "${STATE}/tools.json" <<'EOF'
{
  "connected": ["claude-cli"]
}
EOF

cat > "${STATE}/agents/agents.json" <<'EOF'
[
  {
    "id": "agent-e2e-hybrid",
    "name": "Claude E2E Hybrid",
    "description": "E2E hybrid plain-chat agent",
    "markdownDoc": "# Claude E2E Hybrid\n\n## Protocol\n- Reply concisely for automated tests.\n",
    "lastModified": "e2e",
    "avatar": "",
    "deliverables": [],
    "mcpTools": [],
    "mcpServerIds": [],
    "agentType": "claude-cli",
    "aiEngine": "Claude Code (Local CLI)",
    "skills": []
  }
]
EOF

echo "${E2E_ROOT}"
