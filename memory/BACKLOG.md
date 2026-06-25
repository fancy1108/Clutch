# BACKLOG（候选优化需求池）

> **未立项**的 Orchestrator / 主控 Agent 增强项。不是开发承诺，Agent 不得当作必做任务执行。  
> 调研全文（分派流程图、`dispatch` 字段）见 [`docs/research/orchestrator-optimization-pool.md`](../docs/research/orchestrator-optimization-pool.md) §7。  
> **升格路径：** 候选 → `DECISIONS.md` §开放问题（待拍板）→ Dxx 决策 → `specs/core/tasks.md` + `ROADMAP.md`。

## 主控分派策略（产品共识 · 未立项）

主控 **只调度、不干活**；**不让人选 Flow / Agent**。分派终态三种：

| 场景 | 条件 | 终态 | BACKLOG |
|------|------|------|---------|
| **A** | 能理解需求 + 匹配到 Flow | 专用 Flow | B-01 |
| **B** | 能理解需求 + 无 Flow + 匹配到单 Agent | 指定 Agent + 迷你流 | B-16 |
| **C** | 不能理解需求；或能理解但 Flow、单 Agent 均无匹配 | 内置通用 Agent | B-15 |

与 **D10**（不做 Single Agent **模式切换** UI）不冲突：B/C 为系统自动 fallback，非用户可选产品模式。

## 状态说明

| 状态 | 含义 |
|------|------|
| **候选** | 调研认可，尚未讨论是否做 |
| **待决策** | 已写入 `DECISIONS.md` §开放问题，等人类拍板 |
| **已升格** | 已拆入 `tasks.md`；本行保留作索引，勿删 ID |

## 候选池

### 主控分派（P0 · 优先）

| ID | 候选能力 | 优先级 | 参考 | 状态 | 升格条件 |
|----|----------|--------|------|------|----------|
| B-01 | 主控分派：理解需求 + 匹配 Flow + 精炼 `current_instruction` | P0 | Goose Recipe、LangGraph Supervisor | 候选 | 人类确认 + D14 决策；P2-07 |
| B-16 | 无 Flow 时匹配单个 Agent（Agent Manager 池 + `single-agent-run` 迷你流） | P0 | Agent Manager、Goose Recipe | 候选 | 人类确认 + D14；P2-12 |
| B-15 | 内置通用 Agent + `general-fallback.json` 只读工作流 | P0 | D10 边界、内置模板模式 | 候选 | 人类确认 + D14；P2-13 |
| B-04 | `agent_task` 按 tool 真执行（CLI / Cursor / MCP），非统一 `router.chat` | P0 | M3 CLI Adapter、ARCHITECTURE §6.4 | 候选（部分落地 `eaf2ea0`） | 人类确认 + 决策；P2-10 |

### 监督与成本（P1）

| ID | 候选能力 | 优先级 | 参考 | 状态 | 升格条件 |
|----|----------|--------|------|------|----------|
| B-02 | API 真实 token usage + cache hit/miss 进 `state_patch` | P1 | Reasonix、DeepSeek TUI、M2-13 升级 | 候选 | P2-08 立项 |
| B-03 | Messages compaction + 原文归档 `runs/archive/{run_id}.jsonl` | P1 | Reasonix SPEC §3.6、OpenCode auto-compact | 候选 | 人类确认 + 决策 |
| B-05 | 图内路由 LLM 读 `validation_errors` + 最近日志（非 start 分派） | P1 | LangGraph Supervisor、M1-04 升级 | 候选 | 人类确认 + 决策；P2-11 |
| B-06 | 双模型 Planner / Executor 独立 session（cache 友好） | P1 | Reasonix Coordinator §3.5 | 候选 | 人类确认 + D4 扩展 |

### 增强（P2–P3）

| ID | 候选能力 | 优先级 | 参考 | 状态 | 升格条件 |
|----|----------|--------|------|------|----------|
| B-07 | Auto 模型路由（flash vs pro + thinking 档位） | P2 | DeepSeek TUI `--model auto` | 候选 | 人类确认 + 决策 |
| B-08 | 子 Agent 并行 + git worktree 隔离 | P2 | Stoneforge、DeepSeek TUI RLM | 候选 | 人类确认 + 决策 |
| B-09 | Skills 按任务语义动态注入（非全量塞 prompt） | P2 | DeepSeek TUI `load_skill` | 候选 | P2-01 ✅ 后立项 |
| B-12 | 工作区 `.clutch/AGENTS.md` 项目记忆 + Sidecar 扫描 | P2 | Reasonix `/init`、Goose Goosehints | 候选 | 人类确认 + 决策 |
| B-13 | 编辑后 LSP diagnostics 回灌 Builder 下一轮 | P2 | DeepSeek TUI、OpenCode LSP | 候选 | 人类确认 + 决策 |
| B-14 | Cache-safe 子 Agent fork（prefix 对齐 fan-out） | P2 | [agentcache](https://github.com/masteragentcoder/agentcache) | 候选 | B-08 立项后评估 |
| B-10 | 跨 run 记忆检索（BM25 history / terminal_logs） | P3 | Reasonix `history` / `memory` 工具 | 候选 | 人类确认 + 决策 |
| B-11 | Workspace checkpoint / Human Gate reject 回滚 | P3 | DeepSeek TUI side-git `/restore` | 候选 | 人类确认 + 决策 |

## 与已立项任务的关系

- **P2-01…P2-06**（`tasks.md` §P2）为已承诺交付，**不**在本池重复登记。
- **P2-07～P2-13** 为分派相关预留 ID，升格时再写入 `tasks.md`。
- **B-04 部分落地（2026-06-25，`eaf2ea0` + `6cc6c6b`）**：`engine_router` 已按 Agent `aiEngine` 与 Tools Connect 分流 Claude CLI / Cursor / 全局 LLM；`execute_agent_task` 与 plain chat 已接入。MCP ReAct 路径在 `agent_executor` 内独立实现。主控自动分派（B-01/B-15/B-16）仍属候选。升格待人类确认。

## 维护纪律

- 新增候选：补一行，状态默认 **候选**。
- 进入讨论：改 **待决策**，并在 `DECISIONS.md` §开放问题 增一条（禁止在其他文档另开开放问题列表）。
- 确定开发：改 **已升格**，链到 `tasks.md` 任务 ID 与 `DECISIONS.md` Dxx。
- 明确不做：删行或标 `已否决`（附一行否决理由与日期）。
