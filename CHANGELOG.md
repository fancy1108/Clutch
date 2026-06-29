# Changelog

All notable changes to Clutch are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

**Version policy:** See [`docs/STABILITY.md`](docs/STABILITY.md) for semver and module stability levels.

**Release gate:** A version must have a matching `## [x.y.z]` section here before tagging or publishing a GitHub Release (`scripts/release-preflight.sh` INV-R5). See [`docs/document-governance.md`](docs/document-governance.md) §Release 硬门禁.

**Version snapshots:** Per-release product summaries live in [`docs/releases/`](docs/releases/) (historical); current product truth is [`docs/PRODUCT_INTRO.md`](docs/PRODUCT_INTRO.md).

## [Unreleased]

### Added

- **Release hardening (OSR-16):** Packaged sidecar disables `GET /api/runs/{run_id}/debug` and OpenAPI docs unless `CLUTCH_DEBUG_API=1`; WebView Content-Security-Policy in `tauri.conf.json` (production + `devCsp` for Vite HMR).

### Changed

- **Sidecar distribution (OSR-17):** PyInstaller bundle ships with `console=False` (no terminal window on macOS).

### Added

- Document lifecycle governance: Source of Truth table, event-driven update matrix, and `memory/archive/` rotation with read-only Archive Notice on all archived files.

## [1.0.0] - 2026-06-29

First public release — unsigned macOS DMG via [GitHub Releases](https://github.com/fancy1108/Clutch/releases/tag/v1.0.0). Snapshot: [`docs/releases/v1.0.md`](docs/releases/v1.0.md).

### Added

- **Desktop app (Tauri 2 + React 19):** Multi-agent workflow supervision — visual Flow editor, real-time Chat/Terminal, human approval gates, Files/Changes/Diff panels, session history, and workspace authorization.
- **Hybrid Runtime (D25):** Plain-chat CLI execution via persistent shell sessions (Claude Code and compatible CLIs), session snapshots, and hybrid audit logs.
- **Flow refine:** After a workflow completes or stops, `@Agent` feedback and `/continue` to revise outputs without restarting the full graph.
- **Models & tools:** Provider configuration UI, CC Switch import, Ollama local routing, MCP hub, Skills registry, theme and i18n (EN/ZH) preferences.
- **First-run onboarding wizard (OSR-14):** Seven-step setup — health check, workspace, models, tools, Flow intro, permissions summary, ready.
- **macOS Keychain for API keys (OSR-13):** Provider keys stored in Keychain (`com.clutch.app`); legacy plaintext keys in `models.json` migrated on load (`CLUTCH_USE_KEYCHAIN=0` to opt out).
- **Sidecar session token (OSR-08):** HTTP and WebSocket require a per-launch token from Tauri; `/health` remains public; E2E sandbox bypass documented.
- **Release CI (OSR-12):** Tag-triggered DMG build, gitleaks preflight, `SHA256SUMS.txt`, and `scripts/release-preflight.sh` sensitive-path gates.
- **User & contributor docs:** [`docs/INSTALL.md`](docs/INSTALL.md), [`docs/DATA_AND_PRIVACY.md`](docs/DATA_AND_PRIVACY.md), [`docs/BUILD_FROM_SOURCE.md`](docs/BUILD_FROM_SOURCE.md), [`docs/PRODUCT_INTRO.md`](docs/PRODUCT_INTRO.md), README product screenshots.
- **Community & governance:** MIT [`LICENSE`](LICENSE), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md), GitHub Issue/PR templates, `scripts/doctor.sh`, and open-source boundary docs (`PROJECT_SCOPE`, `STABILITY`, `EXTENSIBILITY`, `GOVERNANCE`, `PERFORMANCE`).
- **Secret scanning (OSR-07):** gitleaks workflow on push/PR.
- **Message compaction (B-03):** Long-session token folding with original messages archived to `runs/archive/{run_id}.jsonl`.

### Changed

- **Semver starting point `1.0.0`** for open source and DMG distribution (D31: unsigned DMG acceptable without Apple Developer account).
- **Default multi-agent mode:** Single/Multi toggle removed from UI; sessions default to multi-agent supervision.
- **CLI permission policy (OSR-09 / D30):** Claude CLI continues to use `--dangerously-skip-permissions` by default; documented in README and SECURITY (disclosure, not runtime gate).
- `experiments/pty_poc/runs/` is local-only (gitignored).

### Security

- Sidecar binds to localhost; session token required for API/WS after app launch.
- API keys prefer macOS Keychain over plaintext `models.json`.
- Release preflight blocks tracked `models.json`, `.env`, and Application Support paths from git.
- High-risk MCP tools require supervisor approval before execution.

### Known limitations (v1.0.0)

- macOS DMG is **not** Apple-notarized (OSR-11 deferred).
