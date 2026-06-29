# Archive Notice

This file is archived and read-only.

Do not append new records here.

For current project state, see:

- memory/PROGRESS.md
- memory/DELIVERABLES.md
- memory/ROADMAP.md

Archived on: 2026-06-29
Reason: milestone M3 completed

---

# DELIVERABLES Archive — M3

- **日期：** 2026-06-26
- **Commit：** `1395a97` — `feat(flow): multi-agent handoff with clutch execution and image routing`
- **Verification：** `uv run pytest tests/test_node_input.py tests/test_workflow_handoff.py tests/test_workflow_projection.py tests/test_workflow_step_patch.py tests/test_agent_executor.py -v` → 8 passed；全量 `uv run pytest` → 280 passed（3 video renderer 用例 event loop 抖动，与 Flow 无关）；用户手动 Weather-to-Vision E2E 通过（Researcher → Artist 出图）
- **证据：** `runs/verification/2026-06-26-M3-F-flow-pytest.log`；用户截图 E2E（上海天气 → 外滩插画）
- **交付文件：**
  - `services/orchestrator/src/compiler/node_input.py` — Flow 节点输入 auto 解析（start 上游 → 用户句；否则 → 上游 output）
  - `services/orchestrator/src/compiler/compiler.py` — `node_outputs` 写入与 `emit_workflow_agent_step`
  - `services/orchestrator/src/agent_prompt.py` — 单聊/Flow 共享 system prompt 组合
  - `services/orchestrator/src/agent_executor.py` — Clutch 文本/MCP/生图与 CLI 分流
  - `services/orchestrator/src/workflow_runtime.py` — 逐步 step callback
  - `services/orchestrator/src/workflow_projection.py` — 终态投影消息 id 去重
  - `services/orchestrator/src/main.py` — `_apply_workflow_step_patch` + Flow 启动注册 callback
  - `services/orchestrator/src/run_log_forwarder.py` — `emit_state_patch`
  - `workflows/weather-to-vision.json` — Researcher → Artist 线性模板
  - `apps/desktop/src/App.tsx` — Flow 启动前 `await clutchStore.connect`
  - `apps/desktop/src/services/clutchState.ts` — `optimisticWorkflowStart`
  - `services/orchestrator/tests/test_node_input.py` — D23 输入解析
  - `services/orchestrator/tests/test_workflow_handoff.py` — 两节点接力
  - `services/orchestrator/tests/test_workflow_projection.py` — 增量消息去重
  - `services/orchestrator/tests/test_workflow_step_patch.py` — step state_patch
  - `services/orchestrator/tests/test_agent_executor.py` — Clutch prompt + 上游生图

### OLLAMA-LOCAL-ROUTING ✅
- **日期：** 2026-06-26
- **Commit：** `e94bcc7` — `feat(orchestrator,desktop): add Ollama routing with per-agent model selection`
- **Verification：** `uv run pytest` → 242 pytest passed
- **证据：** `—`（门禁已覆盖）
- **交付文件：**
  - `services/orchestrator/src/adapters/ollama_adapter.py` — Ollama 适配器，支持动态扫描本地模型及自动推理排序打分，封装本地 chat completions 交互。
  - `services/orchestrator/src/engine_router.py` — 支持 Ollama 引擎标准化映射识别与分流，返回具体调用的模型标签如 `Ollama (qwen3.6:35b)`。
  - `services/orchestrator/src/agent_executor.py` — 将 `ollama` / `ollama-cli` 添加到 Agent 执行的工具白名单中。
  - `services/orchestrator/tests/test_ollama_adapter.py` — 新增单元测试文件覆盖本地模型过滤、评分及接口请求模拟。
  - `services/orchestrator/tests/test_engine_router.py` — 扩展 Ollama 引擎的路由调度与不可用兜底单元测试。

