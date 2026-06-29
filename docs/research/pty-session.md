# Research Notice

Exploratory material only.

This document is **not** a source of truth.

Do **not** record implementation status or feature completion here.

Current implementation status:

- docs/PRODUCT_INTRO.md
- memory/ROADMAP.md
- docs/ARCHITECTURE.md

---

## 〇、背景回顾

### 0.1 Clutch 当前执行路径（不只 Claude CLI）

Clutch 是本地桌面应用（Tauri + FastAPI Sidecar `localhost:8123`），Plain Chat / Flow 节点经 `EngineRouter` 分流到**多条执行路径**：

| 路径 | `agentType` | 当前调用方式 | 第二阶段 Runtime |
|------|-------------|--------------|------------------|
| **Clutch 内置 LLM** | `clutch` | HTTP API + `mcp_react` 工具循环（Skills / MCP Hub） | `SDK_NATIVE`（本阶段不改） |
| **Claude Code CLI** | `claude-cli` | 每轮 `subprocess`：`claude -p … [--resume\|--session-id]` | **`SHELL_EXEC`**（ShellSession + `claude -p`） |
| **Antigravity CLI** | `antigravity-cli` | 每轮 `subprocess`：`agy -p … [--conversation]` | **`SHELL_EXEC`**（待 Route C 复测） |
| **Ollama CLI** | `ollama-cli` | HTTP `localhost:11434/api/chat`（长驻 daemon） | `HTTP_DAEMON`（已是长驻，不改） |
| **待接入 CLI** | — | `tools_status` 已探测、**未**进 `engine_router`：`codex`、`gemini`、`aider` 等 | 按 §2.2 矩阵选型 |

> **代码快照（2026-06-26）**：前端 `AGENT_TYPE_OPTIONS` 与后端 `AGENT_TYPES` 均为 **`clutch` · `claude-cli` · `ollama-cli` · `antigravity-cli` 四类**。`tools_status.CLIENT_CANDIDATES` 为空，**不再探测 macOS 桌面客户端**；`cursor-workspace` 仅残留于 `engine_router` / `agent_type` 的 legacy 映射，UI 不可选且 `cursor-app` 不在工具目录中，**实际不会路由**。PTY 改造针对 **CLI 子进程类后端**；`clutch` LLM 与 Ollama HTTP 不在本阶段范围。

### 0.2 CLI 路径的共性架构问题

对已路由的 CLI 后端（`claude-cli`、`antigravity-cli`），当前均为 **Request → Subprocess → Exit**：

```
用户发一句
    ↓
spawn claude / agy（-p print 模式）
    ↓
等待 stdout 结束
    ↓
进程退出
```

即使已通过 D20 落地 **逻辑 Session**（`ClutchState.cli_session_id` + `--resume` / `--conversation`；读盘兼容旧字段 `claude_session_id`），仍是**每轮新建子进程**，带来：

- 每轮冷启动（Node 类 CLI 约 1.5~2.5s VM 初始化）
- `--resume` 恢复的是**对话上下文**，不是 **cwd / shell / git / 工具运行时** 的物理继承
- 无法在 PTY 内维持 dev server、交互式 shell、长驻工具状态
- 人机确认提示（`Allow tool?`）跨进程难以可靠承接

业界主流 Agent 工具（Open Interpreter、SWE-agent、Cursor、Aider、Codex CLI 等）对交互型编码 Agent 多采用 **Session → Runtime → Many Requests → Exit**，核心是让后台终端进程长期存活，通过 PTY 或常驻 Daemon 实现物理状态继承。

### 0.3 分阶段推进

| 阶段 | 内容 | 工程量 | 收益 |
|---|---|---|---|
| 第一阶段 | 前端 Streaming（打字机效果）+ Terminal 行级日志 | 小 | 体感提升大；CLI 侧 `cli_adapter.on_line` 已具备行级流，前端投影待补齐 |
| **第二阶段（本文档）** | **ShellSession**（长驻 shell PTY + per-turn exec） | 大 | **消除 shell 冷启动，物理继承 cwd/env/dev server** |
| 第三阶段 | 统一 Agent Runtime 抽象层 | 大 | Provider 插件化、跨引擎监督、任务队列与中断恢复 |

> **与 v1 非目标表述的校正**：Clutch **已有**多引擎路由（`engine_router`）与工具探测（`tools_status`）。第三阶段的重点是 **Runtime 抽象与治理**（统一 Session 模型、边界检测插件、监督门控），而非「从零接入多 Provider」。

### 0.4 产品叙事（对用户 / PM）

> 对外一句话：**Clutch 不再每次都「重新上班」，而是像真正的开发助手一样，整个会话期间一直坐在工位上工作。**

#### 旧方案（现网）

用户每说一句话，Clutch 都会**重新启动一次 Claude**——更像每次从零开机：

```
用户：帮我改个 bug

Clutch：
  1. 开电脑
  2. 打开终端
  3. 启动 Claude
  4. 干活
  5. 关掉一切

下一句 → 再重复一遍
```

用户体感：**「怎么又要等几秒？」**（Node CLI 冷启动约 1.5~2.5s，叠加模型首 token。）

#### 新方案（ShellSession · 即将上线）

Clutch **自己一直保持一个工作终端**，Claude **只是随叫随到**：

```
用户打开项目 / 新建聊天
        ↓
Clutch 启动一个长期存在的工作终端（ShellSession）
        ↓
之后所有对话都在这个终端环境里继续
        ↓
每轮在终端里 exec：claude -p "…" / agy -p "…"
```

用户可感知收益：

| 维度 | 旧方案 | 新方案 |
|------|--------|--------|
| 当前目录 | 每轮重新 `cwd=` | **PTY 内 `cd` 跨轮保留** |
| dev server | 难以 `npm run dev &` 长驻 | **后台进程持续运行** |
| 环境变量 | 每轮丢失 | **`export` 跨轮保留** |
| 响应速度 | 每句含 shell/CLI 冷启动 | **首次稍慢，之后明显更流畅** |

**核心比喻**：Clutch 保持的是 **「工作环境」（工位 + 电脑 + 项目）**，不是无限记忆的 Claude 长对话。程序员可以换班，工位和项目不丢——详见 §2.6。

---

## 一、目标与非目标

### 1.1 目标

- 将 **CLI 类 Agent 后端**从「每轮请求新建 shell 上下文」改为「每个 Clutch run 一个 **ShellSession**（长驻 bash PTY），每轮在 shell 内 **exec** Provider 命令」
- **Runtime 无关的 Session 管理层**：状态机、并发控制、健康检查对 `SHELL_EXEC` 策略统一生效；Provider 差异收敛到 `RuntimeStrategy` + `ExecSpec` + `BoundaryDetector`
- 解决 shell / cwd / dev server 冷启动，同时**不驱动上游 Ink TUI**
- 与现有 `ClutchState` 持久化、`WebSocket state_patch`、LangGraph 监督模型对齐
- 产出可量化的验收标准

