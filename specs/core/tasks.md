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

## M0 · 基座

| ID | 任务 | FR | 完成标准 |
|----|------|-----|----------|
| M0-01 | FastAPI Sidecar 健康检查与 CORS | FR-07-02, FR-07-04 | `/health` 可用；仅 `127.0.0.1:8123` |
| M0-02 | WebSocket 连接与信封格式 | FR-03-05 | `event` + `data`；含 `state_patch` |
| M0-03 | 前端 WebSocket store（替换 mock 驱动） | FR-02-04 | `App.tsx` 投影 `ClutchState`；禁止 `setTimeout` 编排 |
| M0-04 | Vite 代理 `/api`、`/ws` → 8123 | — | `pnpm dev` 可连 Sidecar |
| M0-05 | Tauri 拉起 Sidecar 生命周期 | FR-07-01, FR-07-02 | 单入口启动；失败有明确错误 |
| M0-06 | `ClutchState` 共享类型 | FR-03-02 | `packages/shared-types` 与 Python 对齐 |

**M0 门禁**：`ROADMAP` E2E 前提第一行可勾选。

---

## M1 · 引擎

> **已决策**：D4（LLM 默认 DeepSeek V4 Pro、可切换）、D5（用户工作流 → 应用数据目录）— `DECISIONS.md`

| ID | 任务 | FR | 完成标准 |
|----|------|-----|----------|
| M1-01 | Workflow JSON Schema 校验 | FR-01-06 | 对接 `workflows/workflow.schema.json` |
| M1-02 | WorkflowCompiler → LangGraph | FR-03-01 | 五类基础节点可编译 |
| M1-03 | `start_run` / `stop_run` HTTP API | FR-03-01, FR-03-04 | 返回 `run_id`；可终止 |
| M1-04 | Orchestrator 路由节点 | FR-03-03 | 依边 + 规则跳转 |
| M1-05 | `run_completed` 与状态序列化 | FR-03-02, FR-03-06 | 终态 passed/failed 推送 |
| M1-06 | 工作流编辑器保存/加载 | FR-01-02, FR-01-03 | `WorkflowOrchestration.tsx` → 真实 JSON |
| M1-07 | 图结构保存前校验 | FR-01-06 | 中文错误提示 |

---

## M2 · 监督台（去 mock）

| ID | 任务 | FR | 完成标准 |
|----|------|-----|----------|
| M2-01 | Chat 接 `message` 事件 | FR-02-02, FR-02-03 | 移除 `mockData` 消息源 |
| M2-02 | Terminal 接 `log` 事件 | FR-02-05 | 真实子进程输出 |
| M2-03 | Overview / Flow 接 `state_patch` | FR-02-04, FR-02-07 | 活跃节点高亮 |
| M2-04 | Human Gate UI | FR-04-01–05 | Approve / Reject / Retry + 审计 |
| M2-05 | LangGraph `interrupt_before` 人工闸门 | FR-04-02–04 | `human_decision` resume |
| M2-06 | 废弃 `mockData.ts` 编排逻辑 | proposal §15 | 仅保留可选 demo 种子 |
| M2-07 | 运行历史持久化 + 侧栏入口 | D3, FR-02-01 | 可查看过往 run、状态、时间，便于排查 |

**M2 门禁**：D1 可改为 `可执行`；可建 `e2e/` Smoke（health + WS）。

---

## M3 · 工具链

| ID | 任务 | FR | 完成标准 |
|----|------|-----|----------|
| M3-01 | CLI Adapter（Claude Code） | FR-05-01, FR-05-02 | 真实调用 + 非零退出码失败 |
| M3-02 | Changes 面板真实 diff | FR-02-06 | `file_changed` → Diff 预览 |
| M3-03 | Cursor GUI Adapter | FR-05-03 | `open -a Cursor` 生效 |
| M3-04 | FS Watcher + debounce | FR-05-04 | 保存后 ≤3s 触发 Evaluator |
| M3-05 | Evaluator 执行用户 Agent 配置 | D6, FR-01-04, FR-06-03 | Prompt/Skills/Deliverables 驱动；机制含 `file_exists` + `shell` |
| M3-06 | 检查节点分支连线 | FR-01-05 | 不通过 → 人工闸门 / 回退 |

**M3 门禁**：MVP 闭环可演示；E2E 闭环用例可对齐。

---

## M4 · 打磨与发布

| ID | 任务 | FR | 完成标准 |
|----|------|-----|----------|
| M4-01 | 内置模板导入 | FR-01-07 | Video Production 等 1–2 个 |
| M4-02 | Agent 配置持久化 | FR-06-01–03 | `AgentManager.tsx` 接后端 |
| M4-03 | MCP / AI Tools 状态（filesystem） | FR-05-05, FR-05-06 | 至少 filesystem MCP |
| M4-04 | API Key 安全存储 | FR-07-03 | Tauri secure store；日志脱敏 |
| M4-05 | 工作区路径白名单 | proposal §13 | 越界访问拒绝 |
| M4-06 | macOS DMG 打包 | FR-07-01 | 可安装演示 |
| M4-07 | 错误提示与可操作建议 | proposal §8 | 失败卡片旁有下一步 |

---

## P2 延后（MVP 不阻塞）

| 模块 | FR 范围 | 说明 |
|------|---------|------|
| Skills Registry 后端同步 | FR-06-04 | 替代 localStorage |
| 单 Agent 模式 | FR-02-09 | 隐藏 Flow 入口 |
| 全量 MCP 类型 | FR-05-05 | MVP 仅 filesystem |

---

## 任务与文档映射

| 维护什么 | 文件 |
|----------|------|
| 任务定义 | 本文件 |
| 功能验收 ❌/✅ | `memory/ROADMAP.md` |
| 文件路径 | `memory/FILEMAP.md` |
| 开放决策 | `memory/DECISIONS.md` |
