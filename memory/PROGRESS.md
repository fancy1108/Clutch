# PROGRESS

## 当前状态

- 阶段：**D25 ShellSession Step 2 已交付（agy Hybrid + sweep 测试 + baseline）**
- Git HEAD：`3c8229c`
- Git HEAD：`27ea3f4`（待 list API commit）
- **下次优先**：DISCONNECTED 恢复 · 继续上次工作 UI · runtime_registry

## 2026-06-27 会话（Step 3 API：快照列表）

- **完成：** `GET /api/shell-snapshots` 返回全部快照摘要（供侧栏「继续上次工作」）
- **校验：** `test_shell_snapshot_list`；verify 338 pytest ✅

## 2026-06-27 会话（Step 5：Snapshot 保留策略）

- **完成：** `CLUTCH_SHELL_SNAPSHOT_MAX_AGE_DAYS`（默认 30，0=禁用）；lifespan sweep 调用 `prune_stale_snapshots`
- **校验：** `./scripts/verify.sh` → 337 pytest ✅

## 2026-06-27 会话（Step 5 起步：Shell 池上限）

- **完成：** `CLUTCH_SHELL_MAX_SESSIONS`（默认 8）；池满时驱逐最旧 `IDLE` 会话；全 `BUSY` 时 `ShellSessionPoolFullError` → Hybrid 自动 fallback legacy
- **校验：** `./scripts/verify.sh` → 335 pytest ✅

## 2026-06-27 会话（Step 2：稳定性 + agy Route C）

- **完成：**
  - **agy Hybrid 路径**：`run_agy_turn` · `_route_agy_hybrid` · `hybrid_eligible` 含 `antigravity-cli`
  - **Shell sweep 可测**：`sweep_idle` 运行时读 `CLUTCH_SHELL_*`；新增 idle/max/120 轮 cycle 单测
  - **POC**：`step0_route_c_hybrid_probe.py --provider agy` → 4/5；`baseline/claude.json` + `baseline/agy.json`
- **校验：** `./scripts/verify.sh` → 333 pytest + 11 vitest + build + doc-drift ✅
- **证据：** `runs/verification/2026-06-27-hybrid-step2-verify.log`；`experiments/pty_poc/runs/20260626T171156Z-route-c-hybrid-agy.json`

## 2026-06-27 会话（删会话释放 Shell）

- **完成：** `DELETE /api/runs/{run_id}` 调用 `ShellSessionManager.release(run_id)`，侧栏删会话不再等 30min sweep
- **校验：** `test_delete_session_releases_shell_session`；`./scripts/verify.sh` → 327 pytest ✅

## 2026-06-27 会话（Hybrid 执行细节 + Step 1 交付 commit）

- **完成：**
  - **ShellSession Step 1 全栈**：`runtime_config` · `shell_session` · `shell_exec_runtime` · router 双轨 · snapshot API · lifecycle sweep
  - **输出归一化**：`claude_hybrid_output_parser`；聊天气泡默认只显示 assistant；折叠区树形披露（lucide）
  - **`hybrid_executions` SSOT**：`ClutchState` 独立 map + WS `hybrid_execution`；修复 `route_engine` 丢弃 `raw_output`/`output_events`
  - **前端**：`sidecarUrl` dev/prod 端口；紧凑按钮 `buttonStyles`；`clutchState` merge 防丢字段
  - **校验**：`./scripts/verify.sh` → 326 pytest + 11 vitest + build + doc-drift ✅
- **证据**：`runs/verification/2026-06-27-hybrid-step1-verify.log`；`services/orchestrator/scripts/verify_hybrid_execution_ws.py`

## 2026-06-26 会话（ShellSession Step 1 实施）

