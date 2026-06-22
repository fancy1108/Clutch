# FILEMAP（文件路径速查）

> Agent Check-in 用：「改什么 → 去哪个文件」。  
> **完整架构设计、数据流与 ADR 叙事**见 [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)。  
> **开发任务**见 [`specs/core/tasks.md`](../specs/core/tasks.md)。

## 五层架构

| 层 | 目录 | 职责 |
|----|------|------|
| Layer 1 Governance | `CLAUDE.md`、`.cursor/rules/`、`.github/copilot-instructions.md` | 铁律、命令、Check-in — Agent 入口路由 |
| Layer 2 Product Truth | `specs/` | proposal、design、tasks — 产品需求快照（历史） |
| Layer 3 Runtime State | `memory/` | 进度、踩坑、决策 — 跨会话运行态 |
| Layer 4 Execution | `.claude/workflows/`、`.cursor/` | 操作剧本（须符合 `CLAUDE.md` §Layer 4 约束） |
| Layer 5 Evidence | `runs/` | `runs/<run_id>/` 工作流证据；`runs/verification/` 测试/覆盖率报告归档 |

## 权威优先级（冲突时）

`CLAUDE.md`（治理规则） > `memory/DECISIONS.md`（最新决策） > `specs/`（历史快照） > `runs/`（执行记录）

> `specs/core/proposal.md` 一旦与其他文档冲突，永远不是权威来源，只用于查证「最初的想法是什么」。

## 日志字段规范

所有自定义日志/事件输出遵循 `CLAUDE.md` §日志与事件字段规范（`run_id`、`node_id`、`source`、`level`、`message`、`timestamp`）。

## 文件定位

### 治理与规范

| 想改什么 | 去哪里 |
|---------|--------|
| 铁律、命令、Check-in | `CLAUDE.md` |
| 产品需求历史 | `specs/core/proposal.md` |
| 视觉设计快照 | `specs/core/design.md` → `UI_UX_GUIDELINES.md` |
| 开发任务清单 | `specs/core/tasks.md` |
| 进度 / 待办 | `memory/PROGRESS.md` |
| 决策与开放问题 | `memory/DECISIONS.md` |
| 功能验收状态 | `memory/ROADMAP.md` |
| 测试门禁状态 | `memory/TESTS.md` |
| Layer 4 边界与剧本约束 | `CLAUDE.md` §Layer 4 操作剧本 |
| 验收偏差 / 实现漂移物理诊断 | `.claude/workflows/truth-alignment.md` |

### 测试与 CI

| 想改什么 | 去哪里 |
|---------|--------|
| 测试策略与 E2E 范围 | `memory/DECISIONS.md`（D1） |
| E2E 落地前提勾选 | `memory/ROADMAP.md` §E2E 落地前提 |
| 后端单元测试 | `services/orchestrator/tests/` |
| CI 工作流 | `.github/workflows/ci.yml` |
| 本地一键校验 | `scripts/verify.sh` |
| 文档↔代码漂移机检 | `scripts/check-doc-drift.sh` |
| Git pre-commit（条件触发） | `.husky/pre-commit` |
| 验证报告归档 | `runs/verification/`（gitignore） |
| E2E 包（M2 后，D1 可执行时） | `e2e/`（尚未创建） |

### 前端（`apps/desktop/src`）

| 想改什么 | 去哪里 |
|---------|--------|
| 应用根布局、WS 接入 | `App.tsx` |
| 侧栏（工作区 / 历史） | `sidebar.tsx` |
| Chat 流与人工干预 UI | `components/ChatFeed.tsx` |
| 右侧面板（Overview/Terminal/Changes/Flow） | `components/RightPanel.tsx` |
| 工作流画布编辑 | `components/WorkflowOrchestration.tsx` |
| Agent 角色配置 | `components/AgentManager.tsx` |
| AI 工具连接状态 | `components/AiToolsManager.tsx` |
| Skills 注册 | `components/SkillsRegistry.tsx` |
| MCP 配置 | `components/McpServerHub.tsx` |
| 顶栏 | `components/Header.tsx` |
| 全局样式 | `index.css` |
| 类型定义 | `types.ts` |
| **待废弃** mock 数据 | `mockData.ts` |
| Vite 配置与代理 | `vite.config.ts` |
| Tauri 壳与 Sidecar 拉起 | `src-tauri/` |

### 后端（`services/orchestrator`）

| 想改什么 | 去哪里 |
|---------|--------|
| FastAPI 入口、路由注册 | `src/main.py` |
| （待建）WorkflowCompiler | `src/compiler/` |
| （待建）LangGraph 图与节点 | `src/graph/` |
| （待建）WebSocket 推送 | `src/ws/` |
| （待建）CLI / GUI Adapter | `src/adapters/` |
| 依赖与 pytest 配置 | `pyproject.toml` |

### 共享与 Workflow

| 想改什么 | 去哪里 |
|---------|--------|
| 前后端共享 TS 类型 | `packages/shared-types/index.ts` |
| Workflow JSON Schema | `workflows/workflow.schema.json` |
| 内置模板（只读） | `workflows/*.json` |
| 用户工作流（读写，D5） | Tauri 应用数据目录 `workflows/` |
| 可选导出到项目 | `.clutch/workflows/`（导入/导出，非默认） |
| Agent / Evaluator 配置 UI | `components/AgentManager.tsx` |
