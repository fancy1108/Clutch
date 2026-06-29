# BACKLOG（候选优化需求池）

> **定义：** 仅 **未立项** 的候选需求（TODO / IDEA / WAITING）。不是开发承诺，Agent 不得当作必做任务执行。  
> **权威分工：** 验收状态 → [`ROADMAP.md`](./ROADMAP.md) · OSR Task 表 → [`docs/OPEN_SOURCE_RELEASE.md`](../docs/OPEN_SOURCE_RELEASE.md) · 已交付证据 → [`DELIVERABLES.md`](./DELIVERABLES.md) / [`archive/`](./archive/)  
> **升格路径：** 候选 → `DECISIONS.md` §开放问题 → Dxx 决策 → `specs/core/tasks.md` + `ROADMAP.md`  
> **调研全文：** [`docs/research/orchestrator-optimization-pool.md`](../docs/research/orchestrator-optimization-pool.md)

## 状态说明

| 状态 | 含义 |
|------|------|
| **候选** | 调研认可，尚未讨论是否做 |
| **待决策** | 已写入 `DECISIONS.md` §开放问题 |
| **部分落地** | 已有代码，未升格；完成后移入 Completed 索引 |

---

## Active（候选池）

### P0 · 主控分派

| ID | 候选能力 | 状态 | 升格条件 |
|----|----------|------|----------|
| B-01 | 主控分派：理解需求 + 匹配 Flow + 精炼 `current_instruction` | 候选 | 人类确认 + D14；P2-07 |
| B-04 | `agent_task` 按 tool 真执行（CLI / Cursor / MCP） | 部分落地 | 人类确认；P2-10 |

### P1 · 监督与成本

| ID | 候选能力 | 状态 | 升格条件 |
|----|----------|------|----------|
| B-02 | API 真实 token usage + cache 进 `state_patch` | 候选 | P2-08 |
| B-05 | 图内路由 LLM 读 `validation_errors` + 最近日志 | 候选 | P2-11 |
| B-06 | 双模型 Planner / Executor 独立 session | 候选 | D4 扩展 |

### P2–P3 · 增强

| ID | 候选能力 | 状态 | 升格条件 |
|----|----------|------|----------|
| B-07 | Auto 模型路由（flash vs pro） | 候选 | 人类确认 |
| B-08 | 子 Agent 并行 + git worktree 隔离 | 候选 | 人类确认 |
| B-09 | Skills 按任务语义动态注入 | 候选 | P2-01 后立项 |
| B-10 | 跨 run 记忆检索（BM25） | 候选 | 人类确认 |
| B-11 | Workspace checkpoint / reject 回滚 | 候选 | 人类确认 |
| B-12 | 工作区 `.clutch/AGENTS.md` 项目记忆 | 候选 | 人类确认 |
| B-13 | LSP diagnostics 回灌 Builder | 候选 | 人类确认 |
| B-14 | Cache-safe 子 Agent fork | 候选 | B-08 后评估 |

### P0–P2 · Agent 执行对标（Codex / Claude Code）

| ID | 候选能力 | 状态 | 升格条件 |
|----|----------|------|----------|
| B-17 | Codex CLI 引擎（flow 节点待验收） | 部分落地 | flow 节点验收 |
| B-18 | 受控 Shell 执行（PTY + 审批） | 候选 | B-21 或沙箱拍板 |
| B-19 | 长驻 Shell + `write_stdin` | 候选 | B-18 后 |
| B-20 | OS 级沙箱 | 候选 | 安全评审 |
| B-21 | Exec policy（allow/deny/ask） | 候选 | D22 |
| B-22 | 路径级工具权限 | 候选 | B-21 后 |
| B-23 | apply_patch UI diff | 候选 | D21 反馈后 |
| B-24 | PreToolUse hooks | 候选 | B-21 后 |
| B-25 | 计划工具 `update_plan` | 候选 | 人类确认 |
| B-26 | Multi-agents spawn/wait | 候选 | B-08 或主控拍板 |
| B-27 | MCP tool_search | 候选 | 工具数 >N |
| B-28 | MCP resources | 候选 | 人类确认 |
| B-29 | view_image 多模态 | 候选 | 模型就绪 |
| B-30 | 内置 web_search | 候选 | 人类确认 |
| B-31 | request_permissions 运行时扩权 | 候选 | B-21/B-22 后 |
| B-32 | apply_patch 流式 diff 事件 | 候选 | B-23 后 |

> **D21 已落地：** `clutch-tools__apply_patch` — 勿重复立项。  
> **D25 已升格 HRT：** 审计 HRT-05~07 · 并发 HRT-08~10 — 见 [`specs/core/hybrid-runtime-plan.md`](../specs/core/hybrid-runtime-plan.md)。

---

## Completed（索引 only）

| ID | 归宿 |
|----|------|
| B-03 | v1.0.0 — `compaction.py` · `runs/archive/{run_id}.jsonl` · 见 [`archive/DELIVERABLES-POST-MVP.md`](./archive/DELIVERABLES-POST-MVP.md) |
| B-04 | 部分 — `engine_router` / `eaf2ea0` · Git |
| B-17 | 部分 — plain chat + hybrid Codex · Git |

---

## Rejected

| ID | 理由 |
|----|------|
| B-15 | 2026-06-27 否决 — 已有 Single/Multi Agent 模式分类 |
| B-16 | 2026-06-27 否决 — 同上 |

---

## 维护纪律

1. **新增候选：** Active 表补一行，状态默认「候选」。
2. **进入讨论：** 改「待决策」，并在 `DECISIONS.md` §开放问题 增一条。
3. **确定开发：** 从本文件**删除正文**，写入 `tasks.md` + `ROADMAP.md`，Completed 索引留一行。
4. **明确不做：** 移入 Rejected，附日期与一行理由。
5. **禁止：** 在本文件维护 OSR-xx 状态（见 `ROADMAP.md` §开源分发）。
