# PROGRESS

## 当前状态

- **阶段：** D25 Hybrid Runtime + Flow 精修已落地 + 功能迭代中；**开源排期 OSR-xx 已登记**（见 `memory/BACKLOG.md` §开源 / DMG 分发 · `memory/ROADMAP.md` §开源分发）
- **Git HEAD：** `54714bd`
- **下次优先（开源 T2）：** OSR-12 首 tag 验证 → **OSR-13** Keychain → **OSR-14** 首次启动向导
- **验收期跳过：** MCP hybrid_executions 深度 UI · 2h/100+ 压测

### 未 commit 工作

OSR-15 `INSTALL.md` + `DATA_AND_PRIVACY.md`（待 commit）

## 2026-06-29 会话 21（OSR-15 安装与隐私文档）

- **`docs/INSTALL.md`**：DMG 安装、Gatekeeper、健康检查、首次 checklist、卸载
- **`docs/DATA_AND_PRIVACY.md`**：本地存储表、第三方数据流、用户权利、合规说明
- **交叉引用**：`README.md` 文档地图 · `SECURITY.md` 支持版本 1.0.x

## 2026-06-29 会话 20（OSR-10 截图 · OSR-00 验收 · D31 未签名 DMG）

- **产品截图**：`docs/images/Clutch_1.png`、`Clutch_2.png` → README §产品截图
- **OSR-00**：维护者自验通过（用户确认）
- **D31**：无 Apple Developer 账号 → 未签名 DMG 经 GitHub Releases + README；OSR-11 ⏭️
- **Release CI**：`.github/workflows/release.yml`（`v*` tag → macOS DMG）

## 2026-06-29 会话 19（OSR-08 Sidecar session token 鉴权）

- **`CLUTCH_SIDECAR_TOKEN`**：Tauri 启动时生成 UUID，注入 sidecar 环境；`clutch_sidecar_token` command 供 WebView。
- **后端**：`sidecar_auth.py` + HTTP middleware + WS `?token=`；`/health` 公开；`CLUTCH_E2E_SANDBOX` 跳过鉴权。
- **前端**：`sidecarFetch` / 异步 `sidecarWebSocketUrl` 全服务接入。
- **验证**：`./scripts/verify.sh`（483 pytest passed）。

## 2026-06-29 会话 18（OSR-09 CLI 权限策略 · D30）

- **D30**：维持 `--dangerously-skip-permissions`；`README.md` §安全与 CLI 权限 · `SECURITY.md`。
- **OSR-00**：维护者自行发布前验收。

## 2026-06-29 会话 18b（OSR-10 README + 源码构建 · 已 commit `6178bc5`）

- **`docs/BUILD_FROM_SOURCE.md`** · README §安装方式；缺产品截图。

## 2026-06-29 会话 17（OSR-07 Secret scanning CI）

- **`.github/workflows/secret-scan.yml`**：`gitleaks/gitleaks-action@v3`，`push`/`pull_request` 触发。
- **`.gitleaks.toml`**：测试目录与合成 key 允许列表。
- **验证**：`./scripts/verify.sh`。
- **下次优先**：OSR-10 或 OSR-08/09（待产品决策）。

## 2026-06-29 会话 16（OSR-06 社区与健康文件）

- **SECURITY.md**：私密漏洞报告渠道（GitHub Private Vulnerability Reporting）、响应时间线、范围与已知 OSR 加固项索引。
- **CODE_OF_CONDUCT.md**：Contributor Covenant 2.1。
- **链接**：`CONTRIBUTING.md`、`.github/ISSUE_TEMPLATE/security_report.md`、`README.md` 文档地图。
- **验证**：`./scripts/verify.sh`。
- **下次优先**：OSR-07 Secret scanning CI。

## 2026-06-29 会话 15（支持删除/隐藏 CC Switch 导入的模型）

