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
| B-27 | MCP tool_search | 候选 | → 交付表 D28；见 `specs/core/clutch-agent-capability-plan.md` |
| B-28 | MCP resources | 候选 | → 交付表 D43；同上 |
| B-29 | view_image 多模态 | 候选 | 模型就绪 |
| B-30 | 内置 web_search | 候选 | 人类确认 |
| B-31 | request_permissions 运行时扩权 | 候选 | B-21/B-22 后 |
| B-32 | apply_patch 流式 diff 事件 | 候选 | B-23 后 |
| B-33 | 第三方 MCP 记忆工作流示例（Epicode：`workflows/` 模板 + `docs/mcp-servers/` 接入指南） | ✅ 已合并 dev（[#22](https://github.com/fancy1108/Clutch/pull/22)） |

> **D21 已落地：** `clutch-tools__apply_patch` — 勿重复立项。  
> **D25 已升格 HRT：** 审计 HRT-05~07 · 并发 HRT-08~10 — 见 [`specs/core/hybrid-runtime-plan.md`](../specs/core/hybrid-runtime-plan.md)。  
> **B-33 备注：** 与 B-10（内置 BM25 跨 run 记忆）路径不同；Epicode 走 MCP 扩展点。PR 已 triage review，**仅入池，非开发承诺**。

### P0–P2 · 对照《深入理解 AI Agent》01–10（2026-08-24）

> **调研：** [`docs/research/clutch-agent-book-gap.md`](../docs/research/clutch-agent-book-gap.md)。未立项；升格先答 `DECISIONS.md` **Q-AGENT-1–4**。勿改交付表冒充 D54+。  
> **B-34–B-39 已升格：** `specs/core/tasks.md` §Agent Harness · status · context layers · verification gate · progress loop · workspace memory。  
> **重叠勿重开：** B-01 分派 · B-02/Q-USAGE-1 用量 · B-08 并行 worktree · B-10 检索 · B-12 项目记忆 · B-18–B-22 沙箱/policy · B-26 spawn/wait · B-27/B-28 → D28/D43。

| ID | 候选能力 | 状态 | 升格条件 |
|----|----------|------|----------|
| B-40 | 成功策略摘要 / 失败反思写入工作区知识（书 08） | 候选 | B-39 后 |
| B-41 | Builtin ACI 描述：何时用/不用 + 反例 + 1–3 调用样例（书 04） | 候选 | 人类确认 |
| B-42 | 事件 Channel：邮件/Webhook/IM 推送唤醒（书 04；Cron≠推送） | 候选 | 人类确认 |
| B-43 | 多 Agent「新信息」门禁；并行必须 worktree（书 10） | 候选 | 并行隔离见 **B-08** |
| B-44 | 外部内容来源标记 + 工具结果显式截断/分页（书 02） | 候选 | B-35 后 |
| B-45 | 记忆投毒防护：网页/MCP「请记住」不得直入长期记忆（书 03） | 候选 | 与 B-39 同批或其后 |
| B-46 | `notify_user` + 子 Agent send/cancel 与两种上下文传递（书 04） | 候选 | 人类确认；原语见 B-26 |
| B-47 | 独立 Code Interpreter 沙盒（断网/超时结构化错误）（书 05） | 候选 | 语义命令走 **B-21** |
| B-48 | 消融总闸 + 结构化 trajectory 落盘（书 06） | 候选 | B-34 后 |
| B-49 | Design 渲染截图 → 视觉 reviewer（书 09/10 新信息）（≠ Design D36 画布本身） | 候选 | Design D36 路径上评估 |
| B-50 | 子任务步骤预算 + 按复杂度移交包（书 10） | 候选 | 管理者见 **B-01** |

---

## GitHub Issues · 待修复 Bug

> **来源：** 用户反馈 triage。修复后关 Issue 并移入 Completed 索引。

_当前无 open 的待修复 Bug（2026-07-01）。_

---

## 维护者验收（非开发 · 人工）

> **来源：** v1.0.2 发版后登记。非 BACKLOG 功能候选；完成后关 Issue 并更新 `CHANGELOG` / `INSTALL` 免责文案（若通过）。

| Issue | 标题 | 范围 | 状态 |
|-------|------|------|------|
| [#23](https://github.com/fancy1108/Clutch/issues/23) | v1.0.2 Windows MSI/NSIS 实体机 smoke | Win10/11 x64 · Release `v1.0.2` 安装包 | **open** · `ready-for-human` · **Windows 维护：** [@996wuxian](https://github.com/996wuxian) · 集成分支 `win`（PR #17 为历史基础） |
| [#24](https://github.com/fancy1108/Clutch/issues/24) | HRT-F 多 session Hybrid 人工验收 | macOS · hybrid | **closed** · F1/F2/G ✅ · F3–F5 skip · [`runs/verification/2026-07-01-hrt-f-multi-session.md`](../runs/verification/2026-07-01-hrt-f-multi-session.md) |

**资产：** `Clutch_1.0.2_x64-setup.exe` · `Clutch_1.0.2_x64_en-US.msi` · `SHA256SUMS.txt`  
**CI 证据：** [Windows Build #28462065330](https://github.com/fancy1108/Clutch/actions/runs/28462065330)

---

## Completed（索引 only）

| ID | 归宿 |
|----|------|
| B-39 | `specs/core/tasks.md` §Agent workspace memory · `ROADMAP.md` 同名节（书 03；`.clutch/memory/MEMORY.md`） |
| B-38 | `specs/core/tasks.md` §Agent progress loop · `ROADMAP.md` 同名节（书 01；同参 read/grep 空转即停） |
| B-37 | `specs/core/tasks.md` §Agent verification gate · `ROADMAP.md` 同名节（书 01+05；测套+产物闸；Q-AGENT-3=C） |
| B-36 | `specs/core/tasks.md` §Agent context layers · `ROADMAP.md` 同名节（书 02；落盘→噪声→批量→全量熔断） |
| B-35 | `specs/core/tasks.md` §Agent status · `ROADMAP.md` §Agent status（书 02；末尾 `<agent_status>`；Q-AGENT-2=A） |
| B-34 | `specs/core/tasks.md` §Agent Harness · `ROADMAP.md` §Agent Harness（书 06；评测尺子，不挪时钟；Q-AGENT-1=C） |
| B-03 | v1.0.0 — `compaction.py` · `runs/archive/{run_id}.jsonl` · 见 [`archive/DELIVERABLES-POST-MVP.md`](./archive/DELIVERABLES-POST-MVP.md) |
| #18 | v1.0.2 — `lib.rs` sidecar lifecycle · [Issue closed](https://github.com/fancy1108/Clutch/issues/18) |
| #19 | `engine_router.py` CLI 错误单层包装 + 529 文案 · [Issue closed](https://github.com/fancy1108/Clutch/issues/19) |
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
