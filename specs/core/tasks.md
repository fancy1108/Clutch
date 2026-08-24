# Clutch — 开发任务清单（第 6 步）

> 自 [`proposal.md`](./proposal.md)（归档指针）§6、§10 拆解。**M0–M4 已全部验收** — 状态见 [`memory/ROADMAP.md`](../../memory/ROADMAP.md)；交付见 [`memory/archive/`](../../memory/archive/)。  
> **本文件不维护 ✅/❌** — 仅保留任务定义、完成标准与 **Verification 命令**。

## 里程碑总览

| 阶段 | 交付物 | 验收（proposal §10.2） |
|------|--------|------------------------|
| **M0** | Tauri + Sidecar 骨架 + WebSocket | 前端收到真实 `state_patch` |
| **M1** | WorkflowCompiler + 最小 LangGraph | JSON 工作流可执行 |
| **M2** | 去 mock，接入真实事件 | Terminal / Chat 为真数据 |
| **M3** | CLI Adapter + Diff + Cursor 唤起 | Claude CLI 跑通 |
| **M4** | 模板、错误提示、打包 | 可安装 DMG 演示 |

**MVP 闭环**（§10.1）：模板运行 → CLI 真实执行 → 检查失败 → 人工审批 → 通过。

---

## 任务格式说明

每个任务除表内「完成标准」外，**标记完成前必须**：

1. 运行对应 **Verification** 命令，输出记入 `memory/TESTS.md` 或 `runs/verification/`
2. 在 `memory/DELIVERABLES.md` 追加交付索引（Commit、证据路径、交付文件列表）
3. 在 `memory/ROADMAP.md` 勾选前提供证据（pytest 通过 / 手动步骤截图）
4. **禁止**用桩实现或 mock 编排逻辑通过验收（与 `CLAUDE.md` 铁律一致）

| 列 | 含义 |
|----|------|
| **FR** | 对应 `proposal.md` 功能需求 ID |
| **完成标准** | 可观测的交付结果 |
| **Verification** | 必须在终端实际运行的校验命令或步骤 |

---

## M0 · 基座

| ID | 任务 | FR | 完成标准 | Verification |
|----|------|-----|----------|--------------|
| M0-01 | FastAPI Sidecar 健康检查与 CORS | FR-07-02, FR-07-04 | `/health` 可用；仅 `127.0.0.1:8123` | `uv run pytest tests/test_health.py -v` |
| M0-02 | WebSocket 连接与信封格式 | FR-03-05 | `event` + `data`；含 `state_patch`；**无**侧栏调试按钮（联调靠 pytest + 主聊天 `submitChatMessage`） | `uv run pytest tests/test_ws_state_patch.py -v` |
| M0-03 | 前端 WebSocket store（替换 mock 驱动） | FR-02-04 | `App.tsx` 投影 `ClutchState`；禁止 `setTimeout` 编排 | `pnpm build`；`CLUTCH_STRICT_MOCK=1 ./scripts/check-doc-drift.sh` |
| M0-04 | Vite 代理 `/api`、`/ws` → 8123 | — | `pnpm dev` 可连 Sidecar | Sidecar 启动后 `curl -s http://127.0.0.1:8123/health` 返回 200 |
| M0-05 | Tauri 拉起 Sidecar 生命周期 | FR-07-01, FR-07-02 | 单入口启动；失败有明确错误 | `pnpm tauri dev` 启动后 `/health` 可达，无需手动开第二个终端 |
| M0-06 | `ClutchState` 共享类型对齐复审 | FR-03-02 | TS `ClutchState` 与 Python `state.py` 字段一致 | 人工 diff `packages/shared-types` ↔ `services/orchestrator/src/state.py`；`pnpm build` 无类型错误 |

**M0 门禁**：`ROADMAP` E2E 前提第一行可勾选。

---

## M1 · 引擎

> **已决策**：D4（LLM 默认 DeepSeek V4 Pro、可切换）、D5（用户工作流 → 应用数据目录）— `DECISIONS.md`