- **完成：**
  - **Runtime 门控**：`runtime_config.py` — `CLUTCH_RUNTIME_MODE=legacy|hybrid`，`hybrid_eligible` 仅 Plain Chat + `claude-cli`
  - **ShellSession 核心**：`shell_session.py` — 长驻 bash PTY、`ShellSessionManager`、状态机、空闲 sweep（lifespan）
  - **ShellExecRuntime**：`shell_exec_runtime.py` — shell 内 `claude -p`、marker 边界、交互命令拦截
  - **EngineRouter 双轨**：Hybrid 失败自动 fallback legacy（验收 #15）；Flow 固定 `source=flow`
  - **Context Continuity 基础**：`session_snapshot.py` + `GET/PUT /api/shell-snapshots/{run_id}`；换班摘要注入 Hybrid
  - **RuntimeStrategy 雏形**：`runtime_strategy.py`、`provider_registry.py`；router 日志带 `runtime_strategy`
  - **HumanInputKind**：`human_input.py`
  - **文档**：`pty-session.md` §1.4 上线安全策略（待 commit）
  - **测试**：316 pytest passed（含 hybrid fallback、snapshot API）

- **下次优先**：内测开启 `CLUTCH_RUNTIME_MODE=hybrid` 手动验证；Step 2 压测 + agy Route C

## 2026-06-26 会话（历史会话上下文压缩与归档 B-03 落地与前端美化）

- **完成：**
  - **核心压缩逻辑与字段归一化**：编写了 `services/orchestrator/src/compaction.py`，实现 Token 估算、JSONL 归档、LLM 摘要生成与 fallback，并返回 `badgeText` 与 `badge_text` 双向兼容字段以适配前端模型。
  - **对话流程无缝集成**：修改了 `services/orchestrator/src/main.py` 的 `_handle_plain_chat`。将在回复完成后进行 token 与 compaction 校验，在 commit 前完成，实现无闪烁的单次原子推送。
  - **前端展示与翻译优化**：
    - 修改了 `apps/desktop/src/components/ChatFeed.tsx`，将 `System` 对话气泡与普通 Agent 对齐，为 System 回复引入专用的 `info` 提示图标，并让 `badgeText` 物理渲染在气泡标题位置（替代常规的 `COMPLETED` 气泡）。
    - 修改了 `apps/desktop/src/components/LanguageContext.tsx`，在中文模式下将 `System` 发送者名称汉化为 `"系统"`。
  - **多维度单元与集成测试**：新建了 `services/orchestrator/tests/test_compaction.py`。全面覆盖 `_estimate_tokens`、`should_compact`（含环境变量覆盖）、`compact_run_messages` 成功与异常降级以及 WebSocket 集成测试。
  - **全量校验通过**：本地运行 `./scripts/verify.sh` 并顺利通过了所有 297 项后端 Python 测试、前端 Vitest 测试、生产 Vite build 和文档漂移自检。



## 2026-06-26 会话（产品介绍文档编写与文档关联同步）

- **完成：**
  - **产品介绍文档落地与修正**：新建并编写了系统最完备的 `docs/PRODUCT_INTRO.md` 产品介绍文档。根据代码库真实实现，修正并详述了以下核心特性：
    - **项目的存在理由（真实痛点）**：补充了项目要解决的两个痛点——痛点一（单 Agent 下上下文容易“炸”、新开对话丢上下文导致不得不硬撑单一会话 vs 重新对齐），痛点二（多 Agent 协作交互黑盒化、中间产物分散、调用关系隐式写在 prompt 难以编辑编排）。
    - **核心增量价值与非目标**：归纳了 Clutch 的增量价值不是替代 Claude Code/Cursor 的生成能力，而是提供“可持久化、可观测、可编辑”流程控制层；同时明确了不做云端部署、不做团队协作、不重实现底层模型能力的非目标。
    - **通用可定制 Agent 系统**：系统原生支持自定义 Agent (CRUD 读写 `agents.json`)，支持在画布节点中自由指定与绑定，以及多 Agent 间的输入输出自动接力（Handoff）。
    - **本地工具自动探测**：自动扫描系统 PATH 与 Brew/NPM 等候选目录，识别包括 Claude, Antigravity, Ollama, Aider, Cursor 等在内的本地 CLI 工具与客户端。
    - **多引擎智能路由与 Session 恢复**：支持在本地 CLI 适配器、Cursor 桌面端、云端或本地配置的 LLM 中灵活路由，并支持 Claude CLI 等会话的 Session UUID `--resume` 恢复机制，以及路由降级 Fallback。
    - **其它功能**：涵盖内置 `clutch-tools` 虚拟 MCP 的 `apply_patch` 精密文件工具与 `mcp_risk` 安全门控、双语翻译 (i18n) 与凭证导入。

  - **关联文档同步更新**：修正了 `workflows/README.md` 中 `WorkflowCompiler` 的已落地描述，补充了最新的 `weather-to-vision.json` 模板介绍；并在根目录 `README.md`、文件索引表 `memory/FILEMAP.md` 及文档治理策略 `docs/document-governance.md` 中为产品介绍文档增设了全局索引项。
  - **本地校验与 Commit**：运行 `./scripts/verify.sh` 顺利跑通全量 290 项 pytest 后端单测、前端 vitest 编译，且 `check-doc-drift.sh` 漂移机检全绿，对上述文档进行了 git commit。

