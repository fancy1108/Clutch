# Clutch — 本地 AI 多 Agent 编排与监督控制台

## 1. 产品定位与核心价值

**Clutch** 是一款面向独立开发者、技术运营人员以及 AI 工作流与自动化搭建者的桌面应用。它提供了一个 **可视化、零代码的 SOP（标准作业程序）工作流编排与运行控制台**。

通过 Clutch，用户可以在画布上定义任意的多 Agent 协作工作流，由系统动态调度本地多种 AI 引擎（各种本地 CLI 工具、MCP 服务及远程/本地大语言模型）执行，并在统一的 IDE 级控制台中全程监督执行过程、进行人工审批与干预决策。

### 1.1 核心价值主张
- **通用多 Agent 画布编排 (Generic Multi-Agent Orchestration)**：用户通过可视化拖拽连线定义工作流，支持在各节点灵活指定不同的 Agent 角色与任务说明，运行时由编排引擎自动编译为 LangGraph 状态机并处理输入输出接力。
- **本地工具生态打通 (Local AI Tool Integration)**：自动扫描本地开发环境并无缝接入各种主流的本地 AI 命令行工具（CLI，如 Claude Code, Aider, Ollama 等）及 macOS 客户端，打破云端与本地的边界。
- **全流程透明监督 (Console Observability)**：打破 AI 执行的“黑盒”，在统一的控制台界面中展示多角色 Chat 流、流式子进程终端日志、Git 代码变更与 Diff、Flow 进度图以及工作区文件树。
- **人机协同门控 (Human-in-the-Loop)**：在关键检查失败或敏感操作节点，图会自动挂起，由人类进行 Approve（批准强制通过）、Reject（打回）或 Retry（带补充指令重试）。
- **本地优先 (Local First)**：应用完全运行于本地；API Key 与偏好保存在本机用户目录（`models.json` 等，`chmod 600`），不经 Clutch 自有云端上传。macOS Keychain 迁移见开源路线图 T2。

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

## 3. 核心功能特性（按页面与视图）

本节所列特性为**当前项目前端与后端已完全实现并验证**的真实功能与系统架构，不包含任何模拟（Mock）数据：

### 3.1 Chat Workspace (主工作台对话与输入)

* **Single Agent Workspace**：支持绑定自定义 System Prompts 与大语言模型。底层的 `EngineRouter` 在 `clutch` (全局 LLM API)、`claude-cli` (Claude Code 本地 CLI)、`antigravity-cli` (Agy CLI) 与 `ollama-cli` 之间智能路由分流，并自动维持 CLI 引擎的逻辑 Session 恢复。Thinking 加载状态的头像与消息加载完成的静态头像保持逻辑一致。
* **Hybrid 多 Session（plain chat）**：同一工程 workspace 下可并行维护多个 chat session；`CLUTCH_RUNTIME_MODE=hybrid` 时后端为每个 `run_id` 分配独立 shell，并按 workspace 串行执行 CLI turn，避免同目录并发 `claude -p` 互锁。切换 session 时先持久化 `idle` 状态再推送 WebSocket；切走期间后台 turn 完成后可通过 HTTP hydrate 恢复，避免 UI 永久卡在 Thinking。
* **Multi-Agent Graph Workspace**：React Flow 画布可视化编排节点与连线，后台 Workflow Compiler 动态将其编译为 LangGraph 状态机。下游节点自动接收并注入上游的 `node_outputs`。工作流节点的激活状态、运行阶段与详细日志通过 WebSocket 增量 `state_patch` 实时推送到前端渲染。Chat 中各节点回复展示 **Agent Manager 配置的 Agent 类型与品牌 Logo**（而非仅依赖节点 `tool` 字段）；Thinking / 进行中步骤优先跟随后端 `active_node_id` / `active_agent`。`claude-cli` 且 `CLUTCH_RUNTIME_MODE=hybrid` 的节点附带可折叠 **View execution details**（与 Single Agent Hybrid 一致）。运行中用户可通过 Stop **取消工作流**（协作式 cancel + 前端 idle 恢复）。`CLUTCH_RUNTIME_MODE=hybrid` 时，**`claude-cli` 节点**走与 plain chat 相同的 Hybrid PTY shell（含 workspace CLI 锁与 session resume）；Clutch 内置 Agent（含图片模型）等其它节点类型不变。
* **Rich Chat Input Bar & Attachments**：支持从剪贴板直接粘贴图片生成 Chip 缩略图预览；支持从右侧文件树拖拽文件/文件夹进入输入框作为附件；输入框内键入 `/` 触发已扫描 Skills 的指令联想，键入 `#` 触发历史会话引用联想；提供全局运行状态控制（Running 时展示 Stop 按钮，支持用户手动中止运行）；提供持久化的安全审批模式选择（Auto-approve, Ask-on-Write, Manual confirmation）。
* **Observability Chat Feed**：支持对本地子进程 CLI（如 Claude Code CLI）敲击的所有终端命令及 stdout/stderr 输出进行行内展开卡片审计；聊天气泡中优雅地展示 Agent 专属标签、Boundary markers 和系统提示词 metadata。**Hybrid 回复的正文与图片均从 `outputEvents` 的 assistant 内容解析**，避免工作流上一节点气泡误显示下一节点生成的图片。Plain chat 支持 `client_message_id` 与乐观发送合并，避免切换 Agent 后重复「你好」等用户消息被去重或丢失。