### 1.2 非目标（本阶段不做）

- **`clutch` LLM + MCP ReAct 路径**的改造（已是 API 长连接 / 无子进程）
- **Ollama HTTP** 路径改造（`ollama serve` 已长驻）
- **完整「记忆换班 / 恢复工作」产品体验**（`SessionSnapshot`、继续上次工作 — 见 §2.6，**Step 3** 单独排期）
- Token 统计、计费（见 BACKLOG B-02）
- 跨 run 任务队列、多 Agent 协同（LangGraph 图编排已有，PTY 层不重复造）
- 容器级 sandbox（见 BACKLOG B-20；本阶段目录级隔离 + 操作日志为底线）
- **一次性全量切换 Hybrid**（见 §1.4；legacy 路径必须保留至灰度结束）

### 1.3 与现有 D20 决策的关系

| 维度 | D20 已落地（逻辑 Session） | 第二阶段 ShellSession（物理 Session） |
|------|---------------------------|--------------------------------------|
| 进程模型 | 每轮新子进程（含新 shell 上下文） | 单 run 单长驻 **bash** PTY；每轮 exec `claude -p` 等子进程 |
| 上下文 | `--resume session_uuid` | shell 内自然延续 + 可选 `--resume` 兜底 |
| 状态字段 | `cli_session_id` + `cli_session_agent_id` | 可选 `cli_provider`；`ShellSession` 物理句柄 |
| cwd/shell | 每轮重新 `cwd=` 传入 | PTY 内 `cd` / `export` / 后台进程跨轮保留 |
| 失败恢复 | 历史重放 + 新 session id | Shell 重建 + 可选历史回放 + 前端明示 |

ShellSession 是 D20 的**架构升级**，不是替代：重建 shell 时仍可 fallback 到 `--resume` / 历史重放。

### 1.4 上线安全策略（不影响现网）

> **结论**：有风险，但**可控**。前提是 **不一次性替换**现网路径，而是以 Feature Flag + 自动降级 + 灰度接入。  
> Hybrid 每轮仍是 `claude -p`——**最坏情况是关 Hybrid、回到 legacy，核心 AI 能力不会整体瘫痪**。

#### 1.4.1 双轨并行：Legacy 必须始终保留

| 模式 | 实现 | 默认 |
|------|------|------|
| **legacy** | 现网 `subprocess` + `claude -p`（每轮新进程，`cwd=` 传入） | ✅ **默认** |
| **hybrid** | `ShellSession`（长驻 bash）+ shell 内 `claude -p` exec | Beta，需显式开启 |

配置示意（Sidecar / 环境变量，Step 1 落地）：

```yaml
# 或 CLUTCH_RUNTIME_MODE=legacy|hybrid
runtime:
  mode: legacy          # 默认；仅开发/内测改为 hybrid
  hybrid:
    enabled: false
    plain_chat_only: true    # 第一版仅 Plain Chat
    providers: [claude-cli]  # 第一版仅 Claude
```

```python
ENABLE_HYBRID_RUNTIME = False  # 代码侧等价开关；默认 False
```

**铁律**：Step 1 **增加** Hybrid 路径，**禁止删除或替换** legacy `claude_cli_adapter` 直连逻辑，直至灰度验证通过。

#### 1.4.2 失败自动降级（用户无感兜底）

```
用户发消息
      ↓
runtime.mode == hybrid ?
      ├─ 否 → legacy subprocess（现网）
      └─ 是 → ShellExecRuntime.run_turn()
                ↓
            成功 → 返回
                ↓
            失败（超时 / PTY 死 / Detector 异常 / 交互式命令拦截）
                ↓
            自动 fallback → legacy subprocess
                ↓
            state_patch：「本次已切换到兼容模式」（可选，非阻塞）
```

单轮降级 **不得** 使整个 `run_id` 永久不可用；同一聊天下一轮可重试 Hybrid（可配置冷却）。

#### 1.4.3 灰度范围（第一版刻意收窄）

| 范围 | Step 1 Hybrid | 保持 legacy |
|------|---------------|-------------|
| **Plain Chat** | ✅（开关开启时） | 默认仍走 legacy |
| **Agent Flow / LangGraph 节点** | ❌ | ✅ |
| **`claude-cli`** | ✅ | 开关关闭时 |
| **`antigravity-cli` / `ollama-cli` / `clutch`** | ❌ | ✅ |

即使 Hybrid 有 Bug，**影响面 = 自愿开启 Beta 的 Plain Chat + Claude**，不会拖垮 Flow 或其他 Provider。

#### 1.4.4 已知风险与缓解

| 风险 | 现象 | 缓解（Step 1） |
|------|------|----------------|
| **cwd 污染** | 用户 `cd /tmp` 后下一轮路径不对 | 每轮 exec 前 `cd "$workspace"` 或 `session.ensure_workspace_cwd()`；可选仅对 Agent 轮次锚定 |
| **后台进程泄漏** | `npm run dev &` 堆积，CPU 升 | 已有 §2.4：**30min 空闲回收**、**6h 最大重建**；审计日志记录后台任务 |
| **Shell 卡死** | `vim` / `less` / `top` / `ssh` 占住 PTY | v1 **禁止交互式命令**；检测到即 **本轮 fallback legacy** + 提示 |
| **Hybrid 整体不可用** | ShellSessionManager 崩溃 | Flag 置 `legacy` 或热关闭 `ENABLE_HYBRID_RUNTIME`；零代码回滚 |

#### 1.4.5 风险等级重估

| 若无 Flag 一次性替换 | 有 Flag + 降级 + 灰度 |
|----------------------|------------------------|
| 高风险架构重构 | **可灰度、可回滚的性能优化** |

**对产品/用户的承诺**：默认行为与现网一致；Hybrid 是 **可选 Beta**，失败时单轮或单会话回退，不会出现「所有聊天全部不可用」。

---

## 二、核心设计决策

改造为 ShellSession 后，会暴露四个工程问题：**Session 状态机、Runtime 策略选型、边界检测、资源隔离与健康检查**。以下设计以 **RuntimeStrategy** 分层；§2.3 边界检测按 Provider 分表。

### 2.0 Session 状态机（前置，强烈建议）

**问题本质**：Shell PTY 下 stdin 是共享管道。无状态机时，用户连续发两条消息会导致并发写 stdin、输出串台——最难复现的线上故障类型。

#### 2.0.1 Session Ownership（建议纳入数据模型）

未来 LangGraph Flow 可能出现 **多个节点共享同一 `run_id` 下的同一个 ShellSession**（例如 Research → Coding → Review 共用一条 bash）。此时仅有 `run_id` 不足以审计「谁写了 stdin」。

建议核心结构：