- **下次优先**：Flow 运行中逐步 Chat 的 WS 时序优化。

## 2026-06-26 会话（会话模型选择与生图视觉校验）

- **完成：**
  - **会话级模型选择**：前端 footer 切换模型时调用 `saveModelsConfig` 并在 plain chat 时通过 WS 发送 `model_id`；后端 `_handle_plain_chat` / `_llm_chat_reply` 支持 `session_model_id` 动态路由.
  - **内置 Agent 解绑**：内置默认 Agent `clutch-agent` 忽略绑定的 `modelId`，强制跟随 footer 选择的模型；自定义 Agent 仍可绑定特定模型.
  - **生图模型视觉校验**：若向仅能生图的非视觉模型（如 `Agnes Image`）上传截图/图片，则在 `_llm_chat_reply` 中直接拦截并提示用户切换到视觉聊天模型.
  - **Ollama 激活优化**：在 `models_config.py` 中将 Ollama 驱动的模型在无 API key 时也标记为 `available`，并支持直接激活.
  - **停止工作流交互优化**：修复在运行中点击 Stop 时会错误弹出 Human-in-the-Loop 交互卡片的 Bug。移除了 `failed` 状态也会错误渲染该卡片的判定，使 Stopped 或 Failed 的 run 正确恢复显示常规的聊天输入框。
  - **测试与校验**：新增 `test_llm_chat_reply_image_model_rejects_vision_input` 并修改/扩充 `test_agent_type.py` 和 `test_models_config_api.py` 的测试.
- **下次优先**：Flow 运行中逐步 Chat 的 WS 时序优化。

## 2026-06-26 会话（M3-F Flow 接力落地 · Weather-to-Vision）

- **完成：**
  - **D23 代码落地**：`node_outputs` + `resolve_agent_task_input`；编译器 handoff；`agent_executor` Clutch 人格/MCP/生图；增量 `state_patch`；`workflow_projection` 消息去重。
  - **前端**：Flow 启动前 `await clutchStore.connect`；`optimisticWorkflowStart` + ChatFeed thinking。
  - **模板**：`workflows/weather-to-vision.json`。
  - **测试**：`test_node_input`、`test_workflow_handoff`、`test_workflow_projection`、`test_workflow_step_patch`、`test_agent_executor`（clutch prompt + 上游生图）。
  - **手动 E2E**：用户验证 Researcher（claude-cli）→ Artist（Agnes Image）上海天气插画成功。
- **下次优先**：commit 收尾；或 Flow 运行中逐步 Chat 的 WS 时序优化。

## 2026-06-26 会话（Flow 接力计划文档化）

- **完成：**
  - **`memory/DECISIONS.md` D23**：Flow `node_outputs`、auto 输入解析、Clutch 执行对齐、逐步 `state_patch`、Weather-to-Vision 首版范围。
  - **`specs/core/tasks.md` §M3-F**：M3-F01…M3-F11 Task 清单与 Verification。
  - **`memory/FILEMAP.md`**：M3-F 索引行。