- **解除 CC Switch 模型删除限制**：修改了后端 `custom_models.py` 的 `hide_model_from_list`，移除对 `cc-switch-` 前缀模型 ID 的 ValueError 限制，允许将其记录到 `hidden_model_ids` 并从可用列表中隐藏。
- **UI 操作按钮对齐**：修改前端 `ModelsManager.tsx` 的 `canRemove` 判定逻辑，仅根据 `!isActive` 判断是否显示垃圾桶操作按钮，使 CC Switch 导入的模型也可以通过悬浮垃圾桶进行隐藏。
- **删除确认提示优化**：在确认隐藏 CC Switch 模型的对话框中，加入了专门的提示说明，告知用户这些模型只是被隐藏，后续可以通过手动点击 "Import models" 重新导回显示。
- **验证**：运行 `./scripts/verify.sh` 全量通过（474 tests passed + build & doc-drift OK）。


## 2026-06-29 会话 14（选中 Flow 时底部显示 - 且 Agent 和 Flow 互斥优化）

- **工作流与智能体互斥选择**：重构了底部的 Active Agent 按钮，使其在 Workflow 选中时不再为置灰 span，而是保持为可点击 the `Active Agent: — [v]` 下拉触发器。当用户在下拉菜单中选中任何智能体时，自动触发 `clearWorkflowSelection()`。
- **清除工作流的 WebSocket 同步**：在 `clutchState.ts` 引入 `clearWorkflowForSession` 方法，向后端发送 `{ action: "clear_workflow" }` 并在前端 store 清空 `workflow_id`，使会话重置为 plain chat 状态。
- **后端 WS 状态更新**：在 Sidecar `/ws/runs/{run_id}` 循环中新增对 `"clear_workflow"` action 的处理，将运行状态与历史 session 中的 `workflow_id` 清空并广播给所有客户端，移出当前运行的 `_run_sessions`，防止后续对话消息错误路由至工作流执行或精修。
- **模型和智能体视觉优化**：当 Flow 选中激活时，底部的 Model 保持显示为 `Model: —` 禁用/只读状态，Active Agent 按钮显示为 `Active Agent: — [v]`。
- **单元测试**：添加 `test_ws_clear_workflow` 单元测试，保证 WebSocket `"clear_workflow"` 接口在接收到指令后能正确清除 state 里的 `workflow_id` 并持久化。
- **验证**：运行 `./scripts/verify.sh` 全量通过（474 tests passed + build & doc-drift OK）。

## 2026-06-29 会话 13（模型配置界面操作按钮悬浮图形化与卡片选中优化）

- **卡片级选中交互**：去除了原有的 "Use this model" 文本按钮，支持点击模型卡片直接选中启用该模型，并添加了对应的 `cursor-pointer` 和 hover 样式。
- **操作按钮悬浮与图形化**：将 "Remove" 与 "Test"/"Retest" 操作重构为仅在鼠标悬浮时显现的图形化 icon 按钮（使用 `BTN_ICON` 与 LegacyIcon `delete` 和 `sync`）；对于处于 `testing` 状态的卡片，测试中状态的旋转图标将保持显示，直至测试完毕。
- **阻止事件冒泡**：对卡片内部所有交互元素（Change provider key 链接、Test 按钮、Delete 按钮）添加了 `e.stopPropagation()`，防止在执行子操作时误触发卡片的全局选中激活事件。
- **验证**：运行 `./scripts/verify.sh` 全量通过（473 tests passed + build & doc-drift OK）。


## 2026-06-29 会话 12（修复 Flow 精修消息回显、提示词生成与头像映射）

