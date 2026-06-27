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
- **Clutch 架构解法（现状与路线图）**：
  - **当前已实现**：支持基础的 **State 跨会话持久化与恢复**（`states/{run_id}.json`）以及针对 CLI 引擎的 **Session 恢复机制**（通过 `--resume <session_uuid>` 避免重复向命令行终端灌入全部历史），以此优化 Token 开销。
  - **后续路线图规划**：正在规划 **State 分段管理、上下文压缩归档与物理回滚** 机制。将在 prompt tokens 消耗达临界值时自动对中间的冗长工具调用与思考进行折叠摘要压缩，仅保留当前上下文相关的 State 片段送入模型，而非无差别重放。

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

本节所列特性为**当前项目前端与后端已完全实现并验证**的真实功能与系统架构，不包含任何模拟（Mock）或占位数据：

### 3.1 可视化多 Agent 画布与自动接力 (Visual Multi-Agent Canvas & Auto-Handoff)

提供基于 React Flow 的通用工作流编排画布，由后端 LangGraph 状态机引擎提供执行支撑。

```
+--------------------------------------------------------------+
| [ Researcher ] ------( node_outputs )------> [ Artist ]       |
| (Type: custom)                               (Type: AgnesImg)|
+--------------------------------------------------------------+
```

* **通用 Agent 自定义**：支持用户自由创建、修改 Agent 提示词、绑定模型和 MCP 工具，配置持久化于本地 `agents.json`。
* **节点自动输入输出接力 (Handoff)**：工作流节点在被激活运行时，会自动解析其所有上游节点的输出 `node_outputs`，并作为当前节点的输入上下文进行自动注入，实现多角色、流水线式的链式智能体协作。

### 3.2 人机协同门控与高风险命令审批 (Human-in-the-Loop Gate & High-Risk Tool Approval)

保障 Agent 代码改动和命令行执行的安全审计防线。

```
+-------------------------------------------------------------+
| ⚠️ Human Approval Required                                    |
| Command: git add . && git commit -m "update"                |
| High-Risk Actions: Write files to workspace                 |
|                                                             |
|   [ Approve (✓) ]     [ Reject (✗) ]     [ Retry (↺) ]       |
+-------------------------------------------------------------+
```

* **文件打补丁审批**：当 Agent 试图使用 Codex 兼容的文件编辑器工具（`apply_patch`）对本地项目代码进行增、删、改、移时，Sidecar 引擎（通过 `mcp_risk.py` 判定）会自动拦截并挂起图运行。
* **协同门控动作**：在前端弹出的审批卡片中，用户可点击 **Approve**（确认并运行）、**Reject**（回退打回）或 **Retry**（输入补充提示词强制模型重写）。

### 3.3 本地 AI 工具探测与多引擎智能路由 (Local AI Tools Autodiscovery & Multi-Engine Router)

自动打通本地开发工具链并智能路由模型请求。

```
+--------------------------------------------------------------+
| AI Tools Status                                              |
|  [✓] Claude CLI       (/opt/homebrew/bin/claude)  [Connected]|
|  [✓] Antigravity CLI  (/usr/local/bin/agy)        [Connected]|
|  [✗] Ollama CLI       (Not found in PATH)         [Offline]  |
+--------------------------------------------------------------+
```

* **本地二进制文件扫描**：应用启动时自动扫描环境变量 `PATH` 以及 Brew/NPM 等路径，探测本地已安装的 `claude` (Claude Code)、`agy` (Antigravity CLI)、`aider`、`ollama` 等可执行文件，结果存于 `tools.json`。
* **智能路由与逻辑 Session**：`EngineRouter` 根据 Agent 的引擎类型智能分流。如分发给本地 CLI 时，会启动子进程并利用 `--session-id` 或 `--conversation` 参数实现会话上下文物理恢复，以节省重放的 Token 成本。非 CLI 引擎时，则直接路由至本地 Ollama 实例或云端 LLM API。

### 3.4 IDE 级全流程透明监督控制台 (IDE-grade Observability Workbench)

打破大模型后台运行的黑盒状态，让执行轨迹完全透明化。

```
+--------------------------------------------------------------+
| [Sidebar] |  [Chat Feed]                 | [Right Panel]     |
| Sessions  |  Orchestrator: Thinking...   |   Overview        |
|  - Run 1  |   - User: Hello!             |   Files           |
|  - Run 2  |   - SmartToy: I am processing| > Terminal Logs   |
|           |                              |   Changes (Diff)  |
+--------------------------------------------------------------+
```

* **Chat Feed 区域**：支持展示多 Agent 在编排或单聊模式下，以各自专属头像与名称输出的历史聊天气泡。
* **Terminal 终端审计日志**：右侧面板实时展示子进程中 CLI 工具运行产生的标准输出和标准错误日志（Stdout/Stderr），用户能看到 Agent 究竟敲了什么命令。
* **Changes 红绿代码 Diff 追踪**：实时捕获并高亮显示工作区文件系统的每一次具体代码行变动。

### 3.5 个人账号偏好与资料配置 (Personal Settings & Preference Dashboard)

提供用户个性的个性化展示与系统运行配置。