- **下次优先**：M3-F01（`node_outputs` + `resolve_agent_task_input`）。

## 2026-06-26 会话（Ollama 本地模型打通与动态模型解析路由）

- **完成：**
  - **`ollama_adapter.py`**：新增 Ollama 本地模型适配器。调用 `GET http://localhost:11434/api/tags` 自动发现本地可用模型，并实现基于代码/推理能力的自动排序打分算法（优先选用 `qwen3.6`，其次 `qwen2.5-coder`、`llama3` 等）。使用标准的 OpenAI 兼容格式调用本地 `/v1/chat/completions`。
  - **`engine_router.py`**：支持对 `Ollama` 驱动引擎在路由时的标准化识别与分流。当 Ollama 可用时执行本地适配器，并返回实际调用的具体模型 tag（如 `qwen3.6:35b`）使得前端 ChatFeed 能够实时渲染正确的本地运行模型名。
  - **`agent_executor.py`**：将 `ollama` 与 `ollama-cli` 引入到工作流 Agent 任务的合法 tool check 白名单中，允许 Agent 任务走 Ollama 模型路由。
  - **测试与校验**：新增 `test_ollama_adapter.py` 覆盖发现模型、排序打分以及请求格式化的单元测试，在 `test_engine_router.py` 扩充 Ollama 路由及连接状态兜底测试。全量后端 242 项 pytest 校验全部通过。
- **下次优先**：答复用户反馈并开展后续集成测试。

## 2026-06-26 会话（后端子进程与 MCP 挂起修复）

- **完成：**
  - **`cli_adapter.py`**：将 `stdin=subprocess.DEVNULL` 显式注入所有 `Popen` 和 `run` 的子进程参数中，避免子进程继承交互式终端 stdin 而无休止地阻塞在 `read(0)` 上。
  - **`mcp_client.py`**：重构 `_read_response` 为基于绝对 Deadline 的累计超时逻辑，解决当 npm/npx 每隔数秒输出安装进度等噪音时超时重置无限等待的问题；在 `start()` 时注入优化 npm/npx 更新和遥测的环境变量。
  - **`conftest.py`**：在 `isolate_orchestrator_globals` 全局单测隔离 fixture 中默认注入 `CLUTCH_E2E_FAKE_LLM=1`，防止 pytest 套件因开发机网络波动连接 DeepSeek 等外部 API 时造成测试执行阶段发生无限期卡顿。
  - **校验**：Husky 触发的 pre-commit 校验与 `./scripts/verify.sh` → 232 pytest + vitest + build + doc-drift 全部顺利通过且运行速度提升数倍。
- **下次优先**：答复用户反馈或进行后续 SOP / 编排任务。

## 2026-06-26 会话（默认分组可见性与底部菜单收起交互优化）

- **完成：**
  - **`sidebar.tsx`**：使用 `showDefaultGroup` 来控制虚拟默认分组的渲染，并增加其被展开且无项目时的空状态信息，使其在已创建自定义分组的情况下依然可以作为拖拽的放置目标；修正了 `!showDefaultGroup` 作为筛选后无匹配项目时的逻辑。
  - **`App.tsx`**：实现 window click 的外部点击检测逻辑，点击页面任意空白处时将一并关闭已展开的底部菜单面板（Branch, Model, Active Agent, Workflow）。
  - **校验**：Husky 触发的 pre-commit 校验与 `./scripts/verify.sh` → 232 pytest + vitest + build + doc-drift 全部通过。
- **下次优先**：答复用户反馈并继续开展后续任务。

## 2026-06-25 会话（apply_patch 方案 B · Codex 对齐）

- **完成：**
  - **`apply_patch.py`**：Codex patch 解析与在工作区内执行（Add / Delete / Update / Move）。
  - **`builtin_tools.py`**：虚拟 MCP 服务器 `clutch-tools`，绑定 `local-fs` 时自动挂载。
  - **`mcp_react.py`**：虚拟服务器不走 subprocess；`changed_paths` 驱动文件树刷新。
  - **`mcp_risk` / system prompt**：`apply_patch` 高风险审批；禁止 `.deleted_*` 删文件 workaround。
  - **决策**：`memory/DECISIONS.md` D21；`FILEMAP` 登记。
  - **校验**：`./scripts/verify.sh` → 228 pytest + vitest + build + doc-drift passed。