| ID | 任务 | FR | 完成标准 | Verification |
|----|------|-----|----------|--------------|
| M1-01 | Workflow JSON Schema 校验 | FR-01-06 | 对接 `workflows/workflow.schema.json` | `uv run pytest tests/test_workflow_validator.py tests/test_validate_api.py -v` |
| M1-02 | WorkflowCompiler → LangGraph | FR-03-01, FR-01-01 | 加载 `workflows/video-production.json` 编译为 LangGraph；五类节点类型均有对应 handler；**非**最小桩图 | `uv run pytest tests/test_compiler.py -v`（须断言节点数、边、节点类型与 JSON 一致） |
| M1-03 | `start_run` / `stop_run` HTTP API | FR-03-01, FR-03-04 | 返回 `run_id`；`stop_run` 后子进程清理；运行走 M1-02 编译图 | `uv run pytest tests/test_start_run.py -v`（须含「编译图执行后 `active_node_id` 变化」断言，非仅 `run_id`） |
| M1-04 | Orchestrator 路由节点 | FR-03-03 | 依工作流边优先路由；LLM 仅作兜底 | `uv run pytest tests/test_orchestrator_routing.py -v` |
| M1-05 | `run_completed` 与状态序列化 | FR-03-02, FR-03-06 | 终态 passed/failed 经 WS 推送 `run_completed` | `uv run pytest tests/test_run_completed.py -v` |
| M1-06 | 工作流编辑器保存/加载（前端） | FR-01-02, FR-01-03 | `WorkflowOrchestration.tsx` 读写真实 JSON；Agent 节点配置写入 JSON | 保存后磁盘/应用目录存在 JSON；重开编辑器字段还原 |
| M1-07 | 图结构保存前校验 | FR-01-06 | 缺开始/结束、孤立节点时中文错误提示 | `uv run pytest tests/test_workflow_validator.py -k invalid -v` |
| M1-08 | LLM Provider Router | D4 | Provider 抽象；默认 DeepSeek V4 Pro；可切换；API Key 按 Provider 分存 | `uv run pytest tests/test_llm_provider.py -v` |
| M1-09 | 用户工作流持久化 API | D5, FR-01-02 | 内置模板只读自 `workflows/`；用户工作流 CRUD 至 Tauri 应用数据目录 | `uv run pytest tests/test_workflow_storage.py -v`；读写路径符合 D5 |

**M1 门禁**：`POST /api/runs/start` + `video-production.json` 端到端编译并至少推进一个真实节点（非桩 `n1`）。

---

## M2 · 监督台（去 mock）

| ID | 任务 | FR | 完成标准 | Verification |
|----|------|-----|----------|--------------|
| M2-01 | Chat 接 `message` 事件 | FR-02-02, FR-02-03 | 移除 `mockData` / `api.ts` 消息源；含用户输入 `submitChatMessage`；失败卡片样式保留 | `grep` 确认 `ChatFeed.tsx` 无 `mockData` 编排引用；WS 注入 `message` 后 UI 更新 |
| M2-02 | Terminal 接 `log` 事件 | FR-02-05 | 真实子进程 stdout/stderr | Sidecar 推 `log` 事件后 Terminal 可见新行 |
| M2-03 | Overview / Flow 接 `state_patch` | FR-02-04, FR-02-07 | 活跃节点高亮；Overview 摘要随 WS 更新 | `state_patch` 改变 `active_node_id` 后 Flow 高亮对应节点 |
| M2-04 | Human Gate UI | FR-04-01–05 | Approve / Reject / Retry + 审计 | 触发 `human_required` 后三按钮可用；操作后 Chat/Terminal 有 `[SUPERVISOR]` 行 |
| M2-05 | LangGraph `interrupt_before` 人工闸门 | FR-04-02–04 | `human_decision` resume 后继续执行 | `uv run pytest tests/test_human_gate.py -v` |
| M2-06 | 废弃 `mockData.ts` 编排逻辑 | proposal §15 | 仅保留可选 demo 种子；`api.ts` 无 mock 编排 | `CLUTCH_STRICT_MOCK=1 ./scripts/check-doc-drift.sh` 通过 |
| M2-07 | 运行历史持久化 + 侧栏入口 | D3, FR-02-01 | 可查看过往 run、状态、时间；**点选会话可加载完整 messages**（D11） | `uv run pytest tests/test_run_history.py tests/test_run_state_store.py -v`；侧栏列表非空 |
| M2-08 | 底部状态栏接真实状态 | FR-02-08 | Branch / Mode / Flow 来自 `ClutchState` 或运行上下文，非硬编码 | 切换工作流或 `state_patch` 后状态栏文案同步变化 |
| M2-09 | 工作区选择与授权 UX | FR-02-01, proposal §13 | 用户选择本地项目根目录并授权；`Header` 面包屑显示真实项目名；未授权时 Adapter 不读盘 | 选目录后 Sidecar 收到 `workspace_path`；Header 面包屑与所选工作区一致 |
| M2-10 | E2E Smoke + vitest 基础设施 | D1, D2 | D1 状态改为 `可执行`；建 `e2e/`；Smoke：health + WS `state_patch`；**会话历史** `session-history.spec.ts` | `pnpm exec playwright test` Smoke + session-history 绿；`TESTS.md` 增 E2E/vitest 行 |
| M2-11 | Files 面板工作区目录树与预览 | FR-02-04 | `RightPanel` Files  tab 展示授权工作区真实目录；点击文件读盘预览；移除 `fileTreeNodes` / `getFullFileContent` mock | M2-09 后：目录与磁盘一致；预览内容与文件实际内容一致 |
| M2-12 | 「交给 Builder 修复」Reassign | proposal §5.1, FR-04 | `reassignToBuilder` 走真实 API；校验失败后可将任务打回 Builder 重跑 | 手动：Evaluator 失败后点击 Reassign，Chat/Terminal 出现 Builder 活动 |
| M2-13 | Overview Token/成本统计 | FR-02-04 | Session Token 分布、成本摘要来自 `ClutchState` / `state_patch`；非硬编码 | `state_patch` 更新 token 字段后 Overview 数字同步 |
| M2-14 | `validation_result` 事件投影 | FR-02-03, FR-01-04 | Evaluator 检查结果经 WS 推送；Chat 失败卡片与 Overview 状态更新 | Sidecar 推 `validation_result` 后 UI 展示 FAILED 卡片 |