```python
@dataclass
class ShellSession:
    run_id: str
    exec_provider: str     # 当前轮执行的 CLI：claude-cli | antigravity-cli | …
    owner_node_id: str     # 当前持有写入权的 LangGraph node_id；Plain Chat 可用 "plain_chat"
    session_id: str        # 对外 cli_session_id / Provider 原生 id
    state: SessionState
    human_input_kind: HumanInputKind | None  # 见 §2.0.2
    # 长驻层：bash PTY PID、cwd、env 快照等
```

**规则（POC 可先简化，设计须预留）**：

| 场景 | `owner_node_id` | 写入策略 |
|------|-----------------|----------|
| Plain Chat | `plain_chat` 或空 | 单用户单写入 |
| Flow 单节点活跃 | 当前 `agent_task` 的 `node_id` | 节点开始时 claim，结束时 release → `IDLE` |
| Flow 多节点共享 PTY（后续） | 显式 handoff | 未持有 owner 的节点 **不得** 写 stdin |

**日志与 WS 事件最小字段**（对齐 `CLAUDE.md` 日志规范，并扩展 PTY 审计）：

| 字段 | 说明 |
|------|------|
| `run_id` | Clutch 会话 / LangGraph run |
| `node_id` | 写入发起方（Plain Chat 填 `plain_chat`） |
| `source` | 如 `shell_session` / `cli_adapter` |
| `provider` | `claude` / `agy` / … |
| `session_id` | `cli_session_id` 或 Provider 原生 id |
| `message` | 人类可读一行（禁止含密钥） |

否则 stdout 仅显示 `Fix bug...` 时，无法追溯是 Research 还是 Coding 节点注入的 prompt。

**POC 阶段**：可维持「一 `run_id` 一 PTY + `owner_node_id` 字段恒为当前活跃节点」；**不在 POC 做跨节点并发共享**，但接口与日志须带 `node_id`。

#### 2.0.2 人机等待状态 — `HumanInputKind` 扩展点

`WAITING_FOR_INPUT` 作为**父状态**过粗；不同等待类型 UI 与恢复逻辑不同。`HumanInputKind` 是 **Runtime 一级概念**——由 Detector / Boot Handler 产出，**禁止**在业务层写 `if "trust" in text` 式 Provider 特判。

```python
class HumanInputKind(str, Enum):
    BOOT_TRUST = "boot_trust"       # 首次进入 workspace；每目录一次
    TOOL_CONFIRM = "tool_confirm"   # Allow tool / Overwrite? — 必须用户审批
    TEXT = "text"                   # Paste token、自由文本、多行说明
    AUTH = "auth"                   # Login required、OAuth、API key 提示
```

> `claude -p`（print / 非 TTY）**跳过** workspace trust，但 **codex / gemini / aider** 等未来 Provider 未必。`BOOT_TRUST` 仍须在 Runtime 层统一建模，供 `INTERACTIVE_PTY` 策略与偶发 TUI 降级使用。

| 父状态 | `HumanInputKind` | 典型 CLI 提示 | 前端（规划） | 自动策略 |
|--------|------------------|---------------|--------------|----------|
| `WAITING_FOR_INPUT` | `BOOT_TRUST` | `1. Yes, I trust this folder`；`Bypass Permissions` → `Yes, I accept` | 首次工作区引导 | **可自动**（每 workspace 一次；Bypass 需 ↓+Enter） |
| `WAITING_FOR_INPUT` | `TOOL_CONFIRM` | `Allow tool?`、`(y/n)`、`Overwrite?` | 审批卡片 / 双按钮 | **禁止**自动 |
| `WAITING_FOR_INPUT` | `TEXT` | `Paste token:`、多行输入 | 文本框 | 视策略 |
| `WAITING_FOR_INPUT` | `AUTH` | `Login required` | 外链 / 凭证引导 | 人工 |
| `WAITING_FOR_INPUT` | （未分类） | 未匹配 | 通用「Agent 等待输入」 | 人工 |

Detector / BootHandler 命中人机等待时：`state → WAITING_FOR_INPUT` + `human_input_kind` + `human_required` 事件（含 `kind` 字段）。POC 实现 `BOOT_TRUST` + `TOOL_CONFIRM`；其余提示暂映射为 `TEXT` / `AUTH`。

**建议状态集合**

| 状态 | 含义 |
|---|---|
| `CREATING` | PTY 进程正在启动，尚未就绪 |
| `READY` | 进程已就绪，可以接受新请求 |
| `BUSY` | 正在处理一个请求（含等待模型输出、执行工具调用） |
| `WAITING_FOR_INPUT` | `BUSY` 子状态：CLI 等待人机输入（见 §2.0.2 `HumanInputKind`） |
| `IDLE` | 已完成上一个请求，等待下一次输入 |
| `DISCONNECTED` | 进程异常退出或失去响应 |
| `RECOVERING` | 正在重建 PTY 进程 |
| `TERMINATED` | 会话已被主动销毁（用户结束 / 空闲回收 / 达到最大生命周期） |

**状态流转**

```
CREATING
   │
   ▼
READY ───────────┐
   │              │
   │ 收到请求       │ 空闲超时 / 达到最大生命周期（仅 IDLE，见 §2.5）
   ▼              ▼
BUSY ──(确认提示)──► WAITING_FOR_INPUT ──(用户确认)──► BUSY
   │
   │ 输出结束
   ▼
IDLE ──────────────┐
   │                │
   │ 收到新请求       │
   ▼                │
BUSY ◄──────────────┘

(任意状态) ──进程异常退出──► DISCONNECTED ──自动恢复──► RECOVERING ──成功──► READY
```

**关键约束**：

- 只有 `READY` 或 `IDLE` 可接受新请求并转入 `BUSY`
- `BUSY` / `WAITING_FOR_INPUT` 收到新请求时，必须走 §2.1 并发策略，**绝不能直接写 stdin**
- `DISCONNECTED → RECOVERING → READY` 不可跳过 `RECOVERING`
- **最大存活重建**（§2.5）仅在 `IDLE` 触发；`BUSY` / `WAITING_FOR_INPUT` 期间**禁止** kill + respawn

**Clutch 映射**：Plain Chat — 一 `run_id` 一 **ShellSession**；Flow — **默认仍是一 `run_id` 一 ShellSession**（多节点通过 `owner_node_id` handoff）。`agent_id` 切换时可复用同一 shell 或按需重建（对齐 D20）。

---

### 2.1 单 Session 并发输入策略（必须明确）

**第二阶段策略：一个 ShellSession 同时只允许一个任务执行。**

| 方式 | 实现 | 适用场景 |
|---|---|---|
| 拒绝（Reject） | `if session.state in (BUSY, WAITING_FOR_INPUT): reject()` | POC 首选，实现简单 |
| 排队（Queue） | `queue.put(task)`，当前轮结束后消费 | 后续按用户习惯评估 |