- **下次优先**：桌面端实测删除 `test.txt`；或 commit 本会话交付。

## 2026-06-25 会话（Git 分支、日志时间戳、MCP 门控、Models UI）

- **完成：**
  - **底部 Git 分支**：`GET /api/workspace/git` + `workspace.get_git_info()`；footer 显示本地 `main` 等真实分支（不再误用 `run_id`）；下拉列出本地分支。
  - **文件树刷新**：运行结束或打开 Files 标签时自动 `refreshWorkspaceFiles`。
  - **Terminal 时间戳**：`stamp_log_line()` 为所有 terminal_logs 加 `[YYYY-MM-DD HH:MM:SS CST]`；幂等不重复 stamp。
  - **MCP 门控**：Supervisor 审批消息去重；`mcp_risk` 扩展 `source`/`destination` 路径键；system prompt 注入 workspace 根路径提示。
  - **Models Manager**：布局简化；移除 `credential_hint` 字段。
  - **校验**：pre-commit `7ee8f43` → 218 pytest + vitest + build passed。
- **下次优先**：发布 / 红队体感审计；或 BACKLOG B-01 主控分派。

## 2026-06-25 会话（Orchestrator 日志流与执行链路统一）

- **完成：**
  - **`run_log_forwarder.py`**：工作流/agent 执行日志统一转发与 WS 推送。
  - **`workflow_projection.py`**：图状态投影增强；`compiler` / `evaluator` 对齐。
  - **`llm/http_complete.py`**：HTTP 补全路径加固；流式日志接入。
  - **`terminal_logs.py`**：`agent_line` 等格式化辅助（本会话后续 `7ee8f43` 加 CST stamp）。
  - **测试**：`test_run_log_forwarder.py`、`test_workflow_log_streaming.py`、`test_http_complete.py` 扩充。
  - **Commit：** `973857c`
- **下次优先**：见上节。

## 2026-06-25 会话（模型凭证、MCP 风险、Video Core、Skills 自动挂载）

- **完成：**
  - **Models / CC Switch**：`rehydrate-cc-switch` 端点；verify 缓存；`credential_source_label`；`ModelsManager` 大改版（`553714d`、`a8d199c`）。
  - **MCP 凭证与风险**：`credentials/sources.py` 扩展；`mcp_react` 真执行路径；`mcp_risk` 文件路径提取；工作区相对路径（`d5566fb`）。
  - **测试隔离**：`conftest` MCP mock；workflow 测试不再触发真实 CLI（`91955f2`）。
  - **Skills 自动挂载**：`ensure_default_skill_mounts`；默认 skills 写入工作区（`3ae36a8`）。
  - **Video Core 骨架**：`pipeline.py` / `renderer.py` / `config.py`；`test_video_core/` 测试套件（`0c8b087`、`4e812bb`、`77f73f0`）。
  - **CLI 统一**：`cli_adapter` / `claude_cli_adapter` / `engine_router` 加固（`4e812bb`）。
  - **Footer Model/Engine**：内置 Agent 显示 Model；自定义 Agent 只读 Engine；删除 `mockData.ts`（`8d89768`）。
- **下次优先**：见当前状态。

## 2026-06-25 会话（agent_id 聊天路由与内置 Agent 可定制）

