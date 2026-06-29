# 文档治理规范

> **维护阶段原则：** 每类信息只有一个权威真相（Source of Truth）；其他文件只引用，不重复维护状态。  
> **生命周期：** 见下文 §文档生命周期；冷数据归档至 `memory/archive/`。

## 权威真相（Source of Truth）

| 信息 | 唯一权威源 | 禁止双写 |
|------|------------|----------|
| 功能是否存在（对外） | [`docs/PRODUCT_INTRO.md`](./PRODUCT_INTRO.md) | 不在 BACKLOG / research / proposal 写「已上线」 |
| 功能验收状态 | [`memory/ROADMAP.md`](../memory/ROADMAP.md) | 不在 OPEN_SOURCE_RELEASE / BACKLOG / tasks 勾选 |
| 当前系统设计 | [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md) | 不在五件套 / README 复制实现细节 |
| 历史任务规格 + Verification | [`specs/core/tasks.md`](../specs/core/tasks.md) 等 | 不在 tasks 表维护 ✅/❌ |
| 历史产品提案 | [`specs/archive/proposal-v0.1.md`](../specs/archive/proposal-v0.1.md) | 禁止更新 `specs/core/proposal.md` 正文 |
| OSR Task **定义** | [`OPEN_SOURCE_RELEASE.md`](./OPEN_SOURCE_RELEASE.md) §7.2 | 状态只在 ROADMAP |
| 未立项候选 | [`memory/BACKLOG.md`](../memory/BACKLOG.md) | 完成后删除正文 |
| 架构决策 | [`memory/DECISIONS.md`](../memory/DECISIONS.md) | — |
| 用户可见变更 | [`CHANGELOG.md`](../CHANGELOG.md) | Release 硬门禁 |
| 会话 / 交付（开发态） | [`memory/PROGRESS.md`](../memory/PROGRESS.md) · [`memory/DELIVERABLES.md`](../memory/DELIVERABLES.md) | 冷却后 `memory/archive/` |

**任何状态不得在两个文件中同时维护。** 冲突时见下表扩展列：

| 信息类型 | 权威文件 | 其他地方如何处理 |
|----------|----------|------------------|
| 功能是否存在（对外） | [`docs/PRODUCT_INTRO.md`](./PRODUCT_INTRO.md) | 只引用，不复制功能列表；**功能合并后必须先更新本文再关闭 Task** |
| 功能规划 / 验收状态 | [`memory/ROADMAP.md`](../memory/ROADMAP.md) | 只记录状态，不记交付细节 |
| 未立项候选需求 | [`memory/BACKLOG.md`](../memory/BACKLOG.md) | 完成后**立即移除**正文，仅留 Completed 索引一行 |
| OSR-xx Task 定义 | [`docs/OPEN_SOURCE_RELEASE.md`](./OPEN_SOURCE_RELEASE.md) §7.2 | 状态只在 `ROADMAP.md` 勾选，不在 BACKLOG 重复 |
| 架构决策 | [`memory/DECISIONS.md`](../memory/DECISIONS.md) | 永久保存；禁止在其他文档另开开放问题列表 |
| 任务定义与 Verification 命令 | [`specs/core/tasks.md`](../specs/core/tasks.md) | 历史规格，即使全完成也不删 |
| 用户可见变更 | [`CHANGELOG.md`](../CHANGELOG.md) | 每次 Release **必须**更新；历史快照见 [`docs/releases/`](./releases/) |
| 会话接力 | [`memory/PROGRESS.md`](../memory/PROGRESS.md) | 只保留近期；见 §文档生命周期 |
| 交付证据索引 | [`memory/DELIVERABLES.md`](../memory/DELIVERABLES.md) | 冷却后移入 `memory/archive/` |
| 代码实现 | **Git** | 文档不复制 `git diff` |
| 验证原始输出 | [`runs/verification/`](../runs/verification/) | gitignore；`DELIVERABLES` 只记路径 |

**冲突时权威优先级：**

