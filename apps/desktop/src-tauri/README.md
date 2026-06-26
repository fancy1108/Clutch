# Tauri Shell (`src-tauri`)

Rust 宿主层职责：

1. 承载 React WebView（开发态连 `localhost:3000`，发布态加载 `dist/`）
2. **拉起 Python Sidecar**（发布态：PyInstaller 内嵌 `externalBin`）
3. 系统 API：`open -a Cursor`、安全存储 API Key 等

## 开发态

`pnpm tauri dev` 自动用 `uv run uvicorn` 拉起 `services/orchestrator`（需本机安装 uv）。

## 发布打包

```bash
cd apps/desktop && pnpm tauri build
```

`beforeBuildCommand` 会依次执行：

1. `pnpm build`（前端 `dist/`）
2. `../../scripts/build-sidecar.sh`（PyInstaller → `binaries/orchestrator-{target-triple}`）

`tauri.conf.json` 的 `bundle.externalBin` 将 sidecar 打入 `.app`；启动时 Rust 用 Tauri sidecar API 监听 **8123**（开发 sidecar 用 **8124**），再加载 UI。

**验收：** 安装 DMG 后打开 Clutch，约 5s 内 `curl http://127.0.0.1:8123/health` 应返回 `{"status":"ok"}`。开发时 `curl http://127.0.0.1:8124/health`。
