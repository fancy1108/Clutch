# Changelog

All notable changes to Clutch are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

**Version policy:** See [`docs/STABILITY.md`](docs/STABILITY.md) for semver and module stability levels.

**Release gate:** A version must have a matching `## [x.y.z]` section here before tagging or publishing a GitHub Release (`scripts/release-preflight.sh` INV-R5). See [`docs/document-governance.md`](docs/document-governance.md) §Release 硬门禁.

**Version snapshots:** Per-release product summaries live in [`docs/releases/`](docs/releases/) (historical); current product truth is [`docs/PRODUCT_INTRO.md`](docs/PRODUCT_INTRO.md).

## [Unreleased]

Target: **v1.0.4** (not tagged yet).

### Added

- **Terminal Orchestra (D34):** Terminal mode multi-lane PTY, OrchestratorBar dispatch (`@Agent` natural language + graph syntax), handoff files, Overview dispatch log, lane handoff overlay, float-rail collapse, and completion draft queue.
- **Agent-scoped capability tabs:** Settings → **Models**, **MCP Hub**, and **Skills Registry** now use top tabs (**Clutch Agent** · **Claude Code** · **OpenCode**). Clutch tab keeps full edit/bind behavior; CLI tabs scan native config read-only and support CC Switch provider switch when `cc-switch` CLI is on PATH (Claude Code models).
- **Agent Manager clarity:** Create/edit **Module 3 (Skills)** and **Module 4 (MCP)** branch by agent type — Clutch agents bind Clutch Registry/Hub; Claude Code & OpenCode show native scan + Settings deep links; other CLI types show **coming soon** (no misleading Clutch bind UI). Saving non-Clutch agents clears `skills` / `mcpServerIds`.
- **CLI config API:** `GET /api/cli-config/{agent_type}/models|skills|mcp` and `POST .../activate-provider` for `claude-cli` and `opencode-cli`.
- **Agnes Video V2.0 (chat):** Built-in `agnes-video-v2.0` model; generate video from chat with inline player (poster + download); Chinese prompts auto-translated to English before API call; Models settings + Agnes provider key.
- **Product website (GitHub Pages):** Static landing at **https://fancy1108.github.io/Clutch/** — bilingual overview, install commands, contact (`docs/index.html`).
- **README marketing:** Clickable hero banners; high-resolution hero assets.
- **OpenCode Zen text models:** Built-in `opencode` provider in Settings → Models; five curated free chat models (`deepseek-v4-flash-free`, `big-pickle`, `mimo-v2.5-free`, `north-mini-code-free`, `nemotron-3-ultra-free`); optional **Refresh models** from `opencode.ai/zen/v1/models`; **Save** validates API key (chat probe) and model catalog membership; Sidecar uses `User-Agent: ClutchSidecar/1.0` for Zen HTTP (avoids Cloudflare 403 on default Python urllib).
- **CodeBuddy CLI:** First-class `codebuddy-cli` routing (`codebuddy -p` headless, `--resume` / `--session-id` session recovery); listed first in curated install recommendations.

## [1.0.3] - 2026-07-01

Minor release — **Hybrid shell pool queue**, **OpenCode CLI**, **Ollama settings fix**, **brand refresh**, and **maintainer real-connection E2E**.

> **Release assets (v1.0.3):** [GitHub Release](https://github.com/fancy1108/Clutch/releases/tag/v1.0.3) — macOS DMG, Windows MSI/NSIS, `latest.json` + signed updater bundle (macOS), `SHA256SUMS.txt`. Product snapshot: [`docs/releases/v1.0.3.md`](docs/releases/v1.0.3.md).

> **macOS 更新：** v1.0.2+ 用户可通过应用内横幅更新至 v1.0.3；v1.0.0 / v1.0.1 仍须先手动安装 v1.0.2+ 一次。详见 [`docs/UPDATES.md`](docs/UPDATES.md).

> **Windows：** 安装包由 CI 构建；维护者尚未在实体 Win10/11 上完成完整人工验收 ([#23](https://github.com/fancy1108/Clutch/issues/23))。

### Added

- **Hybrid shell pool queue (plain chat):** When all Hybrid shell slots are busy, new sessions **queue globally (FIFO)** with input-bar blocker UI (agent avatars + queue position); auto-resume when a slot frees — replaces Supervisor `pool_full` reject for plain chat.
- **Same-session pending message queue:** Send while a Hybrid turn runs; messages appear as **待发送消息** and drain in order after the current turn.
- **OpenCode CLI:** First-class `opencode-cli` routing (Hybrid shell when `CLUTCH_RUNTIME_MODE=hybrid`).
- **Built-in Agnes 2.0 Flash** chat model preset.
- **Real-connection E2E acceptance** (`./scripts/verify.sh --e2e-real`): 13 desktop cases including same-session queue (Q1) and cross-session pool queue (P1).
- **Install scripts:** `scripts/install.sh` (macOS curl DMG) and `scripts/install.ps1` (Windows NSIS); Homebrew tap [fancy1108/homebrew-clutch](https://github.com/fancy1108/homebrew-clutch).
- **Docs:** Bilingual README, [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md), [`docs/RELEASE_MAINTAINER.md`](docs/RELEASE_MAINTAINER.md).

### Changed

- **Brand / app icons:** Refreshed Clutch mark SVGs and regenerated Tauri desktop icon set (full-bleed black, no Dock white edges); `BrandLogo` shows mark on black background.
- **In-app update UI (macOS):** Compact **Update / Later / Restart** pill on the sidebar footer row beside Settings (`BTN_PRIMARY`); download shows spinner + percent.
- **Settings → Models Config (Ollama):** Model list reflects **local `ollama list`** tags; persisted `active_model_id` from another machine falls back to first installed tag (`models_config.py`).
- **CLI error copy (#19):** Hybrid → legacy fallback no longer double-prefixes failure text; 529 / 5xx gateway errors show clearer busy/unavailable message (`engine_router.py`).
- **README & onboarding:** Latest release v1.0.3; install pin examples updated.

### Fixed

- **Hybrid pool queue stuck:** Drain retry on slot release, WS refresh of blocker metadata, re-enqueue on handler failure (`plain_chat_pool_queue.py`).
- **E2E dev deps:** Playwright kept available for acceptance runs without bloating normal dev builds.

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
