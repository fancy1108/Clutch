# Clutch — 本地 AI 多 Agent 编排与监督控制台

> **This document describes WHAT users can do.**  
> Implementation details belong in [`ARCHITECTURE.md`](./ARCHITECTURE.md).  
> Acceptance status belongs in [`memory/ROADMAP.md`](../memory/ROADMAP.md) — not here.

## 1. 产品定位与核心价值

**Clutch** 是一款面向独立开发者、技术运营人员以及 AI 工作流与自动化搭建者的桌面应用。它提供了一个 **可视化、零代码的 SOP（标准作业程序）工作流编排与运行控制台**。

通过 Clutch，用户可以在画布上定义任意的多 Agent 协作工作流，由系统动态调度本地多种 AI 引擎（各种本地 CLI 工具、MCP 服务及远程/本地大语言模型）执行，并在统一的 IDE 级控制台中全程监督执行过程、进行人工审批与干预决策。

### 1.1 核心价值主张
- **通用多 Agent 画布编排 (Generic Multi-Agent Orchestration)**：用户通过可视化拖拽连线定义工作流，支持在各节点灵活指定不同的 Agent 角色与任务说明，运行时由编排引擎自动编译为 LangGraph 状态机并处理输入输出接力。
- **本地工具生态打通 (Local AI Tool Integration)**：自动扫描 macOS / Windows 本地环境并接入 Claude Code、MiMo Code、ZCode、Codex、Aider、Ollama 等 CLI，打破云端与本地的边界。
- **全流程透明监督 (Console Observability)**：打破 AI 执行的“黑盒”，在统一的控制台界面中展示多角色 Chat 流、流式子进程终端日志、Git 代码变更与 Diff、Flow 进度图以及工作区文件树。
- **人机协同门控 (Human-in-the-Loop)**：在关键检查失败或敏感操作节点，图会自动挂起；Chat 输入框上方以**紧凑操作条**提供 Allow（允许）、Reject（拒绝）或带说明的 Retry（重试），不再使用大块 HITL 面板。
- **本地优先 (Local First)**：应用完全运行于本地；API Key 保存在 macOS **Keychain** 或 Windows **凭据管理器**（模型元数据在 `models.json`），不经 Clutch 自有云端上传。

**首次体验**：安装后首次启动会进入全屏设置向导（工作区授权 → 云模型或本地 CLI 二选一 → Flow 入口引导 → 权限说明），完成后写入 `onboarding_completed` 偏好，重启不再出现；Settings 仍可手动调整各项配置。**分步说明见 [`docs/GETTING_STARTED.md`](./GETTING_STARTED.md)。**

**产品官网（GitHub Pages）：** 静态介绍页 [`docs/index.html`](./index.html)，部署于 **https://fancy1108.github.io/Clutch/** — 中英文切换、功能概览、安装命令与作者微信联系方式；与桌面应用功能同步维护。

**macOS 应用内更新（v1.0.2+）：** 打包版启动后自动检查 GitHub Releases 上的 `latest.json`；有新版本时在**侧栏底部 Settings 同一行**显示紧凑 **Update / Later** pill（下载中 spinner + 进度百分比，完成后 **Restart**），下载签名 bundle 并重启安装。**v1.0.0 / v1.0.1 用户须先手动安装 v1.0.2 一次**；Windows 暂无应用内更新，请从 Release 页手动下载新版本。详见 [`docs/UPDATES.md`](./UPDATES.md) · [`docs/INSTALL.md`](./INSTALL.md) §3。

**macOS Sidecar 热更（v1.2.1+ · D37）：** 在无需升 app 版本时，可静默下载并校验编排服务（`orchestrator`）补丁；就绪后 Settings 旁显示极小 **「更新已就绪」**，确认后仅重启 sidecar（不关整个 App）。与全量 Update 同时存在时只显示全量更新。详见 [`docs/UPDATES.md`](./UPDATES.md) §5。

### 1.2 真实痛点（本项目的存在理由）
如果仅仅是想生成代码，直接使用 Claude Code / Cursor 裸跑就够了，不需要这套工作台。Clutch 旨在解决以下两个真实的工程化场景痛点：