参考：Cursor、Claude Code、Codex CLI 均遵循「单 Session 单任务」。同 Session 并发留给更晚阶段。

---

### 2.2 Runtime Strategy Matrix

Step 0 结论：**不为 Claude 驱动 Ink TUI**。第二阶段默认 **长驻 Shell + per-turn exec**；`INTERACTIVE_PTY` 仅保留为策略枚举值，供未来 Provider 实测后选用，**不作为 Claude 默认路径**。

#### 2.2.1 `RuntimeStrategy` 枚举（第三阶段 Runtime 雏形）

```python
class RuntimeStrategy(str, Enum):
    SHELL_EXEC = "shell_exec"           # 长驻 shell PTY + 每轮 exec 子命令（Route C）
    INTERACTIVE_PTY = "interactive_pty" # 长驻 Provider TUI PTY（expect 驱动；Claude 已否决）
    HTTP_DAEMON = "http_daemon"         # 长驻 HTTP 服务（Ollama 等）
    SDK_NATIVE = "sdk_native"           # 进程内 SDK / API（Clutch LLM + mcp_react）
```

**EngineRouter 演进方向**（Step 3+）：不再 `if provider == "claude"`，而是：

```python
strategy = provider_registry.get(agent_type).runtime_strategy
runtime = runtime_registry.dispatch(strategy)
result = await runtime.execute_turn(shell_session, turn_spec)
```

Provider 注册表示例：

```python
@dataclass(frozen=True)
class ProviderSpec:
    agent_type: str
    runtime_strategy: RuntimeStrategy
    exec_template: str | None   # SHELL_EXEC: "claude -p {prompt!r} …"
    boundary_detector: str      # 插件 id
```

#### 2.2.2 Provider × Strategy 矩阵

| Provider | `agentType` | `RuntimeStrategy` | 每轮调用形态 | Step 0 状态 |
|----------|-------------|-------------------|--------------|-------------|
| Claude Code | `claude-cli` | **`SHELL_EXEC`** | `claude -p "…"`（shell 内 exec） | ✅ Route C 5/5 |
| Antigravity | `antigravity-cli` | **`SHELL_EXEC`**（待验证） | `agy -p "…"` | ⏳ 待 Route C 复测 |
| Codex CLI | `codex`（未接入） | **`SHELL_EXEC`**（预期） | `codex exec …` | ⏳ B-17 预研 |
| Aider | `aider`（仅探测） | **TBD** | 可能 `INTERACTIVE_PTY` 或 `SHELL_EXEC` | ⏳ 待实测 |
| Gemini CLI | `gemini`（仅探测） | **TBD** | 待 help / POC | ⏳ |
| Ollama | `ollama-cli` | `HTTP_DAEMON` | `POST /api/chat` | 已路由，不改 |
| Clutch LLM | `clutch` | `SDK_NATIVE` | `LLMProviderRouter` + `mcp_react` | 已路由，不改 |

**`SHELL_EXEC` 语义**：

```
ShellSession（长驻 bash PTY）
    ├── cwd
    ├── env
    ├── dev servers（npm run dev &）
    ├── shell history
    └── long-running processes
              │
              │  exec command（每轮）
              ▼
     ┌────────────────────┐
     │ claude -p "…"      │
     │ agy -p "…"         │
     │ codex exec …       │
     └────────────────────┘
              │
              ▼
     子进程退出 → BoundaryDetector 判定轮次结束
```

与「长驻 `claude` TUI PTY」的本质区别：**PTY 里是 shell，不是 Claude**；Claude 仅是 shell 的一轮子进程。

---

### 2.3 输出边界检测（按 Provider 分策略）

PTY 是持续字符流，必须定义「本轮结束」判据。**不同 CLI 能力差异大，不能用单一方案覆盖所有 Provider。**

#### 2.3.1 通用方案对比

| 方案 | 原理 | 优点 | 缺点 |
|---|---|---|---|
| A. Sentinel 标记 | 约定输出 `<<<CLUTCH_DONE>>>` | 精确 | 需 CLI 原生支持；靠 prompt 注入不可靠 |
| B. 空闲超时 | N 秒无输出视为结束 | 实现简单 | 长思考/工具调用易误判 |
| C. Prompt 回显 | 检测交互提示符（`> `） | 较可靠 | 依赖 CLI 内部格式，升级易碎 |
| **D. 结构化协议（CLI 首选）** | `--output-format stream-json` 等事件流 | 边界明确，可展示工具进度 | 因 Provider 而异，需实测 |
| E. 退出码 + print 模式 | 子进程结束即一轮完成 | **SHELL_EXEC 首选** | 需 sentinel / stream-json 区分 echo |

#### 2.3.2 各 Provider 边界检测矩阵（POC 前需实测填空）

| Provider | 二进制 | `RuntimeStrategy` | 结构化输出 | POC 建议策略 | 备注 |
|----------|--------|-------------------|------------|--------------|------|
| Claude Code | `claude` | `SHELL_EXEC` | **`stream-json` 仅 `--print` + `--verbose`** | **D（stream-json）+ sentinel marker** | print 跳过 BOOT_TRUST |
| Antigravity | `agy` | `SHELL_EXEC` | 待验证 | 同 Claude 流程独立实测 | 已进 `engine_router` |
| Codex CLI | `codex` | `SHELL_EXEC`（预期） | Codex 有事件流生态 | 接入时以 D 为主 | B-17 |
| Gemini CLI | `gemini` | TBD | 待验证 | POC 不阻塞 | 后续注册 |
| Aider | `aider` | TBD | 多为 TUI | 可能 `INTERACTIVE_PTY` | 交互模型不同 |
| Ollama | `ollama` | `HTTP_DAEMON` | N/A | **不纳入 ShellSession** | 长驻 daemon |

**落地策略**：

1. 定义 `CliBoundaryDetector` 接口：`on_bytes() -> events`、`is_turn_complete() -> bool`、`is_waiting_for_user() -> bool`
2. **POC 先实现 `claude` + `agy` 两个 Detector**；`codex` 接入时新增第三个，不改动 SessionManager
3. 禁止单独依赖方案 A（除非 CLI 原生支持）
4. 人机交互等待（`Allow tool?`、`(y/n)`、`Paste token:` 等）优先级**高于**空闲超时 → `WAITING_FOR_INPUT` + `human_required`（含 `HumanInputKind`）

> ⚠️ **POC Step 0**：见 [`experiments/pty_poc/`](../../experiments/pty_poc/) — Route C 已通过；填 §2.3.2 与 `baseline/*.json`。

---

### 2.4 资源隔离

#### 2.4.1 进程数量控制