```
+--------------------------------------------------------------+
| System Preferences                                           |
|  [ General ]   Avatar: [Change Photo]                        |
|  [ AI Tools ]  Profile Name: [ Fancy User                  ] |
|  [ Themes  ]   Language: [中文/English  ]                    |
+--------------------------------------------------------------+
```

* **个人姓名与头像自定义**：支持在通用设置中上传本地照片（转换为 Base64 持久化）作为用户聊天气泡的头像，支持设定个性化名称以替代默认的 "User" 发送者标签。
* **多语言与系统主题**：支持中英文（zh/en）双语翻译与对照切换；支持在 `pristine-light`、`nordic-frost`、`amber-warm` 配色预设中一键切换桌面环境的主题。
* **本地应用版本检测**：右下角动态调用 Tauri 插件接口读取当前桌面版应用的真实版本号（非 Tauri 环境下安全降级回显 `0.0.0`）。
* **会话级偏好记忆**：自动按 `sessionRunId` 使用 `localStorage` 记录和还原用户在此会话历史中最后选定的单/多 Agent 模式、所选工作流 ID 及 Agent ID。

---

## 4. 规划中特性 (Future Roadmap)

以下特性来源于 **Backlog (候选需求池)**，是针对未来阶段的深度优化与升级规划：

### 4.1 智能主控与任务自愈 (Smart Dispatcher & Self-Healing)
* **需求智能匹配分派**：大模型根据用户的自然语言输入，自动判定应启动哪个已有的工作流 SOP，并提炼出第一步的指导提示，免去手动查找启动的繁琐。
* **图内运行错误自愈**：在 Agent 编写代码出现语法或运行报错时，直接读取错误日志和编译器诊断结果回灌至 Agent 编排流中，让大模型自动尝试排查并编写修复代码，降低人工审批打回的频次。

### 4.2 精细化命令安全拦截与沙箱防护 (Fine-grained Permissions & OS Sandbox)
* **细粒度命令审批策略**：支持用户配置规则，如对 `git` 提交直接无感放行，但对涉及编译执行或疑似敏感修改的指令保持“询问”状态。
* **安全目录 Glob 限制**：设定文件夹路径读写白名单（如仅允许 Agent 操作 `./src`，禁止访问系统盘），若超出边界则在前端弹出临时权限扩权申请。
* **OS 级虚拟沙箱隔离**：深入技术调研，通过容器或 OS 底层沙箱技术（如 Linux Bubblewrap / Windows 隔离 Sandbox）将 Agent 的物理子进程锁死，防范恶意命令破坏系统。

### 4.3 交互体验与效率机制升级 (UX & Efficiency Upgrades)
* **审批行内红绿 Diff 预览**：在用户确认 Approve/Reject 的弹窗卡片中直接嵌入代码改动的红绿对比展示，无需手动切换右侧 Changes 选项卡。
* **代码流式增量补丁推送**：当大模型在后台极快写代码时，通过 WebSocket 增量、流式地将代码 diff 过程在聊天区更新渲染，避免长时卡顿等待。
* **API 真实 Token 成本追踪**：更精准地捕获和累加单次运行中所消耗的大模型真实 Token（包含缓存命中状态），便于用户监控费用支出。
* **上下文压缩与历史归档**：在单轮长对话的 Token 消耗逼近限制时，自动提取中间轮次摘要，并将完整的原始对话历史归档至本地 JSONL 格式中。

### 4.4 长驻 PTY 会话交互与并行多智能体 (PTY Sessions & Parallel Sub-agents)
* **长驻 PTY 终端交互**：支持运行需要键盘输入确认的交互式命令（如向标准输入 `stdin` 动态灌入确认字符），并支持保持类似于本地热更新服务器 (`pnpm dev`) 等长连接会话的后台挂起监控。
* **并行多智能体与 Git Worktree 隔离**：允许编排图内同时拉起多个子 Agent 并行执行不同的分支任务，在底层利用 Git Worktree 机制为不同的 Agent 创建隔离的临时项目副本目录，在确保多智能体开发效率的同时绝对保护主项目代码不被改坏。

---

## 5. 附录：本地开发与构建指南

### 5.1 开发期启动 (Dev)
```bash
# 终端 1：启动 Python Sidecar (端口 8123)
cd services/orchestrator
uv run uvicorn src.main:app --reload --port 8123

# 终端 2：启动 Tauri 前端
cd apps/desktop
pnpm dev
```

### 5.2 本地轻量校验 (Pre-commit)
在提交代码前运行轻量校验，确保编译通过、单元测试正常、文档未产生漂移：
```bash
./scripts/verify.sh
```

### 5.3 全量 E2E 校验 (Push 前)
运行完整 Playwright GUI 自动化端到端测试：
```bash
./scripts/verify.sh --e2e
```

### 5.4 桌面端打包 (Build DMG)
```bash
pnpm tauri build
```
编译打包成功后，生产版会自动内嵌 Sidecar Python 运行环境，输出双击可安装的 `.dmg` 桌面应用程序。

---

*本文档基于最新的前后端实现编写。关联架构设计详述见 [系统架构文档](file:///Users/fancy/clutch/docs/ARCHITECTURE.md)；文件定位见 [FILEMAP.md](file:///Users/fancy/clutch/memory/FILEMAP.md)。*