# Clutch — 系统架构文档

> **文件路径速查：** 具体「改什么去哪个文件」见 [`memory/FILEMAP.md`](../memory/FILEMAP.md)。下文为完整设计理由、数据流与 ADR 叙事。

> **版本**: v0.1  
> **状态**: 已确认方案  
> **最后更新**: 2026-06-22

---

## 1. 文档目的

本文档描述 **Clutch** 从当前 UI Prototype 演进为可交付桌面产品的目标架构。方案已确认：

- **桌面壳**: Tauri
- **前端**: React + Tailwind CSS + Motion + React Flow
- **编排引擎**: Python Sidecar（FastAPI + LangGraph）
- **工作流**: 用户在界面拖拽编排，后端自动编译为 LangGraph 可执行图

读者对象：产品负责人、开发（含 AI Agent 实现）、后续维护者。

---

## 2. 产品定位与架构约束

### 2.1 产品定位

Clutch 是一个面向开发者与技术运营人员的 **本地 AI 多 Agent 编排与监督控制台**。用户通过可视化界面定义 SOP 工作流，由系统调度本地 CLI、MCP 服务及 GUI 工具（如 Cursor），并在 Chat、Terminal、Diff 等面板中监督执行过程，在关键节点进行人工干预。

### 2.2 架构约束

| 约束 | 说明 |
|------|------|
| 必须桌面端 | 需深度访问本地文件系统、子进程、系统应用唤起 |
| 编排核心用 LangGraph | Python 生态最成熟，适合复杂状态机与人机协同 |
| 用户零代码 | 工作流通过 UI 配置，不暴露 LangGraph 代码 |
| 基于现有 Prototype | 保留三栏 IDE 式布局与 React Flow 编辑器 |

---

## 3. 总体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Tauri Desktop Shell                              │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │              React UI (Vite + Tailwind + Motion)                  │  │
│  │  Sidebar │ ChatFeed │ RightPanel │ Settings Modal │ React Flow    │  │
│  └────────────────────────────┬──────────────────────────────────────┘  │
│                               │ WebSocket / HTTP (localhost)            │
│  ┌────────────────────────────┴──────────────────────────────────────┐  │
│  │              Tauri Native Commands (薄层)                          │  │
│  │  打开 Cursor │ 系统路径 │ Sidecar 生命周期 │ 可选 IPC 透传         │  │
│  └────────────────────────────┬──────────────────────────────────────┘  │
└───────────────────────────────┼─────────────────────────────────────────┘
                                │ spawn / supervise
┌───────────────────────────────┴─────────────────────────────────────────┐
│                   Python Orchestration Sidecar                            │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │   FastAPI   │  │  LangGraph   │  │  Workflow   │  │ Tool Adapters  │  │
│  │ REST + WS   │──│ State Machine│──│  Compiler   │──│ CLI/MCP/GUI/FS │  │
│  └─────────────┘  └──────────────┘  └─────────────┘  └────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
   Claude CLI              MCP Servers            File System
   自定义 CLI               (stdio/SSE)           + Cursor 等 GUI