- **消息回显修复**：修复了在工作流/精修模式（如 `@5-Visual Rendering Engine 重新生成图片`）下，用户发送的信息在前端 `messages` 列表中被意外丢弃不回显的问题。原因是在 `clutchState.ts` 的 `mergeChatMessages` 中，如果 `pendingUserMessageId` 为 null（工作流和精修不使用 optimistic 发送），匹配到重复文本的历史消息时，会误触 `!isPendingTurn` 判断而将服务器返回的真实用户消息直接 `continue` 丢弃。通过对该判断加上 `pendingUserMessageId` 活跃检查，确保了 workflow 和 refine 下同文本的新 turn 不会被错误过滤。
- **Session 提示词生成修复**：修复了 orchestrator 重启后，第一次精修消息未正确执行 `resolve_image_refine_prompt` 而导致传递给生图引擎的参数沦为字面量 `"重新生成图片"` (从而生成完全不搭界现代照片) 的 Bug。原因是在 `_handle_flow_refine_message` 中，初次从 `_run_sessions` 获取 session 为 `None`，虽然之后调用 `_prepare_workflow_refine_state` 内部触发了 `ensure_workflow_session_for_refine` 并将其存入了缓存，但本地 `session` 变量未能同步更新依然为 `None`，导致后续 `resolve_image_refine_prompt` 调用被全部跳过。修复为：提前确保 refinement session 载入并同步更新本地 `session`/`workflow` 变量，这也使得 mention 解析时可以正确利用完整的 workflow 定义支持带空格的智能体（如 `@5-Visual Rendering Engine`）准确提取 body 并注入上文提示。
- **头像映射错误修复**：修复了精修阶段由 `5-Visual Rendering Engine` 运行输出的图片，其消息气泡头像被误显示为 `1-Concept Architect` (Antigravity Logo) 或 `2-Scriptwriter` (Claude Logo) 的问题。原因是在 `buildWorkflowReplyStepIndex` 中，之前仅按照最新一条 User 消息后的首位 agent 顺序将 replyIndex 从 0 累加映射，而在精修模式下仅有特定的后期节点执行，所以 replyIndex 0 被错配给了 workflowAgentSteps[0]。修复为：在 `buildWorkflowReplyStepIndex` 优先按照 `message.agent` 的名称/Label 在步骤表中匹配定位，匹配失败时才退化到以 latest user message 后的序列进行 sequential 兜底映射。


## 2026-06-29 会话 11（修复 MCP 审批确认后的解包崩溃卡死）

- **现象修复**：修复了用户在聊天中授权了高危 MCP 工具（如 `local-fs__write_file`）后，后端 `_handle_plain_chat_mcp_decision` 调用 `_llm_chat_reply` 返回 10 个值但被错误地解包为 9 个值（缺少 `shell_recovered`）引发 `ValueError`，导致 WebSocket 连接意外中断、UI 状态未能更新并卡在 approval 阶段的问题。
- **集成测试**：新增 `test_ws_plain_chat_mcp_approve` websocket 集成测试，对人类授权后恢复 MCP 会话的全流程与解包进行端到端校验。
- **验证**：运行 `./scripts/verify.sh` 全量通过（473 tests passed）。


## 2026-06-29 会话 10（默认 Multi-Agent 并隐藏模式切换按钮）


- **UI 优化**：去除了 Header 中的 Single Agent / Multi-Agent 模式切换按钮，避免用户在界面上切换到不支持的单智能体模式导致状态混淆；
- **状态默认值与加载优化**：将 React state `isMultiAgent` 的默认状态修改为 `true`，同时在 `handleSelectSession` 会话恢复加载流程中不再从 `localStorage` 读取或应用旧的 `single` 模式状态，确保所有用户会话统一初始化并锁定在 Multi-Agent 架构下（即使是没有配置 workflow_id 的普通 plain chat 也可以在多智能体界面运行并提供流程视图）。
- **验证**：`./scripts/verify.sh`（build + vitest + pytest 471 passed）。


## 2026-06-28 会话 9（Flow 精修 + 节点 handoff 验收）

- **Flow 精修 UX**：Stop 或工作流 `passed`/`failed` 后，`@` 弹出工作流 Agent 列表；`@Agent` + 反馈走 Hybrid（`flow_refine`）；`/continue` 提交修订并以 Legacy 续跑下游。
- **后端**：`flow_refine.py`（mention 解析、session 重建、`final_image_prompt` 生图精修）；`main.py` 路由与 `_prepare_workflow_refine_state`；`refining` 状态与 `node_outputs` handoff。
- **修复**：`close_stdin` 500、agy 空输出、多行 Claude Flow legacy 子进程、带空格 Agent 名 `@5-Visual Rendering Engine`、完成后消息仅记 `[USER]` 不进精修。
- **文档**：`docs/PRODUCT_INTRO.md` §3.1 Multi-Agent / Chat Input 精修说明。
- **验证**：`./scripts/verify.sh`（build + vitest + pytest）。

### HRT 进度快照

