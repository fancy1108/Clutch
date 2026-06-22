# ARCHITECTURE（文件定位速查）

> 第 6 步架构拆解后填实具体路径。现在只建骨架。

## 五层架构

| 层 | 目录 | 职责 |
|----|------|------|
| Layer 1 Governance | `CLAUDE.md`、`.cursor/rules/`、`.github/copilot-instructions.md` | 铁律、命令、Check-in — Agent 入口路由 |
| Layer 2 Product Truth | `specs/` | proposal、design、tasks — 产品需求快照（历史） |
| Layer 3 Runtime State | `memory/` | 进度、踩坑、决策 — 跨会话运行态 |
| Layer 4 Execution | `.claude/workflows/`、`.cursor/` | workflows、agents — 可选自动化 |
| Layer 5 Evidence | `runs/` | 执行日志、截图 — 第 7 步起按需积累 |

## 权威优先级（冲突时）

`CLAUDE.md`（治理规则） > `memory/DECISIONS.md`（最新决策） > `specs/`（历史快照） > `runs/`（执行记录）

> `specs/core/proposal.md` 一旦与其他文档冲突，永远不是权威来源，只用于查证「最初的想法是什么」。

## 日志字段规范

所有自定义日志/事件输出遵循 `CLAUDE.md` §日志与事件字段规范（`run_id`、`node_id`、`source`、`level`、`message`、`timestamp`）。

## 文件定位（第 6 步填实）

| 想改什么 | 去哪里 |
|---------|--------|
| （待填） | |