---

### 3.2 Observability Panel (右侧监督面板)

* **Run Overview & Token Metrics**：实时追踪会话运行的元数据（工作流 ID、激活节点、绑定模型、当前状态）；展示步骤 checklist 列表高亮标记当前的 active 节点；可视化展示输入与输出的 Token 消耗占比进度条，并折算成真实的 USD 消费。
* **File Tree Browser & Drag-and-Drop**：以树状结构实时呈现工作区的所有本地项目代码文件；支持双击快速在代码编辑器中打开文件；支持直接拖拽文件节点至聊天输入栏以引用文件。
* **Multi-Agent Flow Viewer**：以可视化的流程图节点状态高亮呈现当前 LangGraph 运行图的进度轨迹。
* **Code Diff Auditor**：列出本地工作区发生变化的所有修改文件；支持行内红绿代码 Diff 详情对比审计。
* **Terminal Console Logs**：流式展示本地子进程（如 `claude-cli`）在底层执行的所有 stdout/stderr 日志流；提供一键清空日志按钮。

---

### 3.3 Human-in-the-Loop Dialog (人机门控审批浮窗)

* **High-Risk Tool Interception**：Sidecar 的 `mcp_risk.py` 智能扫描 Agent 的工具调用参数。一旦涉及写入或删除等高风险磁盘操作（如 `apply_patch` 覆盖或删除代码），自动拦截并挂起图状态为 `human_required`。
* **Gate Control Panel**：前端弹窗展示挂起的详情，支持用户 Approve 批准写入、Reject 拒绝步骤，或 Retry 填入反馈提示词重试。

---

### 3.4 Settings Dashboard (设置与配置中心)

* **General Settings**：支持用户修改个人名称并应用在发送气泡标签中；支持上传自定义头像并转换为 base64 存盘；支持中英文双语对照切换，后端 API / WS 错误采用 `tr()` 响应；利用 Tauri `getVersion` 插件动态显示真实桌面客户端版本号。
* **Agent Settings**：提供可视化 Agent 管理器（`AgentManager.tsx`），支持自由增删改自定义 Agent，配置其名称、头像、System Prompt、模型及关联 MCP 工具。
* **Workflow Settings**：管理和选择可用的流程图 SOP 模板，支持一键在 Chat 中启用。
* **Tool Settings**：自动扫描本机 `PATH` 检测已安装的 CLI 工具绝对路径（`claude`, `agy`, `aider`, `ollama`），支持物理“已连接”启用偏好配置。
* **Model Provider Settings**：配置各种云端大模型与 Ollama API Keys 凭证（支持无感导入 `.cc-switch` 凭证）；支持对模型属性（Context Window, Temperature）进行精细注册与调整。
* **Skills Settings**：自动扫描项目关联的 Skills，解析 `.md` 指引文件前缀的 YAML 元数据信息并呈现在表格中。
* **MCP Server Settings**：支持注册、连接或拔除本地/远程的 Model Context Protocol 服务器。
* **Appearance Settings**：提供一键在 Pristine Light、Nordic Frost 和 Amber Warm 主题间切换的设计面板。
* **Session Memory**：使用 LocalStorage 后台自动记忆每个 sessionRunId 的工作流 ID、智能体 ID 以及单/多智能体模式切换状态，在切换会话时精准恢复。

