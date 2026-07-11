# FAILURES（防坑手册）

> 任何导致回滚或浪费超过 10 分钟的问题必须记录。  
> 新会话启动时，在读 `PROGRESS.md` 之后立即读本文件。

## 格式说明

- `[OPEN]` — 尚未解决，会话中须避开或标注风险
- `[RESOLVED]` — 已解决；**必须**同步补一行到 `CLAUDE.md` §已知陷阱

## 活跃问题（尚未解决）

（暂无）

### [RESOLVED] v1.2.0 · Chat 模式 `expected string or bytes-like object, got 'dict'`（2026-07-11）

- **现象：** 打包版 Clutch Agent + 任意配置模型（如 DeepSeek V4 Pro）发消息后气泡直接显示该 TypeError；Terminal 有 `[CHAT] …: 48 chars`（错误文案长度）
- **根因：** Design 模式（`fae22b6`）把 `http_chat_complete` 返回值从 `str` 改成 `{content, reasoning_content}`，但 `engine_router.route_engine` → `sanitize_engine_output` 仍对 `re.sub` 传入 dict
- **解决：** 所有 plain-chat / MCP / handoff / tools_status 调用点用 `LLMProviderRouter.extract_content` 解包；`sanitize_engine_output` 对非 str 做防御
- **规避：** 改 LLM 返回形状时必须同步所有 `router.chat()` 消费方；发版前用 Clutch Agent 无 MCP 路径做一次真实 chat smoke
- **关联：** `engine_router.py`、`mcp_react.py`、`agent_executor.py`；回归测 `test_route_engine_unwraps_dict_chat_response`

### [RESOLVED] macOS · 打开 Clutch 出现两个 Dock 图标（2026-07-10）

- **现象：** 打包版启动后 Dock 出现两个相同 Clutch 图标，其一为内嵌 PyInstaller `orchestrator` sidecar
- **根因：** `clutch.spec` 默认 `console=False`，macOS windowed bootloader 将 sidecar 注册为 GUI 应用
- **解决：** macOS/Linux 构建改为 `console=True`（Tauri 子进程启动不弹终端）；Windows 仍 `console=False`（OSR-17）
- **规避：** 发新版 DMG 前须重跑 `build-sidecar.py`；已安装 v1.1.2 用户需升级

### [RESOLVED] Windows · Design Preview / Tauri build 不能依赖裸命令（2026-07-11）

- **现象：** Design Preview 在 Windows `shell=False` 下直接执行 `pnpm/npm/npx` 可能 `WinError 2`；pnpm 10+ ignored builds 会让临时 Vite preview install 返回非 0；Tauri `beforeBuildCommand` 使用裸 `uv` 时在 PATH 无 `uv` 的机器上失败。
- **根因：** Windows 可执行解析需要 `.cmd` 完整路径；generated Vite preview 需要允许 esbuild postinstall；构建链路假设 `uv` 在 PATH，而本机可用入口是 `python -m uv`。
- **解决：** Design service 统一 `shutil.which` 解析命令，pnpm install 加 `--config.dangerously-allow-all-builds=true`，install 捕获用 UTF-8 replace，preview stop 用进程树清理；Tauri build 入口改为 `scripts/run-build-sidecar.mjs`。
- **规避：** Windows 新增 Node/Python/包管理器调用时，先解析完整可执行路径，避免裸 CLI；Tauri build 不写裸 `uv`。

## 已解决问题（经验库）

### [RESOLVED] D12 · tauri-playwright 无法在 `<textarea>` 上 fill/type（2026-06-23）

- **现象：** `all-ui.spec.ts` 在 `chat-input`（React `<textarea>`）上 `fill` / `type` 报错：`HTMLInputElement.value setter can only be used on instances of HTMLInputElement`
- **根因：** `@srsholmes/tauri-playwright` 0.4 的 `type_text` / `fill` 实现假定 `HTMLInputElement`，未处理 `HTMLTextAreaElement`
- **解决：** `e2e/helpers/tauri.ts` 用 `evaluate` 字符串脚本 + `HTMLTextAreaElement` setter + `input` 事件
- **规避：** 桌面 E2E 输入统一走 helper，勿直接 `fill` textarea
- **关联：** `e2e/tests/desktop/all-ui.spec.ts`

### [RESOLVED] D12 · 桌面侧栏 session hydrate 后消息不可见（2026-06-23）

- **现象：** `desktop/session-history.spec.ts`：`waitForFunction` 含 seedText 通过，但 `getByText(seedText)` 5s 超时
- **解决：** hydrate 路径稳定 + 用例等待 Chat DOM；`9e509c3` 后桌面 3/3 绿
- **规避：** 点选会话后 `waitForSelector` 等消息节点，勿仅依赖 `getByText` 默认 5s
- **关联：** `e2e/tests/desktop/session-history.spec.ts`

### [RESOLVED] D12 · API E2E 勿用 Chromium 测 WebSocket（2026-06-23）

- **现象：** 原 `session-history` / `smoke` 在 Playwright 浏览器里起 WS → `websocket error`（103ms）
- **解决：** `e2e/helpers/ws.ts`（Node 原生 WebSocket）；API 4/4 绿
- **规避：** API 用例禁止 `chromium.launch()` 测 WS
- **关联：** `e2e/tests/smoke.spec.ts`、`session-history.spec.ts`

### [RESOLVED] M1-06 · UI 模型 ↔ compiler JSON 无映射（2026-06-23）

- **现象：** 画布 `WorkflowDef` 与执行 JSON 格式不一致，无法保存
- **解决：** **D9** 双模式 — 线性流程画布互转 + JSON 高级编辑；M1-06 落地
- **规避：** 复杂流程（检查/审批/分支）勿强行用画布，走 JSON 模式

### [RESOLVED] M0-05 · 本机无 Rust 工具链（2026-06-23）

- **现象：** 无法 `pnpm tauri dev`
- **解决：** rustup 安装 Rust；M0-05 Tauri 工程补全中
- **规避：** 开发期仍可手动 `uv run uvicorn` 启动 Sidecar