```

### 3.1 分层职责

| 层级 | 职责 | 不应承担 |
|------|------|----------|
| **Tauri Shell** | 窗口、打包、系统 API、Sidecar 启停 | 业务编排、LLM 调用 |
| **React UI** | 展示、交互、工作流编辑、人工决策上报 | 直接执行 CLI / 读盘 |
| **Python Sidecar** | LangGraph 运行时、状态持久化、工具调度、事件广播 | UI 渲染 |
| **Tool Adapters** | 统一封装外部工具调用与日志流 | 工作流路由逻辑 |

---

## 4. 技术选型

### 4.1 已确认栈

| 类别 | 选型 | 理由 |
|------|------|------|
| 桌面宿主 | **Tauri 2.x** | 轻量、Rust 侧进程管理可靠；编排逻辑不绑进壳层 |
| 前端框架 | **React 19 + Vite** | 与现有 Prototype 一致，无需 SSR |
| 样式 / 动效 | **Tailwind CSS 4 + Motion** | 与 `UI_UX_GUIDELINES.md` 一致 |
| 工作流画布 | **React Flow (@xyflow/react)** | Prototype 已集成，支持拖拽编排 |
| 编排服务 | **FastAPI** | 异步友好，WebSocket 成熟，AI 生成代码资料多 |
| 状态机引擎 | **LangGraph (Python)** | 条件路由、interrupt、checkpoint 能力完整 |
| LLM | **Claude 3.5 Sonnet**（主）+ 可扩展 Router | Orchestrator 路由与 Agent 推理 |
| 实时通道 | **WebSocket**（主）/ SSE（备选） | 状态跳跃、日志流、Chat 推送 |

### 4.2 未采用方案及原因

| 方案 | 不采用原因 |
|------|------------|
| Electron + LangGraph.js | LangGraph 主生态在 Python；Electron 包体更大且不能省掉 Python sidecar |
| Next.js | 桌面 App 无 SSR 需求，迁移成本高、收益低 |
| 纯 Web App | 无法深度调度本地 CLI、进程、GUI 应用 |
| 用户手写 LangGraph | 违背「零代码、界面化」产品目标 |

---

## 5. 仓库结构（当前）

```
clutch/
├── apps/
│   └── desktop/              # Tauri + React 桌面端应用
│       ├── src/              # React UI 代码
│       ├── src-tauri/        # Tauri Rust（拉起 Sidecar）
│       ├── index.html
│       ├── vite.config.ts    # /api、/ws 代理到 8123
│       ├── tsconfig.json
│       ├── package.json      # @clutch/desktop
│       ├── .env.example
│       └── metadata.json     # AI Studio 原型遗留元数据（非 Tauri 配置）
├── services/
│   └── orchestrator/         # Python Sidecar 编排引擎
│       ├── src/
│       │   └── main.py       # FastAPI 入口（端口 8123）
│       ├── tests/
│       ├── .python-version
│       ├── uv.lock
│       └── pyproject.toml
├── packages/
│   └── shared-types/         # @clutch/shared-types
│       ├── index.ts
│       ├── package.json
│       └── tsconfig.json
├── workflows/                # workflow.schema.json + 内置模板
├── docs/
├── .cursor/rules/            # Cursor Agent（精简 → CLAUDE.md）
├── CLAUDE.md                 # 架构与开发纪律（唯一权威）
├── AGENTS.md                 # AI 工具指令索引
├── UI_UX_GUIDELINES.md
├── package.json
└── pnpm-workspace.yaml
```

**解耦**：`apps/desktop` 与 `services/orchestrator` 互不干扰，仅通过 `localhost:8123` 通信。P5 阶段 Tauri 将 PyInstaller 产出的 sidecar 二进制内嵌进 `src-tauri/binaries/`。

---

## 6. 核心子系统

### 6.1 Orchestrator（总控 Agent）

**Orchestrator 不是独立外部软件**，而是 LangGraph 图中的 **路由节点（Router Node）**，由 LLM + 规则共同驱动。

#### 工作机制

1. 读取全局状态 `ClutchState`
2. 结合当前工作流定义、历史消息、校验错误，调用 LLM 分析
3. 通过 **Conditional Edge** 返回下一节点 ID
4. 将状态变更广播至前端

#### ClutchState（全局状态）

```python
from typing import TypedDict, Literal, Optional

class ChatMessage(TypedDict):
    id: str
    agent: Literal["Orchestrator", "Builder", "Evaluator", "Supervisor"]
    text: str
    time: str
    status: Optional[Literal["COMPLETED", "FAILED", "RUNNING"]]

class ClutchState(TypedDict):
    run_id: str
    workflow_id: str
    current_instruction: str          # 用户输入 / 任务描述
    active_node_id: str               # LangGraph 内部节点 ID
    active_agent: str                 # UI 展示用角色名
    status: Literal["running", "failed", "passed", "awaiting_human"]
    artifacts: dict[str, str]         # 产物名 → 文件路径
    validation_errors: list[dict]      # Evaluator 结构化报错
    messages: list[ChatMessage]       # ChatFeed 数据源
    terminal_logs: list[str]          # Terminal 面板
    changed_files: list[str]          # Changes / Diff 面板
    human_decision: Optional[Literal["approve", "reject", "retry"]]
    retry_instructions: Optional[str] # 人工重试时的补充指令
```

#### 典型图结构

```
[Start]
   │
   ▼
[Orchestrator Router] ──► [Agent Task: Builder]
                              │
                              ▼
                         [Check: Evaluator]
                         ╱              ╲
                   passed              failed
                     ╱                    ╲
               [End]              [Human Gate]
                                    ╱    │    ╲
                              approve reject retry
                                 │      │      │
                              [End] [Builder] [Builder + instructions]
