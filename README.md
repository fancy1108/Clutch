# Clutch

本地 AI 多 Agent 编排与监督控制台（Tauri 桌面应用 + Python Sidecar）。

## 仓库结构

> 与磁盘一致（排除 `node_modules`、`.venv`、`dist` 等构建产物）。治理层五层标注见 [`docs/document-governance.md`](./docs/document-governance.md)。

```
clutch/
├── CLAUDE.md                       # Layer 1 — 治理规则唯一权威
├── AGENTS.md                       # 多 AI 工具索引（指针）
├── UI_UX_GUIDELINES.md
├── package.json
├── pnpm-workspace.yaml
├── .env.example
├── src/                            # Pro 空壳占位（第 7 步起）
├── scripts/
│   ├── verify.sh                   # 本地一键校验（build + pytest + drift）
│   └── check-doc-drift.sh          # 文档↔代码机检不变量（D7）
├── .husky/
│   └── pre-commit                  # 条件触发 verify / drift（D7）
├── specs/
│   └── core/
│       ├── proposal.md             # Layer 2 — 产品需求历史快照
│       ├── design.md               # Layer 2 — 视觉设计快照（→ UI_UX_GUIDELINES）
│       └── tasks.md                # Layer 2 — M0–M4 开发任务清单
├── memory/                         # Layer 3 — Agent 跨会话运行态
│   ├── PROGRESS.md
│   ├── FAILURES.md
│   ├── FILEMAP.md                  # 文件路径速查（≠ docs/ARCHITECTURE.md）
│   ├── DECISIONS.md
│   ├── ROADMAP.md
│   └── TESTS.md
├── .claude/workflows/              # Layer 4 — 可选自动化
├── .cursor/rules/
│   └── base.mdc                    # Cursor 指针 → CLAUDE.md
├── .github/
│   ├── workflows/
│   │   └── ci.yml                  # CI：pnpm build + pytest
│   └── copilot-instructions.md     # Copilot 指针 → CLAUDE.md
├── runs/                           # Layer 5 — 执行证据
│   └── verification/               # 测试/覆盖率报告归档（gitignore）
├── apps/
│   └── desktop/                    # Tauri + React 桌面端
│       ├── src/
│       └── src-tauri/
├── services/
│   └── orchestrator/               # Python Sidecar（LangGraph）
│       ├── src/
│       └── tests/
├── packages/
│   └── shared-types/
├── workflows/                      # Workflow JSON Schema + 模板
├── e2e/                            # （D1，M2 后可执行）Playwright 全链路 E2E
└── docs/
    ├── ARCHITECTURE.md             # 系统架构详述（叙事 + ADR）
    └── document-governance.md      # 五层架构与权威优先级
```

**解耦原则**：`apps/desktop` 与 `services/orchestrator` 仅通过 `localhost:8123` HTTP/WebSocket 通信。

## 文档地图

| 文件 | 用途 |
|------|------|
| [`README.md`](./README.md) | 本页：结构、快速开始、文档索引 |
| [`CLAUDE.md`](./CLAUDE.md) | **唯一权威**：铁律、命令、Check-in、日志规范 |
| [`AGENTS.md`](./AGENTS.md) | 多 AI 工具入口索引 |
| [`memory/PROGRESS.md`](./memory/PROGRESS.md) | Agent 进度接力棒 |
| [`memory/FILEMAP.md`](./memory/FILEMAP.md) | 文件路径速查（Check-in 用） |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | 系统架构详述（设计理由、数据流） |
| [`docs/PRODUCT_INTRO.md`](./docs/PRODUCT_INTRO.md) | 产品介绍文档（功能、特性与运行机制概述） |
| [`docs/document-governance.md`](./docs/document-governance.md) | 五层架构与权威优先级 |
| [`specs/core/proposal.md`](./specs/core/proposal.md) | 产品需求历史快照（非权威） |
| [`specs/core/tasks.md`](./specs/core/tasks.md) | M0–M4 开发任务清单 |
| [`specs/core/design.md`](./specs/core/design.md) | 视觉设计快照 |
| [`UI_UX_GUIDELINES.md`](./UI_UX_GUIDELINES.md) | 前端 React + Tailwind UI/UX |

## 快速开始

**前置**：Node 20+、pnpm 9+、Python 3.11+、[uv](https://docs.astral.sh/uv/)、Rust（Tauri 打包时）

```bash
pnpm install
```

启动与校验命令见 [`CLAUDE.md`](./CLAUDE.md) §核心命令。
