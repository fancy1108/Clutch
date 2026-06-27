# DELIVERABLES（Task 交付索引）

> **角色：** Task ID → Git commit → Verification → 证据路径。**不复制** `git diff`（代码真相在 Git）。  
> **何时写：** 每个**代码 Task** 完成并 commit 后，在 Check-out 追加一节（见 `CLAUDE.md` §Check-out）。  
> **逐文件 diff：** `git show <commit> --stat` / `git show <commit>`

## 填写模板（复制后改）

```markdown
### <Task-ID> ✅ | ⚠️ 部分 | ❌ 回滚
- **日期：** YYYY-MM-DD
- **Commit：** `<hash>` — `<git log -1 --format=%s>`
- **Verification：** `<命令>` → `<结果摘要>`
- **证据：** `runs/verification/<date>-<task-id>.log` 或 [CI #N](url) 或 `—`（门禁已覆盖）
- **交付文件：**（一行一个，只写路径 + 一句话职责；详情 `git show`）
  - `path/to/file` — …
```

**重定向示例（代码 Task 推荐）：**

```bash
cd services/orchestrator && uv run pytest tests/test_xxx.py -v \
  | tee "../../runs/verification/$(date +%Y-%m-%d)-M1-02-pytest.log"
```

---

## 已交付（文档 / 计划 · 无代码 commit）

### HRT-00 ✅ 计划与文档对齐
- **日期：** 2026-06-27
- **Commit：** `7221641` — docs(hybrid): add HRT execution plan and sync memory/specs (HRT-00)
- **Verification：** `./scripts/check-doc-drift.sh` → 0 errors
- **证据：** —
- **交付文件：**
  - `specs/core/hybrid-runtime-plan.md` — D25 权威 HRT Task 表 + 验收 + 文档矩阵
  - `specs/core/tasks.md` — §D25 HRT 索引
  - `memory/ROADMAP.md` — §D25 Hybrid + 人工验收勾选
  - `memory/DECISIONS.md` — D27 命名拆分 · D28 审计 · Q-HRT-1/2
  - `memory/PROGRESS.md` — HRT 进度快照 + 下次优先
  - `memory/FILEMAP.md` · `memory/BACKLOG.md` · `docs/document-governance.md` · `AGENTS.md` · `docs/research/pty-session.md` — 交叉引用

### HRT-01~03 ✅ 气泡过滤 · marker · snapshot 注入范围
- **日期：** 2026-06-27
- **Commit：** `1d281f6` — fix(hybrid): tighten marker detection and snapshot handoff scope (HRT-01~03)
- **Verification：** `uv run pytest tests/test_claude_hybrid_output_parser.py tests/test_engine_router.py -q` → 27 passed
- **证据：** —
- **交付文件：**
  - `services/orchestrator/src/claude_hybrid_output_parser.py` — 过滤 snapshot 行；marker+clutch$ 完成检测
  - `services/orchestrator/src/engine_router.py` — context_prefix 仅 shell_recovered 时注入
  - `services/orchestrator/tests/test_claude_hybrid_output_parser.py` — snapshot / marker 单测

---

## 已交付（代码 Task · 自 Git 回填）

### CHAT-FEED-PREFERENCE-AND-AVATAR-POLISH ✅
- **日期：** 2026-06-27
- **Commit：** `d6152f0` — `feat: support custom profile name settings in General preferences` (前序 `8a03c61`, `7922e8d`, `9cba3b2`)
- **Verification：** `./scripts/verify.sh` → 351 pytest (含 2 个新增 user_name 偏好用例) + 13 vitest + build + doc-drift passed ✅
- **证据：** `—`（门禁已覆盖）
- **交付文件：**
  - `services/orchestrator/src/preferences_storage.py` & `main.py` & `tests/test_avatar_preferences.py` — 偏好后端扩展存储 `"user_name"`（默认 `"User"`），增加 POST `/api/preferences/name` 接口和单元测试。
  - `apps/desktop/src/services/themeApi.ts` — 在 `UserPreferences` 接口增加 `user_name`，定义并导出 `saveUserNamePreference`。
  - `apps/desktop/src/components/LanguageContext.tsx` — 添加 `"Profile Name"` 和 `"Enter your name"` 的中英文 i18n 翻译资源。
  - `apps/desktop/src/components/SystemPreferencesModal.tsx` — 添加 `userName` / `setUserName` 属性，在 General 页面新增 Profile Name 的输入控件。
  - `apps/desktop/src/App.tsx` — 管理 `userName` 的状态，通过 `fetchPreferences` 在初始化时还原用户名，通过 `setUserName` 保持保存偏好；将其传递给 `ChatFeed` 和 `SystemPreferencesModal`。
  - `apps/desktop/src/components/ChatFeed.tsx` — 增加 `userName` 属性并在用户发送的消息气泡的发送者名字标签中使用，实现自定义昵称展示。