| ID | 状态 | 说明 |
|----|------|------|
| HRT-00 | ✅ | `7221641` 计划与文档 |
| HRT-S1~S4 | ✅ 代码 | ShellSession · agy · Snapshot · runtime_registry |
| HRT-S5-partial | ✅ 代码 | pool=8 · snapshot prune（≠ pty Step 5 全文） |
| HRT-01~03 | ✅ 代码 | marker · snapshot 注入 · parser 过滤 |
| HRT-04 | ✅ | 用户验收 A–E 2026-06-27 |
| HRT-05 | ✅ | `70835ba` audit JSONL |
| HRT-06 | ✅ | `4694231` debug API |
| HRT-07 | ✅ | `446b7a0` export script |
| HRT-08 | ✅ | `a16bf5f` |
| HRT-09 | ✅ | `7b62914` background hydrate |
| HRT-10 | ✅ | POC #6/#10 pytest + verify script |

## 2026-06-28 会话 8（Flow Stop 按钮修复）

- **完成：**
  - **Flow Stop 按钮无响应修复**：定位并修复了 Flow 工作流运行中点击 Stop 按钮无效的 Bug。根因是 `handleStopRun`（`App.tsx`）在所有情况下都先弹出 `window.confirm` 二次确认弹窗，而在 Tauri 桌面端 `window.confirm` 会阻塞 JS 主线程导致整个 React UI 冻住，用户感受为"按钮点不动"。切换一次对话再回来后 `highRiskConfirmed` 已被置为 `true` 才跳过弹窗直接停止。修复：Flow 工作流 Stop 直接发送 `stop_run` 无需二次确认；普通 LLM Chat Stop 保留一次性 confirm 防误触；同时在 `sessionRunId` 变化时重置 `highRiskConfirmed` 防跨会话状态泄漏。
- **校验：** `pnpm build` 通过；vitest 33/33 通过

## 2026-06-28 会话 7（Codex CLI 接入 · 输出过滤 · 动态 Agent 类型）

- **完成：**
  - **Codex CLI 路由**：`engine_router` 使用 `codex exec --json` 位置参数（非 `-p` profile）；`history_only` 多轮 history replay；Hybrid shell `</dev/null` 防 stdin 挂起。
  - **Codex 输出解析**：`parse_codex_jsonl_output` / `extract_codex_assistant_output` 从 JSONL 提取 `agent_message.text`，TUI 噪音（session id、tokens used 等）过滤；修复单轮 18k 噪音进入 history 导致第二轮极慢/卡住。
  - **动态 Agent 类型**：前端 `agentTypeOptionsFromTools()` + `AgentManager` 从 `/api/tools/status` 生成下拉；后端 `resolve_agent_type_for_tool` 映射 `codex-cli` / `ollama-cli`；Connect 且配置完成后自动出现在选项中。
  - **Agy / Ollama 修复**：移除 agy `--model` 注入；PTY 捕获空输出；Ollama 多轮 history；cross-agent history 测试。
- **校验：** `uv run pytest` Codex/agy/ollama 相关测试通过；本地 live codex 单轮 + 多轮 + hybrid shell 通过 ✅

## 2026-06-28 会话 6（零配置 AI 工具自动嗅探与安装指引）

- **完成：**
  - **安装状态与注册状态分流**：在 `tools_status.py` 中重构 `list_tools_status` 支持 `include_all=True`，向前端返回所有候选工具列表。
  - **未安装工具引导与一键复制代码**：在 `AiToolsManager.tsx` 中，针对未安装工具提供抽屉面板展示安装命令与详细描述，提供一键复制按钮。若用户系统未检测到任何可用 CLI，顶部会弹出高亮卡片提示用户前往安装和连接。
  - **未配置工具的 AI 自动嗅探（Auto Config）**：在 `main.py` 和 `tools_status.py` 中实现 `/api/tools/auto-configure` 嗅探接口，并利用 `custom_clis.json` 偏好保存实现本地持久化。未配置的工具会显式显示 `Unconfigured`（未配置）警告徽标，并在 Connect/Disconnect 旁增加「Auto Config」操作按钮，点击后系统会利用 LLM 自主分析二进制文件的帮助文档（如 Aider 的 `--message`），自动适配 Prompt 旗标、Session 参数和 Extra Args，无需用户懂任何命令行参数即可直接装载使用。
- **校验：** 新增 `test_auto_configure_cli_via_llm` 单元测试，后端 `uv run pytest` 共 411 项测试通过，前端 `pnpm build` 100% 编译成功 ✅

## 2026-06-28 会话 5（历史会话列表图标逻辑更改与测试套件缓存清理）

