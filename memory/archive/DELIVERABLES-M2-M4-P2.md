# Archive Notice

This file is archived and read-only.

Do not append new records here.

For current project state, see:

- memory/PROGRESS.md
- memory/DELIVERABLES.md
- memory/ROADMAP.md

Archived on: 2026-06-29
Reason: milestones M2–M4 and P2 completed

---

# DELIVERABLES Archive — M2-M4-P2

| Task | 焦点 | 状态 |
|------|------|------|
| **发布** | push + CI + DMG（P2 验收） | ✅ `9ce59ba` pushed；DMG 见 `runs/verification/2026-06-24-clutch-p2.dmg` |
| **P2-06** | General Settings | ⏸️ 延后（D14） |
| **T-04** | 红队 / 体感审计 | 可选 |

### P2-03 ✅
- **日期：** 2026-06-24
- **Commit：** `7caeeec` — feat(preferences): persist theme and language via Sidecar (P2-03, P2-04)
- **Verification：** `uv run pytest tests/test_theme_preferences.py -v` → 3 passed；`pnpm build` ✅
- **交付文件：**
  - `services/orchestrator/src/preferences_storage.py` — Application Support 主题/语言偏好
  - `services/orchestrator/src/main.py` — `GET/POST /api/preferences/theme`
  - `services/orchestrator/tests/test_theme_preferences.py`
  - `apps/desktop/src/services/themeApi.ts`
  - `apps/desktop/src/App.tsx` — 启动 hydrate + 切换持久化

### P2-05 ✅
- **日期：** 2026-06-24
- **Commit：** `3e2b6c7` — feat(sidebar): add repository groups with filter and persistence (P2-05)
- **Verification：** `uv run pytest tests/test_repository_groups.py -v` → 2 passed；`pnpm build` ✅
- **交付文件：**
  - `services/orchestrator/src/workspace.py` — `repository_groups` 持久化 + CRUD
  - `services/orchestrator/src/main.py` — `/api/repository-groups/*`
  - `services/orchestrator/tests/test_repository_groups.py`
  - `apps/desktop/src/services/workspaceApi.ts` — 分组 API 客户端
  - `apps/desktop/src/sidebar.tsx` — filter / new group / 分组树
  - `apps/desktop/src/App.tsx` — hydrate + 创建/折叠分组

### P2-04 ✅
- **日期：** 2026-06-24
- **Commit：** `7caeeec` — feat(preferences): persist theme and language via Sidecar (P2-03, P2-04)
- **Verification：** `uv run pytest tests/test_i18n_preferences.py -v` → 3 passed；E2E `i18n.spec.ts` + desktop G-03 断言
- **交付文件：**
  - `services/orchestrator/src/main.py` — `GET/POST /api/preferences/language`、`GET /api/preferences`
  - `services/orchestrator/tests/test_i18n_preferences.py`
  - `apps/desktop/src/components/LanguageContext.tsx` — Sidecar 同步
  - `apps/desktop/src/components/ChatFeed.tsx` — `data-testid="chat-supervised-title"`
  - `e2e/tests/i18n.spec.ts`、`e2e/tests/desktop/all-ui.spec.ts` G-03

### P2-01 ✅
- **日期：** 2026-06-24
- **Commit：** `a8bc6af` — feat(skills): add Sidecar skills registry with SKILL.md scanning (P2-01)
- **Verification：** `uv run pytest tests/test_skills_registry.py -v` → 3 passed；`./scripts/verify.sh` → 104 pytest + 7 Playwright
- **证据：** `runs/verification/2026-06-24-p2-01-skills-pytest.log`、`runs/verification/2026-06-24-p2-01-verify.log`
- **交付文件：**
  - `services/orchestrator/src/skills_storage.py` — Application Support 持久化
  - `services/orchestrator/src/skills_scanner.py` — `SKILL.md` 递归扫描
  - `services/orchestrator/src/main.py` — `/api/skills/*`
  - `services/orchestrator/tests/test_skills_registry.py` — P2-01 门禁
  - `apps/desktop/src/services/skillsApi.ts` — 前端 API 客户端
  - `apps/desktop/src/components/SkillsRegistry.tsx` — 去 localStorage，接 Sidecar
  - `apps/desktop/src/components/AgentManager.tsx` — Skills 从 Sidecar 同步
  - `memory/DECISIONS.md` D13 — P2 任务拆解