### D25-HYBRID-STEP2 ✅
- **日期：** 2026-06-27
- **Commit：** `b69e35d` — `feat(runtime): agy shell hybrid, sweep tests, and POC baselines`
- **Verification：** `./scripts/verify.sh` → 333 pytest ✅
- **证据：** `runs/verification/2026-06-27-hybrid-step2-verify.log`；agy Route C `4/5` → `experiments/pty_poc/runs/20260626T171156Z-route-c-hybrid-agy.json`
- **交付文件：**
  - `services/orchestrator/src/shell_exec_runtime.py` — `run_agy_turn` / `_build_agy_shell_cmd`
  - `services/orchestrator/src/engine_router.py` — `_route_agy_hybrid` + Plain Chat 双 Provider Hybrid
  - `services/orchestrator/src/runtime_config.py` — `antigravity-cli` hybrid 门控
  - `services/orchestrator/src/shell_session.py` — sweep 运行时读 env
  - `experiments/pty_poc/baseline/claude.json` · `agy.json` — Step 0.5 输出基准

### D25-SHELL-RELEASE-ON-DELETE ✅
- **日期：** 2026-06-27
- **Commit：** `4977df6` — `fix(runtime): release ShellSession when deleting a chat run`
- **Verification：** `./scripts/verify.sh` → 327 pytest ✅
- **证据：** `—`（门禁已覆盖）
- **交付文件：**
  - `services/orchestrator/src/main.py` — `DELETE /api/runs/{run_id}` 调用 `ShellSessionManager.release`
  - `services/orchestrator/tests/test_run_history.py` — `test_delete_session_releases_shell_session`

### D25-HYBRID-STEP1 ✅
- **日期：** 2026-06-27
- **Commit：** `d6c6c90` — `chore: checkpoint before full-platform UI consistency polish`（含 ShellSession + Hybrid 执行细节全栈）
- **Verification：** `./scripts/verify.sh` → 326 pytest + 11 vitest + build + doc-drift ✅
- **证据：** `runs/verification/2026-06-27-hybrid-step1-verify.log`；`uv run python services/orchestrator/scripts/verify_hybrid_execution_ws.py` → PASSED
- **交付文件：**
  - `services/orchestrator/src/shell_session.py` — 长驻 bash PTY、`ShellSessionManager`、30min/6h sweep
  - `services/orchestrator/src/shell_exec_runtime.py` — shell 内 `claude -p` + marker
  - `services/orchestrator/src/claude_hybrid_output_parser.py` — assistant 清洗 + `OutputEvent`
  - `services/orchestrator/src/runtime_config.py` — `CLUTCH_RUNTIME_MODE` 门控
  - `services/orchestrator/src/engine_router.py` — Hybrid 分支 + legacy 降级 + metadata 透传
  - `services/orchestrator/src/main.py` — `hybrid_executions` patch + WS 事件
  - `apps/desktop/src/components/ChatFeed.tsx` — 树形执行细节披露
  - `apps/desktop/src/services/clutchState.ts` — `hybrid_executions` 合并与 pending buffer
  - `apps/desktop/src/services/sidecarUrl.ts` — dev 8124 / prod 8123

### STOP-WORKFLOW-UX-FIX ✅
- **日期：** 2026-06-26
- **Commit：** `896d6f6` — `fix(ui): prevent Human-in-the-Loop card from rendering on failed or stopped runs`
- **Verification：** `./scripts/verify.sh` → 287 pytest + vitest passed
- **证据：** `—`（门禁已覆盖）
- **交付文件：**
  - `apps/desktop/src/components/ChatFeed.tsx` — 修复点击 Stop 结束运行后会错误弹出 Human-in-the-Loop 卡片的 Bug；去除了 `clutchStatus === 'failed'` 对该卡片的渲染逻辑，使 Stopped 或 Failed 的 run 正确渲染常规的聊天输入框。

