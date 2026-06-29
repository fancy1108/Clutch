# Archive Notice

This file is archived and read-only.

Do not append new records here.

For current project state, see:

- memory/PROGRESS.md
- memory/DELIVERABLES.md
- memory/ROADMAP.md

Archived on: 2026-06-29
Reason: post-MVP iteration batch archived

---

# DELIVERABLES Archive — POST-MVP

- **日期：** 2026-06-29
- **Commit：** `8ecc3a7` — `fix(orchestrator): fix tuple unpacking crash in plain chat human decision resume`
- **Verification：** `cd services/orchestrator && uv run pytest tests/test_ws_message_log.py -k test_ws_plain_chat_mcp_approve` → 1 passed
- **证据：** `runs/verification/2026-06-29-mcp-approval-unpack-fix.log`
- **交付文件：**
  - `services/orchestrator/src/main.py` — 修复 _handle_plain_chat_mcp_decision 解包 _llm_chat_reply 返回值时的参数数量不匹配崩溃问题，补齐 shell_recovered，并更新 shell_session_status 和 cli_session 偏好补丁
  - `services/orchestrator/tests/test_ws_message_log.py` — 新增 test_ws_plain_chat_mcp_approve websocket 集成测试

### DEFAULT-MULTI-AGENT-AND-HIDE-TOGGLE ✅
- **日期：** 2026-06-29
- **Commit：** `c7213bf` — `feat(ui): remove single/multi-agent toggle and default to multi-agent mode`
- **Verification：** `./scripts/verify.sh` → build + vitest + pytest (471 passed)
- **证据：** `—`（门禁已覆盖）
- **交付文件：**
  - `apps/desktop/src/components/Header.tsx` — 移除 Single Agent / Multi-Agent 模式切换按钮组件
  - `apps/desktop/src/App.tsx` — 将 `isMultiAgent` 默认状态置为 `true`；加载 session 时忽略存储的 single mode 并默认进入 Multi-Agent 模式

### FLOW-REFINE ✅
- **日期：** 2026-06-28
- **Commit：** `0be4e89` — `feat(flow): add pause/refine/continue with @agent hybrid after workflow`
- **Verification：** `./scripts/verify.sh` → build + vitest 33 + pytest（含 `test_flow_refine.py` 11、`test_visual_narrative_flow.py`）
- **证据：** `—`（门禁已覆盖）
- **交付文件：**
  - `services/orchestrator/src/flow_refine.py` — `@` mention 解析、session 重建、`final_image_prompt` 生图精修、`/continue` 续跑
  - `services/orchestrator/src/main.py` — `refining` 状态、`_prepare_workflow_refine_state`、完成后精修路由
  - `services/orchestrator/src/runtime_config.py` — `flow_refine` Hybrid 资格
  - `packages/shared-types/index.ts` — `refining` 状态与 refine 字段
  - `apps/desktop/src/components/ChatInputBar.tsx` — 精修模式 `@` Agent 选择器
  - `apps/desktop/src/components/ChatFeed.tsx` · `App.tsx` — `isWorkflowRefineEligible` / `shouldRouteWorkflowRefine`
  - `apps/desktop/src/services/workflowAgentSteps.ts` — 带空格 Agent 名 mention 解析
  - `docs/PRODUCT_INTRO.md` — §3.1 精修 UX 产品说明
  - `services/orchestrator/tests/test_flow_refine.py` — 精修单测

### SIDEBAR-GROUP-ICONS-REDESIGN ✅
- **日期：** 2026-06-28
- **Commit：** `e7bee5f` — `style(design): redesign repository group icons and support open/collapsed states`
- **Verification：** `./scripts/verify.sh` → 408 passed, 1 warning (100% success) ✅
- **证据：** `—`（门禁已覆盖）
- **交付文件：**
  - `apps/desktop/src/components/ui/LegacyIcon.tsx` — 导入 `Folders`，实现自定义的 `FoldersOpen` 堆叠文件夹 icon 并在 `ICON_MAP` 中进行映射。
  - `apps/desktop/src/sidebar.tsx` — 更新自定义和默认 Repository Group 的 icon，依据 `groupCollapsed` / `defaultGroupCollapsed` 状态动态渲染 `folder_special` 或 `folder_special_open`。

