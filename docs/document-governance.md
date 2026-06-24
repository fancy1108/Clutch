# 文档治理规范

## 五层架构

| 层 | 目录 | 职责 |
|----|------|------|
| Layer 1 Governance | `CLAUDE.md`、`.cursor/rules/`、`.github/copilot-instructions.md` | 铁律、命令、Check-in — Agent 入口路由 |
| Layer 2 Product Truth | `specs/` | proposal、design、tasks — 产品需求历史快照 |
| Layer 3 Runtime State | `memory/` | 进度、踩坑、决策 — 跨会话运行态 |
| Layer 4 Execution | `.claude/workflows/`、`.cursor/` | 操作剧本（须符合 `CLAUDE.md` §Layer 4 约束） |
| Layer 5 Evidence | `runs/` | 工作流执行证据（`runs/<run_id>/`）与验证报告归档（`runs/verification/`）— 第 7 步起按需积累 |

## 权威优先级

冲突时以高层为准：

**`CLAUDE.md`（治理规则） > `memory/DECISIONS.md`（最新决策） > `specs/`（历史快照，仅供追溯） > `runs/`（执行记录）**

`specs/core/proposal.md` 一旦与其他文档冲突，**永远不是权威来源**，只用于查证「最初的想法是什么」。

## 各目录写什么

| 想改什么 | 去哪里 | 何时更新 |
|---------|--------|---------|
| 铁律、命令、Check-in | `CLAUDE.md` | 治理规则变更时 |
| 产品目标、MVP、Non-Goals（历史） | [`specs/core/proposal.md`](./specs/core/proposal.md) | 仅作快照，不随演进更新 |
| 视觉规范 | `specs/core/design.md` | 第 4–5 步 |
| 开发任务清单 | `specs/core/tasks.md` | 第 6 步 |
| 当前进度、下次做什么 | `memory/PROGRESS.md` | 每个 Agent 会话结束 |
| 踩坑记录 | `memory/FAILURES.md` | 卡壳 >10 分钟或回滚时 |
| 架构决策与开放问题 | `memory/DECISIONS.md` | 做技术选型或待决事项时 |
| 文件定位速查 | [`memory/FILEMAP.md`](./memory/FILEMAP.md) | 第 6 步填实 |
| 功能验收状态 | `memory/ROADMAP.md`、`memory/TESTS.md` | 验证通过后 |
| 系统设计详述（叙事 + ADR） | [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | 架构评审时；路径速查见 `memory/FILEMAP.md` |
| Orchestrator 调研 / 候选能力（非决策） | [`docs/research/orchestrator-optimization-pool.md`](./research/orchestrator-optimization-pool.md) | 索引见 `memory/BACKLOG.md` |

## 禁止事项

- 禁止在 `CLAUDE.md` 以外复制命令表、铁律全文、日志字段规范
- 禁止在 `CLAUDE.md` 里复制 proposal 全文或功能列表
- 禁止在未更新 `specs/` 或 `memory/DECISIONS.md` 的情况下做架构级业务变更
- 禁止在未实际运行验证的情况下标记功能完成
- 禁止在 `DECISIONS.md` 以外另开开放问题列表