### SUBPROCESS-MCP-HANGS-FIX ✅
- **日期：** 2026-06-26
- **Commit：** `5df2a9c` — `fix(orchestrator): resolve subprocess and MCP client hangs in chat sessions`
- **Verification：** `./scripts/verify.sh` → 232 pytest + vitest + build passed（pre-commit）
- **证据：** `—`（门禁已覆盖，且 pytest 运行耗时从分钟级缩短至 26 秒）
- **交付文件：**
  - `services/orchestrator/src/adapters/cli_adapter.py` — `_run_cli_streaming` / `run_cli` 注入 `stdin=subprocess.DEVNULL` 解决子进程 TTY 挂起问题。
  - `services/orchestrator/src/mcp_client.py` — `_read_response` 重构为基于绝对 Deadline 的累计超时；`start()` 注入 npm/npx 环境变量优化启动速度。
  - `services/orchestrator/tests/conftest.py` — `isolate_orchestrator_globals` fixture 注入 `CLUTCH_E2E_FAKE_LLM="1"` 隔离测试外部网络 API 请求。

### GIT-BRANCH-FOOTER-LOG-STAMP ✅
- **日期：** 2026-06-25
- **Commit：** `7ee8f43` — `fix(ui,orchestrator): git branch footer, log timestamps, MCP gates, models UI`
- **Verification：** `./scripts/verify.sh` → 218 pytest + vitest + build passed（pre-commit）
- **证据：** pre-commit hook output（`7ee8f43`）
- **交付文件：**
  - `services/orchestrator/src/workspace.py` — `get_git_info()` 本地 git 分支探测。
  - `services/orchestrator/src/main.py` — `GET /api/workspace/git`；terminal_logs 全链路 `stamp_log_line`；MCP supervisor 门控去重。
  - `services/orchestrator/src/terminal_logs.py` — `stamp_log_line` / `china_log_timestamp`。
  - `services/orchestrator/src/mcp_risk.py` — `source`/`destination` 路径参数键。
  - `apps/desktop/src/services/workspaceApi.ts` — `fetchWorkspaceGit()`。
  - `apps/desktop/src/App.tsx` — footer 显示真实 Git 分支；运行后/Files 标签刷新文件树。
  - `apps/desktop/src/components/ModelsManager.tsx` — UI 简化；移除 credential_hint。
  - `services/orchestrator/tests/test_workspaces_api.py` — git 端点测试。
  - `services/orchestrator/tests/test_terminal_logs.py` — stamp 幂等测试。

### ORCHESTRATOR-LOG-STREAMING ✅
- **日期：** 2026-06-25
- **Commit：** `973857c` — `refactor(orchestrator): unify agent execution, LLM HTTP, workflow projection, and main wiring`
- **Verification：** `./scripts/verify.sh` → 218 pytest passed
- **证据：** `—`（门禁已覆盖）
- **交付文件：**
  - `services/orchestrator/src/run_log_forwarder.py` — 运行日志 WS 转发。
  - `services/orchestrator/src/workflow_projection.py` — 图状态投影。
  - `services/orchestrator/src/llm/http_complete.py` — HTTP 补全与流式日志。
  - `services/orchestrator/src/agent_executor.py` — 执行链路与日志对齐。
  - `services/orchestrator/tests/test_run_log_forwarder.py` — 转发器单元测试。
  - `services/orchestrator/tests/test_workflow_log_streaming.py` — 工作流日志流测试。

### MODELS-MCP-VIDEO-CORE ✅
- **日期：** 2026-06-25
- **Commit：** `553714d`…`3ae36a8`（`d5566fb`、`91955f2`、`8d89768`、`a8d199c`、`4e812bb`、`0c8b087`、`77f73f0`）
- **Verification：** `./scripts/verify.sh` → 218 pytest + vitest passed
- **证据：** `—`（多 commit 批次；最终以 `7ee8f43` 门禁为准）
- **交付文件：**
  - `services/orchestrator/src/credentials/sources.py` — 凭证来源解析与 CC Switch 导入。
  - `services/orchestrator/src/models_config.py` — rehydrate-cc-switch、verify 缓存、credential 标签。
  - `services/orchestrator/src/mcp_react.py` — MCP ReAct 真执行与测试 mock 隔离。
  - `services/orchestrator/src/skills_storage.py` — 默认 skills 自动挂载。
  - `services/orchestrator/src/video_core/` — pipeline / renderer / config 骨架。
  - `apps/desktop/src/components/ModelsManager.tsx` — 模型配置 UI 改版。
  - `apps/desktop/src/App.tsx` — footer Model/Engine 切换逻辑。
  - `apps/desktop/src/mockData.ts` — 删除（去 mock 化）。
  - `services/orchestrator/tests/test_models_config_api.py` — 模型 API 测试扩充。
  - `services/orchestrator/tests/test_video_core/` — Video Core 测试套件。