```

**Human Gate** 使用 LangGraph `interrupt_before`：图暂停，等待前端上报 `human_decision` 后 `resume`。

---

### 6.2 工作流系统（UI → Compiler → LangGraph）

用户 **只操作可视化画布**，不接触代码。系统内部维护两层表示：

| 层 | 格式 | 说明 |
|----|------|------|
| 用户层 | **Workflow JSON** | React Flow 导出，字段人类可读 |
| 运行层 | **LangGraph StateGraph** | 由 Compiler 在运行时生成 |

#### 6.2.1 UI 节点类型（第一版）

为降低认知负担，仅暴露有限节点类型：

| UI 类型 | 用户可见名称 | 配置项 | 编译目标 |
|---------|--------------|--------|----------|
| `start` | 开始 | — | 图入口 |
| `agent_task` | Agent 任务 | 角色、说明、可选工具 | 固定 Agent 节点模板 + 工具绑定 |
| `check` | 自动检查 | 检查规则列表 | Evaluator 节点 |
| `human_gate` | 等我确认 | 提示文案 | `interrupt_before` 节点 |
| `end` | 完成 | — | 图出口 |

> 高级能力（MCP、CLI）第一版收纳在 `agent_task` 的工具选择中，不单独暴露复杂节点。

#### 6.2.2 Workflow JSON 与 Schema

**权威 Schema**：[`workflows/workflow.schema.json`](../workflows/workflow.schema.json)

**参考模板**：[`workflows/video-production.json`](../workflows/video-production.json)

`edge.data.when` 合法取值：

| 值 | 来源节点 | 含义 |
|----|----------|------|
| `passed` | `check` | 检查通过 |
| `failed` | `check` | 检查失败 |
| `approve` | `human_gate` | 人工批准 |
| `reject` | `human_gate` | 人工拒绝 |
| `retry` | `human_gate` | 带指令重试 |

`source: "start"` 为虚拟入口，不要求 `nodes` 中存在 `type: "start"` 节点。`position` 为 React Flow 布局字段，可选。

文档内不再维护完整 JSON 副本，避免与 Schema / 模板漂移。结构说明见上表与 Schema 文件。

#### 6.2.3 WorkflowCompiler 职责

```
Workflow JSON
    │
    ├─► Schema 校验（必有 start/end、无孤立节点、分支合法）
    ├─► 节点 type → 预注册 Python 节点函数
    ├─► edge.when → Conditional Edge 函数
    ├─► human_gate → interrupt 配置
    └─► 输出 CompiledGraph（可缓存，workflow_id + version 为键）
```

**设计原则**：

- 编译器代码由开发/AI 维护，用户永不编辑
- 新增节点类型 = 新增 UI 表单项 + 新增一个后端节点模板
- 保存前 UI 做图结构校验，编译失败时返回可读错误（非 Python traceback）

---

### 6.3 实时事件协议（WebSocket）

前端不再使用 `setTimeout` 模拟；所有状态变更由 Sidecar 推送。

#### 连接

- 地址：`ws://127.0.0.1:{port}/ws/runs/{run_id}`
- 鉴权：本地 loopback + 随机 session token（Tauri 启动时注入）

#### 事件 Envelope

所有推送必须使用统一信封：`{"event": "...", "data": {...}}`

```json
{
  "event": "state_patch",
  "data": {
    "run_id": "run_vid_prod_f8423",
    "timestamp": "2026-06-22T10:47:00Z",
    "patch": {
      "active_node_id": "n2",
      "active_agent": "Evaluator",
      "status": "running"
    }
  }
}
```

> 开发环境默认端口：**8123**（见 `CLAUDE.md`）

#### 事件类型

| event | 用途 | 前端落点 |
|-------|------|----------|
| `state_patch` | 部分状态更新 | 全局 run store |
| `message` | 新 Chat 消息 | ChatFeed |
| `log` | 单行终端日志 | RightPanel → Terminal |
| `file_changed` | 工作区文件变更 | Changes tab |
| `validation_result` | 检查结果 | ChatFeed 卡片 + Overview |
| `human_required` | 进入人工闸门 | 显示 Approve/Reject/Retry |
| `run_completed` | 运行结束 | 状态徽章、Footer |

#### 客户端 → 服务端指令

| action / payload | 说明 |
|------------------|------|
| `{ "text": "..." }` | 无工作流时的直连 LLM 聊天（plain chat） |
| `start_run` | 指定 workflow_id + instruction 启动 |
| `human_decision` | 上报 approve / reject / retry + 可选 instructions |
| `stop_run` | 取消当前运行（终止子进程） |
| `resume_run` | interrupt 后继续 |

---

### 6.3.1 会话与对话持久化（D3 + D11）

侧栏「历史会话」分两层存储，均位于应用数据目录（macOS：`~/Library/Application Support/clutch/sessions/`）：

| 文件 | 内容 | 用途 |
|------|------|------|
| `history.json` | `run_id`、标题、工作区、`workflow_id`、状态、时间 | 侧栏列表（M2-07 / D3） |
| `states/{run_id}.json` | 完整 `ClutchState`（含 `messages`、`terminal_logs` 等） | 点选会话恢复对话（D11） |

