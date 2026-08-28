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

### P1 · 监督与成本

| ID | 候选能力 | 状态 | 升格条件 |
|----|----------|------|----------|
| B-02 | API 真实 token usage + cache 进 `state_patch` | 部分落地 | Q-USAGE-1 已接 usage；cache 字段仍候选 |
| B-06 | Planner flash 只读 / Executor pro 写（独立 session） | 候选 | D60 撤回 Settings 双下拉；真双模型运行需人类确认 |
| B-51 | 本机监视 push 后的 CI（轮询 Checks；红了出卡再修） | 候选 | D61 撤回 FM-13 空壳后；人类确认 |

### P2–P3 · 增强

| ID | 候选能力 | 状态 | 升格条件 |
|----|----------|------|----------|
| B-07 | Auto 模型路由（flash vs pro） | 候选 | 人类确认 |
| B-09 | Skills 按任务语义动态注入 | 候选 | P2-01 后立项 |
| B-11 | Workspace checkpoint / reject 回滚 | 候选 | 人类确认 |
| B-12 | 工作区 `.clutch/AGENTS.md` 项目记忆 | 候选 | 人类确认 |
| B-13 | LSP diagnostics 回灌 Builder | 候选 | 人类确认 |
| B-14 | Cache-safe 子 Agent fork | 候选 | FM-11 后评估 |

### P0–P2 · Agent 执行对标（Codex / Claude Code）