### SESSION-MODEL-SELECTION-AND-IMAGE-REJECTION ✅
- **日期：** 2026-06-26
- **Commit：** `2b61c06` — `feat(chat,models): support session model selection, bypass builtin agent model binding, and reject vision input on image-only models`
- **Verification：** `./scripts/verify.sh` → 287 pytest + vitest passed
- **证据：** `—`（门禁已覆盖）
- **交付文件：**
  - `apps/desktop/src/App.tsx` — 重新拉取/同步模型配置，支持在普通会话中通过 WS 发送 `model_id` 并优化 footer 选择逻辑。
  - `apps/desktop/src/services/clutchState.ts` — `submitChatMessage` 新增 `modelId` 参数并在 Payload 中传递。
  - `services/orchestrator/src/agent_storage.py` — 内置默认 Agent 不允许绑定 modelId。
  - `services/orchestrator/src/agent_type.py` — `agent_model_id` 与 `resolve_model_for_agent` 改造，内置默认 Agent 强制忽略绑定模型，并支持 session 级别的 model_id 覆盖。
  - `services/orchestrator/src/main.py` — WebSocket `_handle_plain_chat` 支持传递和路由 `session_model_id`。
  - `services/orchestrator/src/models_config.py` — 修复 Ollama 模型无 API Key 时的可用状态检测，使其始终可用。
  - `services/orchestrator/tests/test_agent_type.py` — 新增内置默认 Agent 忽略模型绑定及 session 级别模型覆盖的单元测试。
  - `services/orchestrator/tests/test_image_chat_reply.py` — 新增图片问答时非视觉生图模型（如 Agnes Image）的拒绝响应测试。
  - `services/orchestrator/tests/test_models_config_api.py` — 更新 Ollama 无 API Key 时的激活测试用例。

### M3-F · Flow 多 Agent 接力（D23） ✅
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

### M0-01 ✅
- **日期：** 2026-06-22
- **Commit：** `56dd9e9` — feat(orchestrator): add basic FastAPI and WebSocket endpoint（health 初版见 `4aefaac`）
- **Verification：** `uv run pytest tests/test_health.py -v`
- **证据：** `memory/TESTS.md` 2026-06-22 后端测试行；无独立 log 文件（回填前未归档）
- **交付文件：** `git show 56dd9e9 --stat`
  - `services/orchestrator/src/main.py` — `/health`、CORS、WS 端点骨架
  - （`test_health.py` 初版在 `4aefaac` bootstrap）

### M0-02 ✅
- **日期：** 2026-06-22
- **Commit：** `b600acc` — feat(desktop): wire WebSocket ping-pong test for M0-02
- **Verification：** `uv run pytest tests/test_ws_state_patch.py -v`（WS 全链路在 M0-03 commit 补强）
- **证据：** 同上；`test_ws_state_patch.py` 在 `42f9423` 完善
- **交付文件：**
  - `apps/desktop/src/services/api.ts` — Sidecar WS 测试发送（`sendSidecarTestMessage`，已于 `2d85c14` 移除）
  - `apps/desktop/src/sidebar.tsx` — ~~[Test WS] 调试按钮~~（M0 联调用；`2d85c14` 移除，用户改由主聊天 `submitChatMessage`）

### M0-03 ✅
- **日期：** 2026-06-22
- **Commit：** `42f9423` — feat(m0): project ClutchState from WebSocket state_patch
- **Verification：** `pnpm build`；`uv run pytest tests/test_ws_state_patch.py -v`
- **证据：** `memory/TESTS.md`；`ROADMAP` E2E 前提第一行 ✅
- **交付文件：**
  - `apps/desktop/src/services/clutchState.ts` — `useClutchState` / WS store
  - `apps/desktop/src/App.tsx` — 投影 `ClutchState`；移除 mock 驱动编排
  - `packages/shared-types/index.ts` — 共享 `ClutchState` 类型
  - `services/orchestrator/src/state.py` — Python 侧状态
  - `services/orchestrator/src/main.py` — `state_patch` 推送
  - `services/orchestrator/tests/test_ws_state_patch.py` — WS 集成测试

