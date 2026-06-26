# Clutch — 本地 AI 多 Agent 编排与监督控制台

## 1. 产品定位与核心价值

**Clutch** 是一款面向独立开发者、技术运营人员以及 AI 工作流与自动化搭建者的桌面应用。它提供了一个 **可视化、零代码的 SOP（标准作业程序）工作流编排与运行控制台**。

通过 Clutch，用户可以在画布上定义任意的多 Agent 协作工作流，由系统动态调度本地多种 AI 引擎（各种本地 CLI 工具、MCP 服务及远程/本地大语言模型）执行，并在统一的 IDE 级控制台中全程监督执行过程、进行人工审批与干预决策。

### 1.1 核心价值主张
- **通用多 Agent 画布编排 (Generic Multi-Agent Orchestration)**：用户通过可视化拖拽连线定义工作流，支持在各节点灵活指定不同的 Agent 角色与任务说明，运行时由编排引擎自动编译为 LangGraph 状态机并处理输入输出接力。
- **本地工具生态打通 (Local AI Tool Integration)**：自动扫描本地开发环境并无缝接入各种主流的本地 AI 命令行工具（CLI，如 Claude Code, Aider, Ollama 等）及 macOS 客户端，打破云端与本地的边界。
- **全流程透明监督 (Console Observability)**：打破 AI 执行的“黑盒”，在统一的控制台界面中展示多角色 Chat 流、流式子进程终端日志、Git 代码变更与 Diff、Flow 进度图以及工作区文件树。
- **人机协同门控 (Human-in-the-Loop)**：在关键检查失败或敏感操作节点，图会自动挂起，由人类进行 Approve（批准强制通过）、Reject（打回）或 Retry（带补充指令重试）。
- **本地优先 (Local First)**：应用完全运行于本地，API Key 仅存于本地安全存储中，敏感的工作区数据与开发日志不会外泄。

### 1.2 真实痛点（本项目的存在理由）
如果仅仅是想生成代码，直接使用 Claude Code / Cursor 裸跑就够了，不需要这套工作台。Clutch 旨在解决以下两个真实的工程化场景痛点：

#### 痛点一：单 Agent 模式下，上下文容易“炸”，新开对话又会丢失上下文
- **典型场景**：在验收阶段发现一堆 Bug，让 Agent 修复，来回修改了几轮后，对话窗口里堆满了“旧代码 + 新代码 + 历次对话”，大模型开始出现记忆混乱、丢失指令的情况，甚至在修 Bug 的过程中顺手把既有需求也悄悄改了一点而不自知。如果对臃肿的会话无法忍受而新开一个对话，之前积累的所有上下文（对需求的理解、避坑经验、已经达成的共识）又会全部丢失，导致每次要么硬撑一个越来越庞大臃肿的单一会话，要么被迫从零重新向模型对齐。
- **Clutch 架构解法**：**State 跨会话持久化与版本化/分段管理**。系统不采用无差别重放全部历史的臃肿模式，而是将每一步的产出和决策记录成结构化的 State，在需要时按需调取相关片段，而不是无差别地把全部历史灌给模型。

#### 痛点二：多 Agent 协作能跑起来，但过程黑盒、产物难找、流程难改
- **典型场景**：在开发复杂本地 SOP 时，即使手动搭过一套多 Agent 协作逻辑（例如：协调者、执行者、视频审核者、需求变更后的代码复核者），且已经在 Claude Code 里实现了 Agent 之间的相互调用，但因为全部跑在同一个对话窗口里，会带来三个具体不便：
  1. **Agent 之间的交互过程不可视**：谁在跟谁说话、说了什么、为什么这么判断，只能看到最终结果，看不到协作过程；
  2. **中间产物分散在文件系统里**：每个 Agent 生成的东西（如中间测试报告、处理过的媒体资源），都得自己手动去翻文件寻找，没有统一的资产视图；
  3. **工作流本身难以编辑**：流程逻辑是隐式写在 prompt 或硬编码的调用关系里的，想要增加一个节点、调整一下审核顺序，修改起来非常不直观。
- **Clutch 架构解法**：**State 流转可视化、中间产物统一收集展示与工作流显式配置**。提供基于 React Flow 的执行状态大盘，统一收集并在 Changes/Overview 选项卡中直观展示中间资产，同时将 Coordinator 的路由规则做成显式可配置的图节点与连线，而非隐藏在 prompt 中。

> **核心增量价值**：
> Clutch **不是**替代 Claude Code / Cursor 的生成能力，而是在其之上加一层**“可持久化、可观测、可编辑”的流程控制层**，解决多轮迭代和多 Agent 协作场景下的工程化短板。

