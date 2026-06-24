# PROGRESS

## 当前状态

- 阶段：**P2 收尾与 UI 修复完成；已完成 7 项 UI 与后端交互优化**
- Git HEAD：`9ce59ba`（本地有未 commit 的改动，等待打包后 commit）

## 治理脚手架就绪标准（文档层 ✅）

- [x] Layer 1–3 治理文档 + Memory 六件套
- [x] 测试规范（D1/D2、TESTS、CI workflow、`verify.sh` + `run-e2e.sh`）
- [x] Vibe 8.5 兜底（D7：Husky、漂移机检、truth-alignment 剧本、Layer 4 约束）
- [x] Task 交付索引（`DELIVERABLES.md` + Check-out 规则 + `runs/verification/README`）
- [x] 产品开放问题 Q1–Q4 → D3–D6 已决策

## 下次 Agent 启动必读

1. 读本文件（`PROGRESS.md`）
2. 读 `FAILURES.md`（**桌面 E2E 坑**）、`FILEMAP.md`、`DECISIONS.md`（D11–D12）
3. 运行 `git log --oneline -10`
4. 运行 `./scripts/run-e2e.sh`（比 `verify.sh` 更快定位 E2E 问题）

## 待办（跨会话）

- [x] **M0–M4**：MVP 任务清单（P2 Skills 延后；单 Agent 不开发见 D10）
- [x] **M4-06**：`pnpm tauri build` → DMG 证据 `runs/verification/2026-06-23-tauri-build.log`
- [x] **T-03**：MVP 闭环 E2E + `test_mvp_closed_loop.py`
- [x] **D11**：会话 messages 持久化 + 侧栏历史 hydrate（代码已写，待 commit）
- [x] **D12**：桌面 E2E 全链路 — `./scripts/run-e2e.sh` 7/7 ✅
- [x] **提交 + push** D11+D12 → `9e509c3`
- [x] **P2-01**：Skills Registry 后端 + 扫描
- [x] **P2-02**：全量 MCP CRUD
- [x] **P2-03**：Theme 持久化
- [x] **P2-04**：i18n 双语验收
- [x] **P2-05**：侧栏 REPOSITORIES CRUD
- [ ] **P2-06**：General Settings — ⏸️ **延后（D14，勿主动推进）**
- [x] **Push + CI**：`9ce59ba` 已 push；CI 见 GitHub Actions（本机无 gh auth）
- [x] **DMG**：`pnpm tauri build` → `runs/verification/2026-06-24-clutch-p2.dmg`
- [ ] **T-04**：红队 / 体感审计（可选）

## 会话日志（最新在上）

### 2026-06-24 会话（UI 与后端交互修复）

- **完成：**
  - 去掉左上角三个红绿灯图标；
  - 修复点击侧栏非空历史会话时，中间仍展示 Supervised Session 引导页的 Bug；
  - 修复 LLM 聊天气泡左/右对齐（User 在右，LLM 在左）；
  - 修复 plain chat 模式下，用户消息没有立刻回显（需等待 LLM 返回才一起展示）的延迟 Bug；
  - 修复 Claude Code proxy 环境下，模型显示名被硬编码为 "Claude" 的 Bug，如果是 GLM 则正确显示 "GLM 4" 等；
  - 实质支持右键项目/会话允许删除（项目只删除侧栏入口，会话是真的物理删除磁盘 json 和 history 记录）；
  - 修复聊天中 LLM 气泡的时间显示为 UTC 时间的 Bug（已改为使用 native local time）。
- **校验：** `./scripts/verify.sh` → 116 pytest + vitest ✅
- **下次优先：** 校验完毕后，原子提交并重新运行 `pnpm tauri build` 重新打包dmg。

### 2026-06-24 会话（收尾 push）

- **Push：** `f1ea1f2`（DMG capability 修复）+ `9ce59ba`（D15 verify 拆分 + schema regen）
- **校验：** `./scripts/verify.sh` 轻量 → 115 pytest ✅
- **DMG：** `runs/verification/2026-06-24-clutch-p2.dmg`

### 2026-06-24 会话（P2 收尾 · 发布）

- **决策：** D14 — P2-06 **延后**（已写入 DECISIONS，勿反复询问）
- **Push：** `609b2d6` → `origin/main`（8 commits）
- **DMG：** `runs/verification/2026-06-24-clutch-p2.dmg`（修复 release 不含 `playwright:default`）
- **CI：** 本机无 `gh auth`；请在 GitHub Actions 页确认 `609b2d6` 绿