**M2 门禁**：D1 → `可执行`；`ROADMAP` E2E 前提第二行可勾选；`./scripts/verify.sh` 含新增 E2E job（或文档约定单独 CI job）。

---

## M3 · 工具链

| ID | 任务 | FR | 完成标准 | Verification |
|----|------|-----|----------|--------------|
| M3-01 | CLI Adapter（Claude Code） | FR-05-01, FR-05-02 | 真实调用 + 非零退出码失败 | `uv run pytest tests/test_cli_adapter.py -v`（或 `@pytest.mark.integration`） |
| M3-02 | Changes 面板真实 diff | FR-02-06 | `file_changed` → Diff 预览 | Sidecar 推 `file_changed` 后 Changes 面板展示 diff |
| M3-03 | Cursor GUI Adapter | FR-05-03 | `open -a Cursor` 生效 | 手动：点击按钮后 Cursor 打开工作区 |
| M3-04 | FS Watcher + debounce | FR-05-04 | 保存后 ≤3s 触发 Evaluator | `uv run pytest tests/test_fs_watcher.py -v` |
| M3-05 | Evaluator 执行用户 Agent 配置 | D6, FR-01-04, FR-06-03 | Prompt/Skills/Deliverables 驱动；机制含 `file_exists` + `shell` | `uv run pytest tests/test_evaluator.py -v` |
| M3-06 | 检查节点分支连线 | FR-01-05 | 不通过 → 人工闸门 / 回退 | `uv run pytest tests/test_check_branch.py -v` |
| M3-07 | 子进程崩溃隔离 | proposal §7 稳定性 | 单个子进程崩溃不导致 Sidecar 退出；`run` 标记 failed 并推送 | `uv run pytest tests/test_subprocess_isolation.py -v` |

**M3 门禁**：MVP 闭环可演示；E2E 闭环用例可对齐 proposal §10.1。

---

## M3-F · Flow 多 Agent 接力（D23 · Weather-to-Vision）

> **决策**：`memory/DECISIONS.md` D23。**依赖**：单 Agent `agentType` + `modelId` 已落地。  
> **最小可演示路径**：M3-F01 → M3-F02 → M3-F04 → M3-F06 → M3-F07 → M3-F09。

| ID | 任务 | 完成标准 | Verification |
|----|------|----------|--------------|
| M3-F01 | `node_outputs` + `resolve_agent_task_input` | `CompilerState` 扩展；auto 规则解析上游/用户输入；`node.data.instruction` 作前缀 | `uv run pytest tests/test_node_input.py -v` |
| M3-F02 | `_handle_agent_task` 写入输出并消费解析输入 | 每节点执行后 `node_outputs[id]=output`；下游收到上游文本 | `uv run pytest tests/test_compiler.py -k handoff -v` |
| M3-F03 | `workflow_projection` 与 `current_instruction` 对齐 | patch 反映链式执行结果，不单锁用户首句 | `uv run pytest tests/test_workflow_projection.py -v` |
| M3-F04 | Flow 注入 Agent `markdownDoc` | 非生图任务使用 `_compose_agent_system_prompt` 或共享模块 | pytest 断言 prompt 含 protocol 片段 |
| M3-F05 | Flow 内 Clutch 对话走 MCP ReAct | 有 `mcpServerIds` 时同 Plain Chat；`modelId` 传入 `mcp_react` | `uv run pytest tests/test_agent_executor.py -k clutch -v` |
| M3-F06 | 生图节点使用上游输出作 prompt | Artist 节点 `task_instruction` = Researcher `output` | `test_flow_image_uses_upstream_output` |
| M3-F07 | 每 `agent_task` 增量 `state_patch` | 节点完成即 Chat 多一条消息；`active_agent` / `active_node_id` 更新 | mock forwarder 断言 patch 次数；手动两节点 Flow |
| M3-F08 | 前端 Flow 等待态 | `running` 时按 `active_agent` 显示 thinking（复用单 Agent） | vitest 或手动 |
| M3-F09 | Weather-to-Vision Flow 配置落地 | 用户 Flow：Researcher（clutch）→ Artist（clutch + Agnes）；线性边 | validator 通过；手动端到端 |
| M3-F10 | Researcher 真实天气（可选） | 天气 MCP/HTTP 或保持 markdown 推断（首版 B 可跳过） | 人工 / 集成测试 |
| M3-F11 | Flow 链式 E2E 冒烟 | fake LLM + fake image 两节点 handoff | `runs/verification/` 证据 |