| 维度 | 设计 |
|---|---|
| 会话与进程 | **一个活跃 `run_id` = 一个 ShellSession（bash PTY）**；不按 Provider 共享 shell |
| 并发上限 | 本机桌面场景：全局最大并发 PTY 数（建议先压测单进程内存再定） |
| 超限策略 | 排队 + 超时拒绝；`state_patch` + UI 提示「会话较多，请稍候」 |
| 空闲回收 | 默认 30 分钟无活动销毁（可配置） |
| 最大存活 | 建议 6 小时优雅重建（防 Node fd/内存泄漏） |

> **校正 v1「多用户」表述**：Clutch 是**单机桌面应用**，此处「并发」指同一台机器上多个 `run_id` / 工作流并行，而非云端多租户。

#### 2.4.2 文件系统与执行隔离

| 风险点 | 缓解措施 |
|---|---|
| PTY 内可执行任意 shell 命令 | 绑定 `workspace_path`（`get_workspace()`）；后续 B-20 sandbox |
| 长驻进程放大危险操作窗口 | 操作日志审计（命令、cwd、时间戳；**必含** `run_id` / `node_id` / `provider` / `session_id` / `source`） |
| 多 Session 资源争抢 | 评估 cgroup / `ulimit`（可选） |

POC 范围：**独立工作目录 + 操作日志**；容器 sandbox 不阻塞 POC。

---

### 2.5 健康检查与异常恢复

| 检查项 | 实现方式 |
|---|---|
| 进程存活 | 定期检测 PTY PID / zombie |
| 响应性 | 轻量探测（Provider 内置 status 或空行） |
| 异常退出 | 捕获 exit code + stderr；区分用户主动结束 vs 崩溃 |
| 自动恢复 | **不静默重启** → `state_patch` 通知前端「会话断开，正在重建」 |
| 恢复后上下文 | PTY 物理状态丢失 → 可选 `--resume` / 历史重放；用户感知优先 |

| 回收触发 | 说明 |
|---|---|
| 空闲超时（30min 可配置） | 用户不活跃；**可在 `IDLE` 立即销毁** |
| 最大存活（6h 可配置） | 防进程劣化；**仅当状态为 `IDLE` 时**调度优雅重建 |

**最大存活重建铁律**：

- 调度器发现「已达最大存活时间」时，若状态为 `BUSY` 或 `WAITING_FOR_INPUT` → **只标记 `rebuild_pending`，等当前轮结束进入 `IDLE` 后再执行** kill + respawn。
- **绝不在** Agent 修改文件 / 工具执行中途强杀 PTY——否则工作区可能半写入、用户无感知。
- 进入 `RECOVERING` 前通过 `state_patch` 通知用户（与异常恢复同一原则）。

> Shell 崩溃 / 回收后的**摘要注入与「继续工作」**属于 §2.6 Context Continuity，不在 Step 1 范围。

---

### 2.6 Context Continuity Strategy（工作环境 vs AI 记忆）

**设计原则**：Clutch 保持的是 **工作环境**，不是无限记忆。

```
┌─────────────────────────────────────┐
│  ShellSession（工位）  ← 长期保留      │
│  cwd · env · dev server · git state  │
└─────────────────┬───────────────────┘
                  │ 每轮 exec
                  ▼
┌─────────────────────────────────────┐
│  Claude / agy 进程（程序员）← 可换班   │
│  对话上下文 · --resume session       │
└─────────────────────────────────────┘
```

**一句话（PM）**：**工作环境长期保留，AI 记忆可以随时更换。**  
**比喻**：Claude 像程序员，终端像工位；程序员可以换班，工位和项目不会丢。

#### 2.6.1 方案完成度一览

| 能力 | 状态 | 所在步骤 | 说明 |
|------|------|----------|------|
| 一聊天 = 一 `run_id` = 一 ShellSession | ✅ 已设计 | Step 1 | Chat A / Chat B 互不影响，不串 `cd` |
| Session 状态机 + 空闲/最大存活回收 | ✅ 已设计 | Step 1 | `CREATING`…`TERMINATED`；30min / 6h |
| Hybrid 天然短 Claude 记忆 | ✅ 已设计 | Step 1 | 每轮 `claude -p` 新进程；shell 长驻 |
| 上下文满 → shell 保留 + Claude 换班 | ⚠️ 部分 | Step 1 基础 + **Step 3** | Step 1：`--resume` / 历史重放；Step 3：摘要注入策略 |
| `SessionSnapshot`（销毁前快照） | ⚠️ 待设计 | **Step 3** | cwd、branch、dev server、任务摘要 |
| 「继续上次工作」/ 恢复 Session 产品入口 | ⚠️ 待设计 | **Step 3~4** | 重新挂载 shell 或从 Snapshot 重建 |
| 跨天持久化（关机后恢复） | ⏳ 后续 | Step 4+ | 依赖 Snapshot 落盘 + 工作区绑定 |

#### 2.6.2 场景：Claude 上下文满了怎么办？

`SHELL_EXEC` 下每轮已是独立 `claude -p` 子进程，**不易出现「单进程上下文爆满」**；但若对话轮次极多、或启用 `--resume` 长会话导致 Provider 侧窗口紧张：

| 层 | 行为 |
|----|------|
| **ShellSession** | **不变** — `cd frontend`、`npm run dev &`、`export API_KEY=…` 仍在 |
| **Claude 会话** | **换班** — 新 `cli_session_id` / 新 `--resume` 链；必要时丢弃旧链 |
| **Clutch** | 自动把**必要信息**重新喂给新 Claude：项目摘要、最近 N 轮、未完成事项（Step 3） |

用户体感：**「换了一个新同事接班，但工位、电脑和项目都没换。」**

#### 2.6.3 场景：用户新开一个聊天

**默认规则**：

```
聊天 A（run_id_A）→ ShellSession A → workspace / cwd 独立
聊天 B（run_id_B）→ ShellSession B → 互不影响
```

不会出现：聊天 A 里 `cd frontend`，聊天 B 里 `ls` 结果莫名变化。

#### 2.6.4 场景：用户想继续之前的工作

产品层（Step 3~4）可提供：

- **继续上次工作** — 列出近期 `TERMINATED` / 空闲回收的 Session
- **恢复 Session** — 从 `SessionSnapshot` 重建 shell 环境

用户体感：**昨天做到一半，今天回来继续** — 类似重新打开 IDE。

#### 2.6.5 `SessionSnapshot`（Step 3 数据模型 · 草案）

Session 进入 `TERMINATED` 或空闲回收前，可选持久化快照（路径待定，如 `runs/snapshots/{run_id}.json`）：

```python
@dataclass
class SessionSnapshot:
    run_id: str
    workspace_path: str
    cwd: str
    git_branch: str | None
  # env_redacted: dict[str, str]   # 键名可存，值脱敏或省略
    recent_commands: list[str]     # 最近 N 条审计命令
    active_dev_servers: list[str]  # 如 "npm run dev :5173"
    task_summary: str              # Clutch 生成的任务摘要
    open_todos: list[str]          # 未完成事项
    cli_session_id: str | None     # 最后一次 Provider 逻辑 session
    captured_at: str               # ISO 8601
```

