# Clutch — 系统架构文档

> **This document describes HOW the system works.**  
> Feature descriptions for users belong in [`PRODUCT_INTRO.md`](./PRODUCT_INTRO.md).  
> Acceptance status belongs in [`memory/ROADMAP.md`](../memory/ROADMAP.md).

> **文件路径速查：** 具体「改什么去哪个文件」见 [`memory/FILEMAP.md`](../memory/FILEMAP.md)。下文为设计理由、数据流与 ADR 叙事。  
> **契约类型：** [`packages/shared-types`](../packages/shared-types/index.ts)（`ClutchState`、WebSocket 事件）。  
> **扩展边界：** [`docs/EXTENSIBILITY.md`](./EXTENSIBILITY.md)。

> **版本**: v1.0.0  
> **状态**: 已交付桌面产品（持续迭代）  
> **最后更新**: 2026-06-29

---

## 1. 文档目的

本文档描述 **Clutch** 桌面产品的系统架构与运行时行为，面向产品负责人、开发者（含 AI Agent）与维护者。

**核心事实（避免与早期原型混淆）：**

- 工作流由用户在 **React Flow 画布**上零代码编排，保存为 **Workflow JSON**；内置 `workflows/*.json` 仅为**示例模板**（如 `video-production` 中的 Builder / Evaluator 名称），**不是**系统固定的 Agent 角色。
- 可执行 Agent（提示词、引擎、MCP、Skills）由用户在 **Settings → Agents** 配置，持久化在应用数据目录的 `agents.json`。
- **LangGraph** 是唯一编排 SSOT；React 只投影 WebSocket 推送的 `ClutchState`。

---

## 2. 产品定位与架构约束

### 2.1 产品定位

Clutch 是面向开发者与技术运营人员的 **本地 AI 多 Agent 编排与监督控制台**。用户通过可视化界面定义 SOP 工作流，由系统调度本地 CLI、MCP 服务及 GUI 工具，并在 Chat、Terminal、Diff、Flow 等面板中监督执行，在关键节点进行人工干预。

除工作流模式外，支持 **单 Agent 直连聊天**（选定工作区 + Agent 后直接对话，不经过 Workflow 图）。

### 2.2 架构约束

| 约束 | 说明 |
|------|------|
| 必须桌面端 | 深度访问本地文件系统、子进程、系统应用唤起 |
| LangGraph 为唯一编排引擎 | Python 侧状态机、interrupt、checkpoint |
| 用户零代码 | 工作流与 Agent 均通过 UI 配置，不暴露 LangGraph 源码 |
| React 只读 SSOT | 禁止 `setTimeout` / mock 模拟编排进度 |
| Sidecar 仅本机 | 开发 `localhost:8124`，打包 DMG `localhost:8123`；Bearer + WS token 鉴权 |

---

## 3. 总体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Tauri 2.x Desktop Shell                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │         React 19 UI (Vite + Tailwind 4 + Motion + React Flow)     │  │
│  │  Sidebar │ ChatFeed │ RightPanel │ Settings │ Workflow 编辑器       │  │
│  └────────────────────────────┬──────────────────────────────────────┘  │
│                               │ HTTP + WebSocket (loopback)             │
│  ┌────────────────────────────┴──────────────────────────────────────┐  │
│  │  Tauri Commands（薄层）                                          │  │
│  │  Sidecar 生命周期 │ CLUTCH_SIDECAR_TOKEN │ 系统路径 / 打开 IDE   │  │
│  └────────────────────────────┬──────────────────────────────────────┘  │
└───────────────────────────────┼─────────────────────────────────────────┘
                                │ spawn / supervise PyInstaller binary
┌───────────────────────────────┴─────────────────────────────────────────┐
│                   Python Orchestration Sidecar (FastAPI)                  │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │ REST + WS   │──│  LangGraph   │──│  Workflow   │──│ Engine Router  │  │
│  │ sidecar_auth│  │  (compiled)  │  │  Compiler   │  │ CLI/MCP/Hybrid │  │
│  └─────────────┘  └──────────────┘  └─────────────┘  └────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
   Claude / agy / …         MCP Servers            Workspace FS
   自定义 CLI                 (stdio/SSE)           + Git diff / watcher