**M3-F 门禁**：Weather-to-Vision 手动跑通：用户一句 → Researcher 消息 → Artist 出图；Chat 逐步出现两条 Agent 消息。

---

## M4 · 打磨与发布

| ID | 任务 | FR | 完成标准 | Verification |
|----|------|-----|----------|--------------|
| M4-01 | 内置模板导入 | FR-01-07 | Video Production 等 1–2 个 | 模板列表可见；一键导入后编辑器可打开 JSON |
| M4-02 | Agent 配置持久化 | FR-06-01–03 | `AgentManager.tsx` 接后端 | 重启应用后 Agent 配置保留 |
| M4-03 | MCP / AI Tools 状态（filesystem） | FR-05-05, FR-05-06 | 至少 filesystem MCP 可连通 | MCP 面板显示 connected；工具数 > 0 |
| M4-04 | API Key 安全存储 | FR-07-03 | **当前**：`models.json` + `chmod 600` + 日志不写 Key；**T2 目标**：Keychain | 日志无 `sk-`；Key 不落仓库 |
| M4-05 | 工作区路径白名单 | proposal §13, M2-09 | 与 M2-09 授权路径联动；越界读写返回 403 + 中文提示 | `uv run pytest tests/test_workspace_whitelist.py -v` |
| M4-06 | macOS DMG 打包 | FR-07-01 | 可安装演示 | `pnpm tauri build` 产出 DMG；安装后可启动 |
| M4-07 | 错误提示与可操作建议 | proposal §8 | 失败卡片旁有下一步 | 手动：触发失败场景，卡片含修复/审批/重试指引 |
| M4-08 | 高危工具执行确认 | proposal §7 安全 | 执行 shell/CLI 等高危步骤前 UI 确认（可配置跳过） | 手动：首次运行高危节点弹出确认；拒绝则不执行 |
| M4-09 | ModelsManager UI 与 Provider 对齐 | D4, FR-06-02 | `ModelsManager` 读写与 M1-08 Provider 配置一致；自定义模型 API Key 走 M4-04 | 重启后模型列表与选中项保留；切换模型后 `start_run` 使用对应 Provider |

---

## 测试与验收（跨里程碑）

> 与 Vibe 第 8 步对齐；**不替代**各 task 的 Verification，而是里程碑级汇总。

| ID | 触发里程碑 | 内容 | Verification |
|----|------------|------|--------------|
| T-01 | M2 完成 | 真实性审计（Phase 0） | `grep -r mockData apps/desktop/src` 无编排源；停 Sidecar 后 UI 显示连接失败 |
| T-02 | M2 完成 | E2E Smoke | 同 M2-10 |
| T-03 | M3 完成 | E2E MVP 闭环 | Playwright 跑通 proposal §10.1 路径；证据入 `runs/verification/` |
| T-04 | M4 前 | 红队 / 体感审计（抽样） | 独立会话 QA；`memory/FAILURES.md` 记录；`TESTS.md` 归档 |

---

## P2 · 打磨（MVP 后，D13 执行顺序）

| ID | 任务 | FR / Prototype | 完成标准 | Verification |
|----|------|----------------|----------|--------------|
| P2-01 | Skills Registry 后端同步 + 扫描 | FR-06-04 · `SkillsRegistry.tsx` | 挂载目录持久化至 Sidecar；扫描 `SKILL.md`；`AgentManager` 联动 | `uv run pytest tests/test_skills_registry.py -v` |
| P2-02 | 全量 MCP 配置与状态 | FR-05-05 · `McpServerHub.tsx` | 用户可增删 stdio/SSE MCP；Hub 展示连接与工具数 | `uv run pytest tests/test_mcp_registry.py -v` |
| P2-03 | Theme 持久化 | `ThemeManager.tsx` | 重启后保留活跃主题 | 手动：切换主题 → 重启 → 主题仍在 |
| P2-04 | i18n 双语验收 | `LanguageContext.tsx` · `Header.tsx` | Header en/zh 切换；监督台关键文案双语 | 手动 + E2E `lang-zh` / `lang-en` data-testid |
| P2-05 | 侧栏 REPOSITORIES CRUD | `sidebar.tsx` | filter / new folder；分组持久化 | 手动：新建分组 → 重启 → 仍在 |
| P2-06 | General Settings 实质功能 | `SystemPreferencesModal` | 替换「功能开发中」占位（已支持用户自定义头像） | 部分落地（D14）— 其余设置项继续延后 |