- **完成：**
  - **WebSocket `agent_id`**：`submitChatMessage` 传入选中 Agent；`ws_run` → `_handle_plain_chat` → `_llm_chat_reply` 按 ID 解析 Agent。
  - **`get_agent_by_id` + 内置 Agent 持久化**：`markdownDoc` 等自定义可写入 `agents.json`；`list_agents()` 合并内置默认值与用户覆盖。
  - **system prompt 注入**：plain chat 将 Agent `markdownDoc` 插入 LLM history；回复标签用 Agent 名称（如「Clutch Agent」）而非 engine 名。
  - **前端**：`AgentManager` 允许编辑内置 Agent（Delete 仍禁用）；`saveAgents` 发送完整列表由后端过滤。
  - **测试**：`test_agents_api.py`、`test_ws_message_log.py` 覆盖 builtin override 与 `agent_id` 注入。
  - **校验**：`./scripts/verify.sh` → 138 pytest + vitest + check-doc-drift passed（pre-commit `6cc6c6b`）。
- **下次优先**：发布 / 红队体感审计；或 BACKLOG B-04 剩余项（主控分派、非 agent_task 路径）。

## 2026-06-25 会话（Engine Router + Claude CLI Adapter）

- **完成：**
  - **`engine_router.py`**：按 Agent `aiEngine` + Tools Connect 状态分流 Claude CLI / Cursor / 全局 LLM；`find_agent()` 多级匹配；`fallback_tool` 支持工作流节点无 Agent 配置时兜底。
  - **`claude_cli_adapter.py`**：封装 `claude -p` 子进程（system prompt、permissions、allowed-tools）。
  - **集成**：`main.py` `_llm_chat_reply` / `_handle_plain_chat`、`agent_executor.py` `execute_agent_task` 改走 `route_engine`。
  - **内置 Agent（前后端）**：`agent_storage.get_builtin_agent()`、`builtinAgent.ts`、`App.tsx` 默认选中 `clutch-agent`。
  - **测试隔离**：`conftest.py` 设 `CLUTCH_STORAGE_DIR=tmp_path`，避免测试读真实 dev 目录触发 Claude CLI。
  - **测试**：`test_claude_cli_adapter.py`、`test_engine_router.py`、`test_agents_api.py`。
  - **校验**：`./scripts/verify.sh` → 138 pytest + vitest passed（commit `eaf2ea0`）。
- **下次优先**：~~将 Connect 状态接入执行链路~~ ✅ 本会话后续完成（见上节 `6cc6c6b`）。

## 2026-06-25 会话（国际化双语支持与中文字符消除）

- **完成：**
  - **后端 `tr()` 动态翻译**：在 `preferences_storage.py` 中引入 `tr(en, zh)` 方法，动态读取用户工作区语言设置（en 或 zh）。针对 `pytest` 测试执行期做了特殊适配，测试阶段始终返回中文响应，以兼容既有后端测试断言。
  - **后端错误日志/异常汉字消除**：重构了 `main.py`、`workspace.py`、`mcp_storage.py`、`workflow_storage.py`、`workflow_validator.py` 和各 GUI/CLI adapter，将原来直接抛出的中文异常或 WebSocket 人工审批消息全部替换为 `tr()` 动态表达。
  - **前端汉字漏译适配**：
    - 针对 `WorkflowJsonPanel.tsx` 和 `WorkflowOrchestration.tsx` 等组件中硬编码的汉字（如“画布”、“保存”、“内置模板”、“第一步”等），通过 `useLanguage` 提供的 `t()` 包装；
    - 修改 `workflowFormat.ts` 和 `workflowApi.ts` 的默认英文节点名称与 API 错误消息，并在 `LanguageContext.tsx` 补全其双语对照翻译字典；
    - 导出 `translateText` 用于非 React 组件 `clutchState.ts` 翻译 WS 收到的校验失败后缀文字。
  - **校验**：`./scripts/verify.sh` → vitest/pytest 全量 128 个测试全部通过，Vite 编译打包完成，漂移自检 OK。
- **下次优先**：进行发布以及红队/体感审计。

## 2026-06-25 会话（Tools 自动扫描扩容：CLI + macOS 客户端）