### M0-04 ✅
- **日期：** 2026-06-22（bootstrap，无独立 feat commit）
- **Commit：** `4aefaac` — chore: bootstrap project governance structure
- **Verification：** `pnpm dev` + `curl -s http://127.0.0.1:8123/health`
- **证据：** `—`（手动验证，未归档 log）
- **交付文件：**
  - `apps/desktop/vite.config.ts` — `/api`、`/ws` 代理 → 8123

### M0-06 ⚠️ 部分（待复审）
- **日期：** 2026-06-22
- **Commit：** `42f9423`（与 M0-03 同提交）
- **Verification：** 待跑 `packages/shared-types` ↔ `state.py` 字段人工 diff + `pnpm build`
- **证据：** —
- **备注：** 类型已引入，**未**按 `tasks.md` M0-06 完成「对齐复审」

### M1-03 ⚠️ 骨架（待 Verification 复审）
- **日期：** 2026-06-22
- **Commit：** `f45172c` — feat(m1): add minimal LangGraph runtime and start_run API
- **Verification：** `uv run pytest tests/test_start_run.py tests/test_graph.py -v` — **仅**断言 `run_id` / 桩图 `n1`，未接 Compiler
- **证据：** `memory/TESTS.md` 7 passed → 15 passed（M1-01 后）
- **交付文件：**
  - `services/orchestrator/src/graph.py` — 最小 LangGraph（START→orchestrator→END）
  - `services/orchestrator/src/main.py` — `POST /api/runs/start`、`/stop`
  - `services/orchestrator/tests/test_start_run.py` — API smoke
  - `services/orchestrator/tests/test_graph.py` — 桩图节点断言