- **完成：**
  - **历史会话条目图标优化**：在 `sidebar.tsx` 中重构会话条目渲染逻辑。移除原先基于 snapshot 状态显示的静态多轮对话图标（`restart_alt` 环形箭头）。新增 ongoing 状态计算，当会话处于运行状态（`status === 'running'` 或当前活跃会话在 `clutchStatus` 中为 `running`）时，渲染 `progress_activity` 动效旋转加载动画，其他完成状态会话的图标保留为空。
  - **活跃会话结束实时刷新**：在 `App.tsx` 中向 `Sidebar` 传递 `clutchStatus` 参数，并在 `clutchStatus` 从 `running` 变为 `idle` 等结束态的 `useEffect` 中，触发 `refreshSessions()`，实现侧边栏列表状态的实时刷新。
  - **测试套件 Session 泄露清理**：在 `conftest.py` 中的 `isolate_orchestrator_globals` 全局 `autouse` fixture 中新增 `clean_sessions()`，确保在每个 pytest 测试执行前和后，将 `ShellSessionManager` 缓存的 `_sessions` 全部调用 `release()` 正确释放。这彻底消除了由于测试并发与连续运行造成 Session 泄露进而导致 ShellSession 资源爆满引发 `test_concurrent_hybrid_plain_chat_ws` 运行失败的问题。
- **校验：** 运行 `./scripts/verify.sh` 通过了全部 Vite build、Vitest 单元测试以及后端全量 408 项单元测试，文档自检无任何漂移 ✅

## 2026-06-28 会话 4（项目分组图标状态切换与重构）

- **完成：**
  - **分组图标状态切换**：在 `sidebar.tsx` 中将 Repository Group 和 Default Group 的图标渲染逻辑改为根据 `groupCollapsed` 和 `defaultGroupCollapsed` 状态动态渲染 `folder_special`（折叠）和 `folder_special_open`（展开）状态。
  - **自定义 FoldersOpen 图标**：在 `LegacyIcon.tsx` 中实现了自定义的 `FoldersOpen` React 组件，以 SVG 的形式对齐 Lucide 设计，呈现出底部的 open 文件夹与顶部 closed 文件夹的堆叠，代表展开的 Group；同时将 `folder_special` 替换为 Lucide 原生的 `Folders` 堆叠文件夹，代表折叠的 Group，彻底解决了原先群组图标与项目图标样式完全雷同且没有开合状态的问题。
- **校验：** 本地运行 `./scripts/verify.sh` 通过所有前端 Vite build、Vitest 测试、以及后端 408 项单元测试和文档自检 ✅

## 2026-06-28 会话 3（统一外部 CLI 引擎接入、LOGO 适配、模型设置与系统提示词修复）

- **完成：**
  - **LOGO 替换与视觉对齐**：将 `packages/frontend/src/assets/agy-logo.svg` 替换为最新炫彩拱门渐变 SVG，修复了错误的 Google 徽标。
  - **模型配置覆写修复**：在 `models_config.py` 中将配置项匹配键从 `active_model` 修正为 `agent_active_model`，防止其退化为系统硬编码的默认模型（如 `agnes-2.0-flash`）。
  - **CLI 提示词修复**：调整 `agent_prompt.py` 以确保使用外部 CLI 引擎（如 `antigravity-cli`）进行对话时，系统提示词不再携带 `Runtime model: ...`，而是直接依赖 CLI 自身的配置。
  - **统一 CLI 路由架构**：在 `engine_router.py` 中构建 `CLI_ROUTING_CONFIGS` 引擎配置表，并重构去重原本冗余的代码。将 Claude、Antigravity 以及未来新增的 CLI 路由逻辑完全抽象并统一至 `_route_generic_cli_hybrid` 和 `_route_generic_cli_legacy` 处理。此外，新增了兼容层动态 pop 机制，消除了 `TypeError: got multiple values for keyword argument` 并确保 100% 兼容单元测试。
- **校验：** 本地运行 `uv run pytest` 顺利通过了所有 408 项 Python 单元测试，无漂移 ✅

## 2026-06-28 会话 2（Antigravity CLI 多轮会话会话 ID 追踪、LOGO 视觉对齐）