---

## D25 · Hybrid Runtime（HRT-xx）

> **权威 Task 表与验收清单**：[`hybrid-runtime-plan.md`](./hybrid-runtime-plan.md)  
> **决策**：D25 · D27 · D28 — [`memory/DECISIONS.md`](../../memory/DECISIONS.md)  
> **ROADMAP 勾选**：[`memory/ROADMAP.md`](../../memory/ROADMAP.md) §D25

| ID | 任务 | 完成标准 | Verification |
|----|------|----------|--------------|
| HRT-00 | 计划与文档对齐 | hybrid-runtime-plan + memory/specs 同步 | `check-doc-drift.sh` |
| HRT-01 | 基础聊天气泡 + idle | §3.1 A–D；无 shell/snapshot 泄漏 | 人工 + pytest |
| HRT-02 | Marker 完成检测 | 真实 turn 不 600s 超时 | pytest + 本地 claude turn |
| HRT-03 | Snapshot 仅断线注入 | 续轮无 Task summary 行 | pytest |
| HRT-04 | **单 session 产品验收** | ROADMAP §D25 勾选 A–E | `runs/verification/2026-06-27-hrt-04-acceptance.md` |
| HRT-05 | Hybrid audit JSONL | 每 turn 结构化行 | pytest |
| HRT-06 | debug API | `GET /api/runs/{id}/debug` | pytest |
| HRT-07 | 诊断导出 | UI 或 script | 手动 |
| HRT-08 | 多 session 并发治理 | 超限 UI 提示 | pytest + 手动 |
| HRT-09 | 后台 turn hydrate | 切 session 后状态正确 | 手动 |
| HRT-10 | POC #6 #10 | BUSY 拒绝；两 run cwd 隔离 | pytest / poc |

已交付代码块（非 HRT 序号）：**HRT-S1 ~ S4**、**HRT-S5-partial** — 见 hybrid-runtime-plan §1.1。

---

## Prototype → Task 映射（`apps/desktop/src`）

> **UI 已存在、去 mock 化任务见下表。** 完整组件职责叙事见 [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) §7。  
> **验收状态：** 仅 [`memory/ROADMAP.md`](../../memory/ROADMAP.md) — 下表不含 ✅/❌。

| Prototype 组件 / 能力 | 去 mock 目标 | Task |
|----------------------|-------------|------|
| `App.tsx` | `ClutchState` 投影、布局、文件预览浮层 | M0-03, M2-11 |
| `App.tsx` footer | Branch / Model / Workflow 状态栏 | M2-08 |
| `Header.tsx` | 面包屑工作区/项目名 | M2-09 |
| `Header.tsx` | 语言切换 en/zh | P2 i18n |
| `sidebar.tsx` | 工作流/会话列表、运行历史、**点选恢复 messages** | M2-07, M2-09, D11 |
| `sidebar.tsx` | REPOSITORIES 文件夹树 | M2-09（上下文）/ P2 CRUD |
| `ChatFeed.tsx` | Agent 消息流、失败卡片、用户输入 | M2-01, M2-14 |
| `ChatFeed.tsx` | Approve / Reject / Retry、Stop Run | M2-04, M1-03 |
| `RightPanel` Overview | 进度摘要、Token/成本 | M2-03, M2-13 |
| `RightPanel` Overview | Reassign to Builder | M2-12 |
| `RightPanel` Files | 工作区目录树、文件预览 | M2-11 |
| `RightPanel` Flow | 活跃节点高亮 | M2-03 |
| `RightPanel` Changes | git/file diff | M3-02 |
| `RightPanel` / `TerminalPanel` | 子进程日志 | M2-02 |
| `WorkflowOrchestration.tsx` | 画布编辑、保存/加载 JSON | M1-02, M1-06, M1-07 |
| `AgentManager.tsx` | Prompt、Deliverables、工具绑定 | M4-02, M3-05 |
| `ModelsManager.tsx` | 模型与 Provider 配置 | M1-08, M4-04, M4-09 |
| `AiToolsManager.tsx` | CLI/GUI 工具连接状态 | M4-03 |
| `McpServerHub.tsx` | MCP 连接配置 + Sidecar CRUD | P2-02 |
| `SkillsRegistry.tsx` | Skills 目录扫描 + Sidecar 持久化 | P2-01 |
| `ThemeManager.tsx` | 主题预设 + Sidecar 持久化 | P2-03 |
| `SystemPreferencesModal.tsx` | 设置壳（承载上表各面板） | — |
| `mockData.ts` / `services/api.ts` | 编排与假 API 响应 | M2-06 |
| `clutchState.ts` / WS | `state_patch`、`message`、`log` 等 | M0-02, M0-03, M2-01~03 |
| `src-tauri/` | 单入口启动 Sidecar | M0-05 |