`CLAUDE.md`（治理规则） > `memory/DECISIONS.md`（最新决策） > `docs/PRODUCT_INTRO.md`（当前产品） > `memory/ROADMAP.md`（验收状态） > `specs/`（历史快照） > `runs/`（执行记录）

`specs/core/proposal.md` 一旦与其他文档冲突，**永远不是权威来源**，只用于查证「最初的想法是什么」。

---

## When X Happens, Update Y

> **事件驱动矩阵：** 改了代码或完成工作后，按行更新对应权威文件；禁止「只改一处」却漏掉下游真相源。

| Event | Must update | Optional / 随后 |
|-------|-------------|-----------------|
| 新功能实现并验收 | [`PRODUCT_INTRO.md`](./PRODUCT_INTRO.md) · [`ROADMAP.md`](../memory/ROADMAP.md) | **PRODUCT_INTRO 与 ROADMAP 同等级**；`TESTS.md` 跑过门禁后 |
| 代码 Task 完成并 commit | [`memory/DELIVERABLES.md`](../memory/DELIVERABLES.md) | `runs/verification/` 日志 |
| **打 Release tag / 发版** | **[`CHANGELOG.md`](../CHANGELOG.md)** · `PRODUCT_INTRO`（若对外可见） | [`docs/releases/`](./releases/) 版本快照 · `DELIVERABLES` 轮转归档 |
| 架构 / 技术选型变更 | [`memory/DECISIONS.md`](../memory/DECISIONS.md) | `specs/`（若影响任务定义） |
| 新候选需求（未立项） | [`memory/BACKLOG.md`](../memory/BACKLOG.md) Active 表 | `docs/research/` 调研笔记 |
| Backlog 项落地 | 从 BACKLOG **删除正文** · `ROADMAP` · `tasks.md`（升格时） | BACKLOG Completed 索引一行 |
| Backlog 项否决 | BACKLOG Rejected 索引一行 | `DECISIONS.md`（若曾待决） |
| Agent 会话结束 | [`memory/PROGRESS.md`](../memory/PROGRESS.md) | — |
| 里程碑全 ✅ 或 Release 后 | `memory/archive/` **新建**归档文件 · 瘦身 `DELIVERABLES` / `PROGRESS` | `FILEMAP` 若路径变更 |
| 踩坑 / 回滚 | [`memory/FAILURES.md`](../memory/FAILURES.md) | — |
| OSR-xx 验收 | [`memory/ROADMAP.md`](../memory/ROADMAP.md) §开源分发 | Task 定义见 `OPEN_SOURCE_RELEASE.md` §7.2 |

### Release 硬门禁

**未更新 `CHANGELOG.md` 中对应版本节 → 禁止打 Git tag → 禁止发布 Release。**

