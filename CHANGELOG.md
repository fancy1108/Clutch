# Changelog

All notable changes to Clutch are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

**Version policy:** See [`docs/STABILITY.md`](docs/STABILITY.md) for semver and module stability levels.

**Release gate:** A version must have a matching `## [x.y.z]` section here before tagging or publishing a GitHub Release (`scripts/release-preflight.sh` INV-R5). See [`docs/document-governance.md`](docs/document-governance.md) §Release 硬门禁.

**Version snapshots:** Per-release product summaries live in [`docs/releases/`](docs/releases/) (historical); current product truth is [`docs/PRODUCT_INTRO.md`](docs/PRODUCT_INTRO.md).

## [Unreleased]

### Fixed

- **Settings → Models Config (Ollama):** Model list now reflects **locally installed** `ollama list` tags (same source as Create Agent), instead of always showing built-in catalog entries like `qwen2.5vl:7b` that are not on the machine (`models_config.py`). Persisted `active_model_id` from another Mac auto-falls back to the first installed local tag.

### Changed

- **README & onboarding docs:** Bilingual README (`README.md` / `README.zh-CN.md`), new **[`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md)** beginner guide (linked prominently from README and `docs/README.md`). Windows installers marked **not yet verified** on physical hardware ([#23](https://github.com/fancy1108/Clutch/issues/23)).
- **CLI installers:** `scripts/install.sh` (macOS aarch64 DMG) and `scripts/install.ps1` (Windows NSIS) — documented in README / `INSTALL.md` (not `npm install`; desktop app).
- **Package managers:** Homebrew tap [fancy1108/homebrew-clutch](https://github.com/fancy1108/homebrew-clutch) live; `scripts/sync-homebrew-tap.sh` bumps cask on release. winget deferred until #23.
- **Intel Mac:** **Not supported** for packaged DMG (Apple Silicon only); documented in `PACKAGE_MANAGERS.md` · `DECISIONS` D32.
- **CLI error copy (#19):** Hybrid → legacy fallback no longer double-prefixes「通过 … CLI 执行任务失败」; 529 / 5xx gateway errors show a clearer busy/unavailable message (`engine_router.py`).

## [1.0.2] - 2026-07-01

Minor release — **Windows installers**, **in-app updates (macOS)**, **macOS sidecar lifecycle fix (#18)**, and **expanded CLI tool discovery (incl. Rivet)**.

> **Release assets (v1.0.2):** [GitHub Release](https://github.com/fancy1108/Clutch/releases/tag/v1.0.2) — macOS DMG, Windows MSI/NSIS, `latest.json` + signed updater bundle (macOS), `SHA256SUMS.txt`. Product snapshot: [`docs/releases/v1.0.2.md`](docs/releases/v1.0.2.md).

> **Windows 说明（v1.0.2）：** MSI / NSIS 安装包由 GitHub Actions CI 构建并通过自动化测试；**维护者尚未在实体 Windows 10/11 机器上完成完整人工验收**。若 Release 页附 Windows 资产，请优先核对 SHA-256 与来源；遇到问题欢迎 [开 Issue](https://github.com/fancy1108/Clutch/issues/new/choose)。macOS DMG 仍为本次主要发布与 smoke 路径。

> **macOS 更新说明：** v1.0.0 / v1.0.1 用户须**手动安装 v1.0.2 一次**；之后可通过应用内横幅自动更新。详见 [`docs/UPDATES.md`](docs/UPDATES.md) · [`docs/INSTALL.md`](docs/INSTALL.md) §3。

### Added

- **Windows desktop distribution:** Windows 10/11 x64 MSI and NSIS installers, ConPTY-backed Hybrid sessions, cross-platform MCP/file-lock handling, and Windows Credential Manager storage for provider API keys.
- **Windows build automation:** Manual/PR workflow builds and uploads Windows installer artifacts.
- **In-app updates (OSR-20):** Tauri `plugin-updater` + update banner; `release-updater.yml` for signed update assets; **go-live on v1.0.2** — see [`docs/UPDATES.md`](docs/UPDATES.md).
- **CLI tools (Rivet + whitelist):** Expanded Agent CLI discovery — installed tools always shown; curated install guides for uninstalled CLIs; **Rivet** headless routing via `rivet-cli` with `RIVET_FORCE_RECOVERY_CLI=1`.

### Changed

- **Tool Settings:** 20+ CLI whitelist scan; uninstalled tools default to Clutch-verified recommendations (`claude`, `ollama`, `codex`, `agy`) with install hints.

### Fixed

- **macOS restart / Dock (#18):** Tauri shell kills sidecar on exit, clears stale `orchestrator` on launch, and restores the main window on Dock reopen after closing the window (red button).
- **Rivet CLI (nvm/npm):** Sidecar prepends Rivet’s `bin` directory to `PATH` so `#!/usr/bin/env node` works when the packaged app lacks nvm in its environment (exit 127).

### Changed (packaging)

- **Release hardening (OSR-16):** Packaged sidecar disables `GET /api/runs/{run_id}/debug` and OpenAPI docs unless `CLUTCH_DEBUG_API=1`; WebView Content-Security-Policy in `tauri.conf.json` (production + `devCsp` for Vite HMR).
- **Sidecar distribution (OSR-17):** PyInstaller bundle ships with `console=False` (no terminal window on macOS).

### Added (docs)

- Document lifecycle governance: Source of Truth table, event-driven update matrix, and `memory/archive/` rotation with read-only Archive Notice on all archived files.

## [1.0.1] - 2026-06-30

Patch release — fixes packaged-app **Models Config** connectivity and macOS Keychain prompt spam. **Upgrade recommended** for all v1.0.0 DMG users.

### Fixed

- **Generated images blank in chat (packaged app):** Agnes returns CDN URLs (`*.agnes-ai.space`), not base64; WebView CSP blocked those hosts. Sidecar now downloads the image and embeds a `data:` URI in chat replies.
- **Release CI sidecar HTTPS broken:** GitHub Actions bundled python.org CPython 3.11.9 (old OpenSSL); outbound model API calls failed in the DMG. Release workflow now uses uv-managed Python 3.11 only.
- **Models Config red error (packaged app):** PyInstaller sidecar crashed on `GET /api/models/config` when Keychain read failed — logging used reserved LogRecord field `message` → HTTP 500; UI misreported as “Cannot reach Clutch sidecar”.
- **Sidecar session token (OSR-08):** Tauri ACL now exposes `clutch_sidecar_token` to the main webview; authenticated fetch retries once on 401.
- **Keychain prompt spam:** Read keys via `security find` with `-A` ACL migration (one-time per machine); avoids repeated prompts on adhoc-signed sidecar rebuilds.
- **Error copy:** Models UI distinguishes unreachable sidecar vs unauthorized session vs server error; `CLUTCH_DEBUG=1` surfaces raw connection errors.

### Changed

- PyInstaller sidecar bundles `keyring` for macOS Keychain on packaged builds; `upx=False` in `clutch.spec`.
- Right-panel **Flow** tab stays visible in multi-agent mode (empty state when no workflow selected).
- WebView CSP allows Agnes image CDN hosts as fallback.

### Known limitations (v1.0.1)

- macOS DMG remains **unsigned** (same as v1.0.0); Gatekeeper workaround unchanged.
- First Models load after install may still take ~10–15s while macOS Keychain grants access — click **Always Allow** when prompted.

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