### 1.3 明确不做什么 (Non-Goals)
- **不做云端部署**：专注于个人本地私有化环境，保障源码与商业秘密不出本地。
- **不做多租户团队协作**：定位为个人 / 一人团队场景下的本地开发与编排提效工具，不做协作分享后台。
- **不追求重新实现底层模型能力**：专注做流程编排与可观测性控制层，模型生成能力完全桥接和调度现有的本地/云端大模型与本地 CLI。

---


## 2. 系统架构概览

Clutch 采用 **前端界面交互与后端编排引擎物理隔离、本地 loopback 通信** 的设计：

```mermaid
graph TD
    subgraph Tauri_Desktop_Shell [Tauri 桌面宿主]
        UI[React UI 前端]
        Tauri_Cmd[Tauri Native Commands]
    end

    subgraph Python_Orchestrator_Sidecar [Python Sidecar 编排引擎 :8123]
        FastAPI[FastAPI REST / WS API]
        LangGraph[LangGraph 状态机运行时]
        Compiler[Workflow Compiler]
        Engine_Router[Engine Router]
        Adapters[Tool/CLI Adapters]
    end

    UI <-->|WebSocket / HTTP| FastAPI
    Tauri_Cmd -->|Spawn / Supervise| Python_Orchestrator_Sidecar
    Engine_Router -->|路由分流| Adapters
    Adapters -->|本地执行| CLI_Tools[本地 CLI 命令行工具 (Claude, Aider, Ollama, agy...)]
    Adapters -->|唤起应用| Cursor_App[Cursor 等本地桌面应用]
    Adapters -->|模型 API| Cloud_Local_LLMs[云端模型 / 本地 Ollama API]
```

1. **前端 (React 19 + Tailwind CSS 4 + Motion + React Flow)**：提供高保真三栏式工作台，负责工作流可视化编辑、运行态投影渲染及捕获用户人工审批决策。
2. **后端 (FastAPI + LangGraph Python Sidecar)**：运行于 `localhost:8123`，作为唯一的真理源 (SSOT) 控制状态跳转。`WorkflowCompiler` 将画布导出的 JSON 动态编译成 LangGraph 可执行图。
3. **通信机制**：前后端通过 WebSocket 实时更新全局状态 `ClutchState`（采用 `state_patch` 增量推送）。

---

## 3. 核心功能特性

### 3.1 通用可定制 Agent 系统
Clutch 不限制或固化 Agent 的角色名称，而是提供了一个完全通用的自定义 Agent 机制：
- **Agent 自定义配置**：用户可通过 UI 自由创建、编辑或删除 Agent（配置持久化存储于 `agents.json`）。支持配置 Agent 的名称、头像、描述、系统提示词（`markdownDoc`）、绑定的模型（`modelId`）、期望交付产物（`deliverables`）以及关联的 MCP 服务器与 Skills。
- **内置 Agent**：系统提供默认的 `clutch-agent`（内置 Clutch Agent）作为通用垫底 Agent。
- **工作流节点绑定**：画布上的 `agent_task` 节点可选择任意自定义或内置的 Agent，编译后节点会自动读取对应 Agent 的属性与提示词，动态调用底层模型进行任务处理。
- **自动输入输出接力 (Handoff)**：节点激活时自动解析上游。若上游是另一个 Agent 任务节点，系统会自动将该上游节点的 `node_outputs` 作为输入上下文接力注入到当前节点的输入中，从而跑通链式多 Agent 协作流。

### 3.2 本地 AI 工具自动扫描与探测
系统启动时，后端 `tools_status.py` 会自动扫描用户本地的系统 `PATH` 以及 Brew、NPM、NVM 等常用工具目录，智能探测已安装的 AI 工具：
- **CLI 命令行工具探测**：支持自动扫描 `claude` (Claude Code CLI), `agy` (Antigravity CLI), `codex` (OpenAI Codex CLI), `aider` (Aider), `ollama` (Ollama CLI), `cursor` (Cursor CLI), `code` (VS Code CLI), `codeium` (Codeium CLI), `gemini` (Gemini CLI) 等工具的可执行路径。
- **macOS 客户端探测**：支持探测 `/Applications` 及 `~/Applications` 下的桌面客户端软件（如 `Cursor.app`）。
- **配置与连接状态**：探测出的工具会在前端 AI Tools 界面统一呈现其安装类型（CLI 或 Client）、二进制可执行绝对路径以及连接启用状态。

### 3.3 多引擎智能路由与 Session 恢复
在执行任务或普通对话时，编排引擎中的 `EngineRouter` 会根据 Agent 配置的 `agentType` (或 legacy 字段 `aiEngine`) 及本地工具的探测可用状态，进行智能路由分流：
1. **本地 CLI 适配器路由**：
   - 如果 Agent 属性配置为 `claude-cli`、`antigravity-cli` 或 `ollama-cli`，且本地探测到相应 CLI 二进制，路由将任务直接下发至对应的本地 CLI 子进程执行。
   - **CLI 会话恢复机制 (Session Resume)**：特别针对 `claude-cli`（使用 `--resume <session_uuid>`）与 `antigravity-cli` 实现了 Session 缓存与绑定。在多轮交互中，直接恢复原有子进程上下文而无需重放历史全文，极大节约了 Token 开销并降低了网络延迟。