### P2-02 ✅
- **日期：** 2026-06-24
- **Commit：** `da3c660` — feat(mcp): add user MCP server registry with stdio and SSE CRUD (P2-02)
- **Verification：** `uv run pytest tests/test_mcp_registry.py -v` → 3 passed；`pnpm build` ✅
- **证据：** `runs/verification/`（pytest 本地）
- **交付文件：**
  - `services/orchestrator/src/mcp_storage.py` — MCP 服务器持久化 + status 聚合
  - `services/orchestrator/src/main.py` — `/api/mcp/servers/*`、增强 `/api/mcp/status`
  - `services/orchestrator/tests/test_mcp_registry.py` — P2-02 门禁
  - `apps/desktop/src/services/mcpApi.ts` — 前端 MCP API
  - `apps/desktop/src/components/McpServerHub.tsx` — 注册 / 启用 / 删除 UI

### cf342c6 — M2–M4 批量 ✅
- **日期：** 2026-06-23
- **Commit：** `cf342c6` — feat(m2-m4): complete supervision desk, toolchain, and release polish
- **Verification：** `./scripts/verify.sh` → 67 pytest + build + vitest + drift
- **证据：** 会话 19 verify 输出
- **交付文件：** `git show cf342c6 --stat`

### M4-04 + T-03 + M4-06 ✅
- **日期：** 2026-06-23
- **Commit：** `c1b16cf` — feat(mvp): Claude Code credentials, human-decision API, and T-03 closed-loop E2E
- **Verification：** `./scripts/verify.sh` → 70 pytest + 3 E2E；`apps/desktop` `pnpm tauri build`
- **证据：** `runs/verification/2026-06-23-e2e-smoke.log`、`runs/verification/2026-06-23-tauri-build.log`
- **交付文件：**
  - `services/orchestrator/src/credentials/claude_code.py` — 读取 Claude Code CLI `ANTHROPIC_AUTH_TOKEN`
  - `services/orchestrator/src/main.py` — `POST /api/runs/{id}/human-decision`、`GET /api/models/credentials`
  - `e2e/tests/mvp-closed-loop.spec.ts` — T-03 Playwright
  - `services/orchestrator/tests/test_mvp_closed_loop.py` — T-03 API

### UI 清理 — 移除 M0 [Test WS] 调试按钮 ✅
- **日期：** 2026-06-23
- **Commit：** `2d85c14` — fix(desktop): remove M0 WebSocket debug button from sidebar
- **Verification：** `2d85c14` pre-commit：`./scripts/verify.sh` → build + 73 pytest + 3 E2E + drift ✅
- **证据：** commit hook 输出（`2d85c14`）；Check-out 时工作区 WIP 致 pytest 收集失败，与本次变更无关
- **交付文件：** `git show 2d85c14 --stat`
  - `apps/desktop/src/sidebar.tsx` — 移除侧栏 `[Test WS]` 按钮
  - `apps/desktop/src/services/clutchState.ts` — 删除 `sendSidecarTestMessage`
  - `apps/desktop/src/services/api.ts` — 移除对应 export
  - `scripts/run-e2e.sh` — E2E 门禁（自动起 Sidecar）