**恢复流程（目标）**：

```
Session 销毁 / 回收
        ↓
保存 SessionSnapshot（若用户开启「可恢复」或产品策略要求）
        ↓
用户点击「继续工作」
        ↓
新建或重连 ShellSession → 按快照 cd / export / 提示重启 dev server
        ↓
向新 Claude exec 注入 task_summary + open_todos
        ↓
继续对话
```

Step 1 **仅**实现：销毁时可选写入最小快照（`cwd` + `run_id`）；完整 Snapshot 与 UI 在 Step 3。

---

## 三、整体架构

### 3.0 Step 0 三路线决策门（BLOCKER）

**原则**：不要让架构对抗上游产品设计。若 Claude CLI 本质是面向人类的 Ink/React TUI，持续 expect 驱动成本可能远大于收益。

| 路线 | 优先级 | 目标 | 通过标准 | 失败后果 |
|------|--------|------|----------|----------|
| **A** | 最高 | 真 PTY + **pexpect** 驱动 `claude` 交互 TUI | 连续 **5/5** 轮 prompt→output | **停止全量 Claude TUI PTY** |
| **B** | 并行 | 扫描 `--headless` / pipe / non-TUI 官方模式 | 发现可用 headless 旗标 | 若无，PTY 难度不变 |
| **C** | **Plan B**（高概率） | **Hybrid Runtime**：长驻 **bash** PTY + 每轮 `claude -p` | 连续 **5/5**；cwd 继承成立 | 成为 Step 1 默认架构 |

实验脚本：[`experiments/pty_poc/README.md`](../../experiments/pty_poc/README.md)

**Route A 流程**（`step0_route_a_pexpect_probe.py`）：

```
pexpect.spawn("claude")
  → expect(BOOT_TRUST) → send("1\r")   # 已信任 workspace 可跳过
  → expect(prompt_ready)
  → send(prompt + "\r") → expect(output)
  × 5 轮
```

**Route C 架构**（`step0_route_c_hybrid_probe.py`）— 若 A 未 5/5，**立即转向**：

```
PtySession (per run_id)
    └── bash (长驻 PTY)
            ├── cd / export / npm run dev …   # shell 状态继承
            └── claude -p "…"               # 每轮子进程，避免驱动 TUI
```

保留：cwd、环境变量、后台 dev server。  
避免：Ink TUI expect、BOOT_TRUST 在 print 模式已跳过（Route B 已确认）。

**Step 0 结论**：Route A 未过 → **Route C 为默认**。Step 1 实现 **ShellSessionManager + `SHELL_EXEC`**，不实现 Claude TUI PTY。

### 3.1 目标架构（ShellSession · Route C）

```
Frontend (React 19)
    │  WebSocket / HTTP  localhost:8123
    ▼
Sidecar (FastAPI main.py)
    │  Plain Chat / LangGraph agent_task
    ▼
EngineRouter (engine_router.py)
    │
    ├── agentType=clutch ──────────► SDK_NATIVE · LLMProviderRouter + mcp_react
    ├── agentType=ollama-cli ──────► HTTP_DAEMON · ollama_adapter
    │
    └── agentType ∈ {claude-cli, antigravity-cli, codex, …}
              │
              │  strategy = provider.runtime_strategy   # 见 §2.2
              ▼
┌──────────────────── ShellSessionManager ────────────────────┐
│  ShellSession(run_id, owner_node_id, session_id, state)      │
│  Session 状态机 · 并发控制 · 健康检查 · HumanInputKind        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              ShellSession（长驻 bash PTY）               │  │
│  │  cwd · env · dev servers · shell history · 后台进程     │  │
│  └──────────────────────────┬─────────────────────────────┘  │
│                             │ exec command（每轮）            │
│  ┌──────────────────────────▼─────────────────────────────┐  │
│  │ ShellExecRuntime（SHELL_EXEC）                          │  │
│  │  claude -p · agy -p · codex exec …                       │  │
│  └──────────────────────────┬─────────────────────────────┘  │
│                             │                                │
│  ┌──────────────────────────▼─────────────────────────────┐  │
│  │ BoundaryDetector（按 Provider 插件）                      │  │
│  │  stream-json / sentinel / exit code                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**ShellSession 盒内状态**（用户视图与实现一致）：

```
┌─────────────────────────────┐
│        ShellSession         │
│                             │
│  cwd                        │
│  env                        │
│  dev servers                │
│  shell history              │
│  long running processes     │
│                             │
└─────────────┬───────────────┘
              │
        exec command
              │
     ┌────────▼─────────┐
     │ claude -p        │
     │ agy -p           │
     │ codex exec       │
     └──────────────────┘
```

**明确不做**：`CliSessionManager → Claude PTY（长驻 Ink TUI）` — Route A 已否决。

### 3.2 EngineRouter 与 Runtime 分发（第三阶段衔接）

| 阶段 | `engine_router.py` 行为 |
|------|-------------------------|
| **现网** | `if agent_type == "claude-cli": claude_cli_adapter…` |
| **Step 1~2** | 引入 `ShellSessionManager`；CLI 路径经 `SHELL_EXEC` runtime |
| **Step 3+** | `strategy = provider.runtime_strategy` → `runtime_registry.dispatch(strategy)` |

```python
# 目标形态（示意）
provider = provider_registry.resolve(agent_type)
match provider.runtime_strategy:
    case RuntimeStrategy.SHELL_EXEC:
        return await shell_exec_runtime.run_turn(session, turn)
    case RuntimeStrategy.HTTP_DAEMON:
        return await http_daemon_runtime.run_turn(session, turn)
    case RuntimeStrategy.SDK_NATIVE:
        return await sdk_native_runtime.run_turn(session, turn)
    case RuntimeStrategy.INTERACTIVE_PTY:
        return await interactive_pty_runtime.run_turn(session, turn)  # 非 Claude 默认
