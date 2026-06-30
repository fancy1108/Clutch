# Clutch

本地 AI 多 Agent 编排与监督控制台（Tauri 桌面应用 + Python Sidecar）。

## 这是什么

**Clutch** 面向独立开发者与技术运营人员，解决「单 Agent 对话上下文膨胀」和「多 Agent 协作过程黑盒、流程难改」两类工程痛点。它不是替代 Claude Code / Cursor 的生成能力，而是在本地加一层**可持久化、可观测、可编辑**的流程控制层：你在画布上零代码拖拽 SOP，系统用 LangGraph 调度本地 CLI、MCP 与大模型，并在统一工作台里全程监督执行与人工审批。

**技术栈：** Tauri 2 · React 19 · FastAPI + LangGraph · 本地优先（Sidecar `localhost:8123`）

### 主要功能（概览）

| 能力 | 说明 |
|------|------|
| **可视化工作流编排** | React Flow 画布定义多 Agent SOP，编译为 LangGraph 状态机运行 |
| **本地 AI 工具接入** | 扫描并连接 Claude Code、Codex、Ollama、Aider 等本地 CLI |
| **统一监督控制台** | Chat 流、终端日志、文件树、代码 Diff、流程进度一屏可见 |
| **人机协同门控** | 高风险操作或检查失败时挂起，支持批准 / 打回 / 重试 |
| **智能体与模型配置** | Agent Manager、模型 API Key、Skills 注册表、MCP 服务网关 |
| **Hybrid 会话** | 多 Session 并行、工作流精修与自动续跑、状态跨会话恢复 |

> **想了解全部功能、架构细节与运行机制？** 请阅读 **[`docs/PRODUCT_INTRO.md`](./docs/PRODUCT_INTRO.md)**（产品介绍权威文档，含痛点分析、页面功能清单与数据流说明）。开发者架构叙事见 [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)。

## 产品截图

**Hybrid 工作流监督台** — 多 Agent 协作、流程进度与 Token 统计一屏可见：

![Clutch Hybrid 工作流监督台](./docs/images/Clutch_1.png)

**可视化 SOP 编排** — 在画布上零代码拖拽多 Agent 流水线：

![Clutch 工作流画布编排](./docs/images/Clutch_2.png)

## 仓库结构

> 与磁盘一致（排除 `node_modules`、`.venv`、`dist` 等构建产物）。治理层五层标注见 [`docs/document-governance.md`](./docs/document-governance.md)。

```
clutch/
├── README.md                       # 项目入口（本页）
├── LICENSE · CHANGELOG.md          # 开源与版本（GitHub 约定放根目录）
├── SECURITY.md · CODE_OF_CONDUCT.md · CONTRIBUTING.md
├── CLAUDE.md · AGENTS.md           # Layer 1 — 治理与多 AI 工具索引
├── package.json · pnpm-workspace.yaml · .env.example
├── scripts/                        # verify · tauri-dev · doctor · release-preflight
├── apps/desktop/                   # Tauri + React 桌面端
├── services/orchestrator/          # Python Sidecar（LangGraph）
├── packages/shared-types/
├── workflows/                      # Workflow JSON Schema + 内置模板
├── docs/                           # 产品与架构文档 → docs/README.md
├── memory/                         # Layer 3 — Agent 跨会话运行态
├── specs/core/                     # Layer 2 — 需求/任务历史快照
├── e2e/ · experiments/ · runs/
└── .github/ · .husky/ · .cursor/   # CI · hooks · Agent 规则指针
```

**解耦原则**：`apps/desktop` 与 `services/orchestrator` 仅通过 loopback HTTP/WebSocket 通信（开发 `8124`，打包 `8123`）。

## 文档地图

**完整索引：** [`docs/README.md`](./docs/README.md)（按角色分组）。

### 根目录（社区与治理）

| 文件 | 用途 |
|------|------|
| [`CLAUDE.md`](./CLAUDE.md) | **唯一权威**：铁律、命令、Check-in、日志规范 |
| [`AGENTS.md`](./AGENTS.md) | 多 AI 工具入口索引 |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | 如何贡献、Phase 1 PR 政策 |
| [`SECURITY.md`](./SECURITY.md) · [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md) | 漏洞报告 · 社区准则 |
| [`CHANGELOG.md`](./CHANGELOG.md) | 版本变更（当前 **1.0.1**） |

### 产品与架构（`docs/`）

| 文件 | 用途 |
|------|------|
| [`docs/PRODUCT_INTRO.md`](./docs/PRODUCT_INTRO.md) | **推荐首读**：定位、功能、运行机制 |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | 系统架构、工作流、WebSocket |
| [`docs/UI_UX_GUIDELINES.md`](./docs/UI_UX_GUIDELINES.md) | 前端 React + Tailwind 规范 |
| [`docs/INSTALL.md`](./docs/INSTALL.md) · [`docs/BUILD_FROM_SOURCE.md`](./docs/BUILD_FROM_SOURCE.md) | 安装 DMG · 源码构建 |
| [`docs/OPEN_SOURCE_RELEASE.md`](./docs/OPEN_SOURCE_RELEASE.md) | 开源排期 OSR-xx |

### Agent 运行态（`memory/`）

| 文件 | 用途 |
|------|------|
| [`memory/PROGRESS.md`](./memory/PROGRESS.md) | 跨会话进度接力 |
| [`memory/FILEMAP.md`](./memory/FILEMAP.md) | 改代码去哪个文件 |
| [`memory/DECISIONS.md`](./memory/DECISIONS.md) | 架构决策与开放问题 |

## 兼容性

> 详细稳定性见 [`docs/STABILITY.md`](./docs/STABILITY.md)。当前 `1.0.x` 遵循语义化版本；历史 pre-1.0 版本可能包含 breaking change。