| ID | 候选能力 | 状态 | 升格条件 |
|----|----------|------|----------|
| B-17 | Codex CLI 引擎（flow 节点待验收） | 部分落地 | FM-04 扫描 + FM-10 画布 |
| B-19 | 长驻 Shell + `write_stdin` | 候选 | FM-03 后 |
| B-23 | apply_patch UI diff | 候选 | D21 反馈后 |
| B-24 | PreToolUse hooks | 候选 | FM-03 后 |
| B-25 | 计划工具 `update_plan` | 候选 | 人类确认 |
| B-26 | Multi-agents spawn/wait | 候选 | FM-11 或 FM-09 |
| B-29 | view_image 多模态 | 候选 | 模型就绪 |
| B-30 | 内置 web_search | 部分落地 | D15 已有工具；产品包装仍候选 |
| B-31 | request_permissions 运行时扩权 | 候选 | FM-03 后 |
| B-32 | apply_patch 流式 diff 事件 | 候选 | B-23 后 |
| B-33 | 第三方 MCP 记忆工作流示例（Epicode） | ✅ 已合并 dev（[#22](https://github.com/fancy1108/Clutch/pull/22)） |

> **D21 已落地：** `clutch-tools__apply_patch` — 勿重复立项。  
> **D25 已升格 HRT。** **D56：** B-01/04/05/08/10/18–22/43/46/47/49 → FM-xx。**D60：** B-06 撤回 FM-19 UI。**D61：** B-42 撤回 FM-13 UI；本机盯 CI 见 **B-51**。  
> **B-27/B-28** → 交付表 D28/D43。B-33 与 FM-12 路径不同。

### P0–P2 · 对照《深入理解 AI Agent》01–10（2026-08-24）

> **调研：** [`docs/research/clutch-agent-book-gap.md`](../docs/research/clutch-agent-book-gap.md)。  
> **B-34–B-41、B-44、B-45、B-48 已升格** harness 各节。  
> **B-43/46/47/49 已升格 FM-15/14/17/16（D56）。B-42 webhook 空壳已撤回（D61）。**

| ID | 候选能力 | 状态 | 升格条件 |
|----|----------|------|----------|
| B-50 | 子任务步骤预算 + 按复杂度移交包（书 10） | 候选 | 管理者见 **FM-09** |

---

## GitHub Issues · 待修复 Bug

> **来源：** 用户反馈 triage。修复后关 Issue 并移入 Completed 索引。

_当前无 open 的待修复 Bug（2026-07-01）。_

---

## 维护者验收（非开发 · 人工）

> **来源：** v1.0.2 发版后登记。非 BACKLOG 功能候选；完成后关 Issue 并更新 `CHANGELOG` / `INSTALL` 免责文案（若通过）。

| Issue | 标题 | 范围 | 状态 |
|-------|------|------|------|
| [#23](https://github.com/fancy1108/Clutch/issues/23) | v1.0.2 Windows MSI/NSIS 实体机 smoke | Win10/11 x64 · Release `v1.0.2` 安装包 | **deferred** · 2026-08-25 无 Windows 电脑（DECISIONS **D55**）；Windows CI flake `test_start_sleep_wait_done` 同样不修 |
| [#24](https://github.com/fancy1108/Clutch/issues/24) | HRT-F 多 session Hybrid 人工验收 | macOS · hybrid | **closed** · F1/F2/G ✅ · F3–F5 skip · [`runs/verification/2026-07-01-hrt-f-multi-session.md`](../runs/verification/2026-07-01-hrt-f-multi-session.md) |

**资产：** `Clutch_1.0.2_x64-setup.exe` · `Clutch_1.0.2_x64_en-US.msi` · `SHA256SUMS.txt`  
**CI 证据：** [Windows Build #28462065330](https://github.com/fancy1108/Clutch/actions/runs/28462065330)

---

## Completed（索引 only）

| ID | 归宿 |
|----|------|
| B-01 | D56 **FM-09** · `frontend-modules-plan.md` |
| B-04 | D56 **FM-10**（余量）；部分执行已在 Git |
| B-17 | 部分 — plain chat + hybrid Codex · Git |
| B-05 | D56 **FM-18** |
| B-08 | D56 **FM-11** |
| B-10 | D56 **FM-12** |
| B-18–B-22 | D56 **FM-03**（OSR-18 界面层） |
| B-43 | D56 **FM-15** |
| B-46 | D56 **FM-14** |
| B-47 | D56 **FM-17** |
| B-49 | D56 **FM-16** |
| B-48 | `specs/core/tasks.md` §Agent eval ablation · `ROADMAP.md` 同名节（书 06；消融闸 + JSONL trajectory） |
| B-44 | `specs/core/tasks.md` §Agent archived tool markers · `ROADMAP.md` 同名节（书 02；`source=tool truncated=yes`） |
| B-45 | `specs/core/tasks.md` §Agent memory poison · `ROADMAP.md` 同名节（书 03；请记住+URL 不入库） |
| B-40 | `specs/core/tasks.md` §Agent verification notes · `ROADMAP.md` 同名节（书 08；`Worked:` / `Failed:` 写入 MEMORY.md） |
| B-39 | `specs/core/tasks.md` §Agent workspace memory · `ROADMAP.md` 同名节（书 03；`.clutch/memory/MEMORY.md`） |
| B-38 | `specs/core/tasks.md` §Agent progress loop · `ROADMAP.md` 同名节（书 01；同参 read/grep 空转即停） |
| B-37 | `specs/core/tasks.md` §Agent verification gate · `ROADMAP.md` 同名节（书 01+05；测套+产物闸；Q-AGENT-3=C） |
| B-36 | `specs/core/tasks.md` §Agent context layers · `ROADMAP.md` 同名节（书 02；落盘→噪声→批量→全量熔断） |
| B-35 | `specs/core/tasks.md` §Agent status · `ROADMAP.md` §Agent status（书 02；末尾 `<agent_status>`；Q-AGENT-2=A） |
| B-34 | `specs/core/tasks.md` §Agent Harness · `ROADMAP.md` §Agent Harness（书 06；评测尺子，不挪时钟；Q-AGENT-1=C） |
| B-03 | v1.0.0 — `compaction.py` · `runs/archive/{run_id}.jsonl` · 见 [`archive/DELIVERABLES-POST-MVP.md`](./archive/DELIVERABLES-POST-MVP.md) |
| #18 | v1.0.2 — `lib.rs` sidecar lifecycle · [Issue closed](https://github.com/fancy1108/Clutch/issues/18) |
| #19 | `engine_router.py` CLI 错误单层包装 + 529 文案 · [Issue closed](https://github.com/fancy1108/Clutch/issues/19) |

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