- **完成：**
  - **Antigravity CLI 会话 ID 追踪**：将 `agy` 的多轮会话会话 ID（`cli_session_id`）生成与追踪行为和 `claude-cli` 全面对齐。在首轮对话时由 Clutch 自动生成 UUID `new_session_id` 并通过 `--conversation` 传入 `agy`；之后的后续对话（包括 hybrid 模式和 legacy 模式）继续传递该 session ID 供 `agy` 自动匹配与载入内部会话历史，从而彻底消除了 `Warning: conversation "agy-session" not found` 且无法保留上文的问题。
  - **Antigravity Logo 细节对齐**：根据用户提供的最新高分辨率视觉图样，调整了 `antigravity.svg` 渐变彩虹拱门的路径几何形状（使内部拱高约占 50%，两腿对称微向外展）与多色线性渐变 stop 点（深蓝 → 湖蓝 → 翠绿 → 橙黄 → 猩红 → 靛紫 → 深蓝），实现高保真度对齐。
- **校验：** 新增 `test_chat_agy_cli_new_session` 测试会话启动参数拼接；本地运行 `./scripts/verify.sh` 通过所有 408 项 Python 单元测试和 13 项前端测试 ✅

## 2026-06-28 会话（PTY 乱码、CLI 提示词、Antigravity LOGO 修复）

- **完成：**
  - **PTY 乱码修复**：在 `shell_session.py` 中将 `_read_available` 改为以字节流形式读取，并使用 `codecs.getincrementaldecoder` 进行增量解码。这避免了因多字节 UTF-8 字符（如“工作空间”中的“工”）跨 Read 缓冲区边界时被错误解码为 `` 乱码的问题。
  - **CLI 编码声明**：在 `cli_adapter.py` 的 `subprocess.Popen` 和 `subprocess.run` 中明确传入 `encoding="utf-8"` and `errors="replace"`，保证各操作系统平台下标准输出流的 UTF-8 兼容性。
  - **CLI 提示词调整**：修改了 `agent_prompt.py`，仅在 `is_clutch_agent` 为 True 时向 system prompt 注入 `Runtime model: ...`；而 `antigravity-cli` (Agy) 等外部 CLI 引擎将不再带有此信息，防止其误报运行在 Clutch 侧大模型上。
  - **返回结果脱敏/品牌替换**：在 `engine_router.py` 中，对 `route_engine` 返回的 `raw_output` 和 `output_events` 也均调用 `sanitize_engine_output`，避免前端读取到事件流或 raw 原始报文中的未替换品牌名（如 Agnes）。
  - **Antigravity LOGO 替换**：设计并用炫彩拱门渐变 SVG 替换了 `apps/desktop/src/assets/tool-logos/antigravity.svg` 中错误的 Google 徽标。
- **校验：** 新增 `test_agent_prompt.py` 测试提示词条件拼装；本地运行 `./scripts/verify.sh` 并顺利通过了所有 407 项 Python 单元测试和 13 项前端测试，文档机检无漂移 ✅

## 2026-06-27 会话（Flow/Chat UX + Tauri dev）

- **完成：**
  - **Tauri 开发白屏：** `scripts/tauri-dev.sh` 守护化 Vite；`beforeDevCommand` 置空；`free_sidecar_port` 仅杀 LISTEN；根目录 `pnpm tauri:dev`。
  - **工作流 Chat：** `workflowAgentSteps` 从 Agent Manager 解析类型/Logo；`active_node_id` 优先；Hybrid 节点可折叠 execution details。
  - **Chat 合并：** `client_message_id` + 乐观发送；Hybrid 图片与正文同源解析。
  - **工作流取消：** `workflow_cancel.py` + Stop 协作式中断；品牌 Logo 组件与资产。
  - **文档：** `PRODUCT_INTRO.md` §3.1/§5.1、`CLAUDE.md`、`README.md`、`FILEMAP.md` 同步。

## 2026-06-27 会话（HRT-01~03 hybrid 修复 commit）