### 平台

| 项 | 支持级别 |
|----|----------|
| macOS 14+（Apple Silicon） | ✅ 官方主要目标 |
| macOS 14+（Intel） | ⚠️ 尽力支持，未充分测试 |
| macOS 13 及更早 | ⚠️ 不保证 |
| Windows 10/11（x64） | ✅ 支持 MSI / NSIS 安装包 |
| Linux | 🚧 无官方安装包 |

### 开发工具链（源码构建）

| 组件 | 版本要求 |
|------|----------|
| Node.js | **≥ 20**（推荐 22 LTS） |
| pnpm | **≥ 9**（仓库锁定 `9.15.0`） |
| Python | **≥ 3.11**（CI 使用 3.11） |
| [uv](https://docs.astral.sh/uv/) | 最新稳定版 |
| Rust | 最新 stable（仅 `pnpm tauri build` 时需要） |
| Windows 构建工具 | Visual Studio 2022 C++ Build Tools + Windows 10/11 SDK |

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

## 安装方式

> ### ⚠️ 未签名 DMG · 首次安装必读
>
> 当前 Release 中的 `.dmg` **未经 Apple 签名/公证**。macOS 可能提示「**无法验证开发者**」或「**应用已损坏**」——**这是 Gatekeeper 对未签名应用的正常反应，不是病毒，也不是包坏了。**
>
> **复制粘贴即可用（终端）：**
>
> ```bash
> xattr -cr /Applications/Clutch.app && open -a Clutch
> ```
>
> 或：**应用程序** → 右键 **Clutch** → **打开** → 确认打开。  
> 详细说明与免责：[`docs/INSTALL.md`](./docs/INSTALL.md) · 每次 Release 说明见 [GitHub Releases](https://github.com/fancy1108/Clutch/releases)。

### 从 Release 安装（终端用户 · macOS）

从 [GitHub Releases](https://github.com/fancy1108/Clutch/releases) 下载 **macOS `.dmg`**（当前版本为未签名构建，这也是开源桌面应用的常见分发方式）：

1. 下载对应架构的 DMG（Apple Silicon 选 `aarch64`）并拖入 **Applications**
2. **首次打开**若被 Gatekeeper 拦截（含「**已损坏**」文案），任选其一：
   - **Finder**：右键 **Clutch.app** → **打开** → 确认打开
   - **终端（推荐，可复制）**：`xattr -cr /Applications/Clutch.app && open -a Clutch`
3. 约 5s 内侧车应就绪：`curl -s http://127.0.0.1:8123/health` → `{"status":"ok"}`

维护者发版：打 tag `v1.0.0`（或后续 `v1.x.x`）触发 [`.github/workflows/release.yml`](./.github/workflows/release.yml) 自动构建并上传 DMG；或本机 `cd apps/desktop && pnpm tauri build` 后手动上传到 Release。

完整安装说明见 [`docs/INSTALL.md`](./docs/INSTALL.md)；数据与隐私见 [`docs/DATA_AND_PRIVACY.md`](./docs/DATA_AND_PRIVACY.md)。获得 Apple Developer 账号后，可再提供代码签名与公证的安装包。

### Windows 安装

下载 `Clutch_*_x64-setup.exe`（向导安装）或 `Clutch_*_x64_en-US.msi`。当前构建未进行 Windows 代码签名；若 SmartScreen 提示未知发布者，请确认安装包来源与 SHA-256 后选择继续。应用安装到 `C:\Program Files\Clutch`，数据保存在 `%APPDATA%\clutch`，API Key 使用 Windows 凭据管理器。

### 从源码构建（开发者）

```bash
git clone https://github.com/fancy1108/Clutch.git
cd Clutch
./scripts/doctor.sh
pnpm install
cd services/orchestrator && uv sync --extra dev && cd ../..
export CLUTCH_RUNTIME_MODE=hybrid   # 可选
pnpm tauri:dev
```

逐步说明、分拆调试与本地打 DMG / Windows 安装包：[`docs/BUILD_FROM_SOURCE.md`](./docs/BUILD_FROM_SOURCE.md)。

**贡献前**请阅读 [`CONTRIBUTING.md`](./CONTRIBUTING.md) 并运行 `./scripts/verify.sh`。

## 安全与 CLI 权限（重要）

Clutch 通过本地 Sidecar（`127.0.0.1:8123` / 开发 `8124`）调度外部 AI CLI。请在使用前了解以下**当前版本**行为：

### CLI 默认跳过内置确认（`--dangerously-skip-permissions`）

对 **Claude Code CLI**（`claude-cli`）与 **Antigravity CLI**（`agy-cli`）等已接入的引擎，Clutch **默认**在调用时追加 `--dangerously-skip-permissions`。这会**绕过**对应 CLI 自身的工具/写入确认提示，以便工作流与 Hybrid 会话自动跑通。

| 含义 | 说明 |
|------|------|
| **适用场景** | 你已信任当前授权工作区，且接受 Agent 在该目录内自动执行工具调用 |
| **风险** | CLI 可在工作区（及 CLI 自身权限可达范围）内改文件、跑命令，**不会**再逐项询问 |
| **UI 中的 Permission 菜单** | 聊天栏旁 `ask` / `auto_edit` / `plan` / `full` 主要作用于 **Clutch 内置 Agent 的 MCP 门控**；**不改变**上述 CLI 的 `skip-permissions` 默认行为 |

**权限策略声明：** 现阶段默认维持跳过确认的设定。后续若安全策略调整为默认 `ask`（逐次询问），将同步更新本文与 [`SECURITY.md`](./SECURITY.md)。

漏洞报告见 [`SECURITY.md`](./SECURITY.md)。Sidecar 仅监听本机回环地址。
