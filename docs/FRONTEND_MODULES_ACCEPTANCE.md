# Frontend modules（FM-01…22）点验剧本

> **给谁用：** 你在桌面 App 里一条条点、打勾。  
> **不是状态表：** 勾完后的结论只记 [`memory/ROADMAP.md`](../memory/ROADMAP.md) §Frontend modules。  
> **功能是否存在：** [`PRODUCT_INTRO.md`](./PRODUCT_INTRO.md)。Task 定义：[`specs/core/frontend-modules-plan.md`](../specs/core/frontend-modules-plan.md)。  
> **范围：** D56 这批能在 UI 里看到的模块 + 相关 D32 worktree。不含价表、Windows 实体机。  
> **版本：** 点验通过后进 **v1.4.0**（已发布安装包仍是 v1.3.0）。

打印或分屏打开本文，左边 App、右边文档。每条有 **入口** 和 **过/不过**。  
灰色代码框是 **整段复制**：Chat 输入框或 Settings 输入框，不要改字。权限 pill 在输入框左边，默认 **Agent**（不是 Ask）。

---

## 0. 开场（先做一次）

```bash
export CLUTCH_RUNTIME_MODE=hybrid && pnpm tauri:dev
```

1. 授权一个 **git 仓库** 工作区（本仓库 `clutch` 即可）。底栏应显示 **Branch: 某分支**，不是 `Branch: -`。
2. 需要云模型时：Settings → Models → **Clutch Agent** 配好 Key（验收 Chat 回复用）。
3. Orchestra（FM-06…08）需要至少一个 **已 Connect 的 CLI Agent**（Claude Code / Codex 等）。没有 CLI 就跳过 Wave 3，先做 Settings / Chat。

**藏得最深的入口（整份文档反复用）：**

| 你想找的 | 实际位置 |
|----------|----------|
| Settings | 侧栏最底 **齿轮**（`nav-settings`） |
| Chat 次要能力 | 输入框左边 **+**，下面一截叫 **Session tools** |
| 右侧监督 | **Overview / Files / Changes / Terminal** |
| 切换 Coding / Design | 顶栏右侧 **Coding · Design** |

**+ 菜单里和本批相关的项：** Enable worktree、Notify user、New information、Interpreter error（后三项是 **预览卡**，不必等 Agent）。

---

## 总表（按这个顺序点）

