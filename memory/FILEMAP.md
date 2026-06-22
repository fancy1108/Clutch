# FILEMAP（文件路径速查）

> Agent Check-in 用：「改什么 → 去哪个文件」。第 6 步填实路径映射表。  
> **完整架构设计、数据流与 ADR 叙事**见 [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)。

## 五层架构

| 层 | 目录 | 职责 |
|----|------|------|
| Layer 1 Governance | `CLAUDE.md`、`.cursor/rules/`、`.github/copilot-instructions.md` | 铁律、命令、Check-in — Agent 入口路由 |
| Layer 2 Product Truth | `specs/` | proposal、design、tasks — 产品需求快照（历史） |
| Layer 3 Runtime State | `memory/` | 进度、踩坑、决策 — 跨会话运行态 |
| Layer 4 Execution | `.claude/workflows/`、`.cursor/` | workflows、agents — 可选自动化 |
| Layer 5 Evidence | `runs/` | `runs/<run_id>/` 工作流证据；`runs/verification/` 测试/覆盖率报告归档 |

## 权威优先级（冲突时）

`CLAUDE.md`（治理规则） > `memory/DECISIONS.md`（最新决策） > `specs/`（历史快照） > `runs/`（执行记录）

> `specs/core/proposal.md` 一旦与其他文档冲突，永远不是权威来源，只用于查证「最初的想法是什么」。

## 日志字段规范

所有自定义日志/事件输出遵循 `CLAUDE.md` §日志与事件字段规范（`run_id`、`node_id`、`source`、`level`、`message`、`timestamp`）。

## 文件定位（第 6 步填实）

| 想改什么 | 去哪里 |
|---------|--------|
| 测试策略与 E2E 范围 | `memory/DECISIONS.md`（D1） |
| E2E 落地前提勾选 | `memory/ROADMAP.md` §E2E 落地前提 |
| 测试门禁状态 | `memory/TESTS.md` |
| 后端单元测试 | `services/orchestrator/tests/` |
| CI 工作流 | `.github/workflows/ci.yml` |
| 本地一键校验 | `scripts/verify.sh` |
| 验证报告归档 | `runs/verification/`（gitignore，本地/CI 快照） |
| E2E 包（M2 后，D1 可执行时） | `e2e/`（尚未创建） |

## 待办（第 6 步填实）

- [ ] 编排引擎、WebSocket、工作流编辑器等业务模块路径映射
- [ ] `specs/core/tasks.md` 创建后，在此表补全「改什么 → 去哪」