---

## 任务与文档映射

| 维护什么 | 文件 |
|----------|------|
| 任务定义 | 本文件 + [`hybrid-runtime-plan.md`](./hybrid-runtime-plan.md)（D25 HRT） |
| Task 交付索引 | `memory/DELIVERABLES.md` |
| 功能验收 ❌/✅ | `memory/ROADMAP.md` |
| 文件路径 | `memory/FILEMAP.md` |
| 开放决策 | `memory/DECISIONS.md` |

## Agent Harness（B-34）

> 书 06 · **Q-AGENT-1 = C**（本机 CC Switch Agnes；CI 不绑密钥）。勿写入交付表 D54+。  
> **无界面变化** — 不请 PM 点验 Chat/设置。

**B-34 做了什么：** 给开发一条尺子，不是改用户路径。

1. **提示词快照** — 同一套 Agent 配置，两次组装；去掉会变的 `env`（本机时间 / 系统 / Shell / 工作区路径）后，静态层指纹必须一致。防「提示词悄悄漂了」。
2. **三条契约** — Ask 层写明只读；todos 出现在 `task_state`；「实现登录页」类请求要求 `propose_plan`。
3. **可选真模型抽检** — `CLUTCH_AGENT_EVAL_LIVE=1` 时用 CC Switch / Clutch 的 Agnes 跑 Ask / 还剩哪些 todo / 网页注入三案。CI 无密钥 skip；禁止把密钥写入日志。

**B-34 没做什么：** 没有冻死系统提示词（故意改文案时测试会红、承认即可）。**没有删掉、也没有挪走本机时间** — 时间仍在 D53 `env` 层、整段 system 前缀里。挪到对话末尾每轮整换的 `<agent_status>`（连同完整 Todo）是 **B-35**（**Q-AGENT-2 = A**），尚未立项落地。对照：现在 = 时钟/Todo 在前缀里破坏缓存；预期 = 前缀只留稳定层。

| ID | 任务 | 完成标准 | Verification |
|----|------|----------|--------------|
| B34-01 | 提示词确定性快照 | 同配置两次组装静态层指纹一致；`env` 含 Local time 但不入指纹 | `cd services/orchestrator && uv run pytest tests/test_agent_eval_b34.py -v` |
| B34-02 | 契约：Ask / todo / propose_plan | Ask 层只读；todos 出现在 `task_state`；特性请求含 `propose_plan` | 同上 |
| B34-03 | 本机 Agnes 任务级小集 | 无密钥 skip；`CLUTCH_AGENT_EVAL_LIVE=1` 时跑 Ask / todo / 注入 3 案 | `CLUTCH_AGENT_EVAL_LIVE=1 uv run pytest tests/test_agent_eval_b34.py -k live -v` |

## Agent eval ablation（B-48）

> 书 06 · B-34 之后。不升 D54+。无 Chat / Settings 变化。

**做了什么：** 评测组装可按 `CLUTCH_AGENT_EVAL_ABLATION`（`all` 或逗号层名）丢掉可选 prompt 层（skills / memory / tools / …），对比指纹。`persist_trajectory` 往 `runs/archive/eval/trajectory.jsonl` 追加 JSONL，写入前剥掉 `api_key` 等密钥字段。

**没做什么：** 不改 Chat；不自动在 CI live 里写仓库 archive；不做消融后的自动打分报表。

| ID | 任务 | 完成标准 | Verification |
|----|------|----------|--------------|
| B48-01 | 消融闸 | `ablation=tools` 后无 tools 层，指纹与全集不同 | `uv run pytest tests/test_agent_eval_b48.py -v` |
| B48-02 | trajectory 落盘 | JSONL 含 name/fingerprint；`api_key` 不落盘 | 同上 |

## Agent status（B-35）

> 书 02 · **Q-AGENT-2 = A**。无 Chat 气泡变化；可感知处：Agent Manager「运行时提示词分层」多一层 `agent_status`，`env` 不再含时钟。

**做了什么：** 本机时间与完整 Todo/计划从 D53 system 前缀移到对话末尾一条 `<agent_status>`；每轮用新条整换旧条（`attach_trailing_status`），不堆历史。`as_system_prompt()` 不含该层。OS / Shell / 工作区仍留在 `env`。