---

## 4. 规划中特性 (Future Roadmap)

以下特性来源于 **Backlog (候选需求池)**，是针对未来阶段的深度优化与升级规划：

### 4.1 对话与审批体验规划 (Chat & Approval Enhancements)
* **需求智能匹配分派**：大模型根据用户的自然语言输入，自动判定应启动哪个已有的工作流 SOP，并提炼出第一步的指导提示，免去手动查找启动的繁琐。
* **图内运行错误自愈**：在 Agent 编写代码出现语法或运行报错时，直接读取错误日志和编译器诊断结果回灌至 Agent 编排流中，让大模型自动尝试排查并编写修复代码，降低人工审批打回的频次。
* **审批行内红绿 Diff 预览**：在用户确认 Approve/Reject 的弹窗卡片中直接嵌入代码改动的红绿对比展示，无需手动切换右侧 Changes 选项卡。
* **代码流式增量补丁推送**：当大模型在后台极快写代码时，通过 WebSocket 增量、流式地将代码 diff 过程在聊天区更新渲染，避免长时卡顿等待。

### 4.2 终端与沙箱权限规划 (Terminal & Sandboxing)
* **长驻 PTY 终端交互**：支持运行需要键盘输入确认的交互式命令（如向标准输入 `stdin` 动态灌入确认字符），并支持保持类似于本地热更新服务器 (`pnpm dev`) 等长连接会话的后台挂起监控。
* **细粒度命令审批策略**：支持用户配置规则，如对 `git` 提交直接无感放行，但对涉及编译执行或疑似敏感修改的指令保持“询问”状态。
* **安全目录 Glob 限制与动态申请**：设定文件夹路径读写白名单（如仅允许 Agent操作 `./src`，禁止访问系统盘），若超出边界则在前端弹出临时权限扩权申请。
* **OS 级虚拟沙箱隔离**：深入技术调研，通过容器或 OS 底层沙箱技术（如 Linux Bubblewrap / Windows 隔离 Sandbox）将 Agent 的物理子进程锁死，防范恶意命令破坏系统。

### 4.3 编排运行与成本性能规划 (Execution & Performance)
* **并行多智能体与 Git Worktree 隔离**：允许编排图内同时拉起多个子 Agent 并行执行不同的分支任务，在底层利用 Git Worktree 机制为不同的 Agent 创建隔离的临时项目副本目录，在确保多智能体开发效率的同时绝对保护主项目代码不被改坏。
* **缓存友好的前缀保护分叉**：多智能体并发或任务分叉执行时，保持提示词的前缀缓存 (Prefix Cache) 对齐，防止大模型发生二次推理编译，从而减小 Token 消耗。
* **真实 Token 成本追踪**：更精准地捕获和累加单次运行中所消耗的大模型真实 Token（包含缓存命中状态），便于用户监控费用支出。
* **上下文压缩与历史归档**：在单轮长对话的 Token 消耗逼近限制时，自动提取中间轮次摘要，并将完整的原始对话历史归档至本地 JSONL 格式中。

---

## 5. 附录：本地开发与构建指南

### 5.1 开发期启动 (Dev)

**推荐：Tauri 桌面一体启动（含 Hybrid Sidecar）**

```bash
# 仓库根目录 — 脚本会守护化启动 Vite :3000，再跑 tauri dev（勿用裸 pnpm tauri dev）
export CLUTCH_RUNTIME_MODE=hybrid
pnpm tauri:dev
```

**分拆调试（双终端）**

```bash
# 终端 1：Vite 前端
cd apps/desktop && pnpm dev

# 终端 2：Tauri 壳（Sidecar 由 Tauri 在 dev 下自动拉起 :8124）
cd apps/desktop
export CLUTCH_RUNTIME_MODE=hybrid
pnpm tauri dev --no-dev-server-wait
```

**仅 Sidecar（无桌面壳）**

```bash
cd services/orchestrator
uv run uvicorn src.main:app --reload --port 8124
```

> 开发期 Sidecar 监听 **8124**；打包 DMG 内嵌 Sidecar 为 **8123**。`tauri.conf.json` 的 `beforeDevCommand` 为空，由 `scripts/tauri-dev.sh` 管理 Vite 生命周期，避免 Tauri 误杀 dev server。

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