#### 痛点一：单 Agent 模式下，上下文容易“炸”，新开对话又会丢失上下文
- **典型场景**：在验收阶段发现一堆 Bug，让 Agent 修复，来回修改了几轮后，对话窗口里堆满了“旧代码 + 新代码 + 历次对话”，大模型开始出现记忆混乱、丢失指令的情况，甚至在修 Bug 的过程中顺手把既有需求也悄悄改了一点而不自知。如果对臃肿的会话无法忍受而新开一个对话，之前积累的所有上下文（对需求的理解、避坑经验、已经达成的共识）又会全部丢失，导致每次要么硬撑一个越来越庞大臃肿的单一会话，要么被迫从零重新向模型对齐。
- **Clutch 架构解法（现状与路线图）**：
  - **当前已实现**：支持基础的 **State 跨会话持久化与恢复**（`states/{run_id}.json`）、针对 CLI 引擎的 **Session 恢复机制**（`--resume` / Codex history replay），以及 **长会话消息压缩（Compaction，capability D8）**：当估算 token 接近上下文窗口限额时自动折叠中间轮次，完整原文归档至 `runs/archive/{run_id}.jsonl`，Chat 展示压缩摘要；**Todo / 计划要点**钉进摘要并每轮以 `task_state` 再注入，压缩后仍可回答「还剩什么」。
  - **后续路线图**：State 分段管理的进一步自动化、Human Gate reject 后的物理回滚（见 [`memory/BACKLOG.md`](../memory/BACKLOG.md) B-11）。

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
2. **后端 (FastAPI + LangGraph Python Sidecar)**：运行于 `localhost:8123`，作为唯一的真理源 (SSOT) 控制状态跳转。`WorkflowCompiler` 将画布导出的 JSON 动态编译成 LangGraph 可执行图。打包发行版默认关闭 debug 导出 API 与 OpenAPI 文档（维护者可设 `CLUTCH_DEBUG_API=1`）；Tauri WebView 启用 Content-Security-Policy 限制外连与脚本来源。DMG / MSI / NSIS 内嵌 Sidecar 启用 loopback 会话令牌（OSR-08）：WebView 经 Tauri IPC 获取 Bearer token 后访问 `/api/*`；Models Config 等面板在 Sidecar 不可达、未授权或后端错误时会显示区分性提示（而非一律「无法连接」）。
3. **通信机制**：前后端通过 WebSocket 实时更新全局状态 `ClutchState`（采用 `state_patch` 增量推送）。

---

## 3. 核心功能特性（按页面与视图）

本节所列特性为**当前项目前端与后端已完全实现并验证**的真实功能与系统架构，不包含任何模拟（Mock）数据：

### 3.1 Chat Workspace (主工作台对话与输入)

