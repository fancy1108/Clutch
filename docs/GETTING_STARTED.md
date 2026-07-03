# Getting Started with Clutch

[English](#english) · [Chinese (Simplified)](#chinese)

---

## English {#english}

> **Time:** ~5 minutes after install · **Audience:** first-time users (no coding required)

### What you'll do

1. Install Clutch from a release package
2. Complete the first-launch setup wizard
3. Send your first message in Chat

### Before you start

| You need | Notes |
|----------|--------|
| **macOS 14+** or **Windows 10/11 (x64)** | See [compatibility](../README.md#compatibility). **Windows installers are not yet verified on physical hardware** — macOS is the primary tested platform. |
| **A project folder** | Any git repo or folder Clutch may read/write |
| **At least one AI backend** | Cloud API key **or** a local CLI (Claude Code, CodeBuddy, Codex, Ollama, …) |

You do **not** need Node, Python, or Rust to use the desktop app.

### Step 1 — Install

**macOS (Apple Silicon) — terminal (easiest):**

```bash
curl -fsSL https://raw.githubusercontent.com/fancy1108/Clutch/main/scripts/install.sh | bash
```

**Or with Homebrew:**

```bash
brew tap fancy1108/clutch
brew install --cask clutch
```

**Or manual download:**

1. Open **[GitHub Releases](https://github.com/fancy1108/Clutch/releases)** and download the latest installer for your OS.
2. **macOS:** drag `Clutch.app` into **Applications**. If macOS blocks launch, see [Install guide — Gatekeeper](./INSTALL.md#gatekeeper).
3. **Windows:** run `Clutch_*_x64-setup.exe` or the MSI. **Not yet verified on real Windows hardware** — CI-built only; report issues on [GitHub](https://github.com/fancy1108/Clutch/issues/new/choose).

> Clutch is a **desktop app**, not an `npm install -g` CLI. See [`INSTALL.md`](./INSTALL.md) for `install.sh` / `install.ps1` options.

Quick Gatekeeper fix (macOS, copy-paste):

```bash
xattr -cr /Applications/Clutch.app && open -a Clutch
```

Full install details: [`docs/INSTALL.md`](./INSTALL.md)

### Step 2 — First-launch wizard

On first open, Clutch shows a **full-screen setup wizard**. Follow the steps in order:

| Step | What it means |
|------|----------------|
| **Welcome** | Waits until the local backend (Sidecar) is healthy |
| **Workspace** | Pick the folder agents may work in — only this tree is writable |
| **Models** | Add a cloud API key (DeepSeek, Anthropic, OpenCode Zen, …) **or** skip if you will use local CLI only |
| **Tools** | Scan and **Connect** CLIs already on your machine (Claude Code, CodeBuddy, Ollama, Codex, …) |
| **Flow guide** | Short tour of Chat vs Workflow |
| **Permissions** | Read how CLI permissions work (important) |
| **Ready** | Launch into the main app |

> **Skipped the wizard?** Open **Settings** (gear, bottom-left) and complete: Workspace → Models → Tools.  
> Developers can replay the wizard: [`INSTALL.md` — first-use checklist](./INSTALL.md#first-use-checklist).

### Step 3 — Your first chat

1. In the sidebar, click **New Chat**.
2. At the bottom, pick an **Agent** (e.g. a connected Claude or Ollama agent).
3. Type a short message — e.g. *"What files are in this repo?"*
4. Watch the **Chat** stream, **Terminal** logs, and **file tree** on the right.

**Tip:** If you see *"model not available"* or *"model not found"*, open **Settings → Models** and pick a model that is actually configured, or **Settings → Tools** to connect a local CLI.

### Step 4 (optional) — Run a workflow

Workflows are multi-step SOPs on a canvas (several agents in sequence).

1. **Settings → Workflows SOP** — open a built-in template or create one.
2. Enable it from Chat or start a run from the workflow panel.
3. Approve or reject steps when Clutch pauses for human review.

Product tour: [`PRODUCT_INTRO.md`](./PRODUCT_INTRO.md) · Architecture: [`ARCHITECTURE.md`](./ARCHITECTURE.md)

### Common setups

| Goal | What to configure |
|------|-------------------|
| **Claude Code locally** | Settings → Tools → Rescan → Connect `claude` |
| **CodeBuddy CLI** | `npm install -g @tencent-ai/codebuddy-code` → Settings → Tools → Connect `codebuddy` → run `codebuddy` once to log in |
| **Ollama locally** | Install [Ollama](https://ollama.com), pull a model (`ollama pull qwen3:8b`), Settings → Tools → Connect Ollama; pick the model in Agent settings or Models |
| **Cloud API only** | Settings → Models → **Clutch Agent** tab → add provider key → activate a model |
| **CLI agent models** | Settings → Models → **Claude Code** or **OpenCode** tab (read-only scan; configure in the CLI or CC Switch) |
| **Terminal Orchestra** | Single Agent chat → pick any connected CLI agent → toggle **Terminal mode** (embedded xterm PTY). Bottom **OrchestratorBar** matches Chat input dock; dispatch history shows **CLI session resume** commands (`claude --resume`, `codex resume`, `opencode -s`, …) |
| **OpenCode Zen (free)** | [opencode.ai/auth](https://opencode.ai/auth) → Zen → API Keys → Settings → Models → **OpenCode Zen** → pick a free model → Save |
| **CC Switch users** | Keys can be imported from `~/.cc-switch` on startup |

### UI map (30 seconds)

```
Sidebar          Main area              Right panel
────────         ─────────              ───────────
New Chat    →    Chat / Workflow    →   Terminal · Files · Diff
AI Agents        canvas
Workflows
Settings ⚙       (Models · Tools · …)
```

### Troubleshooting

| Problem | Try |
|---------|-----|
| App won't open (macOS) | [Gatekeeper steps](./INSTALL.md#gatekeeper) |
| "Cannot connect" / empty UI | Quit fully (`Cmd+Q`), reopen; check `curl -s http://127.0.0.1:8123/health` |
| Model 404 / not found | Settings → Models — pick an installed Ollama tag or valid API model |
| CLI not listed | Settings → Tools → Rescan; ensure CLI works in Terminal `PATH` |
| Folder picker dead | Use **Clutch.app**, not `pnpm dev` in a browser |

More: [`INSTALL.md` — troubleshooting](./INSTALL.md#troubleshooting) · [GitHub Issues](https://github.com/fancy1108/Clutch/issues/new/choose)

### CLI permissions (read once)

Clutch may call local CLIs with `--dangerously-skip-permissions` so workflows can run without per-tool prompts. Only use on folders you trust. Details: [README § Security](../README.md#security--cli-permissions)

### Next steps

- **All features:** [`PRODUCT_INTRO.md`](./PRODUCT_INTRO.md)
- **macOS auto-update (v1.0.2+):** [`UPDATES.md`](./UPDATES.md)
- **Build from source:** [`BUILD_FROM_SOURCE.md`](./BUILD_FROM_SOURCE.md)
- **Contribute:** [`CONTRIBUTING.md`](../CONTRIBUTING.md)

---

## Chinese (Simplified) {#chinese}

> **用时：** 安装后约 5 分钟 · **读者：** 第一次使用、无需写代码

### 你会完成什么

1. 从 Release 安装 Clutch
2. 走完首次启动的设置向导
3. 在聊天里发出第一条消息

### 开始之前

| 需要 | 说明 |
|------|------|
| **macOS 14+** 或 **Windows 10/11 (x64)** | 见 [兼容性说明](../README.zh-CN.md#兼容性)。**Windows 安装包尚未在实体机上完整验收** — 目前以 macOS 为主要测试平台。 |
| **一个项目目录** | 任意 git 仓库或文件夹，Clutch 只在该目录内读写 |
| **至少一种 AI 能力** | 云端 API Key **或** 本机 CLI（Claude Code、CodeBuddy、Codex、Ollama 等） |

使用桌面安装包时，**不需要**安装 Node、Python 或 Rust。

### 第 1 步 — 安装

**macOS（Apple Silicon）— 终端一键安装：**

```bash
curl -fsSL https://raw.githubusercontent.com/fancy1108/Clutch/main/scripts/install.sh | bash
```

**或 Homebrew：**

```bash
brew tap fancy1108/clutch
brew install --cask clutch
```

**或手动下载：**

1. 打开 **[GitHub Releases](https://github.com/fancy1108/Clutch/releases)**，下载适合你系统的最新安装包。
2. **macOS：** 将 `Clutch.app` 拖入 **应用程序**。若被系统拦截，见 [安装指南 § Gatekeeper](./INSTALL.md#4-首次打开gatekeeper)。
3. **Windows：** 运行 `Clutch_*_x64-setup.exe` 或 MSI。**尚未在真实 Windows 实体机上完整验收** — 目前仅 CI 构建；问题请 [提交 Issue](https://github.com/fancy1108/Clutch/issues/new/choose)。

> Clutch 是**桌面应用**，没有 `npm install -g clutch`。详见 [`INSTALL.md`](./INSTALL.md) 中的 `install.sh` / `install.ps1`。

macOS 终端一键解除拦截（可复制）：

```bash
xattr -cr /Applications/Clutch.app && open -a Clutch
```

完整安装说明：[`docs/INSTALL.md`](./INSTALL.md)

### 第 2 步 — 首次设置向导

第一次打开会出现**全屏设置向导**，按顺序完成即可：

| 步骤 | 含义 |
|------|------|
| **欢迎** | 等待本机后端（Sidecar）就绪 |
| **工作区** | 选择 Agent 可以读写的项目目录 |
| **模型** | 填写云端 API Key（含 OpenCode Zen 等），或若只用本机 CLI 可暂时跳过 |
| **工具** | 扫描并 **Connect** 本机已装的 CLI（Claude Code、CodeBuddy、Ollama、Codex 等） |
| **流程引导** | 了解「单聊」和「工作流」的区别 |
| **权限说明** | 阅读 CLI 权限相关说明（建议认真看） |
| **就绪** | 进入主界面 |

> **跳过了向导？** 点左下角 **Settings**，依次配置：工作区 → Models → Tools。  
> 开发环境可重新弹出向导：[`INSTALL.md` §6](./INSTALL.md#6-首次使用-checklist)。

### 第 3 步 — 发出第一条聊天

1. 侧栏点击 **New Chat**（新对话）。
2. 底部选择一个 **Agent**（例如已连接的 Claude 或 Ollama Agent）。
3. 输入简短问题，例如：*「这个仓库里有哪些文件？」*
4. 在中间看 **聊天**，右侧看 **终端日志** 和 **文件树**。

**提示：** 若提示 *模型不可用* 或 *model not found*，请到 **Settings → Models** 选择已配置好的模型，或到 **Settings → Tools** 连接本机 CLI。

### 第 4 步（可选）— 跑一条工作流

工作流是在画布上编排的多 Agent SOP（多个步骤串联）。

1. **Settings → Workflows SOP** — 打开内置模板或新建。
2. 在 Chat 中启用，或从工作流面板启动运行。
3. 需要人工审批时，在界面里 **批准 / 打回 / 重试**。

功能全景：[`PRODUCT_INTRO.md`](./PRODUCT_INTRO.md) · 架构：[`ARCHITECTURE.md`](./ARCHITECTURE.md)

### 常见配置

| 目标 | 怎么配 |
|------|--------|
| **本机 Claude Code** | Settings → Tools → Rescan → Connect `claude` |
| **CodeBuddy CLI** | `npm install -g @tencent-ai/codebuddy-code` → Settings → Tools → Connect `codebuddy` → 终端运行 `codebuddy` 完成登录 |
| **本机 Ollama** | 安装 [Ollama](https://ollama.com)，执行 `ollama pull qwen3:8b`，Settings → Tools 连接 Ollama；在 Agent 或 Models 里选模型 |
| **只用云端 API** | Settings → Models → **Clutch Agent** 标签页 → 填 Key → 激活模型 |
| **CLI Agent 模型** | Settings → Models → **Claude Code** 或 **OpenCode** 标签页（只读扫描；在 CLI 或 CC Switch 中配置） |
| **Terminal Orchestra** | Single Agent 聊天 → 选择任意已 Connect 的 CLI Agent → 切换 **终端模式**（嵌入式 xterm PTY）。底部 **OrchestratorBar** 与 Chat 输入栏同款贴底；派发记录含 **CLI Session 恢复命令**（`claude --resume`、`codex resume`、`opencode -s` 等） |
| **OpenCode Zen（免费）** | [opencode.ai/auth](https://opencode.ai/auth) → Zen → API Keys → Settings → Models → **OpenCode Zen** → 选免费模型 → 保存 |
| **CC Switch 用户** | 启动时可从 `~/.cc-switch` 导入 |

### 界面速览

```
侧栏              主区域                 右侧面板
────              ──────                 ────────
New Chat    →     聊天 / 工作流画布  →   终端 · 文件 · Diff
AI Agents
Workflows
Settings ⚙        （Models · Tools · …）
```

### 常见问题

| 现象 | 处理 |
|------|------|
| macOS 打不开 | [Gatekeeper 步骤](./INSTALL.md#4-首次打开gatekeeper) |
| 连不上 / 空白 | 完全退出（`Cmd+Q`）再开；`curl -s http://127.0.0.1:8123/health` |
| 模型 404 / 找不到 | Settings → Models — 选本机已安装的 Ollama 或有效 API 模型 |
| CLI 扫不到 | Settings → Tools → Rescan；确认终端里能直接运行该命令 |
| 选文件夹无反应 | 必须用 **Clutch.app**，不要用浏览器开 `pnpm dev` |

更多：[`INSTALL.md` § 故障排除](./INSTALL.md#8-故障排除) · [提交 Issue](https://github.com/fancy1108/Clutch/issues/new/choose)

### CLI 权限（建议读一遍）

部分本地 CLI 默认带 `--dangerously-skip-permissions`，工作流才能自动跑通。请只在信任的项目目录使用。详见 [README § 安全](../README.zh-CN.md#安全与-cli-权限)。

### 下一步

- **全部功能：** [`PRODUCT_INTRO.md`](./PRODUCT_INTRO.md)
- **macOS 应用内更新（v1.0.2+）：** [`UPDATES.md`](./UPDATES.md)
- **源码构建：** [`BUILD_FROM_SOURCE.md`](./BUILD_FROM_SOURCE.md)
- **参与贡献：** [`CONTRIBUTING.md`](../CONTRIBUTING.md)