**写入时机：** Sidecar 在 `_commit_run_state()` 时落盘（plain chat、工作流推进、人工决策等所有状态变更）。

**读取时机：**

1. `_get_or_create_run(run_id)` — Sidecar 内存未命中时从 `states/` 加载
2. `GET /api/runs/{run_id}/state` — 前端切换会话时 HTTP hydrate
3. WebSocket 连接 — 推送 `state_patch` 同步增量

**前端路径：** `handleSelectSession` → `fetchRunState` → `clutchStore.setPendingHydrate` → `connect(run_id)`（避免切换时清空已加载消息）。

> E2E 使用 `CLUTCH_E2E_FAKE_LLM=1` 注入 Echo 路由器，避免依赖真实 API Key。

---

### 6.4 Tool Adapter 层

所有外部工具通过统一接口接入：

```python
class ToolAdapter(Protocol):
    async def invoke(self, instruction: str, ctx: RunContext) -> ToolResult: ...
    async def stream_logs(self) -> AsyncIterator[str]: ...
    async def cancel(self) -> None: ...
```

#### 6.4.1 CLI Adapter（如 Claude Code CLI）

| 步骤 | 实现 |
|------|------|
| 调用 | `asyncio.create_subprocess_exec` 或 PTY |
| 日志 | 逐行读取 stdout/stderr → `log` 事件 |
| 完成 | 根据 exit code 写入 `ClutchState` |
| 取消 | SIGTERM → 超时后 SIGKILL |

#### 6.4.2 MCP Adapter

- 对接 `McpServerHub` 配置的 stdio / SSE 端点
- 使用 MCP Python SDK 或 LangChain MCP 工具封装
- 工具列表在 Agent 配置界面选择，运行期注入 Agent 节点

#### 6.4.3 FS Watcher

- 监听 `git status` 变更或文件 write 事件
- 推送 `file_changed` 与 diff 摘要
- 与 FS Watcher 联动，也可被 Check 节点直接触发

---

## 7. 前端模块与 Prototype 映射

> **任务 ID 与验收**见 [`specs/core/tasks.md`](../specs/core/tasks.md) §Prototype → Task 映射。

| Prototype 组件 | 目标职责 | 主要 Task |
|----------------|----------|-----------|
| `App.tsx` | `ClutchState` 投影；三栏布局；文件预览浮层 | M0-03, M2-11 |
| `App.tsx` footer | Branch / Model / Workflow 状态栏 | M2-08 |
| `Header.tsx` | 工作区面包屑；语言切换（P2） | M2-09 · P2 i18n |
| `sidebar.tsx` | 工作区/历史；REPOSITORIES 树；`data-testid="sidebar-session-{run_id}"` | M2-07, M2-09, D11 |
| `ChatFeed.tsx` | `message` / `validation_result`；人工干预；Stop | M2-01, M2-04, M2-14, M1-03 |
| `RightPanel.tsx` | Overview / Files / Flow / Changes / Terminal | M2-03, M2-11~13, M3-02, M2-02 |
| `RightPanel` Reassign | 「交给 Builder 修复」 | M2-12 |
| `TerminalPanel.tsx` | 子进程日志流 | M2-02 |
| `WorkflowOrchestration.tsx` | Workflow JSON 编辑、校验、保存 | M1-02, M1-06, M1-07 |
| `AgentManager.tsx` | Agent prompt、deliverables、工具绑定 | M4-02, M3-05 |
| `ModelsManager.tsx` | 模型与 Provider 配置 UI | M1-08, M4-04, M4-09 |
| `AiToolsManager.tsx` | Tool Adapter 连接状态 | M4-03 |
| `SkillsRegistry.tsx` | Skills 目录（P2 后端同步） | P2 |
| `McpServerHub.tsx` | MCP 连接配置 | M4-03 |
| `ThemeManager.tsx` | 主题预设（P2 持久化） | P2 |
| `SystemPreferencesModal.tsx` | 设置模态壳 | — |
| `LanguageContext.tsx` | en/zh 文案 | P2 |
| `services/clutchState.ts` | WebSocket store；`setPendingHydrate` 会话恢复 | M0-02, M0-03, D11 |
| `services/runApi.ts` | 会话 API；`fetchRunState` / `fetchSessions` | M2-07, D11 |
| `services/api.ts` | HTTP/编排 API 重导出（去 mock） | M2-06, M2-01, M2-12 |
| `mockData.ts` | 逐步废弃，仅 demo 种子 | M2-06 |

### 7.1 运行模式

