# Build Clutch from source

> **Audience:** Contributors and advanced users on macOS.  
> **End-user DMG installs** (unsigned GitHub Releases) are linked from [`README.md`](../README.md) §安装方式. Signing (OSR-11) is deferred per `memory/DECISIONS.md` D31.

## Prerequisites

Run the environment self-check first:

```bash
./scripts/doctor.sh
```

| Tool | Version | Notes |
|------|---------|-------|
| macOS | 14+ recommended | Apple Silicon is the primary target |
| Node.js | ≥ 20 | CI uses 22 LTS |
| pnpm | ≥ 9 | Repo locks `9.15.0` via `packageManager` |
| Python | ≥ 3.11 | Orchestrator sidecar |
| [uv](https://docs.astral.sh/uv/) | latest stable | Installs orchestrator venv |
| Rust (stable) | latest | Required only for `pnpm tauri build` |

## 1. Clone and install dependencies

```bash
git clone https://github.com/fancy1108/Clutch.git
cd Clutch
pnpm install
cd services/orchestrator && uv sync --extra dev && cd ../..
```

## 2. Development workflows

### Option A — Tauri desktop (recommended)

Starts Vite, Tauri shell, and the Python sidecar (dev port **8124**):

```bash
export CLUTCH_RUNTIME_MODE=hybrid   # optional; enables Hybrid CLI runtime
pnpm tauri:dev
```

### Option B — Split terminals

```bash
# Terminal 1 — frontend only
cd apps/desktop && pnpm dev

# Terminal 2 — Tauri shell (sidecar auto-spawned on 8124)
cd apps/desktop
export CLUTCH_RUNTIME_MODE=hybrid
pnpm tauri dev --no-dev-server-wait
```

### Option C — Sidecar only (no desktop shell)

```bash
cd services/orchestrator
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8124
```

Then open the Vite dev server at `http://localhost:3000` (from Option B terminal 1).

**Health check (dev):**

```bash
curl -s http://127.0.0.1:8124/health
# {"status":"ok"}
```

When launched via **Tauri** (`pnpm tauri:dev`), the shell generates `CLUTCH_SIDECAR_TOKEN` for the sidecar; the desktop UI attaches it automatically (OSR-08). Manual `uvicorn` without that env var does not require a token (local dev / pytest).

## 3. Verify before contributing

From the repository root:

```bash
./scripts/verify.sh
```

This runs frontend build, vitest, orchestrator pytest, and `check-doc-drift.sh`.  
For full E2E (heavy): `./scripts/verify.sh --e2e`.

See [`CONTRIBUTING.md`](../CONTRIBUTING.md) and [`CLAUDE.md`](../CLAUDE.md) §核心命令.

## 4. Production DMG (local)

Requires Rust toolchain and PyInstaller (via `build-sidecar.sh`):

```bash
cd apps/desktop
pnpm tauri build
```

Artifacts land under `apps/desktop/src-tauri/target/release/bundle/`.

`beforeBuildCommand` runs:

1. `pnpm build` → `apps/desktop/dist/`
2. `scripts/build-sidecar.sh` → PyInstaller binary in `src-tauri/binaries/`

**Health check (prod build, after installing the `.app`):**

```bash
curl -s http://127.0.0.1:8123/health
# {"status":"ok"}
```

Unsigned builds (local or GitHub Release) may require **right-click → Open** on first launch (Gatekeeper). See README §安装方式. Apple signing (OSR-11) is optional until a Developer account is available (D31).

## 5. Data directories

| Mode | Storage path |
|------|----------------|
| Development (`pnpm tauri dev` / uvicorn) | `~/Library/Application Support/clutch_dev/` |
| Packaged `.app` (PyInstaller sidecar) | `~/Library/Application Support/clutch/` |

Override with `CLUTCH_STORAGE_DIR` (absolute path).

API keys live in `models.json` (`chmod 600`) until Keychain migration (OSR-13). See [`SECURITY.md`](../SECURITY.md).

## 6. Optional CLIs

Clutch scans `PATH` for local AI tools (`claude`, `codex`, `ollama`, etc.). Install and authenticate those CLIs separately; configure **Connect** in Settings → Tools after first launch.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Sidecar timeout on launch | `doctor.sh`; port 8124/8123 not occupied; orchestrator `.venv` exists |
| Folder picker fails | Must run the **Tauri app**, not browser-only `pnpm dev` |
| Tests fail after pull | `pnpm install` + `uv sync --extra dev` |

Installation issues: [installation issue template](../.github/ISSUE_TEMPLATE/installation_issue.yml).