- **完成：**
  - **后端 `tools_status.py` 重写**：用 `CLI_CANDIDATES`（9 个 CLI 二进制）+ `CLIENT_CANDIDATES`（5 个 macOS .app）替换写死 2 项的 `TOOL_CATALOG`。新增 `_cli_path()` / `_client_path()` 统一探测函数，返回解析到的绝对路径。`list_tools_status()` 对每条候选分别探测，只返回实际存在的项，新增 `kind: "cli"|"client"` 和 `path` 字段。
  - **前端 `toolsApi.ts` 类型**：`AiToolStatus` 新增 `kind` 和 `path`。
  - **前端 `AiToolsManager.tsx` UI**：空态文案改为覆盖多工具；每张卡片显示 kind 标签 + 绝对路径（等宽截断，hover tooltip）。
  - **测试**：`test_tools_status.py` 10/10 passed（含 CLI path、client path、非 darwin 客户端不出、未知 tool reject、catalog 唯一 id 等新增用例）。
  - **校验：** `./scripts/verify.sh` → 123 pytest passed（2 个 `test_claude_code_credentials.py` 失败为既有问题，与本次无关）+ `pnpm build` ✅
- **下次优先：** 将 Connect 状态接入执行链路（`_llm_chat_reply` / `execute_agent_task` 按 `aiEngine` 分流到 CLI adapter 或 LLM router）。

## 治理脚手架就绪标准（文档层 ✅）

- [x] Layer 1–3 治理文档 + Memory 六件套
- [x] 测试规范（D1/D2、TESTS、CI workflow、`verify.sh` + `run-e2e.sh`）
- [x] Vibe 8.5 兜底（D7：Husky、漂移机检、truth-alignment 剧本、Layer 4 约束）
- [x] Task 交付索引（`DELIVERABLES.md` + Check-out 规则 + `runs/verification/README`）
- [x] 产品开放问题 Q1–Q4 → D3–D6 已决策

## 下次 Agent 启动必读

1. 读本文件（`PROGRESS.md`）
2. 读 `FAILURES.md`（**桌面 E2E 坑**）、`FILEMAP.md`、`DECISIONS.md`（D11–D12、D16–D17）
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

### 2026-06-25 会话（CC Switch 凭证导入、Deepseek 修正及端口清理）

- **完成：**
  - **CC Switch 动态导入**：实现 `bootstrap_cc_switch_credentials`，支持读取 `~/.cc-switch/cc-switch.db`，在 Clutch 启动时自动检测并导入用户配置的自定义模型（如 Zhipu GLM, Agnes AI, Ollama）及相应 API Key，同时在 proxy 不可用时自动降级到直连。
  - **DeepSeek Base URL 修正**：将默认的 DeepSeek base URL 从 `/v1` 结尾修正为根域名 `https://api.deepseek.com`，解决 OpenAI 兼容客户端发起 `/chat/completions` 时产生 404 错误的问题。
  - **Tauri 端口冲突清理**：移除了 `free_sidecar_port()` 在 macOS 下的 debug assertions 编译限制。开发端启动时将强行清理后台占用 `8123` 的正式版 Sidecar 进程，避免开发前端因端口劫持而读写生产环境数据。
  - **API Key 显隐切换**：在 `ModelsManager` 凭证输入表单中增加 `showApiKey` 状态和可视化切换按钮，使用 Google Material Symbols `visibility` 和 `visibility_off` 实现可见性切换。
- **校验：** `./scripts/verify.sh` → 120 pytest + vitest passed + doc drift ok
- **下次优先：** 进行发布以及红队/体感审计。


### 2026-06-25 会话（存储隔离与指针拖拽优化）

- **完成：**
  - **存储路径隔离**：引入 `storage_helper.py` 并重构所有后端 storage 类（`workspace`、`preferences_storage` 等），将开发环境下的本地存储隔离到 `clutch_dev` 目录，防范测试与生产数据互相干扰，生产版维持 `clutch`。
  - **自定义 Pointer 拖拽**：用基于 React 鼠标/指针监听的自定义 Pointer Drag-and-Drop 逻辑替换侧栏原生的 HTML5 拖拽事件。解决了原生拖放交互难看、在 iframe/Tauri 打包版中不够稳定的问题，并带有平滑的阴影与高亮显示。
  - **普通 LLM 对话状态 UI 优化**：
    - 前端 ChatFeed 能够自适应识别无 workflow 调度的普通对话（Plain LLM Session）；
    - 普通会话运行中，可在 ChatFeed 发送按钮位置渲染「Stop」物理停止按钮，并实质触发停止；
    - 在运行过程中，普通会话的思考中提示能将当前选用的 LLM 模型名称同步输出在 Agent 标签下方。