**没做什么：** 不改 Chat 里 Todo 卡的样子；不做分层压缩（B-36，已另节）；不把状态写进用户可见气泡。

| ID | 任务 | 完成标准 | Verification |
|----|------|----------|--------------|
| B35-01 | 前缀去掉时钟与 Todo | `compose_agent_system_prompt` 无 `Local time:`；todos 只在 `agent_status` | `uv run pytest tests/test_agent_prompt.py tests/test_task_state_d8.py tests/test_agent_eval_b34.py -v` |
| B35-02 | 末尾状态整换 | 连续两次 attach 后历史里只有一条 `<agent_status>` | 同上 |

## Agent context layers（B-36）

> 书 02 · B-35 之后。不升 D54+。无新 Chat 气泡；`/compact` 仍是最后一档（D8/D18）。

**做了什么：** ReAct 送给模型的工具结果按四层收：大段先落盘只留指针 → 丢掉重复/空转噪声 → 工具正文合计超阈值时把较旧的一批也落盘（最近 2 条保持全文）→ 会话 token 仍超 15000 才走现有全量 digest（`should_compact` / `/compact`）。L1–L3 **不调 LLM**。

**没做什么：** 不改 Chat 气泡折叠交互；来源标记见 B-44；不把落盘正文自动再灌回模型。

| ID | 任务 | 完成标准 | Verification |
|----|------|----------|--------------|
| B36-01 | L1 磁盘化 | 超阈值 tool content 写成 `runs/archive/tool_results/*.txt`，消息只留指针+预览 | `uv run pytest tests/test_context_layers_b36.py -v` |
| B36-02 | L2 噪声 + L3 批量 | 重复/空转旧工具被丢掉；合计超阈值时只压旧工具、保留最近 2 条 | 同上 |
| B36-03 | L4 全量熔断仍在 | `should_compact` / `/compact` 行为不变 | `uv run pytest tests/test_compaction.py tests/test_context_layers_b36.py -v` |

## Agent archived tool markers（B-44）

> 书 02 · B-36 之后。不升 D54+。无新 Chat 气泡。

**做了什么：** 落盘后的工具结果指针标明 `source=tool truncated=yes`（外部工具产出、正文已收走）。模型下一轮只看到指针 + 短预览；全文在 `runs/archive/tool_results/`。

**没做什么：** 不改 Chat 展开交互；不做分页把落盘正文自动灌回模型。

| ID | 任务 | 完成标准 | Verification |
|----|------|----------|--------------|
| B44-01 | 指针带来源与截断标记 | offload 后 content 含 `source=tool` 与 `truncated=yes` | `uv run pytest tests/test_context_layers_b36.py -v` |

## Agent verification gate（B-37）

> 书 01+05 · **Q-AGENT-3 = C**。不升 D54+。沿用 D5 验证报告卡，不新增卡片。

**做了什么：** Agent 声称 `submit_verification` 通过时，harness 先跑工作区测套（有 `tests/` / `pytest.ini` / `package.json` test）；失败则卡上多一步失败、结论改 failed。再机械核对 `changed_files` 是否在磁盘上（隔离子检查，**不**用同一个模型给自己的作文打分）。

**没做什么：** 不另开一个会写长评的同模型 reviewer；空转循环见 B-38。

| ID | 任务 | 完成标准 | Verification |
|----|------|----------|--------------|
| B37-01 | 测套失败不得通过 | 有失败测试时 conclusion=failed，步骤含 `harness_tests` | `uv run pytest tests/test_verify_harness_b37.py tests/test_verification_d5.py -v` |
| B37-02 | 产物缺失不得通过 | 列出的 changed file 不在磁盘 → failed + `harness_artifacts` | 同上 |
| B37-03 | 无工作区不改 D5 | 未授权工作区时自报结论保持原样 | 同上 |

## Agent progress loop（B-38）

> 书 01。不升 D54+。沿用 D9 Continue，不新开卡片。

**做了什么：** 同一回合里 `read_file` / `list_dir` / `grep` / `read_skill` 用同一参数第 2 次提醒、第 3 次停住（不真执行），对话出现 Continue。写文件不计入。

**没做什么：** 不改失败熔断阈值；不做 B-39 记忆。

| ID | 任务 | 完成标准 | Verification |
|----|------|----------|--------------|
| B38-01 | 同参读三次即停 | 第 3 次 identical read → stop；写工具不计 | `uv run pytest tests/test_progress_loop_b38.py tests/test_run_control_d9.py -v` |
| B38-02 | Continue 仍出现 | stop 文案触发 `should_offer_continue` | 同上 |

## Agent workspace memory（B-39）

> 书 03+08 · **Q-AGENT-4 = C 用 B 落地**。不升 D54+。无新 Chat 卡片。

