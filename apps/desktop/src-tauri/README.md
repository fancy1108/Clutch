# Tauri Shell (`src-tauri`)

Rust 宿主层职责：

1. 承载 React WebView（开发态连 `localhost:3000`，发布态加载 `dist/`）
2. **拉起 Python Sidecar**（P5：PyInstaller 产物作为 `externalBin` 内嵌）
3. 系统 API：`open -a Cursor`、安全存储 API Key 等

## 开发态

Sidecar 需单独启动（见根目录 `README.md`）：

```bash
cd services/orchestrator && uv run uvicorn src.main:app --reload --port 8123
```

## P5 打包

- `services/orchestrator` → PyInstaller → `src-tauri/binaries/orchestrator-{target-triple}`
- `tauri.conf.json` → `bundle.externalBin` 注册 sidecar
- 应用启动时由 Rust `Command` 或 Tauri sidecar API 拉起编排进程

## 初始化 Tauri CLI（首次）

```bash
cd apps/desktop
pnpm add -D @tauri-apps/cli@2 @tauri-apps/api@2
# 若需从模板补全 Rust 工程：
pnpm tauri init --ci
```

当前目录为 **结构占位**；完整 `Cargo.toml` / `lib.rs` 在接入 Tauri CLI 时生成。