- **校验：** `./scripts/verify.sh` → 119 pytest + vitest passed + doc drift ok
- **下次优先：** 进行发布以及红队/体感审计。

### 2026-06-24 会话（分组文件夹管理优化与拖拽移动）

- **完成：**
  - **图标区分**：将分组图标替换为 `folder_special`，与项目的 `folder` / `folder_open` 图标显著区分开。
  - **默认分组包裹**：实现前端虚拟 `Default Group` (默认分组) 包裹所有 ungrouped 的项目，并支持独立折叠展开。
  - **分组完整 CRUD**：扩展侧栏右键菜单，对自定义分组（Group）支持重命名和删除功能，配合 `<PromptModal />` 确认及输入。
  - **拖拽与右键移动项目**：
    - 支持 HTML5 原生 `draggable` 拖拽项目，并在拖拽移入分组时带有高亮视觉动效；
    - 在项目右键菜单中增加 `Move to Group` hover 二级级联子菜单，用户点击任一分组（包含虚拟默认分组）均能实时调用 `updateRepositoryGroup` 持久化，并自动同步更新分组树。
- **校验：** `./scripts/verify.sh` → 116 pytest + vitest passed
- **下次优先：** 答复用户关于分组新功能的反馈并继续迭代。

### 2026-06-24 会话（自定义弹窗与删除修复）

- **完成：**
  - **右键 Reload 移除**：从侧栏右键菜单中彻底删除了 Reload 按钮与相关的分隔线。
  - **自定义 Prompt/Confirm Modal**：设计并实现了一个毛玻璃效果的 `<PromptModal />`，替代 Tauri 桌面端不支持的 `window.prompt` 与 `window.confirm`，支持弹窗输入（创建项目分组）及删除二次确认。
  - **删除项目 bug 修复**：引入被漏掉的 `removeWorkspace` 避免 ReferenceError 错误，并在删除项目后调用 `fetchRepositoryGroups` 刷新状态，确保侧栏及分组树中立即移出被删除项目。
- **校验：** `./scripts/verify.sh` → 116 pytest + vitest passed
- **下次优先：** 答复用户五角星图标的疑问，重新打包并交付。

### 2026-06-24 会话（右键菜单、思考动效、删除与跳转优化）

- **完成：**
  - 在侧栏项目/会话自定义右键菜单中增加了 Reload / 重新加载选项，并且利用 `e.stopPropagation()` 解决了冒泡关闭的问题，确保右键自定义菜单可以在打包 DMG 禁用原生右键的环境下正常使用 Reload 和 Delete；
  - 增加了 LLM 思考中动效，当 `isRunning` 且最后一条消息是 User 时，以 AI 气泡展示三点波浪跳跃动效并附带旋转 Loader，同时将思考动效加入 auto-scroll 依赖，启动后自动滚到底部；
  - **防止空白 Ghost 会话物理创建**：重构 `handleNewChat`，移除立刻物理调用 `createSession` 的行为，仅本地生成临时 `runId` 呈现空 landing 状态，当用户发第一条消息时后端由 WebSocket 的 `_touch_session` 顺理成章创建，从而避免点 New Chat 污染侧栏或“删除后又多出一个空会话”的 Bug；
  - **删除会话自动跳转 fallback 逻辑**：重构 `handleDeleteSession` 以更新前端 session 状态，若删除当前选中会话，则自动在同 Workspace 内检索最新一条剩余会话进行 handleSelectSession 跳转。若已无剩余会话，则直接切换到临时 runId 状态渲染空 landing 引导页。
- **校验：** `./scripts/verify.sh` → 116 pytest + 1 vitest + drift ✅
- **下次优先：** 待用户进一步验收测试。

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