**做了什么：** 用户说「记住：…」或 Agent 调用 `remember_preference` 时，写入工作区 `.clutch/memory/MEMORY.md`（可在 Files 打开编辑）。下一轮把该文件概览注入 prompt。条目过多只留最近 40 条。全局 D16 JSON 仍在。

**没做什么：** 不做 B-10 检索；不做 B-40 成败反思；投毒过滤见 B-45。

| ID | 任务 | 完成标准 | Verification |
|----|------|----------|--------------|
| B39-01 | 可打开 MEMORY.md | append 后文件存在且含笔记 | `uv run pytest tests/test_workspace_memory_b39.py -v` |
| B39-02 | 重复不膨胀 | 相同句子不重复；超过 40 条裁旧 | 同上 |

## Agent verification notes（B-40）

> 书 08。不升 D54+。无新 Chat 卡片。

**做了什么：** `submit_verification` 通过/失败后，往工作区 `.clutch/memory/MEMORY.md` 追加一行 `Worked: {title}` 或 `Failed: {title}`。

**没做什么：** 不做长篇反思；投毒过滤见 B-45。

| ID | 任务 | 完成标准 | Verification |
|----|------|----------|--------------|
| B40-01 | 验证结果落盘 | passed → `Worked:`；failed → `Failed:` | `uv run pytest tests/test_workspace_memory_b39.py -v` |

## Agent memory poison（B-45）

> 书 03。不升 D54+。无新 Chat 卡片。

**做了什么：** 网页/MCP「请记住 + URL」或裸 URL 不写入 `.clutch/memory/MEMORY.md`，也不写入 Settings Memory；`remember_preference` 返回错误，Agent 不得说已保存。

**没做什么：** 不做检索（B-10）；不加新 Chat 卡。

| ID | 任务 | 完成标准 | Verification |
|----|------|----------|--------------|
| B45-01 | 投毒不入库 | 裸 URL / 请记住+https 被拒绝 | `uv run pytest tests/test_workspace_memory_b39.py -v` |

## Agent tool ACI（B-41）

> 书 04。不升 D54+。无新 Chat 卡片。

**做了什么：** 内置工具描述写明何时用/不用。按文件名查是否存在（如 README.md）走 `list_dir`；若模型仍 `grep` 文件名，harness 改写成 `list_dir`，步骤条显示 **List** 而不是 Search。不读文件内容。

**没做什么：** 不加按名递归 glob 工具；不改 D46 步骤条组件。

| ID | 任务 | 完成标准 | Verification |
|----|------|----------|--------------|
| B41-01 | 文件名 grep 改走 list | `grep README.md` 返回目录列表，不含文件正文 | `uv run pytest tests/test_tool_aci_b41.py -v` |
| B41-02 | 步骤条是 List | 改写后 kind=list，header 为 Listed 不是 Searched | 同上 |

## Spurious verification card（D5）

> D5 回归。不升 D54+。无新 Chat 卡片。

**做了什么：** `submit_verification` 在记住 / 问答 / 本轮未改文件且用户未要报告时不发布验证卡；上一轮的卡不复制到后一轮回复；也不因此往 MEMORY.md 写 `Worked:`。

**没做什么：** 不改 D5 卡片样子；不做 B-48。

| ID | 任务 | 完成标准 | Verification |
|----|------|----------|--------------|
| D5-fix-01 | 记住不发卡 | remember 回合 `verification_report is None` | `uv run pytest tests/test_verification_d5.py -v` |
| D5-fix-02 | 旧卡不跟到新用户消息 | 后一轮 seal 不含 leftover report | 同上 |

## 待建 pytest 文件（随 task 交付）

| 文件 | 关联 task |
|------|-----------|
| `tests/test_compiler.py` | M1-02 |
| `tests/test_orchestrator_routing.py` | M1-04 |
| `tests/test_run_completed.py` | M1-05 |
| `tests/test_llm_provider.py` | M1-08 |
| `tests/test_workflow_storage.py` | M1-09 |
| `tests/test_human_gate.py` | M2-05 |
| `tests/test_run_history.py` | M2-07 |
| `tests/test_run_state_store.py` | M2-07, D11 |
| `tests/test_cli_adapter.py` | M3-01 |
| `tests/test_fs_watcher.py` | M3-04 |
| `tests/test_evaluator.py` | M3-05 |
| `tests/test_check_branch.py` | M3-06 |
| `tests/test_subprocess_isolation.py` | M3-07 |
| `tests/test_repository_groups.py` | P2-05 |
| `tests/test_skills_registry.py` | P2-01 |
| `tests/test_agent_eval_b34.py` | B34-01–03 |
| `tests/test_agent_eval_b48.py` | B48-01–02 |
| `tests/test_tool_aci_b41.py` | B41-01–02 |