> **D10**：仅 **Multi Agent**；单 Agent 模式不开发。Prototype `isMultiAgent` 为历史占位，默认 true。

| 模式 | UI 行为 |
|------|---------|
| **Multi Agent**（唯一） | 完整工作流 + Flow tab + 多角色 Chat |

---

## 8. 数据流（一次完整运行）

```
1. 用户在 Sidebar 选择 Workflow，输入任务描述
2. UI → start_run(workflow_id, instruction)
3. Compiler 加载 Workflow JSON → 构建 LangGraph
4. Orchestrator 节点激活 → state_patch → UI 高亮当前步骤
5. Builder 节点 → CLI Adapter 执行 → log 事件刷屏 Terminal
6. FS Watcher 检测文件变更 → file_changed → Changes tab 更新
7. Evaluator 节点 → check 规则 → validation_result
8. 若 failed → human_gate → human_required → UI 展示干预按钮
9. 用户 Approve → human_decision → 图 resume → passed → run_completed
```

---

## 9. 安全与权限

| 主题 | 策略 |
|------|------|
| API Key | 仅存本地加密存储（Tauri secure store），不经 UI 明文展示 |
| MCP / CLI 权限 | Agent 配置时显式勾选；高危工具（shell、git push）需二次确认 |
| 网络 | Sidecar 默认只监听 `127.0.0.1` |
| 工作区 | 用户显式授权项目根目录，Adapter 不可越界访问 |
| 日志 | 本地落盘，可选脱敏 API Key |

---

## 10. 打包与部署

### 10.1 开发态

```bash
# 终端 1：Python sidecar
cd services/orchestrator && uv run uvicorn src.main:app --reload --port 8123

# 终端 2：Tauri dev
cd apps/desktop && npm run tauri dev
```

### 10.2 发布态

- Tauri 打包 DMG（macOS）/ MSI（Windows）
- Python sidecar 以 embedded Python 或 PyInstaller 一并打入
- 首次启动：健康检查 sidecar → 建立 WebSocket → 加载 UI

---

## 11. 自 Prototype 的迁移路径

| 阶段 | 内容 | 产出 |
|------|------|------|
| **P0** | Sidecar 骨架 + WebSocket + 最小 LangGraph | 替换 `setTimeout` 模拟 |
| **P1** | WorkflowCompiler + React Flow 保存/加载 | 用户可界面编排 |
| **P2** | CLI Adapter + Terminal 真日志 | Claude Code 闭环 |
| **P3** | FS Watcher + Cursor 唤起 + Evaluator | GUI 工具协同 |
| **P4** | MCP Hub 实连 + Agent 配置持久化 | 完整工具链 |
| **P5** | Tauri 打包 + Python 内嵌 | 可分发安装包 |

---

## 12. 关键架构决策记录（ADR）

| ID | 决策 | 理由 |
|----|------|------|
| ADR-001 | Tauri 而非 Electron | 更轻量；编排已在 Python sidecar，Electron 无额外收益 |
| ADR-002 | LangGraph Python 而非 JS | 生态、文档、interrupt/checkpoint 能力更完整 |
| ADR-003 | Workflow JSON + Compiler | 满足零代码；UI 与运行时解耦 |
| ADR-004 | WebSocket 而非轮询 | 日志流与状态跳跃低延迟 |
| ADR-005 | 保留 Vite React 而非 Next.js | 桌面无 SSR 需求，与 Prototype 一致 |

---

## 13. 开放问题（后续迭代）

> **已决策 / 已拆任务**项见 [`memory/DECISIONS.md`](../memory/DECISIONS.md) 与 [`specs/core/tasks.md`](../specs/core/tasks.md)，**不再**重复列于下方。

### 已关闭或已拆入 tasks

| 原问题 | 决策 / 任务 |
|--------|-------------|
| LLM Provider 统一 Router | **D4** → **M1-08** |
| 运行历史持久化 | **D3** → **M2-07**（元数据 `history.json`）+ **D11**（对话 `states/{run_id}.json`） |
| 工作区授权与白名单 | **M2-09** + **M4-05** |
| 子进程崩溃隔离 | **M3-07** |

### 仍开放（MVP 后或未定方案）

- [ ] 多工作区**并行**运行的资源隔离与进程沙箱（单工作区见 M2-09）
- [ ] Workflow 版本管理与回滚 UI
- [ ] 团队协作（工作流导出/导入格式标准化）

---

*本文档随实现进展持续更新。关联文档：[需求提案历史快照](../specs/core/proposal.md) · [开发纪律](../CLAUDE.md) · [文件路径速查](../memory/FILEMAP.md)*