2. **GUI 客户端唤起**：
   - 如果 `agentType` 配置为 `cursor-workspace`，系统可直接在本地通过 `open -a Cursor` 唤起 Cursor 桌面端并打开当前工作区，实现 GUI 级别的人机无缝流转。
3. **全局 LLM 模型路由 (`clutch`)**：
   - 路由至用户配置的云端或本地模型 API（如 OpenAI, DeepSeek, 智谱 GLM 等）。
   - **本地 Ollama 自动发现与打分排序**：对于本地 `Ollama` 驱动，系统会自动向本地 `11434` 端口发起探测，自动发现用户本地的所有已下载模型，并通过内置的打分排序算法（评估模型代码能力与推理能力）优先推荐最合适的模型（如 `qwen3.6`），支持在无 Key 时直接一键激活使用。
   - **生图/视觉模型适配**：针对生图/视觉模型进行特殊判定。若是生图模型（如 `Agnes Image`），输入时会自动走生图路由并回显图片产物；若向仅能生图的非视觉模型上传图片，系统会自动拦截并进行友好提示。
4. **智能降级回退 (Fallback)**：
   - 若 Agent 设定了特定的本地 CLI 类型但本地未检测到该工具，路由系统会自动将任务降级回退至 `clutch` 全局 LLM 引擎执行，并在 Terminal 日志中输出明确的 Fallback 审计警示。

### 3.4 虚拟 MCP 服务器与 Codex 文件补丁
- **虚拟 MCP 客户端 (`clutch-tools`)**：当 Agent 访问本地文件系统（`local-fs`）时，Sidecar 会动态挂载该内置虚拟 MCP 服务。
- **`apply_patch` 精密文件工具**：提供 Codex 语法兼容的文件打补丁工具（支持 Add, Delete, Update, Move 动作），使模型可以通过标准的 diff 或指令精密增删改移本地文件，避免了传统模型缺乏删除文件 API 而导致的工作区垃圾残留。
- **安全门控 (mcp_risk)**：涉及删除、修改工作区代码文件的高风险 MCP 动作会在 Sidecar 侧被自动判定，拦截并强制推送为 `human_required` 人工决策，必须经由 Supervisor 审批同意后方能真正对磁盘应用变更。

### 3.5 多语言 (i18n) 与凭证导入
- **多语言双语对照**：支持中英文（zh/en）切换。后端通过 preferences 动态加载语言偏好，在 API/WebSocket 的异常捕获、干预提示上使用 `tr()` 响应，且完全兼容既有测试断言。
- **凭证自动导入**：支持自动读取 `~/.cc-switch/cc-switch.db` SQLite 数据库，无感导入用户在第三方工具中配置的模型 API Keys，免去繁琐的手动配置过程。

---

## 4. 内置 SOP 模板

Clutch 默认打包了以下经典 SOP 工作流模板，位于 `workflows/` 目录：

- **Video Production (视频生产)**：适用于流水线式的视频素材处理、文案生成、评估校验及人工确认发布。
- **Weather to Vision (天气插画接力)**：
  - **节点 1 (Researcher / 天气情报官)**：分析用户请求，调研并产出包含天空、光影、氛围的场景描述。
  - **节点 2 (Artist / 视觉艺术家)**：绑定生图模型（如 Agnes Image），自动读取并接力上游的描述文本，最终生成一张高质量插画。
  - **节点 3 (End / 结束)**。

---

## 5. 本地运行与构建指令

### 开发期启动 (Dev)
```bash
# 终端 1：启动 Python Sidecar (端口 8123)
cd services/orchestrator
uv run uvicorn src.main:app --reload --port 8123

# 终端 2：启动 Tauri 前端
cd apps/desktop
pnpm dev
```

### 本地轻量校验 (Pre-commit)
在提交代码前运行轻量校验，确保编译通过、单元测试正常、文档未产生漂移：
```bash
./scripts/verify.sh
```

### 全量 E2E 校验 (Push 前)
运行完整 Tauri-Playwright GUI 自动化测试：
```bash
./scripts/verify.sh --e2e
```

### 桌面端打包 (Build DMG)
```bash
pnpm tauri build
```
编译打包成功后，生产版会自动内嵌 Sidecar Python 运行环境，输出双击可安装的 `.dmg` 桌面应用程序。

---

*本文档基于最新的前后端实现编写。关联架构设计详述见 [系统架构文档](file:///Users/fancy/clutch/docs/ARCHITECTURE.md)；文件定位见 [FILEMAP.md](file:///Users/fancy/clutch/memory/FILEMAP.md)。*