### AGENT-ID-CHAT-ROUTING ✅
- **日期：** 2026-06-25
- **Commit：** `6cc6c6b` — `feat(chat): route plain chat by agent_id and allow builtin agent customization`
- **Verification：** `./scripts/verify.sh` → 138 pytest + vitest + check-doc-drift passed
- **证据：** pre-commit hook output（`6cc6c6b`）
- **交付文件：**
  - `services/orchestrator/src/main.py` — WebSocket `agent_id`；`_llm_chat_reply` / `_handle_plain_chat` 按 Agent 解析并注入 system prompt。
  - `services/orchestrator/src/agent_storage.py` — `get_agent_by_id`；内置 Agent 覆盖持久化与 `save_agents` 规范化。
  - `apps/desktop/src/services/clutchState.ts` — `submitChatMessage(text, agentId?)` 附带 `agent_id`。
  - `apps/desktop/src/App.tsx` — 发送聊天时传 `selectedAgentId`。
  - `apps/desktop/src/components/AgentManager.tsx` — 内置 Agent 可编辑；persist 保留 builtin 行。
  - `apps/desktop/src/services/agentApi.ts` — `saveAgents` 提交完整列表。
  - `services/orchestrator/tests/test_agents_api.py` — builtin override 与 `get_agent_by_id` 测试。
  - `services/orchestrator/tests/test_ws_message_log.py` — `agent_id` system prompt 注入与回复标签测试。

### ENGINE-ROUTER-CLI-ADAPTER ✅
- **日期：** 2026-06-25
- **Commit：** `eaf2ea0` — `feat(routing): implement clutch AI agent engine routing refactor, add Claude CLI adapter, routing tests, and test storage isolation`
- **Verification：** `./scripts/verify.sh` → 138 pytest + vitest + check-doc-drift passed
- **证据：** `runs/verification/`（会话内 verify；commit `eaf2ea0`）
- **交付文件：**
  - `services/orchestrator/src/engine_router.py` — `route_engine` / `find_agent`；Claude CLI / Cursor / 全局 LLM 三分流。
  - `services/orchestrator/src/adapters/claude_cli_adapter.py` — `chat_claude_cli` 封装本地 `claude -p`。
  - `services/orchestrator/src/agent_executor.py` — `execute_agent_task` 经 `route_engine` + `fallback_tool`。
  - `services/orchestrator/src/main.py` — plain chat 改走 `route_engine`（初版，后续 `6cc6c6b` 增强 agent_id）。
  - `services/orchestrator/src/agent_storage.py` — 内置 Clutch Agent 注入 `list_agents`。
  - `apps/desktop/src/services/builtinAgent.ts` — 前端内置 Agent 定义与 `mergeAgentsWithBuiltin`。
  - `apps/desktop/src/App.tsx` — 默认选中内置 Agent、`localStorage` 持久化。
  - `apps/desktop/src/components/AgentManager.tsx` — 内置 Agent UI 集成。
  - `services/orchestrator/tests/conftest.py` — `CLUTCH_STORAGE_DIR` 测试隔离。
  - `services/orchestrator/tests/test_claude_cli_adapter.py` — CLI 参数拼装单元测试。
  - `services/orchestrator/tests/test_engine_router.py` — 路由决策单元测试（6 场景）。
  - `services/orchestrator/tests/test_agents_api.py` — 内置 Agent API 测试。

