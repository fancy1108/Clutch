# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |
| < 0.1   | No        |

While Clutch is `0.x`, security fixes land on `main` and ship with the next semver tag. See [`docs/STABILITY.md`](docs/STABILITY.md).

## Reporting a vulnerability

**Do not report security vulnerabilities through public GitHub Issues**, Discussions, or pull request comments.

### Preferred channel

Use **[GitHub Private Vulnerability Reporting](https://github.com/fancy1108/Clutch/security/advisories/new)** for this repository.

Enable **Private vulnerability reporting** in the repository Settings → Security if it is not already on.

### What to include

- Description and realistic impact (local app, sidecar, workspace files, credentials)
- Steps to reproduce on macOS when possible
- Affected version or commit hash
- Optional: minimal proof-of-concept without weaponized payloads

### What not to include

- API keys, tokens, or contents of `models.json`
- Full session state dumps or `runs/` archives with secrets
- Unrelated personal data from your machine

Redact before sending. See [`.github/ISSUE_TEMPLATE/security_report.md`](.github/ISSUE_TEMPLATE/security_report.md) for the public reminder text.

## Response timeline (best effort)

| Stage | Target |
|-------|--------|
| Acknowledgment | within **7 days** |
| Initial severity assessment | within **14 days** |
| Fix, mitigation, or agreed disclosure plan | depends on severity; critical issues prioritized |

We coordinate public disclosure after a fix is available or an agreed embargo ends. Credit is given when reporters wish to be named.

## Scope notes

**In scope (examples):**

- Remote code execution via Clutch when processing untrusted workflow JSON or MCP payloads
- Sidecar HTTP/WebSocket APIs reachable beyond the Tauri WebView without user intent
- Credential leakage via logs, debug APIs, or crash reports
- Path traversal or workspace escape in filesystem tools

**Out of scope (examples):**

- Issues that require physical access to an unlocked machine with Clutch already running
- Misconfiguration of third-party CLIs (Claude Code, Codex, etc.) outside Clutch
- Vulnerabilities in upstream dependencies without a Clutch-specific exploit path (report upstream; tell us if a Clutch release bundles a fix)

## Known limitations (current release)

Summary only — details in [`docs/OPEN_SOURCE_RELEASE.md`](docs/OPEN_SOURCE_RELEASE.md) §5:

| Topic | Current behavior | Planned |
|-------|------------------|---------|
| Sidecar API / WebSocket | No session token; localhost binding only | **OSR-08** session Bearer + WS `?token=` (Tauri spawn) |
| API key storage | `models.json` on disk, `chmod 600` | OSR-13 Keychain |
| CLI permissions | `--dangerously-skip-permissions` on some adapters | **D30** — documented; not gated (OSR-09) |

Reporting these as **hardening gaps** is welcome; we track them on the OSR roadmap.

### CLI tool permissions (current behavior)

Clutch **defaults to** passing `--dangerously-skip-permissions` to supported local CLIs (e.g. Claude Code, Antigravity) so workflows and Hybrid sessions can run without interactive CLI prompts. This **disables those CLIs' own** tool/write confirmation UI within the authorized workspace.

See [`README.md`](README.md) §安全与 CLI 权限 and decision **D30** in [`memory/DECISIONS.md`](memory/DECISIONS.md). The in-app Permission menu (`ask` / `full`, etc.) governs **Clutch MCP gating** for the built-in agent; it does **not** currently remove this CLI flag.

## Secure development

Contributors: follow [`CLAUDE.md`](CLAUDE.md) — no secrets in commits or logs. Run `./scripts/verify.sh` before PRs that touch application code.
