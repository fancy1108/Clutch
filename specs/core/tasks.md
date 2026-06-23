# Clutch — 开发任务清单（第 6 步）

> 自 [`proposal.md`](./proposal.md) §6、§10 拆解。**执行顺序按里程碑 M0 → M4。**  
> 验收状态维护于 [`memory/ROADMAP.md`](../../memory/ROADMAP.md)；开放决策见 [`memory/DECISIONS.md`](../../memory/DECISIONS.md)。

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
| M0-02 | WebSocket 连接与信封格式 | FR-03-05 | `event` + `data`；含 `state_patch` | `uv run pytest tests/test_ws_state_patch.py -v` |
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
| M2-07 | 运行历史持久化 + 侧栏入口 | D3, FR-02-01 | 可查看过往 run、状态、时间 | `uv run pytest tests/test_run_history.py -v`；侧栏列表非空 |
| M2-08 | 底部状态栏接真实状态 | FR-02-08 | Branch / Mode / Flow 来自 `ClutchState` 或运行上下文，非硬编码 | 切换工作流或 `state_patch` 后状态栏文案同步变化 |
| M2-09 | 工作区选择与授权 UX | FR-02-01, proposal §13 | 用户选择本地项目根目录并授权；`Header` 面包屑显示真实项目名；未授权时 Adapter 不读盘 | 选目录后 Sidecar 收到 `workspace_path`；Header 面包屑与所选工作区一致 |
| M2-10 | E2E Smoke + vitest 基础设施 | D1, D2 | D1 状态改为 `可执行`；建 `e2e/`；Smoke：health + WS `state_patch`；前端 vitest 首条用例 | `pnpm exec playwright test`（或 `e2e/` 包内命令）Smoke 绿；`TESTS.md` 增 E2E/vitest 行 |
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

## M4 · 打磨与发布

| ID | 任务 | FR | 完成标准 | Verification |
|----|------|-----|----------|--------------|
| M4-01 | 内置模板导入 | FR-01-07 | Video Production 等 1–2 个 | 模板列表可见；一键导入后编辑器可打开 JSON |
| M4-02 | Agent 配置持久化 | FR-06-01–03 | `AgentManager.tsx` 接后端 | 重启应用后 Agent 配置保留 |
| M4-03 | MCP / AI Tools 状态（filesystem） | FR-05-05, FR-05-06 | 至少 filesystem MCP 可连通 | MCP 面板显示 connected；工具数 > 0 |
| M4-04 | API Key 安全存储 | FR-07-03 | Tauri secure store；日志脱敏 | `grep` 日志无 `sk-` 等密钥；Key 存 secure store |
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

## P2 延后（MVP 不阻塞）

| 模块 | FR / Prototype | 说明 |
|------|----------------|------|
| Skills Registry 后端同步 | FR-06-04 · `SkillsRegistry.tsx` | 替代 localStorage |
| 单 Agent 模式 | FR-02-09 · `isMultiAgent` | 隐藏 Flow / Workflows 入口；Header 模式切换 |
| 全量 MCP 类型 | FR-05-05 · `McpServerHub.tsx` | MVP 仅 filesystem |
| 主题 Appearance 持久化 | `ThemeManager.tsx` | 预设主题 localStorage → 可选后端 |
| i18n 双语 | `LanguageContext.tsx` | en/zh 切换；MVP 可保留现有 UI |
| 侧栏仓库文件夹 CRUD | `sidebar.tsx` filter/new folder | REPOSITORIES 分组管理；非 MVP 核心路径 |
| General Settings 实质功能 | `SystemPreferencesModal` settings 占位 | 当前为占位页 |

---

## Prototype → Task 映射（`apps/desktop/src`）

> **UI 已存在、去 mock 化任务见下表。** 完整组件职责叙事见 [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) §7。

| Prototype 组件 / 能力 | 去 mock 目标 | Task | MVP |
|----------------------|-------------|------|-----|
| `App.tsx` | `ClutchState` 投影、布局、文件预览浮层 | M0-03, M2-11 | ✅ |
| `App.tsx` footer | Branch / Model / Workflow 状态栏 | M2-08 | ✅ |
| `Header.tsx` | 面包屑工作区/项目名 | M2-09 | ✅ |
| `Header.tsx` | 语言切换 en/zh | P2 i18n | — |
| `sidebar.tsx` | 工作流/会话列表、运行历史 | M2-07, M2-09 | ✅ |
| `sidebar.tsx` | REPOSITORIES 文件夹树 | M2-09（上下文）/ P2 CRUD | 部分 |
| `ChatFeed.tsx` | Agent 消息流、失败卡片、用户输入 | M2-01, M2-14 | ✅ |
| `ChatFeed.tsx` | Approve / Reject / Retry、Stop Run | M2-04, M1-03 | ✅ |
| `RightPanel` Overview | 进度摘要、Token/成本 | M2-03, M2-13 | ✅ |
| `RightPanel` Overview | Reassign to Builder | M2-12 | ✅ |
| `RightPanel` Files | 工作区目录树、文件预览 | M2-11 | ✅ |
| `RightPanel` Flow | 活跃节点高亮 | M2-03 | ✅ |
| `RightPanel` Changes | git/file diff | M3-02 | ✅ |
| `RightPanel` / `TerminalPanel` | 子进程日志 | M2-02 | ✅ |
| `WorkflowOrchestration.tsx` | 画布编辑、保存/加载 JSON | M1-02, M1-06, M1-07 | ✅ |
| `AgentManager.tsx` | Prompt、Deliverables、工具绑定 | M4-02, M3-05 | ✅ |
| `ModelsManager.tsx` | 模型与 Provider 配置 | M1-08, M4-04, M4-09 | ✅ |
| `AiToolsManager.tsx` | CLI/GUI 工具连接状态 | M4-03 | ✅ |
| `McpServerHub.tsx` | MCP 连接配置与状态 | M4-03 | ✅ |
| `SkillsRegistry.tsx` | Skills 目录扫描 | P2 | — |
| `ThemeManager.tsx` | 主题预设 | P2 | — |
| `SystemPreferencesModal.tsx` | 设置壳（承载上表各面板） | — | — |
| `mockData.ts` / `services/api.ts` | 编排与假 API 响应 | M2-06 | ✅ |
| `clutchState.ts` / WS | `state_patch`、`message`、`log` 等 | M0-02, M0-03, M2-01~03 | ✅ |
| `src-tauri/` | 单入口启动 Sidecar | M0-05 | ✅ |

---

## 任务与文档映射

| 维护什么 | 文件 |
|----------|------|
| 任务定义 | 本文件 |
| Task 交付索引 | `memory/DELIVERABLES.md` |
| 功能验收 ❌/✅ | `memory/ROADMAP.md` |
| 文件路径 | `memory/FILEMAP.md` |
| 开放决策 | `memory/DECISIONS.md` |

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
| `tests/test_cli_adapter.py` | M3-01 |
| `tests/test_fs_watcher.py` | M3-04 |
| `tests/test_evaluator.py` | M3-05 |
| `tests/test_check_branch.py` | M3-06 |
| `tests/test_subprocess_isolation.py` | M3-07 |
| `tests/test_workspace_whitelist.py` | M4-05 |