### MCP-AND-I18N-COMPLETION ✅
- **日期：** 2026-06-25
- **Commit：** `0b90000` — `feat(mcp,i18n): implement full stdio MCP client, raw JSON editor, claude scanner import and fix dynamic backend/frontend English translations`
- **Verification：** `./scripts/verify.sh` → 128 pytest + vitest + check-doc-drift passed
- **证据：** `runs/verification/2026-06-25-mcp-i18n-verify.log`
- **交付文件：**
  - `services/orchestrator/src/mcp_client.py` — Synchronous stdio JSON-RPC 2.0 client for MCP server handshakes and tool executions.
  - `services/orchestrator/tests/test_mcp_client.py` — Lifecycle tests for MCP subprocess clients.
  - `services/orchestrator/tests/test_mcp_api_extensions.py` — Integration tests for raw JSON edits and Claude imports.
  - `services/orchestrator/src/preferences_storage.py` — Implement thread-safe dynamic translation helper `tr(en, zh)`.
  - `services/orchestrator/src/main.py` — Integrate `tr()` in HTTP exception responses, websocket status logs, and evaluator gate alerts.
  - `services/orchestrator/src/workspace.py` — Wrap all folder/file path access failures in `tr()`.
  - `services/orchestrator/src/mcp_storage.py` — Dynamic translation for MCP registrations.
  - `services/orchestrator/src/workflow_storage.py` — Dynamic translation for workflow loader and save logic.
  - `services/orchestrator/src/workflow_validator.py` — i18n support for graph schema validators.
  - `services/orchestrator/src/evaluator.py` — Localize evaluator checks error outputs.
  - `services/orchestrator/src/adapters/cursor_adapter.py` — Translate macOS specific command exceptions.
  - `services/orchestrator/src/adapters/cli_adapter.py` — Translate empty CLI validations.
  - `apps/desktop/src/components/LanguageContext.tsx` — Export `translateText`, add translation keys for workflow panel, delete confirmations, and JSON structures.
  - `apps/desktop/src/components/WorkflowJsonPanel.tsx` — Localize JSON schema description.
  - `apps/desktop/src/components/WorkflowOrchestration.tsx` — Translate workflow canvas, templates list, buttons, delete popups, and error messages.
  - `apps/desktop/src/App.tsx` — Wrap stop run confirm alert message.
  - `apps/desktop/src/services/clutchState.ts` — Translate evaluator validation status suffix.
  - `apps/desktop/src/services/workflowFormat.ts` — Set default end node label to English.
  - `apps/desktop/src/services/workflowApi.ts` — Convert default API error text to English and update delimiters.

### DEV-PROD-ISOLATION-POINTER-DRAG ✅
- **日期：** 2026-06-25
- **Commit：** `01a88dd` — `feat(storage,ui): isolate dev/prod storage directories, custom pointer drag-and-drop, and chat feed stop option`
- **Verification：** `./scripts/verify.sh` → 119 pytest + 1 vitest passed
- **证据：** `runs/verification/2026-06-25-storage-drag-verify.log`
- **交付文件：**
  - `services/orchestrator/src/storage_helper.py` — Isolation utility for DEV (`clutch_dev`) vs PROD (`clutch`) base storage path.
  - `services/orchestrator/tests/test_storage_helper.py` — Unit tests for DEV vs PROD base storage paths and overrides.
  - `services/orchestrator/src/agent_storage.py` — Refactor storage directories to use `storage_helper`.
  - `services/orchestrator/src/credentials/sources.py` — Refactor storage directories to use `storage_helper`.
  - `services/orchestrator/src/mcp_storage.py` — Refactor storage directories to use `storage_helper`.
  - `services/orchestrator/src/models_config.py` — Refactor storage directories to use `storage_helper`.
  - `services/orchestrator/src/preferences_storage.py` — Refactor storage directories to use `storage_helper`.
  - `services/orchestrator/src/run_history.py` — Refactor storage directories to use `storage_helper`.
  - `services/orchestrator/src/skills_storage.py` — Refactor storage directories to use `storage_helper`.
  - `services/orchestrator/src/tools_status.py` — Refactor storage directories to use `storage_helper`.
  - `services/orchestrator/src/workflow_storage.py` — Refactor storage directories to use `storage_helper`.
  - `services/orchestrator/src/workspace.py` — Refactor storage directories to use `storage_helper`.
  - `services/orchestrator/tests/test_credential_sources.py` — Refactor storage directories to use `storage_helper`.
  - `apps/desktop/src/sidebar.tsx` — Re-implement workspace drag-and-drop using custom React pointer events rather than HTML5 Drag-and-Drop.
  - `apps/desktop/src/App.tsx` — Improve sequential repository group movement and pass active session settings.
  - `apps/desktop/src/components/ChatFeed.tsx` — Polish plain LLM session UI, rendering model name info and adding run stop button.