```

**与现有代码的落点建议**（避免推翻重写）：

| 模块 | 现状 | 第二阶段演进 |
|------|------|--------------|
| `cli_adapter.py` | `subprocess.run` / `Popen`，`stdin=DEVNULL` | 新增 `shell_session.py` · `ShellExecRuntime` |
| `claude_cli_adapter.py` | 拼 `claude -p` 命令 | 改为 shell 内 exec 模板；保留直连 subprocess 作降级 |
| `agy_cli_adapter.py` | 同上 | 同上 |
| `engine_router.py` | 每轮调 adapter | 经 `ShellSessionManager.get_or_create(run_id)` + `SHELL_EXEC` |
| `ClutchState` | `cli_session_id` | 可选 `cli_provider` |
| `main._handle_plain_chat` | 持久化 session id | 对接 ShellSession 生命周期 |

---

## 四、POC 验收清单

**范围**：单用户、单 `run_id`；**主验证 `claude-cli`，副验证 `antigravity-cli`**（因已路由）。

| # | 验收项 | 验证方法 | 通过标准 |
|---|---|---|---|
| 1 | 冷启动只发生一次 | 同 run 内连续 5 条消息，对比耗时 | 第 1 条含冷启动；第 2~5 条显著下降（排除模型推理） |
| 2 | 边界检测可靠 | 20 轮含工具调用（**claude + agy 各 10 轮**） | 无截断、无「误判结束后又有输出」 |
| 3 | 状态物理继承 | 一轮 `cd` 子目录，下一轮相对路径操作 | 成功，无需模拟上下文 |
| 4 | 异常恢复不静默 | 手动 kill **bash** PTY 子进程 | 前端提示断开/重建，非卡死 |
| 5 | 空闲回收 | 超过阈值无活动 | 进程销毁，内存释放 |
| 6 | 并发输入不串台 | `BUSY` 时立即发第二条 | 拒绝或排队，stdout 不混 |
| 7 | 人机交互等待 | 触发覆盖文件 / Allow tool 确认 | `WAITING_FOR_INPUT` + `HumanInputKind` + 前端引导 |
| 8 | 最大生命周期 | 临时调短上限（如 5min）；**仅在 `IDLE` 触发** | 达上限后若 `BUSY` 则延迟至 `IDLE` 再重建；用户可感知 |
| 9 | 长时间稳定性 | **2 小时、100+ 请求**（claude 为主） | 无卡死、内存不线性涨、无串台 |
| **10** | **Provider 隔离** | 同机开两个 run：`claude` / `agy` 各一 | 两 ShellSession 互不串输出；`run_id` 与 bash PID 一一对应 |
| **11** | **非 CLI 路径无回归** | `clutch` / `ollama-cli` 冒烟 | 行为与改造前一致 |
| **15** | **Legacy 保留 + 降级** | Hybrid 故意注入失败 | 自动 fallback legacy；该轮仍有正常回复；默认 `mode=legacy` 零行为变化 |

> 验收 9 是可靠性核心——PTY 最大风险是「跑久了会不会坏」。验收 **#15** 是上线安全核心——Hybrid 坏了也不能拖垮聊天。

POC 通过后：多 `run_id` 并发、进程池上限、目录隔离、操作日志。

---

## 五、风险与待确认事项

| 事项 | 等级 | 说明 | 建议处理 |
|---|---|---|---|
| **Claude TUI PTY 可驱动性** | **已关闭** | Route A 严格 5/5 失败 | **不实现**；维持 `SHELL_EXEC` |
| Hybrid Shell + exec | **默认路径** | Route C 5/5 | Step 1 `ShellSessionManager` |
| 各 CLI 结构化输出能力 | 高 | `--output-format stream-json` 仅 `--print` + `--verbose` | Hybrid / print Detector；交互 PTY 不能假设 stream-json |
| 输出行为基准 | 决定 `BoundaryDetector` 超时与正则 | Step 0.5 → `baseline/*.json` |
| `cli_provider` 字段 | 区分 claude / agy / codex 重建策略 | POC 写入 `ShellSession.exec_provider` |
| PTY 单进程内存基线 | 决定并发上限 | 压测 claude / agy 稳定占用 |
| 异常恢复回放 | Shell 重建后体验 | Step 1：`--resume` + 明示断开；Step 3：Snapshot 注入 |
| **Context Continuity / 换班摘要** | 长期记忆与恢复机制未完整 | **Step 3** `SessionSnapshot` + 产品入口 |
| 拒绝 vs 排队 | 交互体感 | POC 先用拒绝 |
| 确认提示模式覆盖 | 因 Provider 而异 | 可配置正则 + `HumanInputKind` 映射 |
| LangGraph 多节点共享 PTY | Research / Coding / Review 同 `run_id` | **设计预留** `owner_node_id`；POC 不实现跨节点并发 |
| `clutch` 路径混淆 | 用户以为所有 Agent 都变快 | UI / 文档区分「CLI Agent」与「Clutch 内置 LLM」 |
| **Hybrid 影响现网** | 一次性替换导致聊天不可用 | §1.4 Feature Flag 默认 `legacy` + 单轮自动降级 |

---

## 六、后续排期建议

> **开工顺序**：Step 0 Route C 已通过（~85%）→ **Step 1** `ShellSessionManager`；**工作环境生命周期**先落地，**记忆换班**在 Step 3。

### 总览

| 步骤 | 工期 | 主题 | 用户可感知 |
|------|------|------|------------|
| **Step 0** | 0.5~2 天 | 三路线实验 | —（内部） |
| **Step 1** | 3~4 天 | ShellSession 核心 | 首次慢、之后快；cwd/dev server 不丢 |
| **Step 2** | 0.5~1 天 | 稳定性 + agy | 长会话不卡死 |
| **Step 3** | 2~3 天 | **Context Continuity** | 换班接班；继续上次工作（MVP） |
| **Step 4** | 1~2 天 | RuntimeStrategy 分发 | 多 Provider 一致体验 |
| **Step 5** | 按排期 | 多 run 并发、审计、池化 | 多项目并行 |
| **Step 6** | 后续 | Codex 接入、沙箱 | 更多 Agent |

### Step 0 — 实验（0.5~2 天）· 三路线 ✅ ~85%

| 路线 | 子步骤 | 内容 | 产出 | 门控 |
|------|--------|------|------|------|
| **B** | 0.B | `claude * --help` 扫描 headless / pipe / json | `runs/*-route-b-headless-search.json` | 信息性 |
| **A** | **0.A** | **pexpect 驱动交互 TUI**，BOOT_TRUST → 5 轮 | `runs/*-route-a-pexpect.json` | **BLOCKER：5/5 否则停 Claude TUI PTY** |
| **C** | 0.C | 长驻 bash PTY + `claude -p` ×5，cwd 继承 | `runs/*-route-c-hybrid.json` | ✅ **5/5 — 默认架构** |
| — | 0.2 | `claude` / `agy` `--print --output-format stream-json`（供 Hybrid Detector） | `runs/*-print-probe.txt` | — |
| — | 0.3 | `agy` 重复 A 或 C（视 agy TUI 实测） | 同上 | — |
| — | 0.4 | `codex --help` 预研 | 更新 §2.2.2 / §2.3.2 | — |
| — | 0.5 | 输出行为基准 JSON | `baseline/*.json` | A 或 C 通过后 |

遗留对比脚本：`step0_pty_probe.py`（裸 PTY，已证伪 trust gate）。

**0.5 基准字段**（直接喂给 `CliBoundaryDetector` 实现）：

- 首 token 时间（`first_token_ms`）
- 平均 token 间隔（`avg_token_gap_ms`）
- 最大静默时间（`max_silence_ms`）
- 工具调用最大静默（`max_tool_silence_ms`）
- Prompt 回显格式（`prompt_echo_pattern`）
- 人机确认 / 文本 / 鉴权格式（→ `HumanInputKind` 正则表）
- stderr 行为（是否污染 stdout）
- Ctrl+C 后进程状态（`sigint_behavior`）

### Step 1 — ShellSession 核心（3~4 天）

**目标**：落地 §0.4 新方案 — **在 legacy 旁路增加 Hybrid Beta**，默认不影响现网。

| 交付 | 说明 |
|------|------|
| `ShellSessionManager` + `ShellExecRuntime` | 一 `run_id` 一 bash PTY；`claude -p` exec |
| **`runtime.mode` Feature Flag** | 默认 `legacy`；`hybrid` 需显式开启（§1.4.1） |
| **失败自动降级** | Hybrid 异常 → 当轮 `claude_cli_adapter` legacy；可选 `state_patch` 提示 |
| **灰度范围锁** | 仅 `Plain Chat` + `claude-cli`；Flow / agy / ollama 不走 Hybrid |
| 交互式命令拦截 | `vim`/`less`/`top`/`ssh` 等 → 本轮 fallback legacy |
| `ensure_workspace_cwd()` | 每轮 exec 前锚定项目目录（§1.4.4） |
| 状态机 §2.0 | `CREATING`…`TERMINATED`；30min 空闲 / 6h 最大存活 |
| `BoundaryDetector` | `stream-json` + sentinel marker |
| `HumanInputKind` 骨架 | `BOOT_TRUST` / `TOOL_CONFIRM` 事件载荷 |
| 销毁时**最小**快照 | 仅 `cwd` + `run_id` 落盘（为 Step 3 预留） |
| **legacy 路径零删除** | `engine_router` 保留现网 subprocess 分支 |

**验收**：§四 #1~#8、#11、**#15**。

### Step 2 — 稳定性与副线（0.5~1 天）

| 交付 | 说明 |
|------|------|
| 压测 | 2h / 100+ 请求（验收 #9） |
| `agy` Route C 复测 | 验收 #2、#10 |
| `baseline/*.json` | 补齐 §0.5 输出基准 |

### Step 3 — Context Continuity（2~3 天）⭐

**目标**：§2.6 — **工作环境长期保留，AI 记忆可换班**；补齐 PM 关心的三个场景。

| 交付 | 说明 |
|------|------|
| `SessionSnapshot` 完整 schema | §2.6.5；回收 / `TERMINATED` 前持久化 |
| **换班摘要注入** | 新 `claude -p` / 新 `--resume` 时注入 `task_summary`、最近轮次、`open_todos` |
| **继续上次工作** MVP | 侧栏或会话列表：挂载 Snapshot → 重建 shell → 注入摘要 |
| 产品文案对齐 | §0.4 对用户说明「工位不丢、程序员可换班」 |

**验收（新增）**：

| # | 项 | 通过标准 |
|---|-----|----------|
| 12 | 上下文换班 | 模拟长对话后换 `cli_session_id`；`cwd` + dev server 仍在；任务可继续 |
| 13 | Snapshot 恢复 | 回收后从 Snapshot 恢复；`cd` 与摘要注入正确 |
| 14 | 多聊天隔离 | 两 `run_id` 并行；互不改对方 `cwd` |

### Step 4 — RuntimeStrategy 与路由（1~2 天）

| 交付 | 说明 |
|------|------|
| `ProviderSpec` + `runtime_registry` | §2.2 · §3.2；`strategy = provider.runtime_strategy` |
| `engine_router` 重构 | 去除 `if provider == "claude"` 扩散 |
| 非 CLI 回归 | 验收 #11 |

### Step 5 — 规模与治理（按排期）

> **执行状态**：见 [`specs/core/hybrid-runtime-plan.md`](../../specs/core/hybrid-runtime-plan.md)（HRT-xx）。  
> 已实现子集 = **HRT-S5-partial**（池上限 + Snapshot prune）；全文 Step 5 = **HRT-05 ~ HRT-10**（审计 + 并发 + POC #6/#10）。

- 多 `run_id` 并发、ShellSession 池上限、操作日志审计
- 跨天持久化策略（Snapshot 保留时长、磁盘占用）

### Step 6 — 扩展（后续）

- B-17 Codex CLI（`SHELL_EXEC`：`codex exec`）
- B-20 sandbox；B-18~B-19 受控 Shell 策略

---

## 七、本阶段的本质

把 Clutch 的 **CLI Agent 执行层**从命令执行器升级为 **Agent Runtime**：

```
Request → Subprocess → Exit     ShellSession → bash PTY → Many exec → Exit
 （现网 claude/agy）                    （第二阶段目标 · Route C）
```

这不只是性能优化：

- **`clutch` LLM 路径**已在 Sidecar 内做 ReAct 监督；ShellSession 让 **本地 CLI Agent** 达到「长会话、可监督、cwd 继承」
- 第三阶段在此基础上统一 **`RuntimeStrategy` 分发**、Provider 注册表、中断恢复、沙箱（B-18~B-21）

**第二阶段是否扎实，决定 Codex / Gemini / Aider 等后续接入成本**——差异应收敛在 `ProviderSpec.runtime_strategy` + `BoundaryDetector` 两个插件点，`ShellSessionManager` 保持稳定。

**Claude TUI PTY 已否决**。默认路径：**长驻 bash + `claude -p`**（`SHELL_EXEC`），不与上游 Ink TUI 对抗。

**对产品的一句话**：当前方案已设计 **工作环境生命周期**（Step 1）；**长期记忆与恢复机制**（§2.6 · Step 3）单独排期。**默认不改变现网行为**（§1.4 `legacy` + 降级）。

---

## 附录 A · Clutch 引擎与工具一览（代码快照）

**已路由执行（`agent_type.py` · `engine_router.py` · 前端 `AGENT_TYPE_OPTIONS`）**

- `clutch` — 内置 LLM + Skills + MCP
- `claude-cli` — `claude_cli_adapter`
- `antigravity-cli` — `agy_cli_adapter`
- `ollama-cli` — `ollama_adapter`（HTTP）

**已探测未路由（`tools_status.CLI_CANDIDATES`）**

- `codex`、`gemini`、`aider`、`code`、`codeium`、`cursor` CLI

**相关 BACKLOG**

- B-17 Codex CLI 引擎接入
- B-18/B-19 受控 Shell / 长驻 stdin（与 PTY 互补）
- B-20~B-22 沙箱与 exec policy

**相关决策**

- D19 双引擎分工（CLI 路径不叠加 Clutch MCP/Skills）
- D25 ShellSession + `SHELL_EXEC` 默认（`memory/DECISIONS.md`）

---

*本文档 v5.1 新增 §1.4 上线安全（Feature Flag · 自动降级 · 灰度范围）；v5 含产品叙事与 Context Continuity；基于 Step 0 Route C 5/5 对齐。*