### 2026-06-24 会话（P2-05 REPOSITORIES CRUD）

- **完成：** `repository_groups` Sidecar 持久化；侧栏 filter + 新建分组 + 折叠；`test_repository_groups.py` 2 passed
- **Commit：** `3e2b6c7`

### 2026-06-24 会话（P2-04 i18n）

- **完成：** `preferences_storage` 合并 language；`/api/preferences/language`；`LanguageContext` Sidecar 同步；`i18n.spec.ts` + desktop G-03 断言
- **校验：** `test_i18n_preferences.py` 3 passed；`pnpm build` ✅
- **下次优先：** P2-05 侧栏 REPOSITORIES CRUD

### 2026-06-24 会话（P2-03 Theme 持久化）

- **完成：** `preferences_storage` + `/api/preferences/theme`；`themeApi.ts`；`App.tsx` 启动 hydrate + 切换保存
- **校验：** `test_theme_preferences.py` 3 passed；`pnpm build` ✅
- **下次优先：** P2-04 i18n 双语验收

### 2026-06-24 会话（P2-02 MCP Registry）

- **完成：** `mcp_storage` + `/api/mcp/servers/register|remove|toggle`；`mcpApi.ts`；`McpServerHub` CRUD UI
- **校验：** `test_mcp_registry.py` 3 passed；`pnpm build` ✅
- **下次优先：** P2-03 Theme 持久化

### 2026-06-24 会话（P2-01 Check-out + e2e 修复）

- **完成：** D13 决策 + P2-01 全链路；`./scripts/verify.sh` → 104 pytest + 7 Playwright ✅
- **校验：** Check-out 完成（DELIVERABLES / TESTS / FAILURES 同步）
- **下次优先：** P2-02 全量 MCP CRUD

### 2026-06-23 会话 23（D12 桌面 E2E 修复 — 进行中）

- **完成：**
  - **根因修复（API）**：`session-history` / `smoke` 不再用 Chromium 起 WebSocket；新增 `e2e/helpers/ws.ts`（Node 原生 WebSocket）→ API **4/4 passed**
  - **门禁脚本**：`run-e2e.sh` 加 `wait_tauri_ready`（vite + health + playwright socket）、显式传递 `CLUTCH_*` 环境变量、`playwright install chromium`
  - **沙箱**：`e2e-sandbox-setup.sh` + `CLUTCH_E2E_SANDBOX` 注入；`pickWorkspaceFolder.ts` / `clutch_e2e_sandbox` Tauri command
  - **桌面基建**：`tauri-plugin-playwright`（`e2e-testing` feature）、`e2e/fixtures/desktop.ts`、`e2e/tests/desktop/all-ui.spec.ts`
  - **tauri-playwright 适配**：`waitForFunction(expr, timeoutMs)` 非 Playwright options；`authorizeSandboxWorkspace` helper；`evaluate` 须传字符串 script
  - **Sidecar 环境**：`lib.rs` `spawn_dev_sidecar` 转发 `CLUTCH_*` 给 uvicorn 子进程
  - **占位清理**：Branch 菜单、Terminal Clear、`data-testid` 等（前序会话）
- **校验：**
  - `./scripts/run-e2e.sh` → API 4 passed；Desktop 2 failed（见 `runs/verification/2026-06-23-e2e-full.log`）
  - 桌面失败 1：`type_text` on `<textarea>`（`HTMLInputElement` setter）
  - 桌面失败 2：侧栏 session 恢复后 `getByText(seedText)` 不可见
- **下次优先：** 修 textarea 输入 + 侧栏 hydrate；跑绿 `run-e2e.sh`；commit

### 2026-06-23 会话 22（D11 文档/用例完善）

- 完成：E2E `session-history`（API + desktop 用例草稿）；`CLUTCH_E2E_FAKE_LLM`；ARCHITECTURE §6.3.1
- 校验：`uv run pytest` 101 passed；E2E 当时未全绿
- 下次优先：commit；用户验收历史续聊

### 2026-06-23 会话 21（移除 [Test WS] 调试 UI）

- 完成：识别侧栏 `[Test WS]` 为 M0-02 开发联调遗留；移除按钮与 `sendSidecarTestMessage`
- Commit：`2d85c14`

### 2026-06-23 会话 20（MVP 验收收尾）

- 完成：Claude Code 凭证；`human-decision` HTTP；T-03 Playwright + pytest
- 校验：`./scripts/verify.sh` → 70 pytest + 3 E2E ✅