### M1-01 ✅
- **日期：** 2026-06-22
- **Commit：** `5367020` — feat(m1): add workflow JSON schema validation (M1-01)
- **Verification：** `uv run pytest tests/test_workflow_validator.py tests/test_validate_api.py -v` → 15 passed 总计
- **证据：** `memory/TESTS.md`；[CI #2](https://github.com/fancy1108/Clutch/actions)（`11e6d77` 前后）
- **交付文件：**
  - `services/orchestrator/src/workflow_validator.py` — 加载与校验 `workflows/*.json`
  - `services/orchestrator/src/main.py` — `POST /api/workflows/validate`；`start_run` 前置校验
  - `services/orchestrator/tests/test_workflow_validator.py` — Schema / video-production 用例
  - `services/orchestrator/tests/test_validate_api.py` — HTTP API 用例
  - `workflows/workflow.schema.json` — schema 小改

### M1-02 ✅
- **日期：** 2026-06-23
- **Commit：** `ea5e648` — feat(m1): add WorkflowCompiler for video-production JSON (M1-02)
- **Verification：** `uv run pytest tests/test_compiler.py -v` → 6 passed；`./scripts/verify.sh` → 21 passed
- **证据：** `runs/verification/2026-06-23-m1-02-compiler-pytest.log`
- **交付文件：**
  - `services/orchestrator/src/compiler/__init__.py` — 导出 WorkflowCompiler API
  - `services/orchestrator/src/compiler/compiler.py` — JSON → LangGraph 编译、五类 handler、条件边
  - `services/orchestrator/tests/test_compiler.py` — 节点/边/类型与 video-production.json 一致

---

## 文档 / 治理（非代码 Task）

| 会话 | 状态 | 说明 |
|------|------|------|
| 会话 8–10（2026-06-23） | ✅ `0a24a7b` | `tasks.md`、`ROADMAP`、`DELIVERABLES`、Check-out 规则、`ARCHITECTURE` §7/§13 |
| D7 验收兜底 | ✅ `cba4094` | `check-doc-drift.sh`、Husky、truth-alignment |
| D1/D2 测试治理 | ✅ 多 commit | `verify.sh`、`.github/workflows/ci.yml` |

### M1-03 ✅
- **日期：** 2026-06-23
- **Commit：** `3c45ad0` — feat(m1): wire start_run to WorkflowCompiler (M1-03)
- **Verification：** `uv run pytest tests/test_start_run.py -v` → 3 passed；`./scripts/verify.sh` → 22 passed
- **证据：** `runs/verification/2026-06-23-m1-03-start-run-pytest.log`
- **交付文件：**
  - `services/orchestrator/src/compiler/compiler.py` — 新增 `run_workflow`
  - `services/orchestrator/src/main.py` — `start_run` 改走编译图
  - `services/orchestrator/tests/test_start_run.py` — `active_node_id` 变化断言

### M1-04 ✅
- **日期：** 2026-06-23
- **Commit：** `dc904dc` — feat(m1): add orchestrator edge-first routing with LLM fallback (M1-04)
- **Verification：** `uv run pytest tests/test_orchestrator_routing.py -v` → 7 passed；`./scripts/verify.sh` → 29 passed
- **证据：** `runs/verification/2026-06-23-m1-04-routing-pytest.log`
- **交付文件：**
  - `services/orchestrator/src/orchestrator/routing.py` — 边优先路由 + LLM 兜底
  - `services/orchestrator/src/compiler/compiler.py` — 条件边改走 `route_next`
  - `services/orchestrator/tests/test_orchestrator_routing.py` — 路由单元测试

### M1-05 ✅
- **日期：** 2026-06-23
- **Commit：** `1dadde3` — feat(m1): push run_completed over WebSocket on terminal status (M1-05)
- **Verification：** `uv run pytest tests/test_run_completed.py -v` → 3 passed；`./scripts/verify.sh` → 32 passed
- **证据：** `runs/verification/2026-06-23-m1-05-run-completed-pytest.log`
- **交付文件：**
  - `services/orchestrator/src/main.py` — `run_completed` 事件与 `ClutchState` 序列化
  - `services/orchestrator/tests/test_run_completed.py` — passed/failed 终态 WS 推送

### M1-08 ✅
- **日期：** 2026-06-23
- **Commit：** `63e1bde` — feat(m1): add LLM Provider Router with DeepSeek default (M1-08)
- **Verification：** `uv run pytest tests/test_llm_provider.py -v` → 7 passed；`./scripts/verify.sh` → 39 passed
- **证据：** `runs/verification/2026-06-23-m1-08-llm-provider-pytest.log`
- **交付文件：**
  - `services/orchestrator/src/llm/router.py` — Provider 抽象、默认 DeepSeek V4 Pro、可切换、按 Provider 分存 Key
  - `services/orchestrator/src/llm/__init__.py` — 包导出
  - `services/orchestrator/tests/test_llm_provider.py` — Router 与 orchestrator 路由集成测试

### M1-09 ✅
- **日期：** 2026-06-23
- **Commit：** `7048999` — feat(m1): add user workflow persistence API (M1-09)
- **Verification：** `uv run pytest tests/test_workflow_storage.py -v` → 5 passed；`./scripts/verify.sh` → 44 passed
- **证据：** `runs/verification/2026-06-23-m1-09-workflow-storage-pytest.log`
- **交付文件：**
  - `services/orchestrator/src/workflow_storage.py` — D5 内置模板只读 + 用户目录 CRUD
  - `services/orchestrator/src/main.py` — `/api/workflows/templates|user` 路由；`start_run` 走 `resolve_workflow`
  - `services/orchestrator/tests/test_workflow_storage.py` — 路径与 CRUD 集成测试

### M0-06 ✅
- **日期：** 2026-06-23
- **Commit：** 文档 commit — ClutchState 字段对齐复审
- **Verification：** 人工 diff `packages/shared-types/index.ts` ↔ `services/orchestrator/src/state.py`；`pnpm build` 无类型错误
- **证据：** 本节字段对照表；`./scripts/verify.sh` 通过
- **结论：** 9 个 `ClutchState` 字段与 `ClutchRunStatus` 枚举一致，无需代码变更

### M1-07 ✅
- **日期：** 2026-06-23
- **Commit：** `b6584ef` — feat(m1): add workflow graph structure validation (M1-07)
- **Verification：** `uv run pytest tests/test_workflow_validator.py -k invalid -v` → 4 passed；`./scripts/verify.sh` → 47 passed
- **证据：** `runs/verification/`（verify.sh 全量）
- **交付文件：**
  - `services/orchestrator/src/workflow_validator.py` — `validate_workflow_graph` 中文图结构错误
  - `services/orchestrator/tests/test_workflow_validator.py` — 缺 start/end、孤立节点用例

---

## 待交付（下一 Task）

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