### UI-GROUP-DRAG-AND-DROP ✅
- **日期：** 2026-06-24
- **Commit：** `d4d116b` — `feat(ui): distinguish group icons, virtual default group, group CRUD, drag-and-drop, and right-click move`
- **Verification：** `./scripts/verify.sh` → 116 pytest + vitest passed
- **证据：** `runs/verification/2026-06-24-group-drag-verify.log`
- **交付文件：**
  - `apps/desktop/src/components/LanguageContext.tsx` — Add translations for group actions.
  - `apps/desktop/src/sidebar.tsx` — Folder special icons, default group virtual wrapping, HTML5 Drag-and-Drop dragover/drop handlers, right-click group menus and workspace move submenu.
  - `apps/desktop/src/App.tsx` — Implement delete group, rename group, and move project API handlers, pass callbacks to Sidebar.

### UI-CUSTOM-DIALOGS ✅
- **日期：** 2026-06-24
- **Commit：** `f1e0eac` — `feat(ui): delete reload and add custom PromptModal to replace native prompt and confirm`
- **Verification：** `./scripts/verify.sh` → 116 pytest + vitest passed
- **证据：** `runs/verification/2026-06-24-custom-dialog-verify.log`
- **交付文件：**
  - `apps/desktop/src/App.tsx` — Add custom PromptModal component, implement non-blocking modal states to replace window.prompt/confirm for deleting projects, sessions, and creating groups.
  - `apps/desktop/src/components/LanguageContext.tsx` — Add modal translations for prompt fields, confirmation alerts, and button labels.
  - `apps/desktop/src/sidebar.tsx` — Remove "Reload" context menu item and its separator line.

### UI-DELETE-NAV-SYNC ✅
- **日期：** 2026-06-24
- **Commit：** `0a0a74c` — `feat(ui): prevent ghost session on new chat and auto navigate on delete`
- **Verification：** `./scripts/verify.sh` → 116 pytest + vitest passed
- **证据：** `runs/verification/2026-06-24-delete-navigation-verify.log`
- **交付文件：**
  - `apps/desktop/src/App.tsx` — Prevent creating sessions immediately on New Chat click, and implement auto-navigation to the next available session or temporary landing page upon deletion.

### UI-FIXES-RELOAD-THINKING ✅
- **日期：** 2026-06-24
- **Commit：** `31752ce` — `feat(ui): add reload to context menu and show thinking animation during runs`
- **Verification：** `./scripts/verify.sh` → 116 pytest + vitest passed
- **证据：** `runs/verification/2026-06-24-rightclick-thinking-verification.log`
- **交付文件：**
  - `apps/desktop/src/sidebar.tsx` — Add StopPropagation to context menu, add custom "Reload" action
  - `apps/desktop/src/components/LanguageContext.tsx` — Add Chinese translations for Reload, Thinking..., and Clutch Agent
  - `apps/desktop/src/index.css` — Define wave keyframe and bounce animation for thinking dots
  - `apps/desktop/src/components/ChatFeed.tsx` — Render bouncing dots when LLM is thinking and add auto-scroll logic

### UI-FIXES ✅
- **日期：** 2026-06-24
- **Commit：** `725f6b5` — `feat(ui): fix multiple UI and backend interaction issues`
- **Verification：** `./scripts/verify.sh` → 116 pytest + vitest passed
- **证据：** `runs/verification/2026-06-24-ui-fixes-verify.log`
- **交付文件：**
  - `apps/desktop/src/App.tsx` — Compute and pass sessionTitle to ChatFeed, handle deletions
  - `apps/desktop/src/components/ChatFeed.tsx` — User messages on the right, AI/Agents on the left, hide empty state for existing sessions
  - `apps/desktop/src/components/LanguageContext.tsx` — Delete prompt translations
  - `apps/desktop/src/services/runApi.ts` — deleteSession API
  - `apps/desktop/src/sidebar.tsx` — Traffic lights removal, local context menu state and UI
  - `services/orchestrator/src/credentials/claude_code.py` — Dynamic model name formatting
  - `services/orchestrator/src/main.py` — Immediate echo, local time, DELETE /api/runs/{run_id} endpoint
  - `services/orchestrator/src/run_history.py` — delete_session metadata deletion
  - `services/orchestrator/src/run_state_store.py` — delete_run_state file deletion
  - `services/orchestrator/tests/test_run_history.py` — test_delete_session_api test case
  - `services/orchestrator/tests/test_ws_message_log.py` — updated WS assertions for plain chat sequence
  - `services/orchestrator/tests/test_ws_state_patch.py` — updated WS assertions for connect state