* **Single Agent Workspace**：支持绑定自定义 System Prompts 与大语言模型。底层的 `EngineRouter` 在 `clutch` (全局 LLM API)、`claude-cli` (Claude Code 本地 CLI)、`antigravity-cli` (Agy CLI)、`codex-cli` (Codex CLI)、`opencode-cli` (OpenCode CLI)、`mimo-cli` (小米 MiMo Code CLI)、`codebuddy-cli` (Tencent CodeBuddy / WorkBuddy CLI)、`cursor-cli` (Cursor Agent CLI)、`zcode-cli` (Z.AI ZCode CLI)、`rivet-cli` (天枢 Rivet CLI) 与 `ollama-cli` 之间智能路由分流，并自动维持 CLI 引擎的逻辑 Session 恢复（Codex 使用 `codex exec --json` + history replay，聊天区仅展示 `agent_message` 正文；OpenCode 使用 `opencode run --auto` 非交互 headless；MiMo Code 使用 `mimo run --dangerously-skip-permissions` headless；CodeBuddy 使用 `codebuddy -p` headless 并支持 `--resume` / `--session-id` 会话恢复；ZCode 使用 `zcode -p --mode yolo --json` headless 并支持 `--resume sess_...` 会话恢复；Rivet 由 Sidecar 自动注入 `RIVET_FORCE_RECOVERY_CLI=1` 以 headless 调用）。**Agent 类型下拉**由 `/api/tools/status` 动态生成：已 Connect 且配置完成的 CLI 工具自动出现在 Single Agent 与 Agent Manager 选项中（含 Codex、Ollama、CodeBuddy、MiMo Code、ZCode 等）。Thinking 加载状态的头像与消息加载完成的静态头像保持逻辑一致。
* **Hybrid 多 Session（plain chat）**：同一工程 workspace 下可并行维护多个 chat session；`CLUTCH_RUNTIME_MODE=hybrid` 时后端为每个 `run_id` 分配独立 shell，并按 workspace 串行执行 CLI turn，避免同目录并发 `claude -p` 互锁。切换 session 时先持久化 `idle` 状态再推送 WebSocket；切走期间后台 turn 完成后可通过 HTTP hydrate 恢复，避免 UI 永久卡在 Thinking。**同 session 忙时 Send 不禁用**：当前轮次仍在处理时后续消息进入本 session 队列依次执行，用户消息即时展示、不静默丢弃。**跨 session 池满时排队**：当 `CLUTCH_SHELL_MAX_SESSIONS` 槽位均被占用时，新 session 的消息进入全局 FIFO 队列（`shell_session_status: queued_pool`），待其他 session 释放 shell 后自动续跑，不再弹出 Supervisor 拒绝。
* **New Chat 默认文本模型**：点击 New Chat 时自动将全局 `active_model_id` 重置为默认文本模型（优先 **Agnes 2.0 Flash**，否则首个可用 chat 模型），避免从生图模型切回新会话后仍走 image 路由。
* **Multi-Agent Graph Workspace**：React Flow 画布可视化编排节点与连线，后台 Workflow Compiler 动态将其编译为 LangGraph 状态机。下游节点自动接收并注入上游的 `node_outputs`；各节点执行时自动注入**分层组装后的 system prompt**（`markdownDoc` 为 D53 协议层，叠加 Env / 项目规则 / Skills 目录等）。工作流节点的激活状态、运行阶段与详细日志通过 WebSocket 增量 `state_patch` 实时推送到前端渲染。Chat 中各节点回复展示 **Agent Manager 配置的 Agent 类型与品牌 Logo**（而非仅依赖节点 `tool` 字段）；Thinking / 进行中步骤优先跟随后端 `active_node_id` / `active_agent`。`claude-cli` 且 `CLUTCH_RUNTIME_MODE=hybrid` 的节点附带可折叠 **View execution details**（与 Single Agent Hybrid 一致）。运行中用户可通过 Stop **暂停并进入精修模式**（`status=refining`）；工作流正常结束（`passed`/`failed`）后也可在同一 session 内继续精修。精修时输入框 `@` 弹出工作流 Agent 列表（支持带空格的节点名，如 `@5-Visual Rendering Engine`），向指定 Agent 发送修改意见（`source=flow_refine`，Hybrid 交互）；满意后发送 `/continue` 提交修订并 **以 Legacy 模式继续执行下游节点**。生图节点精修时自动复用上游 `final_image_prompt` 并结合用户补充说明。Sidecar 重启后可从聊天记录重建 `node_outputs` 以恢复精修会话。`CLUTCH_RUNTIME_MODE=hybrid` 时，**`claude-cli` 节点**走与 plain chat 相同的 Hybrid PTY shell（含 workspace CLI 锁与 session resume）；Flow 多行 Claude prompt 自动降级为 legacy subprocess；Clutch 内置 Agent（含图片模型）等其它节点类型不变。
* **Rich Chat Input Bar & Attachments**：支持从剪贴板直接粘贴图片生成 Chip 缩略图预览；支持从右侧文件树拖拽文件/文件夹进入输入框作为附件；输入框内键入 `/` 触发已扫描 Skills 的指令联想，键入 `#` 触发历史会话引用联想；工作流精修模式（`refining` 或已完成工作流）下键入 `@` 触发工作流 Agent 联想；提供全局运行状态控制（Running 时展示 Stop 按钮，工作流 Stop 进入精修而非 failed）；提供持久化的安全审批模式选择（Auto-approve, Ask-on-Write, Manual confirmation）。**Coding 发图**：Chat 底栏与 Terminal **OrchestratorBar**（非 xterm 黑框）均可粘贴/选择图片；**聊天 LLM 先 multimodal 发图**，有效回复直接展示；仅当软拒绝视觉或 API 拒图时，才降级本地 OCR/调色板。**本地 CLI Agent（Mimo / Claude Code 等）**则先把图落盘 `.clutch/attachments/`，再注入 `@path` / `[file: path]` 让 CLI 自己读图（禁止把 base64 塞进命令行）；仅当 CLI 拒绝读图时再降级 OCR。Terminal 发图同样先落盘再注入路径（目录含 `.gitignore` 为 `*`，过大时清理 3 天前旧图）；发送期间输入与发送按钮 Loading，防重复派发。
* **中间产物点击预览**：Chat 气泡中的工作区路径、`[file:]` / `@path`、fenced 代码块可点击打开全屏预览（大文件 plain view 降级）；**图片路径**打开媒体预览。Terminal xterm 与派发历史中的路径/带扩展名文件名同样可点；**Terminal Overview 派发记录**对 `.clutch/attachments/` 等图片显示缩略图，点击放大。
* **Workspace Chrome（平台差异）**：macOS 与 Windows 侧栏折叠 rail、折叠按钮位置、Chat 间距与右侧监督 Tab 样式分文件维护（`apps/desktop/src/platform/chrome/`）；共享导航图标与文案见 `navConfig.ts`。macOS 默认保留图标+微标签折叠 rail 与 App 级浮动折叠按钮；Windows 使用纯图标 rail 与侧栏边缘折叠按钮。**项目绑定**：侧栏会话按工作区路径稳定 id 挂载（同路径重授权不会丢掉历史）；开发态与打包态分目录存储（`clutch_dev` / `clutch`），E2E 须隔离 `CLUTCH_STORAGE_DIR`。
* **Long-session compaction（D8）**：Plain chat 在 token 估算接近模型上下文上限时自动压缩历史消息；用户消息与摘要 digest 保留，完整原文写入 `runs/archive/{run_id}.jsonl`。压缩后 **Todo/计划** 仍通过 `task_state` 层与 digest 快照可达。
* **Run control（D9）**：Plain chat 运行中可 **Stop**；停止后 Chat 显示 Supervisor 提示与 **Continue**（`continue_run`）。连续工具失败触发 **loop fuse**（`CLUTCH_LOOP_FUSE_FAILURES`，默认 3）。输入栏上方展示实时 **Steps n/m · ~tok**（`run_stats`）。
* **Subtask delegation（D10 + D48）**：Clutch Agent 可调用 `delegate_subtask` 派发 **explore**（只读）或 **implement** 子任务；父气泡下嵌套 **Subtasks** 卡展示状态、摘要与可展开步骤；子失败在父卡可见。
* **Background commands（D11）**：`run_terminal_cmd` 可设 `background=true` 立即返回 `job_id`；Chat 输入栏上方展示后台任务条（查看输出 / Kill）；前台仍可继续对话。
* **Git + web fetch（D12）**：Builtin `git_status` / `git_diff` / `git_commit`（提交需审批）与 `web_fetch`（抓取 URL 文本供总结）；步骤进入对话工具条。
* **Permission rules（D13）**：可配置命令 allow/ask/deny 规则；`rm -rf` / `sudo` 等危险命令在 Full 模式下仍强制询问；权限菜单可 **清除记住的批准**。
* **Observability Chat Feed**：支持对本地子进程 CLI（如 Claude Code CLI）敲击的所有终端命令及 stdout/stderr 输出进行行内展开卡片审计；聊天气泡中优雅地展示 Agent 专属标签、Boundary markers 和系统提示词 metadata。**Hybrid 回复的正文与图片均从 `outputEvents` 的 assistant 内容解析**，避免工作流上一节点气泡误显示下一节点生成的图片。Plain chat 支持 `client_message_id` 与乐观发送合并，避免切换 Agent 后重复「你好」等用户消息被去重或丢失。
* **Chat / Terminal 双模式（Single Agent plain chat）**：当 Active Agent 为 **任意已 Connect 的 CLI 类型**（`*-cli` 路由键，如 Claude Code、OpenCode、Codex、Aider、CodeBuddy、Rivet、Ollama、Antigravity 等；不含 Clutch 内置 LLM）时，主工作台右上角可切换 **对话模式**（默认）与 **终端模式**（Terminal Orchestra：多 Lane 嵌入式 xterm + `INTERACTIVE_PTY`；**Windows 通过 WinPTY 后端附着交互式 CLI**）。**终端模式下底部 Active Agent 下拉仅列出 CLI 类型 Agent**。终端模式下底部 `ChatInputBar` 隐藏，改为 **OrchestratorBar**（与 Chat 输入栏同款 `+` / ✋ / `@` Agent 选择，**`fixed bottom-8` 贴底布局**）；支持 `@目标Agent` 自然语言或图语法派发、确认卡预览、handoff 文件写入与 Lane 间可视化（Orchestrator `@` 提及与已路由 CLI 显示名一致）。**OrchestratorBar 发送后，系统将任务文本注入目标 Lane 的 PTY（等待 TUI 就绪后自动提交 Enter）**；Ollama 以 `ollama run <model>` 启动交互会话。展开 Lane 超过 4 个时，终端区顶部显示分页圆点（每页 2×2）；**收起、翻页或侧栏切换时 Lane PTY 保持连接，xterm 从缓冲 transcript 恢复并重绘，避免黑屏**。派发确认后 Overview **即时以 Loading 步骤形式（「正在生成交接摘要…」、「正在打开终端…」、「正在注入任务目标…」）显示派发记录并支持异步更新**，时间戳按用户本地时区显示。Handoff「Send to Bar」填入图语法 `@目标 from @来源 @handoff.md`；Handoff 预览不再出现标题下空白卡片。用户可在 xterm Lane 内直接输入，或通过 OrchestratorBar 派发到其它 Lane；切回对话模式后历史消息与监督发消息能力不变，PTY 会话在后台保持以减少切换卡顿。工作流 session 不展示切换。右侧监督面板 Tab 为 **Overview · Files · Changes · Terminal**（Overview 文本可选中复制）；Overview 展示派发记录（**含 CLI Session 恢复命令与 Copy**：Claude/CodeBuddy `claude --resume`、Codex `codex resume --last`、OpenCode `opencode -c` / `opencode -s`、MiMo Code `mimo -c` / `mimo -s`、ZCode `zcode --resume sess_...` / `zcode -c`、Ollama/Antigravity 等按 Agent 类型生成，Clutch 内部分配的 UUID 不误用于不支持 resume 的 CLI）；Terminal 审计日志独立 Tab 保留。

