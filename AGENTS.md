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
| [`specs/core/clutch-agent-capability-plan.md`](./specs/core/clutch-agent-capability-plan.md) | Chat Agent 开发者 | Chat 自研 Clutch Agent 能力交付表 D0–D53（D44） |
| [`specs/core/prd-one-click-interactive-prototype.md`](./specs/core/prd-one-click-interactive-prototype.md) | 全体开发者 | 一键原型生成与交互契约规格 (PRD) |
| [`specs/core/hybrid-runtime-plan.md`](./specs/core/hybrid-runtime-plan.md) | Hybrid 开发者 | D25 HRT Task 与验收（权威） |
| [`specs/core/design.md`](./specs/core/design.md) | 前端开发者 | 视觉设计快照 → `docs/UI_UX_GUIDELINES.md` |
| [`docs/UI_UX_GUIDELINES.md`](./docs/UI_UX_GUIDELINES.md) | 前端开发者 | React + Tailwind UI/UX 规范 |
| [`docs/DESIGN_WORKSPACE_GUIDE.md`](./docs/DESIGN_WORKSPACE_GUIDE.md) | 产品与业务人员 | Design 模式产品功能与业务逻辑分析指南 |
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

---

## Cursor Cloud specific instructions

Durable notes for cloud agents (the startup update script already runs `pnpm install` + `uv sync --extra dev` for the orchestrator). Standard commands live in [`CLAUDE.md`](./CLAUDE.md) §核心命令 and [`docs/BUILD_FROM_SOURCE.md`](./docs/BUILD_FROM_SOURCE.md); this section only captures non-obvious cloud gotchas.

- **`uv` is not in the base image.** It is installed to `~/.local/bin` (added to `~/.bashrc`). If `uv` is missing from `PATH`, invoke it as `~/.local/bin/uv`.
- **Run in web dev mode, not Tauri, on the Linux cloud VM.** `pnpm tauri:dev` targets macOS/Windows and needs the Rust WebKitGTK desktop toolchain, so it is not runnable headless here. Instead run the two services separately:
  - Sidecar: `cd services/orchestrator && ~/.local/bin/uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8124`
  - Frontend: `pnpm dev` (Vite on `:3000`, proxies `/api`, `/ws`, `/health` → `8124`). Health check: `curl -s http://127.0.0.1:8124/health` → `{"status":"ok",...}`.
- **Web mode has no folder picker.** Workspace/folder selection needs Tauri desktop APIs, so onboarding blocks core features (chat, workflows). To unblock in the browser, authorize a workspace directly against the sidecar: `curl -X POST http://127.0.0.1:8124/api/workspaces -H 'Content-Type: application/json' -d '{"path":"/abs/path"}'` (auto-activates). Mark onboarding done via `curl -X POST http://127.0.0.1:8124/api/preferences/onboarding-complete`, then reload the page.
- **Agent/chat runs need credentials.** Without a connected CLI or a cloud LLM API key (Settings → Models), sending a chat returns a clear "No API key configured for provider …" error — this is expected, not a bug. Workflow (SOP) editing on the canvas works without any keys.
- **`pnpm lint` (`tsc --noEmit`) is not part of the CI gate** and currently has pre-existing type errors in some `*.test.ts` files. The authoritative verification is `./scripts/verify.sh` (build + vitest + pytest + doc-drift); `vitest` transpiles via esbuild so tests pass regardless.