- CI：`scripts/release-preflight.sh` 校验 tag 版本在 `CHANGELOG.md` 有 `## [x.y.z]` 条目（INV-R5）。
- 格式遵循 [Keep a Changelog](https://keepachangelog.com/)：`Added` · `Changed` · `Removed` · `Fixed` · `Security`。

---

## 三层文档模型（仓库长期规则）

| 层 | 目录 | 职责 | 生命周期 |
|----|------|------|----------|
| **活跃态** | `memory/`（非 archive） | 开发进行态、接力、交付索引 | 轮转归档 |
| **当前真相** | `docs/`（非 archive、非 research） | 用户/贡献者面对的「现在」 | 随发布演进 |
| **历史规格** | `specs/core/` | Task 定义、Verification 手册 | 冻结形态，不删 |
| **历史叙事** | `docs/archive/` · `specs/archive/` · `docs/research/` | 规划、调研、handover | **只读**，禁止追加状态 |

**`docs/archive/` 原则：** 只归档叙事（planning、handover、risk review、historical assessment）。**不归档**宪法：`ARCHITECTURE`、`GOVERNANCE`、`PERFORMANCE`、`INSTALL`、`DATA_AND_PRIVACY`、五件套政策文档。

**`specs/` 原则：** 不拆 `tasks.md`（Verification 需 Ctrl+F）；状态全部交给 `ROADMAP.md`。

---

| 层 | 目录 | 职责 |
|----|------|------|
| Layer 1 Governance | `CLAUDE.md`、`.cursor/rules/`、`.github/copilot-instructions.md` | 铁律、命令、Check-in — Agent 入口路由 |
| Layer 2 Product Truth | `specs/`、`docs/PRODUCT_INTRO.md` | proposal、design、tasks — 规格与对外产品介绍 |
| Layer 3 Runtime State | `memory/` | 进度、踩坑、决策 — 跨会话运行态 |
| Layer 4 Execution | `.claude/workflows/`、`.cursor/` | 操作剧本（须符合 `CLAUDE.md` §Layer 4 约束） |
| Layer 5 Evidence | `runs/` | 工作流执行证据（`runs/<run_id>/`）与验证报告归档（`runs/verification/`） |

---

## 文档生命周期

### `memory/PROGRESS.md`

| 规则 | 说明 |
|------|------|
| 保留 | **Current Status** · **Next Actions** · **Recent Sessions**（最近 10 次会话） |
| 轮转触发 | 超过 10 次会话 **或** 主文件超过 **200 行** |
| 归档目标 | `memory/archive/PROGRESS-YYYY-Qn.md`（按自然季度） |
| 禁止 | 在 PROGRESS 重复 ROADMAP 全表或 DELIVERABLES 交付文件列表 |

### `memory/DELIVERABLES.md`

| 规则 | 说明 |
|------|------|
| 保留 | **Active Deliverables** · **Recently Completed**（最近一个版本）· **Archive Index** |
| 轮转触发 | 里程碑全 ✅ 或 Release 发布后，该里程碑整节移入 archive |
| 归档目标 | `memory/archive/DELIVERABLES-{M0,M1,…,OSR,HRT,POST-MVP}.md` |
| 禁止 | 与 Git 重复粘贴大段 diff |

### `memory/BACKLOG.md`

| 规则 | 说明 |
|------|------|
| 定义 | **仅**未立项候选需求池（TODO / IDEA / WAITING） |
| 完成后 | 删除正文，在 **Completed** 索引补一行 → `CHANGELOG` + `PRODUCT_INTRO` + Git |
| 否决后 | 在 **Rejected** 索引补一行，删除正文 |
| 禁止 | 维护 OSR 状态表（见 `ROADMAP.md`）· 禁止当历史博物馆 |

### `memory/ROADMAP.md`

| 规则 | 说明 |
|------|------|
| 保留 | 功能 / 里程碑 **状态**（✅ ❌ ⚠️）与 Task ID 引用 |
| 禁止 | 复制 commit hash、交付文件列表、会话叙述 |

### `memory/DECISIONS.md`

| 规则 | 说明 |
|------|------|
| 保留 | **全部**架构决策（可用 Active / Closed / Rejected Alternatives 分区） |
| 禁止 | 拆散到 `archive/` 或删除已关闭决策 |

### `specs/core/tasks.md`

| 规则 | 说明 |
|------|------|
| 保留 | 任务定义、验收标准、Verification 命令 — **永久** |
| 说明 | 天然历史档案；不因里程碑完成而归档 |

### `CHANGELOG.md`

| 规则 | 说明 |
|------|------|
| 更新时机 | 每次打 Release tag **之前**（硬门禁，见 §Release 硬门禁） |
| 内容 | 用户可见 `Added` · `Changed` · `Removed` · `Fixed` · `Security` |
| 受众 | 用户 · 开源贡献者 · 未来的维护者（非 Agent 内部日记） |

### 版本快照（`docs/releases/` · 按需）

| 规则 | 说明 |
|------|------|
| 用途 | 记录**该版本当时**的产品全貌；解答「v1.0 有什么、v1.1 删了什么」 |
| 权威 | **当前**产品仍以 `PRODUCT_INTRO.md` 为准；`docs/releases/vX.Y.md` 为历史快照 |
| 创建时机 | 打 major/minor tag 时可选创建；内容可从当版 `CHANGELOG` + `PRODUCT_INTRO` 摘要 |
| 禁止 | 用 `docs/releases/` 替代 `CHANGELOG` 或 `PRODUCT_INTRO` |

### `memory/archive/*`（冻结归档）

| 规则 | 说明 |
|------|------|
| 性质 | **只读**；禁止向已有归档文件追加会话或交付记录 |
| 文件头 | 必须含 **Archive Notice**（见 `memory/archive/README.md` 模板） |
| 轮转 | 满触发条件时**新建**归档文件，不修改旧文件 |

### 归档位置

```
memory/archive/
├── README.md                    # 归档索引 + Archive Notice 模板
├── PROGRESS-YYYY-Qn.md          # 顶部含 Archive Notice（只读）
├── DELIVERABLES-*.md
docs/releases/                   # 按需：版本产品快照 vX.Y.md
├── README.md
└── v1.0.md
```

---

## 各目录写什么

| 想改什么 | 去哪里 | 何时更新 |
|---------|--------|---------|
| 铁律、命令、Check-in | `CLAUDE.md` | 治理规则变更时 |
| 产品最新功能与特性 | [`docs/PRODUCT_INTRO.md`](./PRODUCT_INTRO.md) | 功能发布或大幅迭代时 |
| 产品目标、MVP、Non-Goals（历史） | [`specs/core/proposal.md`](../specs/core/proposal.md) | 仅作快照，不随演进更新 |
| 视觉规范 | `specs/core/design.md` | 第 4–5 步 |
| 前端 UI 规范（权威） | [`docs/UI_UX_GUIDELINES.md`](./UI_UX_GUIDELINES.md) | 组件与视觉变更时 |
| 文档总索引 | [`docs/README.md`](./README.md) | 新增/移动 `docs/` 文件时 |
| 开发任务清单 | `specs/core/tasks.md` | 第 6 步 |
| D25 Hybrid Runtime 执行计划 | `specs/core/hybrid-runtime-plan.md` | D25 Task（HRT-xx） |
| 当前进度、下次做什么 | `memory/PROGRESS.md` | 每个 Agent 会话结束 |
| 踩坑记录 | `memory/FAILURES.md` | 卡壳 >10 分钟或回滚时 |
| 架构决策与开放问题 | `memory/DECISIONS.md` | 做技术选型或待决事项时 |
| 文件定位速查 | [`memory/FILEMAP.md`](../memory/FILEMAP.md) | 第 6 步填实 |
| 功能验收状态 | `memory/ROADMAP.md`、`memory/TESTS.md` | 验证通过后 |
| 候选需求（未立项） | `memory/BACKLOG.md` | 新候选 / 升格 / 否决时 |
| 系统设计详述（叙事 + ADR） | [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md) | 架构评审时 |
| Orchestrator 调研（非决策） | [`docs/research/orchestrator-optimization-pool.md`](./research/orchestrator-optimization-pool.md) | 索引见 `BACKLOG.md` |
| 开源 / DMG 分发排期（OSR-xx） | [`docs/OPEN_SOURCE_RELEASE.md`](./OPEN_SOURCE_RELEASE.md) §7.2 | 验收勾选 `memory/ROADMAP.md` §开源分发 |

## 禁止事项

- 禁止在 `CLAUDE.md` 以外复制命令表、铁律全文、日志字段规范
- 禁止在 `CLAUDE.md` 里复制 proposal 全文或功能列表
- 禁止在未更新 `specs/` 或 `memory/DECISIONS.md` 的情况下做架构级业务变更
- 禁止在未实际运行验证的情况下标记功能完成
- 禁止在 `DECISIONS.md` 以外另开开放问题列表
- **禁止在 `BACKLOG.md` 维护 OSR / 已完成功能的状态表**（权威：`ROADMAP.md`）
- **禁止向 `memory/archive/*` 追加新记录**（须新建归档文件；见 Archive Notice）
- **禁止未更新 `CHANGELOG.md` 即打 Release tag**（见 §Release 硬门禁 · `release-preflight.sh` INV-R5）