<!-- capability-ui-table:start -->
#### Capability → Chat UI（D52 门禁对照）

发版或将 capability Task 标完成前，须核对本表与真机一致（抽查 **D1 / D10 / D37** 至少各一条）。权威交付表见 [`specs/core/clutch-agent-capability-plan.md`](../specs/core/clutch-agent-capability-plan.md)。

| Capability | What you see in Chat |
|------------|----------------------|
| D1 builtins | Verb-group tool trail (D46) + files-changed chips (D47) + Allow/Reject for risky writes/shell |
| D2–D4 plan/todo/ask | In-chat Plan / Todo / Question cards (D49) |
| D5–D6 verify/diff | Verification report card + Cursor-style Diff cards (D50) |
| D7 rules/skills | Runtime prompt layers panel in Agent Manager; Skills via `read_skill` (D53) |
| D8 task state | Compaction digest badge; Todo/Plan survive fold via `task_state` |
| D9 run control | Stop / Continue + Steps n/m · ~tok (`run_stats`) |
| D10 subtasks | Nested Subtasks cards under parent bubble (D48) |
| D11 background | Background jobs bar (view output / kill) above composer |
| D12 git/web | Tool-trail steps for `git_*` / `web_fetch` |
| D13 permissions | Permission mode menu + Clear remembered approvals |
| D37 MCP bind | Agent Manager Module 4 Hub checkboxes; bound tools in ReAct trail |
| D38 Hub probe | MCP Hub **Test connection** → tool count or readable error (no “under development” banner) |
| D39 transport | Hub register form: stdio only; SSE disabled / API 400; optional Env `KEY=value` |
| D40 MCP badge | Chat composer: `N MCP · ~M` badge or **Bind MCP** CTA → Agent Manager |
| D41 MCP approve | Risky MCP pause → Allow/Reject dock + tool/path in approval copy |
| D42 real tools | Agent list/detail show real Hub tool names (not fake permission chips) |
| D44 one-click FS | Agent Module 4 **Enable workspace file tools** → binds `local-fs` |
| D46 tool trail | Foldable verb_group steps on the assistant bubble |
| D47 chips | Clickable files-changed chips → workspace preview |
| D48 nested | Subtasks cards with status / summary / expandable steps |
| D49 cards | Plan / Todo / Question live in the conversation timeline |
| D50 reports | Verification + Diff cards in the conversation timeline |
| D51 terminal sync | **View in Terminal** on Shell steps / subtasks → log highlight / lane focus |
| D53 prompt layers | Agent Manager「运行时提示词分层」+ `GET /api/agents/{id}/prompt-assembly` |
<!-- capability-ui-table:end -->

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
* **Gate Control Panel**：挂起时在 Chat 输入区上方提供紧凑 **Allow / Reject**，以及可选「附加说明 → Retry」；不再占用大块 Human-In-The-Loop 卡片。