### D11 · 会话消息持久化 + 历史 hydrate ✅
- **日期：** 2026-06-23
- **Commit：** `9e509c3`
- **Verification：** `./scripts/verify.sh` → 101 pytest + 7 Playwright ✅
- **证据：** `runs/verification/2026-06-23-e2e-full.log`
- **交付文件：**
  - `services/orchestrator/src/run_state_store.py` — `states/{run_id}.json` 读写
  - `services/orchestrator/src/main.py` — `_commit_run_state` / `_get_or_create_run` 磁盘加载
  - `services/orchestrator/tests/test_run_state_store.py` — 持久化 + plain chat 落盘
  - `services/orchestrator/tests/conftest.py` — 全量测试隔离 `CLUTCH_RUN_HISTORY_DIR`
  - `services/orchestrator/src/models_config.py` — `CLUTCH_E2E_FAKE_LLM` Echo 路由
  - `apps/desktop/src/services/runApi.ts` — `fetchRunState`
  - `apps/desktop/src/services/clutchState.ts` — `setPendingHydrate`、WS 切换修复
  - `apps/desktop/src/App.tsx` — `handleSelectSession` hydrate
  - `apps/desktop/src/sidebar.tsx` — `data-testid="sidebar-session-{run_id}"`
  - `e2e/tests/session-history.spec.ts` — API：plain chat → GET state（Node WS）
  - `e2e/tests/desktop/session-history.spec.ts` — 桌面：侧栏点选恢复对话（待绿）
  - `scripts/e2e-sandbox-setup.sh` — `CLUTCH_E2E_FAKE_LLM=1`
  - `docs/ARCHITECTURE.md` §6.3.1 — 持久化叙事
  - `memory/DECISIONS.md` D11；`specs/core/tasks.md` M2-07 / M2-10 更新

### D12 · 桌面 E2E 全链路（tauri-playwright）✅
- **日期：** 2026-06-23
- **Commit：** `9e509c3`
- **Verification：** `./scripts/verify.sh` → **7/7 Playwright** + 101 pytest ✅
- **证据：** `runs/verification/2026-06-23-e2e-full.log`；`e2e/test-results/desktop-*/`
- **已交付（代码在工作区）：**
  - `apps/desktop/src-tauri/` — `e2e-testing` feature、`tauri-plugin-playwright`、`clutch_e2e_sandbox`、`spawn_dev_sidecar` 转发 `CLUTCH_*`
  - `apps/desktop/package.json` — `tauri:e2e`
  - `e2e/playwright.config.ts` — `api` + `desktop`（`mode: 'tauri'`）projects
  - `e2e/helpers/ws.ts`、`tauri.ts`、`seed.ts`
  - `e2e/fixtures/desktop.ts`、`e2e/tests/desktop/all-ui.spec.ts`
  - `scripts/run-e2e.sh` — API → 杀端口 → Tauri → `wait_tauri_ready` → Desktop
  - UI：`data-testid`、Branch 菜单、Terminal Clear 去占位
- **待完成：**（无 — 2026-06-23 门禁全绿）

### CC Switch 动态凭证导入、DeepSeek 修正与侧端端口隔离 ✅
- **日期：** 2026-06-25
- **Commit：** `c9ea0d6` — feat(llm,ui): fix deepseek base url, add credentials bootstrap from cc-switch database, toggle api key visibility, and solve dev/prod sidecar port collision
- **Verification：** `./scripts/verify.sh` → 120 pytest + vitest passed + doc drift ok
- **证据：** `runs/verification/2026-06-25-deepseek-ccswitch-verification.log`
- **已交付：**
  - `apps/desktop/src-tauri/src/lib.rs` — 移除了 macOS 上 `free_sidecar_port()` 的 debug assertions，确保开发模式也能释放并绑定 `8123` 端口，实现数据安全隔离。
  - `apps/desktop/src/components/ModelsManager.tsx` — 增加了 API Key 的可见性切换按钮（使用 Material Symbol `visibility`/`visibility_off`）。
  - `services/orchestrator/src/llm/router.py` — 修复 DeepSeek Base URL 为根域名 `https://api.deepseek.com`，补全 OpenAI, Google Gemini, Ollama 默认内置模型。
  - `services/orchestrator/src/credentials/claude_code.py` — 实现对 `~/.cc-switch/cc-switch.db` SQLite 数据库的读取，实现从 CC Switch 导入自定义模型和凭证的动态引导程序。
  - `services/orchestrator/src/credentials/sources.py` — 增加 CC Switch 凭证来源标签。
  - `services/orchestrator/tests/test_claude_code_credentials.py` — 增加 `test_bootstrap_cc_switch_credentials` 单元测试，修正环境污染问题。