```

### 3.1 分层职责

| 层级 | 职责 | 不应承担 |
|------|------|----------|
| **Tauri Shell** | 窗口、打包、Sidecar 启停、注入 session token | 业务编排、LLM 调用 |
| **React UI** | 展示、工作流/Agent 编辑、人工决策上报 | 直接执行 CLI / 读盘 |
| **Python Sidecar** | LangGraph 运行时、状态持久化、工具调度、事件广播 | UI 渲染 |
| **Adapters / Router** | 统一封装 CLI、MCP、Hybrid Shell、LLM Provider | 工作流图拓扑逻辑 |

---

## 4. 技术选型

| 类别 | 选型 | 理由 |
|------|------|------|
| 桌面宿主 | **Tauri 2.x** | 轻量；Rust 侧进程管理可靠 |
| 前端 | **React 19 + Vite** | 桌面无 SSR；与 UI 规范一致 |
| 样式 / 动效 | **Tailwind CSS 4 + Motion** | 见 [`docs/UI_UX_GUIDELINES.md`](./UI_UX_GUIDELINES.md) |
| 工作流画布 | **@xyflow/react** | 拖拽编排、导出 Workflow JSON |
| 编排服务 | **FastAPI** | 异步、WebSocket、与 Python AI 生态一致 |
| 状态机 | **LangGraph** | 条件边、interrupt、checkpoint |
| LLM | **可配置 Provider Router** | DeepSeek / OpenAI / Anthropic / Ollama / 自定义 |
| 实时通道 | **WebSocket** | `state_patch`、日志流、Chat、hybrid_execution |
| 凭证（macOS） | **Keychain**（`keyring`） | Provider API Key 不落盘 `models.json`（OSR-13） |

未采用 Electron+LangGraph.js、Next.js、纯 Web、用户手写 LangGraph 等原因见历史 ADR（§12）。

---

## 5. 仓库结构（当前）

```
clutch/
├── apps/desktop/              # Tauri + React（唯一前端源码根）
│   ├── src/                   # 组件、clutchState store、API 客户端
│   └── src-tauri/             # Sidecar 二进制嵌入、token 注入
├── services/orchestrator/     # Python Sidecar（唯一后端业务根）
│   └── src/
│       ├── main.py            # FastAPI 入口
│       ├── compiler/          # Workflow JSON → LangGraph
│       ├── orchestrator/      # 图边路由（非「总控 Agent」）
│       ├── engine_router.py   # Agent → CLI / LLM / Hybrid
│       ├── agent_storage.py   # 用户 Agent 持久化
│       └── workflow_storage.py
├── packages/shared-types/     # ClutchState、WS 事件 TypeScript 契约
├── workflows/                 # 内置模板 + workflow.schema.json（非用户数据）
└── docs/                      # 架构、安装、开源排期等
```

**解耦：** `apps/desktop` 与 `services/orchestrator` 仅经 loopback HTTP/WS 通信。开发时 Vite 代理 `/api`、`/ws` → `8124`；打包后 WebView 直连 `8123`。

---

## 6. 核心子系统

### 6.1 工作流：用户定义，非固定角色流水线

#### 6.1.1 两层存储

| 来源 | 路径 | 说明 |
|------|------|------|
| **内置模板** | 仓库 `workflows/*.json` | 示例 SOP；随 DMG/源码分发，只读种子 |
| **用户工作流** | `~/Library/Application Support/clutch/workflows/{id}.json` | UI 保存/导出；**同 id 覆盖模板** |

加载入口：`workflow_storage.resolve_workflow(workflow_id)` — 用户目录优先，否则回退模板。

#### 6.1.2 UI 节点类型（Schema 权威）

[`workflows/workflow.schema.json`](../workflows/workflow.schema.json) 定义五种节点：

| `type` | 用户可见用途 | 编译后行为 |
|--------|--------------|------------|
| `start` | 入口（虚拟） | 图入口；`source: "start"` 边 |
| `agent_task` | 执行一步 Agent 任务 | 解析 `data.agent` → 用户 Agent 配置 → `execute_agent_task` |
| `check` | 自动检查 | `file_exists` / `shell` / `lint` 规则列表（**非**固定 Evaluator 智能体） |
| `human_gate` | 等我确认 | LangGraph `interrupt`；等待 `human_decision` |
| `end` | 结束 | 图出口 |

`agent_task.data` 关键字段：

- **`agent`** — 用户 Agent 的 `id` 或 `name`（经 `engine_router.find_agent` 解析）
- **`instruction`** — 本步任务说明（可与上游 `node_outputs` 拼接）
- **`tool`** — 可选，覆盖 Agent 默认引擎

> **关于 Builder / Evaluator / Orchestrator 字样：** 仅出现在早期演示模板与 Chat UI 的**展示角色枚举**（`AgentRole`）中。运行时 Chat 气泡的 `agent` 字段来自**当前步骤绑定的用户 Agent 名称**，或检查失败时的系统摘要标签（如 `"Evaluator"` 用于 validation 卡片）。系统**没有**内置不可删除的 Builder 或 Evaluator Agent。

#### 6.1.3 典型用户自定义图（概念）

```
[Start]
   │
   ▼
[Agent: 我的调研助手]  ──►  [Check: pytest]
                              ╱              ╲
                        passed              failed
                          ╱                    ╲
                    [End]              [Human Gate]
                                          ╱    │    ╲
                                    approve reject retry
                                       │      │      │
                                    [End] [上一步 Agent] [带补充指令重跑]
```

边分支键 `edge.data.when`：`passed` / `failed`（来自 `check`）、`approve` / `reject` / `retry`（来自 `human_gate`）。

#### 6.1.4 WorkflowCompiler

```
Workflow JSON
    ├─► Schema / 结构校验（workflow_validator）
    ├─► 节点 type → 处理器（compiler/compiler.py）
    ├─► 出边 → route_next（边优先，可选 LLM fallback）
    ├─► human_gate → interrupt_before
    └─► 输出 CompiledGraph（按 workflow 实例编译，可缓存）
```

编译与执行代码由维护者演进；用户只编辑 JSON / 画布。

---

### 6.2 Agent 配置（用户定义执行单元）

| 项 | 说明 |
|----|------|
| 存储 | `Application Support/clutch/agents/agents.json` |
| 内置 | `clutch-agent`（`Clutch Agent`）— 单聊默认 |
| 字段 | `markdownDoc`（系统提示）、`deliverables`、`mcpServerIds`、`skills`、`agentType` |
| 引擎 | 由 `agentType` + `engine_router` 解析为 Claude CLI、agy、LLM Provider、Hybrid Shell 等 |

工作流中的 `agent_task` **引用** Agent 配置，不在工作流 JSON 内嵌完整 Prompt。检查节点（`check`）按 **D6** 使用节点上的 `checks` 数组，不由独立 Evaluator Agent 配置驱动（与早期原型 mock 不同）。

Settings UI：`AgentManager.tsx` · API：`/api/agents/*` · 后端：`agent_storage.py`、`agent_executor.py`。

---

### 6.3 图路由模块（`orchestrator/routing.py`）

名为 **Orchestrator** 的代码包表示 **工作流边路由**，不是 Chat 里的一个固定大模型角色：

1. 从当前节点读取 LangGraph / `CompilerState`
2. **优先**按 Workflow JSON 的 `edges` + `when` 解析下一跳（`route_next` → `resolve_from_edges`）
3. 条件边缺省信号时，可选 LLM 建议下一分支（fallback）
4. 路由结果驱动 LangGraph 条件边，并经 `state_patch` 同步 `active_node_id` / `active_agent` 到前端

`active_agent` 是 **UI 高亮用显示名**（通常为用户 Agent 的 `name`），不是硬编码角色表。

---

### 6.4 ClutchState（全局运行状态）

**权威定义：** [`packages/shared-types/index.ts`](../packages/shared-types/index.ts) 中的 `ClutchState`。

要点：

| 字段 | 含义 |
|------|------|
| `run_id` / `workflow_id` | 运行与会话标识；单聊时 `workflow_id` 可为空 |
| `active_node_id` / `active_agent` | 工作流当前步骤（Flow 面板高亮） |
| `status` | `running` · `failed` · `passed` · `awaiting_human` · `refining` · `idle` |
| `messages` | ChatFeed 消息列表 |
| `terminal_logs` | Terminal 审计行 |
| `changed_files` | Changes / Diff |
| `cli_session_id` / `cli_session_agent_id` | CLI 多轮会话恢复 |
| `hybrid_executions` | Hybrid 模式结构化输出（按 message id） |
| `refining_*` | 人工闸门 Refine 草稿与节点 |

持久化：`states/{run_id}.json`；侧栏元数据：`sessions/history.json`（见 §6.6）。

---

### 6.5 执行引擎（Engine Router + Adapters）

`engine_router.py` 根据 Agent 记录与工具可用性选择执行路径：

| 路径 | 场景 |
|------|------|
| **LLM Provider** | `agentType` 为 clutch / 纯模型对话 |
| **CLI Adapter** | `claude`、`agy`、`codex`、`aider` 等子进程 |
| **Hybrid Shell** | `CLUTCH_RUNTIME_MODE=hybrid` — 长驻 PTY + `SHELL_EXEC`（见 `specs/core/hybrid-runtime-plan.md`） |
| **MCP** | Agent 绑定的 MCP Server 工具（ReAct 循环） |

日志经 `run_log_forwarder` → WebSocket `log` / `message`；文件变更经 FS watcher → `file_changed`。

---

### 6.6 实时事件协议（WebSocket）

#### 连接

- 地址：`ws://127.0.0.1:{port}/ws/runs/{run_id}?token=...`
- 鉴权：Tauri 启动生成 `CLUTCH_SIDECAR_TOKEN`；HTTP `Authorization: Bearer`（OSR-08）
- 开发端口 **8124**；打包 **8123**

#### 信封

```json
{
  "event": "state_patch",
  "data": {
    "run_id": "run_xxx",
    "timestamp": "2026-06-29T10:00:00Z",
    "patch": { "active_node_id": "n2", "status": "running" }
  }
}
```

#### 主要事件

| event | 用途 |
|-------|------|
| `state_patch` | 部分 `ClutchState` 更新 |
| `message` | 新 Chat 消息 |
| `hybrid_execution` | Hybrid 结构化输出挂载到消息 |
| `log` | Terminal 行 |
| `file_changed` | 工作区变更 |
| `validation_result` | 检查节点结果摘要 |
| `human_required` | 进入人工闸门 |
| `run_completed` | 运行结束 |

#### 客户端动作（节选）

| 动作 | 说明 |
|------|------|
| 纯文本 | 无工作流时单 Agent / LLM 聊天 |
| `start_run` | 指定 `workflow_id` + 指令 |
| `human_decision` | `approve` / `reject` / `retry` + 可选补充指令 |
| `stop_run` | 取消运行与子进程 |

---

## 7. 前端模块（当前职责）

| 模块 | 职责 |
|------|------|
| `App.tsx` | 三栏布局；`ClutchState` 投影；工作区 / 工作流 / Agent 选择 |
| `sidebar.tsx` | 工作区、历史会话、仓库树 |
| `ChatFeed.tsx` / `ChatInputBar.tsx` | 消息流、人工闸门、Stop、@提及 |
| `RightPanel.tsx` | Overview · Files · **Flow** · Changes · Terminal |
| `WorkflowOrchestration.tsx` | 用户工作流画布编辑、校验、保存 |
| `AgentManager.tsx` | 用户 Agent CRUD |
| `ModelsManager.tsx` | Provider / 模型 / Key（Keychain 由 Sidecar 管理） |
| `McpServerHub.tsx` / `AiToolsManager.tsx` | MCP 与工具连接状态 |
| `services/clutchState.ts` | WebSocket store、hydrate、patch 合并 |
| `services/sidecarUrl.ts` | loopback URL + token |

任务 ID 与历史验收见 [`specs/core/tasks.md`](../specs/core/tasks.md)；**不再**以 Prototype 组件名为架构主轴。

---

## 8. 数据流（一次工作流运行）

```
1. 用户选择工作区 + Workflow（或新建并保存用户 Flow）
2. 输入任务描述 → start_run(workflow_id, instruction)
3. resolve_workflow → compile_workflow → LangGraph.invoke
4. 各 agent_task：find_agent → engine_router → CLI/MCP/LLM → message + log 事件
5. check 节点：evaluate_node_data(checks) → passed/failed 分支
6. failed → human_gate → interrupt → human_required → UI 按钮
7. 用户 Approve / Retry → resume → 直至 end → run_completed
8. 全程 _commit_run_state → states/{run_id}.json + history.json
```

单 Agent 聊天省略步骤 3–7 的图遍历，直接 `engine_router` 对话，仍写入同一 `ClutchState` 持久化模型。

---

## 9. 安全与权限

| 主题 | 策略 |
|------|------|
| API Key | macOS **Keychain**（`com.clutch.app`）；`models.json` 仅存模型元数据（OSR-13） |
| Sidecar | `127.0.0.1` + session token；`/health` 公开 |
| 工作区 | 用户授权根目录；Adapter 路径校验（`workspace` 白名单） |
| CLI | 部分适配器使用 `--dangerously-skip-permissions`（**D30**，见 README / SECURITY） |
| MCP | 用户显式配置 Server；高风险工具门控与 `permission_mode` 偏好 |
| 日志 | 本地落盘；禁止写入密钥 |

---

## 10. 打包与部署

### 10.1 开发

```bash
# 终端 1：Sidecar
cd services/orchestrator && uv run uvicorn src.main:app --reload --port 8124

# 终端 2：Tauri（Hybrid 示例）
export CLUTCH_RUNTIME_MODE=hybrid && pnpm tauri:dev
```

### 10.2 发布

- GitHub Release：**未签名 DMG**（D31）+ `SHA256SUMS.txt`；Gatekeeper 说明见 `docs/INSTALL.md`
- Sidecar：PyInstaller 打入 `src-tauri/binaries/`，Tauri 拉起并注入 token
- 版本：**1.0.0** semver；`CHANGELOG.md` 随 tag 维护

---

## 11. 实现状态（相对早期路线图）

| 能力 | 状态 |
|------|------|
| Sidecar + WebSocket + LangGraph | ✅ 生产路径 |
| 用户 Workflow 编辑 / 保存 / 覆盖模板 | ✅ |
| 用户 Agent 配置 + 多引擎路由 | ✅ |
| CLI + MCP + FS Watcher | ✅ |
| Hybrid Runtime（PTY 会话） | ✅ 代码交付；`CLUTCH_RUNTIME_MODE=hybrid` |
| Tauri 打包 + Release CI | ✅ v1.0.0 |
| Keychain 凭证 | ✅ OSR-13 |
| Apple 签名 / 公证 | ⏭️ D31 豁免 |
| 首次启动向导 | ✅ OSR-14 |
| Windows MSI | ❌ OSR-19 |

---

## 12. 关键架构决策（ADR 摘要）

| ID | 决策 | 理由 |
|----|------|------|
| ADR-001 | Tauri 而非 Electron | 轻量；编排已在 Python |
| ADR-002 | LangGraph Python | interrupt / checkpoint 生态 |
| ADR-003 | Workflow JSON + Compiler | 零代码；UI 与运行时解耦 |
| ADR-004 | WebSocket 推送状态 | 日志与状态低延迟 |
| ADR-005 | 用户 Agent 与工作流分离 | 同一 Agent 可被多 Flow 复用 |
| ADR-006 | 模板仅为示例 | 产品能力是**任意**用户自定义 Flow，非固定三四角色流水线 |

开放问题与已关闭项见 [`memory/DECISIONS.md`](../memory/DECISIONS.md)；开源排期见 [`docs/OPEN_SOURCE_RELEASE.md`](./OPEN_SOURCE_RELEASE.md)。

---

*关联文档：[`docs/PRODUCT_INTRO.md`](./PRODUCT_INTRO.md) · [`CLAUDE.md`](../CLAUDE.md) · [`memory/FILEMAP.md`](../memory/FILEMAP.md)*
