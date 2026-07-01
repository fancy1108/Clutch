# Clutch

**Local AI multi-agent orchestration & supervision — on your desktop.**

[English](README.md) · [简体中文](README.zh-CN.md) · [**Getting Started**](docs/GETTING_STARTED.md#english) · [Releases](https://github.com/fancy1108/Clutch/releases)

> [!TIP]
> **New here?** Read the **[Getting Started Guide](docs/GETTING_STARTED.md)** — install, first-launch wizard, and your first chat in ~5 minutes. No dev setup required.

Clutch is a **desktop app** (Tauri + React) for developers and technical operators who want **visible, editable, multi-agent workflows** on top of tools you already use — Claude Code, Codex, Ollama, MCP, and cloud LLMs. Drag a SOP on a canvas; LangGraph runs it locally; you supervise chat, terminal, diffs, and approvals in one place.

**Not a replacement for Claude Code or Cursor** — a **control layer** for long sessions and multi-agent pipelines.

| | |
|---|---|
| **Stack** | Tauri 2 · React 19 · FastAPI + LangGraph · local-first (`localhost:8123`) |
| **License** | See [LICENSE](LICENSE) |
| **Latest release** | [v1.0.2](https://github.com/fancy1108/Clutch/releases) |

---

## Quick start (end users)

### Option A — Terminal install (recommended)

**macOS (Apple Silicon) — pick one:**

```bash
# One-liner (no Homebrew required)
curl -fsSL https://raw.githubusercontent.com/fancy1108/Clutch/main/scripts/install.sh | bash
```

```bash
# If you already use Homebrew
brew tap fancy1108/clutch
brew install --cask clutch
```

**Windows (x64 · not yet verified on hardware):**

```powershell
irm https://raw.githubusercontent.com/fancy1108/Clutch/main/scripts/install.ps1 | iex
```

Pin a version: `CLUTCH_VERSION=v1.0.2` before running either script.

Install channels (maintainers): [`docs/RELEASE_MAINTAINER.md`](docs/RELEASE_MAINTAINER.md)

### Option B — Manual download

**1. Download** — [GitHub Releases](https://github.com/fancy1108/Clutch/releases)

| Platform | File | Status |
|----------|------|--------|
| macOS (Apple Silicon) | `Clutch_*_aarch64.dmg` | ✅ Verified |
| Windows 10/11 x64 | `Clutch_*_x64-setup.exe` or `.msi` | ⚠️ **Not yet verified** on physical hardware |

> [!WARNING]
> **Windows:** Installers are built in CI and attached to Releases, but maintainers have **not completed full smoke testing on real Windows 10/11 machines** yet. Expect rough edges; please [open an Issue](https://github.com/fancy1108/Clutch/issues/new/choose) with your OS version and installer filename if something breaks. Tracking: [#23](https://github.com/fancy1108/Clutch/issues/23).

**2. First open (macOS unsigned build)** — Gatekeeper may block the app. This is normal for unsigned OSS desktop apps:

```bash
xattr -cr /Applications/Clutch.app && open -a Clutch
```

Or: **Applications** → right-click **Clutch** → **Open** → confirm.

**3. Follow the setup wizard** — workspace → model or CLI → tools → done.

**4. New Chat** — pick an agent, send a message.

→ **Full walkthrough:** [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md#english) · **Install details:** [`docs/INSTALL.md`](docs/INSTALL.md)

---

## What you can do

| Capability | In plain terms |
|------------|----------------|
| **Visual workflows** | Drag agents on a canvas; Clutch compiles to LangGraph and runs the SOP |
| **Local CLI bridge** | Connect Claude Code, Codex, Ollama, Aider, Rivet, … from Settings → Tools |
| **One supervision desk** | Chat, terminal, file tree, diffs, and flow progress in one window |
| **Human-in-the-loop** | Pause on risky steps; approve, reject, or retry with instructions |
| **Agents & models** | Custom agents, API keys, Skills registry, MCP servers |
| **Hybrid sessions** | Multiple sessions, workflow refine, state across restarts |

Deep dive: [`docs/PRODUCT_INTRO.md`](docs/PRODUCT_INTRO.md) · Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## Screenshots

**Hybrid workflow console** — multi-agent run, progress, and token stats:

![Clutch Hybrid workflow console](./docs/images/Clutch_1.png)

**Visual SOP editor** — zero-code multi-agent pipeline on a canvas:

![Clutch workflow canvas](./docs/images/Clutch_2.png)

---

## Documentation

| I want to… | Read |
|------------|------|
| **Get started (recommended)** | [**`docs/GETTING_STARTED.md`**](docs/GETTING_STARTED.md) |
| Install DMG / Windows | [`docs/INSTALL.md`](docs/INSTALL.md) |
| Understand all features | [`docs/PRODUCT_INTRO.md`](docs/PRODUCT_INTRO.md) |
| macOS in-app updates | [`docs/UPDATES.md`](docs/UPDATES.md) |
| Build from source | [`docs/BUILD_FROM_SOURCE.md`](docs/BUILD_FROM_SOURCE.md) |
| Contribute | [`CONTRIBUTING.md`](CONTRIBUTING.md) (PRs to **`dev`**) |
| Report a security issue | [`SECURITY.md`](SECURITY.md) |

Full index: [`docs/README.md`](docs/README.md) · **Maintainers:** [`docs/RELEASE_MAINTAINER.md`](docs/RELEASE_MAINTAINER.md)

---

## Compatibility

Details: [`docs/STABILITY.md`](docs/STABILITY.md)

| Platform | Support |
|----------|---------|
| macOS 14+ (Apple Silicon) | ✅ Primary target · in-app updates v1.0.2+ |
| macOS 14+ (Intel) | ❌ **Not supported** — Apple Silicon DMG only; source build at your own risk |
| Windows 10/11 x64 | ⚠️ MSI/NSIS from v1.0.2 · CI built · **not yet verified on physical Windows hardware** ([#23](https://github.com/fancy1108/Clutch/issues/23)) |
| Linux | 🚧 No official installer |

**Dev toolchain** (source only): Node ≥ 20, pnpm ≥ 9, Python ≥ 3.11, [uv](https://docs.astral.sh/uv/), Rust (for `tauri build`). Run `./scripts/doctor.sh` to check.

---

## For developers

```bash
git clone https://github.com/fancy1108/Clutch.git
cd Clutch
./scripts/doctor.sh
pnpm install
cd services/orchestrator && uv sync --extra dev && cd ../..
export CLUTCH_RUNTIME_MODE=hybrid   # optional
pnpm tauri:dev
```

Commands & discipline: [`CLAUDE.md`](CLAUDE.md) · Before PR: `./scripts/verify.sh`

---

## Security & CLI permissions

Clutch talks to local AI CLIs through a loopback Sidecar (`127.0.0.1:8123`).

> [!IMPORTANT]
> For **Claude Code** and **Antigravity (agy)** CLIs, Clutch **defaults** to `--dangerously-skip-permissions` so workflows can run without per-tool CLI prompts. Only use on workspaces you trust. The in-chat Permission menu controls **MCP gating for built-in agents**, not this CLI default.

Report vulnerabilities: [`SECURITY.md`](SECURITY.md)

---

## Repository layout

```
clutch/
├── apps/desktop/           # Tauri + React UI
├── services/orchestrator/  # Python Sidecar (LangGraph)
├── docs/                   # Product & install docs
├── workflows/              # Workflow schemas & templates
└── scripts/                # verify · doctor · release
```

Frontend and Sidecar communicate only over loopback HTTP/WebSocket (dev `8124`, packaged `8123`).

---

## Community

- **Questions / bugs:** [GitHub Issues](https://github.com/fancy1108/Clutch/issues/new/choose)
- **Contributing:** [`CONTRIBUTING.md`](CONTRIBUTING.md) · [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- **Changelog:** [`CHANGELOG.md`](CHANGELOG.md)