### Default Group 虚拟分组及底部选项点击空白收起优化 ✅
- **日期：** 2026-06-26
- **Commit：** `831dbbd` — feat(ui): fix default group visibility and add click outside handler to collapse footer menus
- **Verification：** `./scripts/verify.sh` → 232 pytest + vitest passed + doc drift ok
- **已交付：**
  - `apps/desktop/src/sidebar.tsx` — 修复 `showDefaultGroup` 条件与空状态，并在 filter warning 时关联 showDefaultGroup。
  - `apps/desktop/src/App.tsx` — 添加全局 click 事件监听器，点击页面空白处自动关闭展开的底部菜单面板。

### 产品介绍文档与关联文档更新同步 ✅
- **日期：** 2026-06-26
- **Commit：** `e7a7e04` & `6754466` & `7c314fb` & `437ede6` — docs: create, revise and plan product introduction docs
- **Verification：** `./scripts/verify.sh` → 290 pytest + vitest passed + doc-drift OK
- **已交付：**
  - `docs/PRODUCT_INTRO.md` — 产品介绍文档，已区分当前已实现与未来路线图，并依据 Backlog 与开源项目（Reasonix、DeepSeek TUI、agentcache）补充了上下文压缩、工作区快照回滚、缓存友好分叉等 3.6 节状态与上下文管理技术规划
  - `workflows/README.md` — 纠正 compiler 状态与登记 `weather-to-vision.json` 模板
  - `README.md` — 主 README 注册产品介绍文档条目
  - `memory/FILEMAP.md` — 文件定位速查表中登记新文档
  - `docs/document-governance.md` — 职责划分表格中登记新文档