| 本轮 | ID | 一句话 | 入口（找不到就看这列） |
|:----:|----|--------|------------------------|
| ☑ | [FM-01](#fm-01-general) | 默认工作区 / Stop 确认 / 版本号 | Settings → General |
| ☑ | [FM-02](#fm-02-本机信任) | 未信任 MCP 先确认 | Settings → General 开关 + Hub Enable |
| ☑ | [FM-03](#fm-03-命令策略) | allow / ask / deny 规则 | Settings → Tools |
| ☑ | [FM-04](#fm-04--fm-05-cli-只读扫描) | Codex 扫描 | Settings → Models → **More → Codex** |
| ☑ | [FM-05](#fm-04--fm-05-cli-只读扫描) | 另外六个 CLI 扫描 | More → Aider / CodeBuddy / … |
| ☑ | [FM-09](#fm-09-分派横幅) | 空 Chat 不必先选工作流 | New Chat 顶上灰条 |
| ☐ | [FM-19](#fm-19-plannerexecutor) | 规划模型 / 执行模型分开 | Settings → Models；Overview 两行名字 |
| ☐ | [FM-12](#fm-12-记忆搜索) | 搜 `.clutch/memory` | Settings → General → Search |
| ☐ | [FM-13](#fm-13-事件-channel) | Test event → Chat 横幅 Continue | Settings → General → Event channel |
| ☐ | [D32+FM-11](#d32--fm-11-worktree) | Enable → 蓝条 → Discard/Merge / 并行树 | Chat **+** → Enable worktree |
| ☐ | [FM-14](#fm-14-notify-user) | 通知卡 Send / Cancel | **+** → Notify user（预览） |
| ☐ | [FM-15](#fm-15-新信息门禁) | 并行前 Proceed / Hold | **+** → New information（预览） |
| ☐ | [FM-17](#fm-17-解释器错误卡) | 超时/离线结构化卡 | **+** → Interpreter error（预览） |
| ☐ | [FM-10](#fm-10-画布-node-engine) | 节点选 CLI/MCP/llm | Workflows 画布点节点 |
| ☐ | [FM-18](#fm-18-校验失败条) | 校验失败可读 | 跑一个会失败校验的工作流 |
| ☐ | [FM-06](#fm-06-orchestra-队列与确认卡) | 排队条 + 确认卡 | Chat mode → **Terminal mode** |
| ☐ | [FM-07](#fm-07-保存为工作流) | Overview 保存 SOP | 终端派发后 Overview |
| ☐ | [FM-08](#fm-08-对话-handoff) | Chat 草稿 / Send to Bar | 对话模式输入栏 |
| ☐ | [FM-16](#fm-16-design-视觉审查) | 渲染图 + 驳回 | 顶栏 **Design** |
| ☐ | [FM-20](#fm-20-性能数字) | 文档里有本机数字 | 打开 PERFORMANCE.md §1.1 |
| ☐ | [FM-21](#fm-21-apple-公证) | 流程文档；**未公证** | 打开 APPLE_NOTARIZATION.md |
| ☐ | [FM-22](#fm-22-外部审计) | 委托说明；**无报告** | 打开 EXTERNAL_AUDIT.md |

---

## Wave 1 · Settings

### FM-01 General

**是什么：** 启动默认工作区、Chat Stop 可先确认、Settings 里能看到版本。

**入口：** 齿轮 → 左侧 **General**。

| # | 操作 | 期望 |
|---|------|------|
| 1 | 找到 **Default workspace** 下拉 | 有「Last used」和已授权项目名（`general-default-workspace`） |
| 2 | 选中 `clutch`，完全退出 App 再开 | 仍打开 clutch，不是空白/别的盘 |
| 3 | **Confirm before stopping a run** 打开 | 开关可点（`high-risk-confirm-toggle`） |
| 4 | New Chat，发一句让 Agent 跑起来，点 **Stop** | 先弹出确认，不是立刻停（工作流 Stop **不应**弹这个确认） |
| 5 | General 页底部 | 有 `Clutch v…`（`general-app-version`） |

**不过：** 重启丢默认工作区；Stop 从不确认；没有版本行。

---

### FM-02 本机信任

**是什么：** 第一次启用陌生 MCP 要确认一次，本机记住 id。自己创建的 SOP 在 Workflows 列表点选即绑定，不弹信任框（D58）。

**入口：**

- 开关：Settings → General → **Confirm untrusted MCP**（`untrusted-confirm-toggle`）
- MCP：Settings → **MCP** Hub，Enable 某个未信任 server

| # | 操作 | 期望 |
|---|------|------|
| 1 | 打开上述开关 | 能保存，刷新 Settings 仍是 On |
| 2 | Hub 里 Enable 新 MCP | 先确认卡，确认后才启用 |

**不过：** 直接启用 MCP、没有确认卡。本机已信任过的 MCP id 可以不再问（这是过，不是不过）。工作流绑 Chat **不应**再弹信任框。

---

### FM-03 命令策略

**是什么：** 自己加 shell 的 allow / ask / deny。**Deny 不会弹审批卡**（工具直接失败）。**Ask** 和危险命令（`rm -rf` / `sudo`）即使权限是 **Full** 也会弹 Allow / Reject。

**入口：** 齿轮 → **AI Tools**（不是 Models）。往下翻到 **Command policy**（`exec-policy-panel`）。底栏 Agent 必须是 **Clutch Agent**。权限 pill（输入框左边）不要选 Ask。

| # | 操作 | 期望 |
|---|------|------|
| 1 | 输入框能打 pattern，下拉 Allow / Ask / Deny，点 Add | 列表多一行（`exec-policy-add` / `exec-policy-pattern`） |
| 2 | 按下面 **用例 A** | Chat **没有** Allow 卡；工具结果含 `[Permission] Denied`；工作区 **没有** `clutch-fm03-deny.txt` |
| 3 | 删掉 A 的规则，按 **用例 B** | 权限 **Full** 仍弹出 Allow / Reject，不能默默执行 |

**不过：** Deny 却直接建了文件；Full 下 `rm -rf` 不询问就跑了。

**用例 A · Deny（权限 pill = Agent）**

Settings → Tools → Command policy，pattern 整段粘贴，Action = **Deny**，点 Add：

```
touch clutch-fm03-deny.txt
```

New Chat，整段发送：

```
只执行这一条 shell，一个字都不要改，必须用 run_terminal_cmd：
touch clutch-fm03-deny.txt
不要用 apply_patch，不要换路径。
```

测完：Settings 里把这条规则 **Remove**。

**用例 B · Full 仍问（权限 pill 改成 Full）**

pattern 粘贴，Action = **Ask**，点 Add：

```
echo clutch-fm03-ask
```

整段发送：

```
只执行这一条 shell，一个字都不要改，必须用 run_terminal_cmd：
echo clutch-fm03-ask
```

期望：Allow / Reject。点 **Reject**。再发（不必加规则，内置危险名单）：

```
只执行这一条 shell，一个字都不要改，必须用 run_terminal_cmd：
rm -rf /tmp/clutch-fm03-does-not-exist
不要改成工作区路径。
```

期望：仍 Allow / Reject。**Reject**，不要 Allow。测完 Remove `echo clutch-fm03-ask` 那条，权限 pill 改回 **Agent**。

---

## Wave 2 · CLI 只读扫描

### FM-04 / FM-05 CLI 只读扫描

**是什么：** Settings 里按 CLI 看本机配置，只读，不替你改。

**入口：** 齿轮 → **Models**（Skills / MCP 同样有 More）→ 顶栏 **More**。

| ID | 点哪 | 期望 |
|----|------|------|
| FM-04 | **Codex**（`cli-scan-codex-cli`） | 列出当前模型（`config.toml` 的 `model`）和缓存 catalog；有 **Rescan**；没装/没文件才是空态 |
| FM-05a | Aider | 同上 |
| FM-05b | CodeBuddy | 同上 |
| FM-05c | Antigravity | 同上 |
| FM-05d | Rivet | 同上 |
| FM-05e | Ollama | 同上 |
| FM-05f | ZCode | 同上 |

本机没装对应 CLI → **空态也算过**。装了但配置里没写模型（本机 Aider / Antigravity 常见）→ 有 Config 路径、模型列表可以为空。Cursor / Grok 不在这一批。

**复制（没有 Chat 句，按点）：** 齿轮 → **Models** → 顶栏 **More** → 依次点 `cli-scan-codex-cli`、Aider、CodeBuddy、Antigravity、Rivet、Ollama、ZCode。每页要么有配置摘要，要么有明确 Empty / 未检测到，不要白屏。

---

## Wave 4 先做（Chat 空态，不依赖 CLI）

### FM-09 分派横幅

**是什么：** 空会话可以直接打字发送，不必先点 Choose workflow。顶上一条告诉你会用谁。

**入口：** 侧栏 **New Chat**。横幅 `dispatch-banner`，在 Chat/Terminal 切换条下面。

| # | 操作 | 期望 |
|---|------|------|
| 1 | 新会话、不选工作流 | 文案类似 **No workflow selected — using current Agent: …**（中文：未选择工作流，将使用当前 Agent） |
| 2 | 底栏选一个 Workflow，或空态点 Choose workflow | 横幅变成 **Matched SOP:** 名称 |
| 3 | 不选 SOP，直接在输入框发一句 | 能发出去（有 Key 才会有模型回复） |

**不过：** 强制先选工作流才能输入；横幅完全没有。

**复制：** New Chat，不要点工作流。输入框整段发送：

```
只回复两个字：收到
```

期望：能发出去；顶上横幅仍是「未选择工作流，将使用当前 Agent」。再从底栏选一条 SOP，横幅变成 Matched SOP 名称。

---

### FM-19 Planner/Executor

**是什么：** 规划可以用便宜模型，真正对话用 Executor。

**入口：** Settings → **Models** → Clutch Agent 页。右侧 Overview 在 IDLE 时也能看到两行名字。

| # | 操作 | 期望 |
|---|------|------|
| 1 | 看到 **Planner** / **Executor** 两个下拉 | `planner-model-select` · `executor-model-select` |
| 2 | 两个选成不同模型 | Overview 显示两个名字（`overview-model-roles`） |
| 3 | 发一轮 Chat | Overview 能看出本轮走的是 Executor |

**复制：** Planner 和 Executor 选两个**不同**的已有模型（没有第二套就跳过第 2、3 步并写原因）。New Chat 发送：

```
只回复两个字：收到
```

期望：右侧 Overview IDLE 时就能看到两行模型名；这一轮标注的是 Executor。

---

## Wave 5 · 记忆 / 事件 / 卡片（多数可预览）

### FM-12 记忆搜索

**入口：** Settings → General，往下翻到 Memory，**Search** 框（`memory-search-input`）。

前置：Chat 里说过「记住：…」，Files 里应有 `.clutch/memory/MEMORY.md`。

| # | 操作 | 期望 |
|---|------|------|
| 1 | 输入关键词，点搜（`memory-search-run`） | 有命中（`memory-search-hit`）或明确无结果 |
| 2 | 点一条命中 | 打开该文件预览，不是死链 |

**复制：** New Chat，Clutch Agent，整段发送：

```
记住：验收关键词 clutch-fm12-probe
```

等回复后：齿轮 → General → Memory **Search** 框粘贴 `clutch-fm12-probe`，点搜。期望命中 `.clutch/memory/MEMORY.md`，点开能预览。

---

### FM-13 事件 Channel

**入口：** Settings → General → **Event channel**（webhook / email）。

| # | 操作 | 期望 |
|---|------|------|
| 1 | 填一个 webhook 或邮箱，Save（`event-channel-save`） | 保存成功 |
| 2 | 点 **Test event**（`event-channel-test`） | 回到 Chat，顶上有横幅（`event-channel-banner`） |
| 3 | 点 **Continue** | 横幅消失，会话可继续 |

没有真实 webhook 也可以点 Test（走本机测试通道）。

**复制：** Event channel 的 URL 框粘贴（不必是真服务）：

```
https://example.com/clutch-fm13
```

Save → **Test event**。回到 Chat，点横幅 **Continue**。

---

### D32 + FM-11 Worktree

**是什么：** Agent 改代码可以在隔离目录，主仓保持干净。FM-11 是「再加一棵并行树」。侧栏项目名 **不是** worktree。

**入口（启用前看不见蓝条，这是预期）：** 输入框 **+** → **Session tools** → **Enable worktree**。

工作区必须是 git（底栏有 Branch）。Discard/Merge 需要 **当前这次 `tauri:dev` 已带上 Sidecar 修复**（点 Discard 应出 Supervisor 消息；若完全没反应，重启 App）。

| # | 操作 | 期望 |
|---|------|------|
| 1 | 未 Enable | 输入栏上方 **没有**「Add parallel worktree」 |
| 2 | + → Enable worktree | Supervisor：「Worktree isolation enabled at …/.clutch/worktrees/wt_…」；上方蓝条（`worktree-active-chip`）显示 `clutch/wt_…` |
| 3 | 点 **Discard** | Supervisor：「Discarded worktree …」；蓝条消失；`.clutch/worktrees/wt_…` 目录没了 |
| 4 | 再 Enable，让 Agent 在隔离目录写文件 | 主仓 `git status` 仍干净；蓝条可显示 dirty |
| 5 | 启用后出现 **Add parallel worktree** | 再长出一条并行树，可各自 Merge/Discard |
| 6 | 非 git 工作区 Enable | 可读错误（工作区不是 git），不是空白 |

**不过：** Discard 点了没任何 Supervisor 字、蓝条还在。

**复制：** 底栏有 Branch 时，Chat **+** → Enable worktree。Discard 测完再 Enable，然后发送：

```
只在当前 worktree 里新建文件 clutch-fm11.txt，内容写 ok。不要改仓库里其它文件。
```

期望：主仓 `git status` 仍干净。再点 **Add parallel worktree**。非 git 文件夹测第 6 步即可。

---

### FM-14 Notify user

**入口：** **+** → **Notify user**（预览，不必等子 Agent）。真路径是子 Agent 调 `notify_user`。

| # | 操作 | 期望 |
|---|------|------|
| 1 | 点菜单项 | Chat 出现通知卡（`notify-user-card`） |
| 2 | **Send** / **Cancel** 都能点 | 卡状态变化，不是死按钮 |

**复制：** 不必等 Agent。Chat **+** → **Notify user**。卡上先点 **Cancel** 一次；再打开一次点 **Send**。

---

### FM-15 新信息门禁

**入口：** **+** → **New information**（预览）。真路径：已有并行子任务时再 `delegate_subtask`。

| # | 操作 | 期望 |
|---|------|------|
| 1 | 点菜单项 | 确认卡 **Proceed / Hold**（`new-info-card`） |
| 2 | 两个按钮都能点 | 不是只展示文案 |

**复制：** Chat **+** → **New information**。先点 **Hold**，再打开一次点 **Proceed**。

---

### FM-17 解释器错误卡

**入口：** **+** → **Interpreter error**（预览）。真路径：`run_terminal_cmd` 超时或 shell 起不来。

| # | 操作 | 期望 |
|---|------|------|
| 1 | 点菜单项 | 结构化卡（`interpreter-error-card`），标题是超时或 offline，不是 Python traceback |
| 2 | 有下一步说明 | 能看懂「去改 PATH / 缩短命令」 |

**复制：** Chat **+** → **Interpreter error**。看卡标题是超时或 offline，不是 Python traceback。

---

## Wave 4 · 画布

### FM-10 画布 Node engine

**入口：** 侧栏 **Workflows SOP** → 打开任一个 SOP → 点画布上一个节点。

| # | 操作 | 期望 |
|---|------|------|
| 1 | 右侧/节点编辑器有 **Node engine** | 下拉 CLI / MCP / llm（`node-tool-select`） |
| 2 | 改一下保存，跑这个工作流 | Overview 步骤行能看到该引擎（`step-engine-*`） |

**复制：** 齿轮 → Workflows SOP → 点开任一条 → 点一个 Agent 节点 → **Node engine** 选 `llm` → Save。底栏绑这条 SOP 后发送：

```
按当前工作流跑一步即可，不要改节点配置。
```

没有「跑起来」也可以：保存后 Overview 步骤行能看到 engine 字样即过第 2 步的弱过；真跑才算满过。

---

### FM-18 校验失败条

**入口：** 跑一个节点校验会失败的工作流（或看已失败 run）。

| # | 操作 | 期望 |
|---|------|------|
| 1 | Chat 里失败节点 | 可读条，不是只有红点（`validation-failure-chat`） |
| 2 | 右侧 Overview | 同样可读（`validation-failure-strip`） |

没有现成失败流时：可标「跳过，待有失败 run 再补」，不要假装过。

**复制（造一个必失败的 check）：** Workflows → Create Flow，名字粘贴 `fm18-missing-file`。画布加一个 **Check** 节点，`check(file_exists)` 的 path 粘贴：

```
.clutch/fm18-missing.txt
```

Save，Chat 绑这条 SOP，发送：

```
运行当前工作流，不要改 check 的 path。
```

期望：Chat **VALIDATION FAILED**，Overview 同样可读。没有失败条就标跳过。

---

## Wave 3 · Orchestra（要 CLI）

前置：底栏 **Active Agent** 换成已 Connect 的 `*-cli`。主区右上出现 **Chat mode / Terminal mode**。

### FM-06 Orchestra 队列与确认卡

**入口：** 切到 **Terminal mode**。底栏变成 OrchestratorBar（不是普通 Chat 输入框）。

| # | 操作 | 期望 |
|---|------|------|
| 1 | `@某CLI 做一件小事` 发送 | 出现确认卡（`dispatch-confirm-card`），可改 sources，再 **Confirm**（`confirm-dispatch-btn`） |
| 2 | 连续派发超过可见 Lane（约 4 个） | 上方排队条（`orchestra-queue`）看得到第 5 路 |
| 3 | Lane Complete | 草稿可填进 Bar 或关掉（`orchestra-drafts` / `dismiss-draft-*`） |

没有 CLI → **整节跳过**（在总表写跳过原因）。

**复制：** 底栏换成已 Connect 的 CLI。切 **Terminal mode**。输入框按你已 Connect 的名字改 `@` 后面，其余照贴：

```
@claude 只回复 pong，不要改文件。
```

若 Agent 叫 Codex：用 `@codex 只回复 pong，不要改文件。` 出现确认卡再 Confirm。要测排队：连发 5 次同样内容。

---

### FM-07 保存为工作流

**入口：** 终端里至少成功派发 1～2 路后，右侧 **Overview**。

| # | 操作 | 期望 |
|---|------|------|
| 1 | 看到派发记录 | `overview-dispatch-log` |
| 2 | **Save as workflow**（`save-dispatch-as-workflow`） | Workflows 列表出现新 SOP，节点顺序和派发顺序一致 |

**复制：** FM-06 至少 Confirm 过 1 路后，右侧 Overview → **Save as workflow**。名字用默认即可。去 Workflows 列表核对新 SOP。

---

### FM-08 对话 handoff

**入口：** 同一会话切回 **Chat mode**。

| # | 操作 | 期望 |
|---|------|------|
| 1 | 终端 Handoff「Send to Bar」 | Chat 输入区出现草稿芯片（`chat-handoff-drafts`） |
| 2 | Chat 空输入时再切 Terminal | 能带上近期对话，不是空白 Bar |

**复制：** Terminal 某 Lane Complete 后点 Handoff **Send to Bar**，再切 **Chat mode**。期望输入区有草稿芯片。清空输入，再切回 Terminal，Bar 里应带近期对话。

---

## Wave 5 · Design

### FM-16 Design 视觉审查

**入口：** 顶栏 **Design**（`mode-design`）。不是 Chat 里的 SOP。

| # | 操作 | 期望 |
|---|------|------|
| 1 | 走完一轮生成到 handoff 第 1 步 | 审查卡带渲染截图（`design-review-card` / `design-review-shot`） |
| 2 | 点 **Reject**（`design-review-reject`） | 进入下一轮，不是卡死或直接结束 |

**复制：** 顶栏 **Design**。欢迎大输入整段发送：

```
做一个只有一个主按钮的空白页，不要多余装饰。
```

走到 handoff 第 1 步有渲染图后点 **Reject**。

---

## Wave 6 · 文档（没有新按钮）

### FM-20 性能数字

打开 [`PERFORMANCE.md`](./PERFORMANCE.md) **§1.1**。

**过：** 有日期、本机环境、health / templates / verify 的实测数。  
**不过：** 只有目标表、没有「测得」列。  
**不是过：** 冷启动 DMG 数字（文档已写明未测）。

### FM-21 Apple 公证

打开 [`APPLE_NOTARIZATION.md`](./APPLE_NOTARIZATION.md)。

**过：** 写了账号到位后的步骤，并写明 **当前阻塞 / 仍发未签名 DMG**。  
**不是过：** 本机已经公证成功（没有 Developer 账号就做不到，不要等这个）。

### FM-22 外部审计

打开 [`EXTERNAL_AUDIT.md`](./EXTERNAL_AUDIT.md) 和 [`docs/security-audit/`](./security-audit/)。

**过：** 有委托步骤和报告该放哪。  
**不是过：** 已经有第三方 PDF（还没有）。日常漏洞仍走 [`SECURITY.md`](../SECURITY.md)。

---

## 点完怎么记

- 本轮哪条不过：在 Issue / Chat 里写 **FM-xx + 你点了什么 + 实际看到什么**。
- 正式勾选只改 [`memory/ROADMAP.md`](../memory/ROADMAP.md)（已 ✅ 的不要仅因「我今天才点」再改，除非你确认是回归失败）。
- 旧能力（Stop/Continue、Todo 卡、MCP Hub…）不在本表；见 `runs/verification/pm-acceptance/` 里 D08…D52。