---

### 3.4 Settings Dashboard (设置与配置中心)

* **General Settings**：支持用户修改个人名称并应用在发送气泡标签中；支持上传自定义头像并转换为 base64 存盘；支持小/默认/大/特大/超级大字体大小偏好并持久化（`data-font-size`）；支持中英文双语对照切换，后端 API / WS 错误采用 `tr()` 响应；利用 Tauri `getVersion` 插件动态显示真实桌面客户端版本号。
* **Agent Settings**：提供可视化 Agent 管理器（`AgentManager.tsx`），支持自由增删改自定义 Agent，配置其名称、头像、**可编辑协议段**（`markdownDoc`，capability **D53** 中仅作 protocol 层，不再假装等于完整 runtime system）、模型及关联 MCP 工具。运行时 system 由分层组装：底座 / Env / 协议 / **项目规则**（**D7**，对齐 Grok：从 git 根走到授权工作区路径，加载 `AGENTS.md`·`CLAUDE.md` 与 `.grok/.claude/.cursor/rules`，更深优先；无 User home 规则）/ **Skills 开放目录**（全局∪当前仓∪自定义 SEARCH PATHS 中 Enabled 项自动进 catalog，同名项目优先；Agent 绑定可选叠加；全文经 `read_skill`）/ Plan 模式当轮 reminder。切换工作区时仅轮换项目自动 Skills 挂载，手动 Search Paths 保留。**Agent Manager → Clutch Agent 详情右侧**可查看「运行时提示词分层」（层名+字符量，可刷新）；亦可用 `GET /api/agents/{id}/prompt-assembly`。**Skills / MCP 模块按 Agent 类型分档**：仅 **Clutch** 内置 Agent 可绑定 Clutch Skills Registry 与 MCP Hub（Module 4 可勾选 Hub 服务器并持久化 `mcpServerIds`）；**Claude Code** / **OpenCode** / **MiMo Code** CLI Agent 展示各自原生配置只读扫描与 Settings 深链；其他 CLI 类型显示「即将上线」，避免误用全局 Registry。
* **Clutch Agent 内置手脚（capability D1 / DECISIONS D44）**：授权工作区后，Chat 选择 **Clutch Agent** 默认挂载虚拟 MCP **`clutch-tools`**（无需先绑 Hub）：`read_file` / `list_dir` / `grep` / `search_replace` / `run_terminal_cmd` / `apply_patch` / **`propose_plan`** / **`todo_write`** / **`ask_user_question`** / **`submit_verification`** / **`submit_diff_summary`**。写文件与 shell 仍走既有风险审批（`permission_mode`）。额外 Hub 服务器（如 `local-fs`）可在 Agent Manager Module 4 绑定叠加。Chat 输入栏上方显示 **已绑 N 个 MCP / ~M 工具** 徽章（capability **D40**）；未绑时显示「绑定 MCP」引导至 Agent Manager。运行中与结束后，Chat 气泡展示可折叠 **工具轨迹**（capability **D46**，对标 Grok verb_group：如 `Read 2 files, Searched 1 pattern`；展开可见逐步；审批等待时标 awaiting）——不必切 Terminal；步骤随该条回复持久化，刷新仍可回看。本回合写出的工作区文件会以 **变更文件芯片**（capability **D47**）出现在气泡下方；点击走与路径预览相同的全屏预览（**DECISIONS D42**），无需在正文里自己找路径。Shell / 执行类步骤与子任务卡提供 **在 Terminal 查看**（capability **D51**）：打开右侧 Terminal 日志并高亮匹配的 `[CHAT] Step …` 行；若有 CLI Terminal 会话则同时切到 Terminal mode 并 focus 对应 lane。
* **先计划再动手（capability D2 + D49）**：多步/功能类任务时，Agent 先调用 `propose_plan`；对话流内出现 **计划卡**（步骤列表）与 **批准计划 / 修改计划 / 取消**。未批准前不执行写文件或可变 shell；简单问答可跳过计划。批准后同条回合继续实现。
* **Todo 清单（capability D3 + D49）**：多步执行时 Agent 调用 `todo_write`（**不走人工审批**，仅更新会话 Todo UI）；Chat 时间线展示待办/进行中/完成状态。**未全部完成时** Todo 卡吸顶固定在对话滚动区顶部（滚动长轨迹时仍可见）；**全部打钩后**取消固定，回合结束 seal 到气泡 `todoList` 并随历史滚动，刷新仍可回看。计划卡步骤会去掉模型自带的 `1.` 前缀，避免显示成 `1. 1. …`。
* **结构化提问（capability D4 + D49）**：存在真实分叉（如 Redis vs Memcached）且用户未指定时，Agent 调用 `ask_user_question`；对话流内出现 **提问卡**（选项按钮）。点选选项（或底部自定义文字）后继续；**取消提问** 结束本回合。该工具不走通用 MCP 风险审批门，而是独立暂停路径。
* **自检报告（capability D5 + D50）**：实现收尾时 Agent 调用 `submit_verification`；对话内出现 **验证报告卡**（步骤通过/失败 + 总结）。结论为失败时列出可操作的下一步；Todo 未完成时禁止谎称通过。卡上 **查看改动** 可打开本回合变更文件预览（与 D47 芯片同源）。
* **Diff 审查（capability D6 + D50）**：每次成功改文件后，对话流**立即**出现单文件 Diff 卡（文件名 + 红绿 hunk，对标 Cursor 边改边看）；可选 `submit_diff_summary` 出多文件汇总卡。与右侧 Changes 面板并存。
* **Workflow Settings**：管理和选择可用的流程图 SOP 模板，支持一键在 Chat 中启用。内置模板含 `weather-to-vision`、`video-production`、**Design to Code**（`design-to-code`，Design 批准后交给 Builder）与社区贡献的 **Memory-Augmented Pipeline (Epicode)**（`epicode-memory-pipeline.json`；需自行配置 Epicode MCP，见 [`docs/mcp-servers/epicode.md`](./mcp-servers/epicode.md)）。含 `check` / `human_gate` / 条件边的复杂流程会强制 **JSON 编辑模式**；提示条会点名导致降级的节点 id / 边 id（如 `review-gate (human_gate)`、`edge e5 when:reject`），不再只显示泛化的「复杂流程」。`check(file_exists)` 的 `path` 必须是**工作区相对路径**（如 `.clutch/staging/kp.json`）；主机绝对路径（如 `/tmp/...`）会被拒绝并在 Terminal 标明 FORBIDDEN，避免与 agent 写入位置错位时静默失败。
* **Tool Settings**：对 20+ 主流 Agent CLI 白名单做本机探测——**已安装的一律展示**（含 Rivet、OpenCode、MiMo Code、CodeBuddy、Cursor Agent、ZCode 等扩展工具）；**未安装时默认仅推荐经 Clutch 验证的 CLI**（`codebuddy`、`cursor-agent`、`mimo`、`opencode`、`claude`、`ollama`、`codex`、`agy`、`zcode`）及安装指引。CodeBuddy 内置 headless 路由（`codebuddy -p`，curated `--dangerously-skip-permissions`）；OpenCode 内置 headless 路由（`run --auto`）；MiMo Code 内置 headless 路由（`mimo run --dangerously-skip-permissions`）；ZCode 内置 headless 路由（`zcode -p --mode yolo --json`），Auto Config 错误参数不会覆盖 curated 配置。支持 Connect 偏好与 **Auto Config**（LLM 分析 `--help` 写入 `custom_clis.json` 路由参数）。
* **Model Provider Settings**（**Models by Agent** 顶栏 Tab：**Clutch Agent** · **Claude Code** · **OpenCode** · **MiMo Code**）：**Clutch** Tab 配置内置 Agent 所用云端/本地模型 API Keys（支持无感导入 `.cc-switch` 凭证至 Clutch 侧）。内置文本提供商含 **DeepSeek**、**Anthropic**、**OpenAI**、**Google**、**Ollama**、**Agnes** 与 **OpenCode Zen**（[opencode.ai](https://opencode.ai/auth) Zen 工作区 API Key；端点 `https://opencode.ai/zen/v1`）。**Claude Code** / **OpenCode** / **MiMo Code** Tab 只读扫描各 CLI 原生 model 配置；Claude Code 在已安装 `cc-switch` CLI 时可切换 provider。**OpenCode Zen**（供 Clutch 内置 Agent，非 OpenCode CLI）仍在 Clutch Tab 配置。内置 **Agnes 2.0 Flash**（对话）、**Agnes Image 2.1 Flash**（生图）与 **Agnes Video V2.0**（文生视频）；**Ollama 条目与 Create Agent 下拉同源**——实时读取本机 `ollama list` 已安装 tag。
* **Skills Settings**（同上 Agent Tab）：Clutch Tab 管理 Skills Registry 挂载；Claude Code / OpenCode / **MiMo Code** Tab 只读扫描原生 `SKILL.md` 目录。
* **MCP Server Settings**（同上 Agent Tab）：Clutch Tab 注册/开关 MCP Hub 服务器（**stdio only**，capability **D39**——SSE 选项禁用且 API 拒绝新注册；表单支持可选 `KEY=value` Env）；每行可 **Test connection**（capability **D38**）——成功显示工具数，失败显示可读错误；不再展示误导性「开发中」横幅。Claude Code / OpenCode / **MiMo Code** Tab 只读扫描原生 MCP 配置。
* **Appearance Settings**：提供一键在 Pristine Light、Nordic Frost 和 Amber Warm 主题间切换的设计面板。
* **Session Memory**：使用 LocalStorage 后台自动记忆每个 sessionRunId 的工作流 ID 与智能体 ID，在切换会话时精准恢复并统一展示为多智能体视图架构。

---

### 3.5 Design Workspace (工作区会话 · 原型交互画布 · D36)

在 Coding 编排之前，用 Header 的 **Coding | Design** 切换进入 Design，在**当前授权工作区**下新建/恢复 Design 会话（与 Chat 同属 session 历史，按 `mode` 过滤），快速验证界面与交互。产物落在 `.clutch/design/sessions/{标题}-{web|mobile}__{run_id}/`，由 Sidecar 生成与持久化（非前端 mock）；删除会话时同步清理该目录。语言切换在 Settings → General。

* **欢迎态**：点阵背景、居中大输入；Web/App 设备切换；模型 pill（绑定全局 `active_model_id`，可跳转 Models）。支持 **`+` 附件菜单**：上传 **Design.md**（自动填入「使用 the file [XXX] 创建设计系统…」）、**网站网址**（chip + 画布先展示站点卡）、粘贴/上传**参考图**；有 vision 能力的模型会读图，否则按文案回退。
* **设备规格**：欢迎态 **Web / App** 写入会话 `device`。**Web** = **1920×1080**（16:9 桌面，画布内等比缩放预览）；**App（Mobile）** = **390×844** 手机视口。侧栏角标区分 Web / Mobile。
* **生成引擎**：Design **不调度 CLI Agent**；两阶段 Spec→UI generate/iterate 走 Sidecar `ModelRouter`（Settings → Models 的 `active_model_id`）。**默认一次生成连跑** Spec 与界面卡，不暂停确认；需人工审 Spec 时可设环境变量 `CLUTCH_DESIGN_SPEC_CONFIRM=1`。底栏 Agent / Workflow 在 Design 下禁选；可切换的是 **Model**。CLI 仅在 **Send to Coding** 或 Design-to-Code 工作流之后进入 Coding 编排。
* **侧栏历史**：Design 会话列表展示**与画布一致的界面缩略图**（对已生成 HTML 做等比预览）+ 标题 + 日期；**新对话 / 尚未生成界面**时为灰色缺省占位，不展示假缩略图。点 **New Design** 会新建会话并排在列表顶部（同时清掉未开始的空草稿），不会复用旧的「New Design」行。
* **右侧栏**：与 Coding 相同的可折叠 Overview / Files / Changes / Terminal；进入 Design 时**默认收缩**。产物落在工作区 `.clutch/design/sessions/` 下，**每个会话一个文件夹**，命名为 `{标题}-{web|mobile}__{run_id}`（便于在 Files 中辨认）；**删除侧栏会话时同步删除**对应产物目录（含 HTML / DESIGN.md / React 等）。**Terminal** 会镜像 Design 生成进度（`process_log` 与 status/html 回显），便于排查「侧栏已停转但画布仍 Sketching」类问题。
* **无限画布（Prototype）**：提交后进入 React Flow 画布；有参考时先展示 **Design.md / 网址 / 参考图** 源卡，再**设计规范卡**（色板 / 字体 / 组件），**再**描绘生成界面卡；左侧 **Agent Log** 展示 Thinking 与 Execution，**每条执行记录**以标签形式显示步骤 `status`、所用 **model** 与 **token** 用量（会话中途切换模型时历史步骤仍保留当时标签）；底部浮动条用自然语言修改界面或规范。**选中**画布卡片（UI / 规范 / 参考）后底栏出现上下文 chip；发送时默认在选中 UI 上**就地修改**（明确说「新增/另一个页面」才加新画板）；支持 ⌘/Ctrl+C/V 复制粘贴 UI 卡；UI 卡可 **点选元素** 做局部修改。侧栏转圈与画布 UI 回显对齐：仅在屏幕 HTML 真正可用（或失败）后才结束 busy。
* **界面代码层（UI code，D39/D41）**：入口在 **Preview Demo → Coding**。面板 4 步：批准原型 → **生成前端工程（确定性 HTML→React，非 AI 重画；每屏 `.tsx` + 同源 Tailwind CDN 主题 + 连线写入路由）** → 预览并批准（小窗缩放 / 完整尺寸打开）→ 交给编码。交付物为会话目录 `react/`：前端 UI + 客户端导航已就绪，后续接 API/联调。若已落盘 `interaction_contract.json`，导航写入源码。不以 `generated/` 交接。Windows 下 preview 会解析 `pnpm.cmd` / `npm.cmd` / `npx.cmd` 完整路径，停止或重新生成时清理 Vite/Node 进程树，避免端口残留。
* **非目标**：不替代 Figma 协作；无独立 Design 项目 CRUD 左栏；不生成全栈 Auth/DB；不做云端分享。

内置工作流模板 **Design to Code**（`design-to-code`）可在批准后将设计产物交给 Builder CLI 继续实现。

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

> **已落地（v1.0.0）**：长会话 **Compaction + JSONL 归档** — 见 §3.1；勿在 Backlog 重复立项（B-03）。

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

> 开发期 Sidecar 监听 **8124**；打包桌面安装包内嵌 Sidecar 为 **8123**。`tauri.conf.json` 的 `beforeDevCommand` 为空，由跨平台 `scripts/run-tauri-dev.mjs` → `scripts/tauri-dev.py` 管理 Vite 生命周期，避免 Tauri 误杀 dev server；旧版 Bash 启动器保留为 `pnpm tauri:dev:sh`。

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

**真实连接验收（CLI / API / Ollama / Workflow，无 fake LLM）**：
```bash
./scripts/verify.sh --e2e-real
```
含 13 项 desktop acceptance（U12、B1/B2、Q1 同 session 排队、P1 跨 session 池满排队、X1、I1、N1 New Chat 模型重置、F1、CLI 矩阵）。跑完后 `./scripts/e2e-teardown.sh` 可清理残留 Tauri/Vite/Sidecar 进程。

### 5.4 桌面端打包 (Build DMG / Windows installers)
```bash
pnpm tauri build
```
编译成功后，生产版自动内嵌 Sidecar Python 运行环境，并按当前平台输出 `.dmg`、`.msi` 或 NSIS `.exe` 安装包。Tauri build 通过 `scripts/run-build-sidecar.mjs` 构建 PyInstaller sidecar：优先使用 `uv`，再尝试 `python -m uv`，最后复用 `services/orchestrator/.venv`。桌面壳启动时会清理残留的 Sidecar 进程；**Cmd+Q** 完全退出时终止内嵌 `orchestrator`；macOS 在仅关闭窗口后点击 Dock 图标可重新显示主窗口。

**Windows（v1.0.2+）：** MSI / NSIS 由 CI 构建；维护者尚未在实体 Win10/11 上完成完整人工 smoke，详见 Release 说明与 [`docs/INSTALL.md`](./INSTALL.md#windows)。

---

*本文档基于最新的前后端实现编写。关联架构设计详述见 [系统架构文档](./ARCHITECTURE.md)；文件定位见 [FILEMAP.md](../memory/FILEMAP.md)。*
