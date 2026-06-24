# FAILURES（防坑手册）

> 任何导致回滚或浪费超过 10 分钟的问题必须记录。  
> 新会话启动时，在读 `PROGRESS.md` 之后立即读本文件。

## 格式说明

- `[OPEN]` — 尚未解决，会话中须避开或标注风险
- `[RESOLVED]` — 已解决；**必须**同步补一行到 `CLAUDE.md` §已知陷阱

## 活跃问题（尚未解决）

（暂无）

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
