# Clutch — Agent Instructions Index

跨 AI 工具的统一入口。**不要在本文件维护实质规则**——规则只写在权威源里，本文件只做指针。

| 文档 | 读者 | 用途 |
|------|------|------|
| [`CLAUDE.md`](./CLAUDE.md) | Claude Code、全体开发者 | **唯一权威**：铁律、命令、Check-in、日志规范 |
| [`memory/PROGRESS.md`](./memory/PROGRESS.md) | 所有 Agent | 跨会话进度接力棒 |
| [`memory/DELIVERABLES.md`](./memory/DELIVERABLES.md) | 所有 Agent | Task 交付索引（Commit / Verification / 证据） |
| [`memory/DECISIONS.md`](./memory/DECISIONS.md) | 所有 Agent | 最新决策与开放问题（唯一汇总地） |
| [`memory/FILEMAP.md`](./memory/FILEMAP.md) | 所有 Agent | 文件路径速查（Check-in 用） |
| [`specs/core/proposal.md`](./specs/core/proposal.md) | 产品追溯 | 历史快照，非权威 |
| [`specs/core/tasks.md`](./specs/core/tasks.md) | 全体开发者 | M0–M4 开发任务清单 |
| [`specs/core/hybrid-runtime-plan.md`](./specs/core/hybrid-runtime-plan.md) | Hybrid 开发者 | D25 HRT Task 与验收（权威） |
| [`specs/core/design.md`](./specs/core/design.md) | 前端开发者 | 视觉设计快照 → `docs/UI_UX_GUIDELINES.md` |
| [`docs/UI_UX_GUIDELINES.md`](./docs/UI_UX_GUIDELINES.md) | 前端开发者 | React + Tailwind UI/UX 规范 |
| [`.cursor/rules/base.mdc`](./.cursor/rules/base.mdc) | Cursor Agent | 精简指针（`alwaysApply`）→ `CLAUDE.md` |
| [`.github/copilot-instructions.md`](./.github/copilot-instructions.md) | GitHub Copilot | 精简指针 → `CLAUDE.md` |
| [`docs/document-governance.md`](./docs/document-governance.md) | 架构评审 | 五层架构、权威真相、文档生命周期 |
| [`docs/agents/issue-tracker.md`](./docs/agents/issue-tracker.md) | Agent skills | 问题追踪器配置（GitHub） |
| [`docs/agents/triage-labels.md`](./docs/agents/triage-labels.md) | Agent skills | 标签词表映射 |
| [`docs/agents/domain.md`](./docs/agents/domain.md) | Agent skills | 领域文档消费规则 |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | 架构评审 | 系统设计详述（叙事 + ADR） |

---

**For Claude Code users:** see [`CLAUDE.md`](./CLAUDE.md).

**For Cursor Agent users:** `.cursor/rules/base.mdc` applies automatically; canonical rules remain in [`CLAUDE.md`](./CLAUDE.md).

**For GitHub Copilot users:** see [`.github/copilot-instructions.md`](./.github/copilot-instructions.md).

**For frontend UI work:** see [`docs/UI_UX_GUIDELINES.md`](./docs/UI_UX_GUIDELINES.md).