### AUTO-CONFIG-PROBING-AND-INSTALL-GUIDE ✅
- **日期：** 2026-06-28
- **Commit：** `<pending>` — `feat(hybrid): add AI-probing auto configuration and install guides for CLI tools`
- **Verification：** `uv run pytest` -> 411 passed, 1 warning (100% success) ✅, `pnpm build` in apps/desktop -> 100% success ✅
- **证据：** `—`（门禁已覆盖）
- **交付文件：**
  - `services/orchestrator/src/tools_status.py` — 支持 `list_tools_status(include_all=True)` 并返回 `registered` 状态；实现了 `auto_configure_cli_via_llm`，它执行二进制文件的 `--help`，调用默认大模型对文本进行识别解析，自动推导出适配参数。
  - `services/orchestrator/src/main.py` — `/api/tools/status` 调用 `list_tools_status(include_all=True)`，新增了 POST `/api/tools/auto-configure` 端点。
  - `services/orchestrator/src/engine_router.py` — 补充了 `load_custom_cli_configs` 和 `save_custom_cli_configs` 帮助函数，在 `CLI_ROUTING_CONFIGS` 加载时自动读取并合并 `custom_clis.json` 配置。
  - `services/orchestrator/tests/test_tools_status.py` — 编写了 `test_auto_configure_cli_via_llm` 单元测试。
  - `apps/desktop/src/services/toolsApi.ts` — 在 `AiToolStatus` 接口中增加 `registered` 字段，实现 `autoConfigureTool` 前端接口函数。
  - `apps/desktop/src/components/AiToolsManager.tsx` — 重构 UI，将工具归类为 Connected、Detected、Available to Install。为未注册工具展示 Unconfigured 警告角标并提供一键 Auto Config 按钮，为未安装工具实现带有展开功能的一键复制代码安装指南，且在全无工具安装时提供置顶显目引导横幅。

### GENERIC-CLI-ROUTING-AND-CONFIG-DISPATCH ✅
- **日期：** 2026-06-28
- **Commit：** `<pending>` — `feat(hybrid): unify CLI agent routing under a central config-driven registry`
- **Verification：** `uv run pytest` -> 408 passed, 1 warning (100% success) ✅
- **证据：** `—`（门禁已覆盖）
- **交付文件：**
  - `packages/frontend/src/assets/agy-logo.svg` — 替换为了炫彩无限循环 SVG 图标，对齐品牌视觉。
  - `services/orchestrator/src/models_config.py` — 将设置键匹配项由 `active_model` 修正为 `agent_active_model`，修复模型覆写退化问题。
  - `services/orchestrator/src/agent_prompt.py` — 修复系统提示词，当使用外部 CLI 时不写入 `Runtime model: ...` 配置。
  - `services/orchestrator/src/engine_router.py` — 定义了中心化 `CLI_ROUTING_CONFIGS` 配置表，将 Claude 和 Antigravity 路由去重重构，提取为完全通用的 `_route_generic_cli_hybrid` 和 `_route_generic_cli_legacy` 函数，同时为单测保持了向下兼容代理并消除了 TypeError 重复传参冲突。

### ANTIGRAVITY-CLI-SESSION-TRACKING ✅
- **日期：** 2026-06-28
- **Commit：** `b1ff689` — `fix(hybrid): support multi-turn session ID tracking for Antigravity CLI`
- **Verification：** `./scripts/verify.sh` → 408 passed, 1 warning (100% success) ✅
- **证据：** `—`（门禁已覆盖）
- **交付文件：**
  - `services/orchestrator/src/adapters/agy_cli_adapter.py` — 对 `chat_agy_cli` 进行了改造，支持在首轮对话传入 `--conversation` 以生成统一的 UUID 会话 ID。
  - `services/orchestrator/src/shell_exec_runtime.py` — 在 `run_agy_turn` 中接收并传递 `new_session_id` 到 `_execute_hybrid_turn`，解决 hybrid 运行时首次执行的 ID 生成问题。
  - `services/orchestrator/src/engine_router.py` — 修改 `_route_agy_hybrid` 和 `_agy_legacy` 逻辑，若未找到 `cli_session_id` 则首轮对话自动生成 UUID 形式的 `new_session_id` 并持久化，后续轮次继续引用该 ID。
  - `services/orchestrator/tests/test_agy_cli_adapter.py` — 增加 `test_chat_agy_cli_new_session` 测试用例验证首轮对话的参数传递。

### PTY-DECODING-AND-CLI-PROMPT-FIX ✅
- **日期：** 2026-06-28
- **Commit：** `f0b78c1` — `fix(hybrid): correct PTY decoding, CLI agent prompts, brand sanitization, and Antigravity logo`
- **Verification：** `./scripts/verify.sh` → 407 passed, 1 warning (100% success) ✅
- **证据：** `—`（门禁已覆盖）
- **交付文件：**
  - `services/orchestrator/src/shell_session.py` — 增量读取字节并在 `read_until_contains`/`read_until_marker` 中通过 incremental decoder 解决 PTY 跨 buffer 乱码问题。
  - `services/orchestrator/src/adapters/cli_adapter.py` — 对 `subprocess` 调用强制声明 `encoding="utf-8"` 和 `errors="replace"`。
  - `services/orchestrator/src/agent_prompt.py` — 仅对 `clutch` (API 直连) 智能体注入 `Runtime model` 指导，排除外部 CLI/hybrid 类型的引擎以防误导。
  - `services/orchestrator/src/engine_router.py` — 在 `route_engine` 中对 `raw_output` 和 `output_events` 均进行品牌 sanitization（Agnes 转换为 Gemini），保证前端一致。
  - `services/orchestrator/tests/test_agent_prompt.py` — 针对 system prompt 中 Runtime model 条件注入逻辑的单元测试。
  - `apps/desktop/src/assets/tool-logos/antigravity.svg` — 重新设计了渐变拱门 SVG Logo，替换掉原先错误的 Google logo。

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