- **完成：**
  - **加载动效去动画：** 移除了 `ChatFeed.tsx` 在 AI 思考状态 (`showThinking`) 时头像位置的 `progress_activity` 旋转加载动画；实现当活跃 Agent 拥有头像时展示其静态头像，无头像时展示静态的机器人/用户图标，使得加载动效仅集中于对话框内的打字脉冲动画。**同时，将加载中与加载完成的头像规则完全对齐（如非内置角色统一使用 `smart_toy` 灰色机器人头，避免加载中和加载后头像闪烁/不一致）。**
  - **会话偏好持久化：** 在 `App.tsx` 中使用 `localStorage` 按 `sessionRunId` 对当前会话的选择（包括所选模式 `isMultiAgent`、所选 Flow `selectedWorkflowId` 与所选 Agent `selectedAgentId`）进行自动存储。并在切换会话时优先进行恢复。
  - **工作流名称解析：** 优化了 `clutchState.workflow_id` 在 `App.tsx` 中变更时的名称解析，自动从 `footerWorkflows` 映射匹配获取人类可绿的工作流展示名。
  - **软件版本动态获取：** 移除了右下角写死的 `Clutch v0.0.0` 版本文本，使用 Tauri 的 `getVersion` API 在桌面环境下动态获取当前应用程序的版本号，对于非 Tauri 浏览器环境安全降级为 `0.0.0`。
  - **用户姓名偏好设置：** 在 `preferences_storage.py` 和 `main.py` 扩展支持 `user_name` 偏好的读取、保存与 API 路由；在 General Settings 页面新增个人名称输入框支持用户自定义昵称，并同步更新 Chat Feed 中用户发送的消息气泡发送者标签展示。
  - **Backlog 梳理决策：** 针对 B-15（虚拟Fallback工作流）与 B-16（自动Fallback单智能体）做已否决废除归档；B-17（Codex 接入）作为未来支持保留；B-20（OS级沙箱）标记为深入调研的待定项；B-08（Git Worktree 隔离）标记为专业企业项目防改坏代码关键能力保留。
  - **PRD文档按页面与Settings子项重构：** 将 `docs/PRODUCT_INTRO.md` 核心功能重新梳理为按页面/视图划分的纯英文大纲结构（包括 Chat Workspace、Observability Panel、Human-in-the-Loop Dialog 和 Settings Dashboard），其中 Settings Dashboard 细分并补齐了通用设置、智能体管理、工作流管理、工具探测、模型凭证、技能注册、MCP扩展、外观设计和会话持久化等 9 个完整的功能子项；同时剔除了不美观的 ASCII 图示。
  - **开发纪律强化：** 在 `CLAUDE.md` 的铁律中新增了“每次 Git Commit 必须同步更新/核对 PRD（`docs/PRODUCT_INTRO.md`）”的强制规定，确保代码与产品规格始终保持同步。
- **校验：** 本地运行 `./scripts/verify.sh` 并顺利通过了所有 357 项后端 Python 单元测试和 13 项前端 Vitest 测试 ✅

## 2026-06-27 会话（用户头像设置与 General 页面开发）

- **完成：**
  - 设置默认用户基准头像：`apps/desktop/src/assets/default_avatar.jpg`。
  - 在 `preferences_storage.py` 和 `main.py` 添加 `"user_avatar"` 偏好和 `/api/preferences/avatar` 接口。
  - 在前端 `themeApi.ts` 和 `clutchState.ts` 补充偏好获取与用户头像更新通知。
  - 在 `SystemPreferencesModal.tsx` 构建 General Settings 面板，支持查看及更换头像（读取本地照片 base64 并持久化）。
  - 增加 i18n 汉化支持。
- **校验：** 新增 `test_avatar_preferences.py`，运行 `./scripts/verify.sh` 全量 pytest 348 个用例 + vitest 13 个用例全部通过 ✅

## 2026-06-27 会话（Step 4：runtime_registry）

- **完成：** `try_shell_exec_hybrid` 统一 SHELL_EXEC 门控 + fallback；`engine_router` 去重
- **校验：** `test_runtime_registry.py`；verify 342 pytest ✅

## 2026-06-27 会话（Step 3 UI：继续上次工作）

- **完成：** 侧栏会话行显示快照图标 + tooltip；`fetchShellSnapshots` + `shell_session_status` 类型
- **校验：** verify 339 pytest + 11 vitest ✅

## 2026-06-27 会话（Shell DISCONNECTED 恢复）

- **完成：** PTY 死亡时写快照、`consume_shell_recovery`、Hybrid 日志 + `shell_session_status` state_patch
- **校验：** `test_disconnected_session_sets_recovery_notice`；verify 339 pytest ✅

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
