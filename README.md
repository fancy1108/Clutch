# Clutch

本地 AI 多 Agent 编排与监督控制台（Tauri 桌面应用 + Python Sidecar）。

## 仓库结构

```
clutch/
├── apps/
│   └── desktop/                    # Tauri + React 桌面端
├── services/
│   └── orchestrator/               # Python Sidecar（LangGraph）
├── packages/
│   └── shared-types/               # @clutch/shared-types
├── workflows/                      # Workflow JSON Schema + 模板
├── specs/
│   └── core/
│       └── proposal.md             # 产品需求历史快照
├── memory/                         # Agent 跨会话运行态（六件套）
├── runs/                           # 执行证据（第 7 步起）
├── docs/
│   ├── ARCHITECTURE.md
│   ├── document-governance.md
│   └── PROPOSAL.md                 # 遗留副本；权威快照见 specs/core/
├── .cursor/rules/base.mdc          # Cursor Agent 指针 → CLAUDE.md
├── CLAUDE.md                       # 治理规则唯一权威
├── AGENTS.md                       # 多 AI 工具索引
└── UI_UX_GUIDELINES.md
```

**解耦原则**：`apps/desktop` 与 `services/orchestrator` 仅通过 `localhost:8123` HTTP/WebSocket 通信。

## 文档地图

| 文件 | 用途 |
|------|------|
| [`README.md`](./README.md) | 本页：结构、快速开始、文档索引 |
| [`CLAUDE.md`](./CLAUDE.md) | **唯一权威**：铁律、命令、Check-in、日志规范 |
| [`AGENTS.md`](./AGENTS.md) | 多 AI 工具入口索引 |
| [`memory/PROGRESS.md`](./memory/PROGRESS.md) | Agent 进度接力棒 |
| [`docs/document-governance.md`](./docs/document-governance.md) | 五层架构与权威优先级 |
| [`UI_UX_GUIDELINES.md`](./UI_UX_GUIDELINES.md) | 前端 React + Tailwind UI/UX |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | 系统架构详述 |
| [`specs/core/proposal.md`](./specs/core/proposal.md) | 产品需求历史快照 |

## 快速开始

**前置**：Node 20+、pnpm 9+、Python 3.11+、[uv](https://docs.astral.sh/uv/)、Rust（Tauri 打包时）

```bash
pnpm install
```

启动与校验命令见 [`CLAUDE.md`](./CLAUDE.md) §核心命令。