### 历史会话上下文压缩与归档 (Backlog B-03) 与前端展示美化 ✅
- **日期：** 2026-06-26
- **Commit：** `f6642cd` & `78115be` — feat(orchestrator): implement context message compaction, archiving and frontend UI enhancements
- **Verification：** `./scripts/verify.sh` → 297 passed (7 new tests added, including WS integration tests) + Vite build and Vitest OK
- **已交付：**
  - [services/orchestrator/src/compaction.py](file:///Users/fancy/clutch/services/orchestrator/src/compaction.py) — 核心压缩逻辑，包括 `should_compact` 检测、LLM 摘要生成与 Fallback 机制、历史消息归档 JSONL 以及 Token 重新计数与成本估算，支持 `badgeText` 与 `badge_text` 兼容字段。
  - [services/orchestrator/src/main.py](file:///Users/fancy/clutch/services/orchestrator/src/main.py) — 在单 Agent 普通对话消息处理流程 `_handle_plain_chat` 中集成上下文压缩，在 commit 与 notify 之前执行，实现无感、无闪烁 of 原子状态更新。
  - [services/orchestrator/tests/test_compaction.py](file:///Users/fancy/clutch/services/orchestrator/tests/test_compaction.py) — 包含对 token 估算、不同阈值与环境变量下的 compaction 决策、归档路径与文件内容、LLM 摘要合并、异常降级等分支的全面测试，以及 WebSocket 真实连接的集成测试。
  - [apps/desktop/src/components/ChatFeed.tsx](file:///Users/fancy/clutch/apps/desktop/src/components/ChatFeed.tsx) — 优化 `System` 对话气泡展示逻辑，采用 `info` 信息提示图标，并自动在气泡顶部渲染 `badgeText` 内容以呈现出上下文压缩摘要提示信息。
  - [apps/desktop/src/components/LanguageContext.tsx](file:///Users/fancy/clutch/apps/desktop/src/components/LanguageContext.tsx) — 补充中文语言下的 `"System": "系统"` 字典映射，使系统通知在 UI 显示上更亲民。


### USER-AVATAR-SELECTION ✅
- **日期：** 2026-06-27
- **Commit：** `7fabcff` — `feat(ui): set default user avatar and allow custom photo selection in General settings`
- **Verification：** `./scripts/verify.sh` → 348 pytest passed + 13 vitest passed + build and doc-drift OK
- **证据：** `—`（门禁已覆盖）
- **已交付：**
  - [apps/desktop/src/assets/default_avatar.jpg](file:///Users/fancy/clutch/apps/desktop/src/assets/default_avatar.jpg) — 新增的默认用户头像（粉色卡通猪玩偶照片）。
  - [services/orchestrator/src/preferences_storage.py](file:///Users/fancy/clutch/services/orchestrator/src/preferences_storage.py) — 扩展偏好管理，支持默认及自定义的 `user_avatar` 偏好项。
  - [services/orchestrator/src/main.py](file:///Users/fancy/clutch/services/orchestrator/src/main.py) — 增加 `AvatarPreferenceRequest` 以及 `/api/preferences/avatar` 偏好更新 POST 接口。
  - [services/orchestrator/tests/test_avatar_preferences.py](file:///Users/fancy/clutch/services/orchestrator/tests/test_avatar_preferences.py) — 覆盖获取默认头像、修改及重置自定义头像的单元测试。
  - [apps/desktop/src/services/themeApi.ts](file:///Users/fancy/clutch/apps/desktop/src/services/themeApi.ts) — 扩展 `UserPreferences` 类型与 `saveAvatarPreference` 网络适配器。
  - [apps/desktop/src/services/clutchState.ts](file:///Users/fancy/clutch/apps/desktop/src/services/clutchState.ts) — 将 `USER_CHAT_AVATAR` 指向默认猪玩偶头像，并提供 `setUserChatAvatar` 触发应用组件重绘。
  - [apps/desktop/src/App.tsx](file:///Users/fancy/clutch/apps/desktop/src/App.tsx) — 应用启动时 hydrate 获取用户定制头像，并将其作为 state 参数透传至监督及设置组件。
  - [apps/desktop/src/components/ChatFeed.tsx](file:///Users/fancy/clutch/apps/desktop/src/components/ChatFeed.tsx) — 动态计算用户消息的气泡头像，支持按 state 中的 custom 头像或 default 猪玩偶头像展示。
  - [apps/desktop/src/components/SystemPreferencesModal.tsx](file:///Users/fancy/clutch/apps/desktop/src/components/SystemPreferencesModal.tsx) — 重构设置 General 面板，构建毛玻璃卡片、圆形头像预览、支持读取本地文件转 base64 并提交至 Sidecar 保存。
  - [apps/desktop/src/components/LanguageContext.tsx](file:///Users/fancy/clutch/apps/desktop/src/components/LanguageContext.tsx) — 新增 General Settings 页面元素及按钮提示的中英对照双语翻译。


### 历史会话正在进行加载动效与完成无图标更改 ✅
- **日期：** 2026-06-28
- **Commit：** `fa88fcd` — `fix(desktop): connect clutchStatus to sidebar and prevent session pool exhaustion in tests`
- **Verification：** `./scripts/verify.sh` → 408 passed + vitest OK + build and doc-drift OK
- **已交付：**
  - [apps/desktop/src/sidebar.tsx](file:///Users/fancy/clutch/apps/desktop/src/sidebar.tsx) — 更改会话条目图标逻辑：正在运行的会话（`status === 'running'`）显示 `progress_activity` 动效旋转加载动画，已完成的会话显示为空（无图标），不再显示原有的 `restart_alt` 环形多轮会话图标。
  - [apps/desktop/src/App.tsx](file:///Users/fancy/clutch/apps/desktop/src/App.tsx) — 向 Sidebar 传入 `clutchStatus` 状态，并实现在会话执行结束（状态从 `running` 变为非 `running`）时自动调用 `refreshSessions` 刷新会话列表。
  - [services/orchestrator/tests/conftest.py](file:///Users/fancy/clutch/services/orchestrator/tests/conftest.py) — 修复 pytest 全量测试时由于 `ShellSession` 缓存泄露导致 Pool 爆满引发 `test_concurrent_hybrid_plain_chat_ws` 错误的问题。在全局孤立 fixture `isolate_orchestrator_globals` 中新增 `clean_sessions()` 清理逻辑。

### Codex CLI 接入 · JSON 输出过滤 · 动态 Agent 类型 ✅
- **日期：** 2026-06-28
- **Commit：** `a75bf5d` — feat(orchestrator,desktop): integrate Codex CLI with JSON output and dynamic agent types
- **Verification：** `./scripts/verify.sh` → 433 pytest passed + vitest OK + build + doc-drift OK
- **证据：** `runs/verification/2026-06-28-codex-cli-integration.log`
- **已交付：**
  - `services/orchestrator/src/engine_router.py` — `codex-cli` 路由：`codex exec --json`、history replay、`close_stdin`
  - `services/orchestrator/src/claude_hybrid_output_parser.py` — `parse_codex_jsonl_output` / Codex TUI 噪音过滤
  - `services/orchestrator/src/shell_exec_runtime.py` — Hybrid shell `</dev/null`、Codex 专用解析
  - `services/orchestrator/src/tools_status.py` — `codex-cli` agentType 映射与 Auto-configure
  - `apps/desktop/src/services/agentTypes.ts` — 动态 Agent 类型下拉（Connect 工具驱动）
  - `apps/desktop/src/components/AgentManager.tsx` — 使用 eligible tools 替代硬编码列表
  - `docs/PRODUCT_INTRO.md` — Codex CLI 与动态 Agent 类型产品说明对齐


### FLOW-REFINE-BUGS-FIX ✅
- **日期：** 2026-06-29
- **Commit：** `7ee2ae2` — `fix(flow-refine): resolve user message echo, missing session prompt generation and avatar mapping in workflow refine`
- **Verification：** `./scripts/verify.sh` → build + vitest 33 passed + pytest 473 passed (100% success) ✅
- **证据：** `—`（门禁已覆盖）
- **已交付：**
  - [services/orchestrator/src/main.py](file:///Users/fancy/clutch/services/orchestrator/src/main.py) — 修复在 `_handle_flow_refine_message` 中初次由于 session 从 `_run_sessions` 取出为 `None` 时未能同步更新本地变量导致的 image refine prompt 忽略和 mention 匹配失效问题。
  - [apps/desktop/src/services/clutchState.ts](file:///Users/fancy/clutch/apps/desktop/src/services/clutchState.ts) — 修复 `mergeChatMessages` 在 `pendingUserMessageId` 为 null 时误过滤掉同文本的新 User 精修消息气泡的问题。
  - [apps/desktop/src/services/clutchState.test.ts](file:///Users/fancy/clutch/apps/desktop/src/services/clutchState.test.ts) — 更新 `mergeChatMessages` 单元测试，将原先错误的 duplicate text 丢弃行为断言改为允许在不同 turn 间多次发送同文本消息的符合预期断言。
  - [apps/desktop/src/services/workflowAgentSteps.ts](file:///Users/fancy/clutch/apps/desktop/src/services/workflowAgentSteps.ts) — 重构 `buildWorkflowReplyStepIndex` 逻辑，优先依据消息的 `agent` 名称/Label 匹配定位 WorkflowStep 获取准确的工具配置与头像，无法匹配时才退化至 Sequential 累加偏移，从而修复了精修结果气泡头像被张冠李戴的现象。


### 模型设置卡片选择与悬浮图形按钮优化 (Model UI Alignment) ✅
- **日期：** 2026-06-29
- **Commit：** `4ab1a27` — `feat(ui): align model configuration action buttons and card-level selection interaction`
- **Verification：** `./scripts/verify.sh` → build + vitest + pytest 473 passed (100% success) ✅
- **证据：** `—`（门禁已覆盖）
- **已交付：**
  - [apps/desktop/src/components/ModelsManager.tsx](file:///Users/fancy/clutch/apps/desktop/src/components/ModelsManager.tsx) — 重构模型卡片容器与动作按钮。去选择原有的 "Use this model" 文本按钮，将整个模型卡片变为可点击（点击自动触发 `handleActivate` 以选中/启用模型，并添加了 `cursor-pointer` 和 hover 边框高亮样式）；将 "Remove" 与 "Test"/"Retest" 操作重构为仅在鼠标悬浮时显现的图形化 icon 按钮（使用 `BTN_ICON` 与 LegacyIcon `delete` 和 `sync`）；同时对所有内部交互子元素（包括 Change Key 按钮和测试/删除按钮）添加 `e.stopPropagation()` 以防点选穿透。


### 选中 Flow 时底部显示 - 且 Agent 和 Flow 互斥优化 (Workflow Agent Mutex) ✅
- **日期：** 2026-06-29
- **Commit：** `9566376` — `feat(ui): clear workflow selection and backend state when selecting an agent and display Model/Agent as '-' when Flow is active`
- **Verification：** `cd services/orchestrator && uv run pytest tests/test_ws_state_patch.py -k test_ws_clear_workflow` → 1 passed; `./scripts/verify.sh` → build + vitest + pytest 474 passed (100% success) ✅
- **证据：** `—`（门禁已覆盖）
- **已交付：**
  - [apps/desktop/src/App.tsx](file:///Users/fancy/clutch/apps/desktop/src/App.tsx) — 当 Workflow 处于选中状态时，Model 显示为 `Model: —`（禁用/非交互状态元素），而 Active Agent 保持下拉按钮，但显示为 `Active Agent: —`。当用户在 Agent 菜单中选择任意智能体时，自动触发 `clearWorkflowSelection` 清理工作流，恢复常规 Plain Chat 下的模型/智能体切换；导入并整合 `clearWorkflowForSession` 方法。
  - [apps/desktop/src/services/clutchState.ts](file:///Users/fancy/clutch/apps/desktop/src/services/clutchState.ts) — 新增 `clearWorkflowState` store 状态重置与 `clearWorkflowForSession` WebSocket 消息指令发送，供前端在解绑工作流时清空本地状态并同步重置后端 session 级别的 `workflow_id`。
  - [services/orchestrator/src/main.py](file:///Users/fancy/clutch/services/orchestrator/src/main.py) — 在 WebSocket `/ws/runs/{run_id}` 循环中新增对 `"clear_workflow"` action 载荷的处理。清空当前活跃运行状态和运行历史中的 `workflow_id` 记录，移出当前运行的 `_run_sessions`，并广播最新的 `workflow_id: ""` patch，保证该会话在后续交互时正常路由至 plain chat。
  - [services/orchestrator/tests/test_ws_state_patch.py](file:///Users/fancy/clutch/services/orchestrator/tests/test_ws_state_patch.py) — 添加 `test_ws_clear_workflow` 单元测试，校验当发送 `"action": "clear_workflow"` 时 state_patch 中的 `workflow_id` 被正确清空且持久化落盘。


### CC Switch 导入模型的隐藏与删除支持 ✅
- **日期：** 2026-06-29
- **Commit：** `cdfb87b` — `feat(models): allow hiding/deleting CC Switch imported models from models list`
- **Verification：** `cd services/orchestrator && uv run pytest tests/test_models_config_api.py` → 17 passed; `./scripts/verify.sh` → build + vitest + pytest 474 passed (100% success) ✅
- **证据：** `—`（门禁已覆盖）
- **已交付：**
  - [services/orchestrator/src/custom_models.py](file:///Users/fancy/clutch/services/orchestrator/src/custom_models.py) — 解除了 `hide_model_from_list` 对 `cc-switch-` 前缀的移除屏蔽，支持将其通过写入 `hidden_model_ids` 从可用列表进行逻辑删除/隐藏。
  - [apps/desktop/src/components/ModelsManager.tsx](file:///Users/fancy/clutch/apps/desktop/src/components/ModelsManager.tsx) — 前端 UI 的 `canRemove` 条件放开为 `!isActive`，使用户可以对已失效的 CC Switch 模型点击垃圾桶删除；同时优化了相关的确认对话框文字，清晰指引其可以通过 Import models 重新导回。



