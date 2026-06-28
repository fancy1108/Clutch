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
│   ├── tauri-dev.sh                # Tauri 开发：守护化 Vite + tauri dev
│   ├── doctor.sh                   # 环境自检（Node / uv / 平台）
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
| [`docs/PRODUCT_INTRO.md`](./docs/PRODUCT_INTRO.md) | 产品介绍（功能与运行机制） |
| [`docs/OPEN_SOURCE_RELEASE.md`](./docs/OPEN_SOURCE_RELEASE.md) | 开源、安全、分发与 OSR 排期 |
| [`docs/PROJECT_SCOPE.md`](./docs/PROJECT_SCOPE.md) | Goals / Non-Goals |
| [`docs/STABILITY.md`](./docs/STABILITY.md) | API / Schema 稳定性 |
| [`docs/EXTENSIBILITY.md`](./docs/EXTENSIBILITY.md) | 官方扩展点 |
| [`LICENSE`](./LICENSE) | MIT 开源协议 |
| [`CHANGELOG.md`](./CHANGELOG.md) | 版本变更（当前 **0.1.0**） |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | **如何贡献**、Phase 1 PR 政策 |
| [`docs/GOVERNANCE.md`](./docs/GOVERNANCE.md) | 维护者治理 |
| [`docs/PERFORMANCE.md`](./docs/PERFORMANCE.md) | 性能基线 |
| [`docs/document-governance.md`](./docs/document-governance.md) | 五层架构与权威优先级 |
| [`specs/core/proposal.md`](./specs/core/proposal.md) | 产品需求历史快照（非权威） |
| [`specs/core/tasks.md`](./specs/core/tasks.md) | M0–M4 开发任务清单 |
| [`specs/core/design.md`](./specs/core/design.md) | 视觉设计快照 |
| [`UI_UX_GUIDELINES.md`](./UI_UX_GUIDELINES.md) | 前端 React + Tailwind UI/UX |

## 兼容性

> 详细稳定性见 [`docs/STABILITY.md`](./docs/STABILITY.md)。**0.x 版本可能随时 breaking change。**

### 平台

| 项 | 支持级别 |
|----|----------|
| macOS 14+（Apple Silicon） | ✅ 官方主要目标 |
| macOS 14+（Intel） | ⚠️ 尽力支持，未充分测试 |
| macOS 13 及更早 | ⚠️ 不保证 |
| Windows | 🚧 架构预留，无官方安装包 |
| Linux | 🚧 无官方安装包 |

### 开发工具链（源码构建）

| 组件 | 版本要求 |
|------|----------|
| Node.js | **≥ 20**（推荐 22 LTS） |
| pnpm | **≥ 9**（仓库锁定 `9.15.0`） |
| Python | **≥ 3.11**（CI 使用 3.11） |
| [uv](https://docs.astral.sh/uv/) | 最新稳定版 |
| Rust | 最新 stable（仅 `pnpm tauri build` 时需要） |

环境自检：

```bash
./scripts/doctor.sh
```

## 快速开始

**前置**：Node 20+、pnpm 9+、Python 3.11+、[uv](https://docs.astral.sh/uv/)、Rust（Tauri 打包时）

```bash
pnpm install
```

启动与校验命令见 [`CLAUDE.md`](./CLAUDE.md) §核心命令。
