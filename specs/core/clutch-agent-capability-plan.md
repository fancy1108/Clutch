# Chat Clutch Agent 能力交付表（权威）

> **权威任务表**：Chat 模式自研 Clutch Agent 适配 Grok 级能力 + MCP 专项 + Chat 监督 UX。  
> **决策**：见 `memory/DECISIONS.md` **D44**。  
> **Cursor 工作副本**：`~/.cursor/plans/clutch_agent_hands_008ad800.plan.md`（可与本文同步；冲突以本文件 + DECISIONS 为准）。  
> **编号**：本文 **交付期 Dn**（D0–D53）≠ `DECISIONS.md` 的 Dx（例如 DECISIONS D42=路径预览，本文 D42=MCP 真实工具目录）。

## 文档落点

| 仓库路径 | 角色 |
|----------|------|
| **本文** `specs/core/clutch-agent-capability-plan.md` | **权威任务表**（D0 已落库） |
| `memory/DECISIONS.md` **D44** | 架构决策 |
| `memory/ROADMAP.md` §Chat Clutch Agent | 勾选状态（Default FAIL） |
| `memory/FILEMAP.md` | 入口索引 |

**各交付期再更新：** `docs/PRODUCT_INTRO.md`、`CHANGELOG.md` `## [Unreleased]`（已发 v1.4.0）；MCP 真相时 `docs/mcp-servers/*`；会话 Check-out 写 `PROGRESS` / `DELIVERABLES`。

**编号约定：** 本文交付期 Dn ≠ DECISIONS Dx。

---

## 定位

- **表面**：Chat · 自研 Clutch Agent（编排 SOP 在上层，不单独立项）。
- **策略**：Grok 可适配能力 D1–D36；MCP 缺口 D37–D45；**对话内监督交互 D46–D52**；**运行时提示词分层 D53（渐进式披露，禁止整坨静态 markdown 当唯一 system）**。
- **验收**：每项 = PM 在 Chat（为主）能直接看出效果。
- **不做**：嵌 Rust、前端自建编排循环、默认 always-approve、用外挂替代自研主路径。

## 都覆盖全了吗？（直接回答）

**能力逻辑：D1–D36 + MCP D37–D45 已列。**  
**对话交互：D46–D52。**  
**提示词组装：D53（分层 + 渐进披露；对标 Grok 运行时组装，不是一份文档）。**  
**Grok TUI 1:1：有意不对齐。**

| 批次 | 编号 | 含义 |
|------|------|------|
| 文档 | D0 | 共识 |
| 主线 | D1–D13 | 编码 Agent 闭环 |
| 旁路 | D14 | 外挂 grok CLI |
| 扩展 | D15–D36 | 其余 Grok 级能力 |
| MCP | D37–D45 | Hub/绑定/传输等 |
| **Chat 监督 UX** | **D46–D52** | 实时活动、产物、子 Agent、计划/验证嵌对话 |
| **Prompt 运行时** | **D53** | 分层 system / env / rules / skills / mode；渐进披露 |

铁律：**每个能力交付期必须带对应前端可见交互**；禁止「只合后端、Chat 仍只有 Thinking…」算完成（D52 作对照门禁）。

---

## 前端现状（为何要 D46+）

今天大概是：

| 体验 | 现状 |
|------|------|
| 正在干嘛 | Chat 多半只有 **Thinking…** 点点；CLI Hybrid 详情多为**事后折叠**；Terminal Orchestra 有 live，但 **Plain Chat / Clutch builtins 弱** |
| 中间产物 | 产品决策 **DECISIONS D42**（路径/fence 可点预览、Changes）已有；**缺**回合内自动「产物芯片条」→ 本表 **D47**（勿与本表编号 D42「MCP 真实工具目录」混淆） |
| 子 Agent | Terminal `@` 派发/多 lane 有；**Chat 气泡内无嵌套子任务卡**；Design 的 Agent Log **未接到 Coding Chat** |
| 计划/Todo/提问 | 能力在 D2–D4；**须明确做成对话内卡片**（D49），不能只藏在状态里 |

对标「别的 agent 界面」：要在 **对话流里**看到步骤、点开中间文件、看到自动派发的 subagent 并可点进去——这就是 D46–D48。

---

## Chat 监督 UX 专项 D46–D52

#### D46 — 对话内实时「正在干嘛」
- **可见**：运行中在 Thinking 下方出现 **Grok 式 verb_group** 折叠摘要（如 `Reading 2 files, Searching 1 pattern`）；可展开逐步 `title` / `detail`。回合结束把同组步骤 **seal** 进该条 assistant 气泡 `toolSteps`，刷新后仍可回看。
- **验收**：Clutch Agent（builtins 或 MCP）读写/搜索时，**不必切 Terminal** 也能看见当前步骤；结束后摘要仍在该条回复上；审批 pause 时步骤为 awaiting，Allow 后同条轨迹变 completed。
- **实现笔记（PM 2026-07-24 点验通过）**：Sidecar `pending_tool_steps` + `ChatMessage.toolSteps`；`tool_steps.py` / `mcp_react` 同步累积并 seal（避免 async race）；FE `AgentLiveActivity` verb_group；`apply_patch` Add File 接受无 `+` 正文行；Search 标题含 path 以区分多次 grep。

#### D47 — 中间产物芯片可点
- **可见**：本回合 `files_changed` / 写出的报告路径自动变成芯片；点击走现有预览（**DECISIONS D42** 路径预览能力）；可选缩略图。
- **验收**：Agent 写出 `notes.md` → 气泡旁出现芯片 → 一点打开预览；不必在正文里自己找路径。
- **编号注意**：本表 **D42** = MCP 真实工具目录 UI；路径预览是仓库已有决策 **DECISIONS D42**，两套编号勿混。
- **实现笔记（PM 2026-07-24 点验通过）**：Sidecar seal `ChatMessage.filesChanged`（与 D46 `toolSteps` 同路径）；FE `FilesChangedChips` → `onOpenWorkspaceFile`；既有 `file_changed` → Changes 面板不变。

#### D48 — 子 Agent 嵌套交互
- **可见**：自动派 subagent（D10）时，父气泡下出现子任务卡（状态、类型 explore/implement、摘要）；可点开子轨迹或跳到对应 lane/日志；失败可见。
- **验收**：说「先调研再改」→ 出现子卡片从 running→done → 主气泡继续；点卡片能看到子步骤或摘要，不是只有 Terminal Overview 一行字。
- **实现笔记（PM ✅ 随 D10 2026-07-25）**：嵌套卡 + Show steps；implement 第二张卡非强制。

#### D49 — 计划 / Todo / 提问嵌在对话流
- **可见**：D2 计划审批卡、D3 Todo 列表、D4 选择题 **出现在 Chat 时间线**（不只右侧栏或设置）。
- **验收**：复杂需求 → 对话里直接批准计划；Todo 在对话旁或气泡下勾选变化；歧义题在对话里点选。
- **实现笔记（计划卡 · PM 2026-07-24 点验通过）**：`propose_plan` → seal `ChatMessage.planCard`；FE `PlanCardView`（步骤展示）+ 底部 Approve / Revise / Cancel；Todo 卡随 D3；提问卡随 D4。

#### D50 — 验证报告与 Diff 嵌对话
- **可见**：D5 验证结论、D6 diff 摘要作为气泡块/可展开卡，而不只是 Terminal 一行。
- **验收**：做完后对话里看到「验证失败/通过」块；点「查看改动」打开 diff/预览。
- **实现笔记（验证卡 · PM ✅ 2026-07-24；Diff 卡 · PM ✅ 2026-07-24）**：D5 `verificationReport`；D6 每次 edit 挂 `toolSteps[].fileDiff` + Cursor 式 `InlineFileDiffCard`；Changes 与 hunk 同源。

#### D51 — Chat ↔ Terminal 同步
- **可见**：步骤条或子任务卡上「在 Terminal 查看」→ 聚焦对应 lane/滚动到日志。
- **验收**：Chat 点某 Shell 步骤 → Terminal 跳到该段输出（有 Terminal 会话时）。

#### D52 — 能力↔交互对照门禁
- **可见**：`PRODUCT_INTRO` 增加表：能力 → Chat 里看见什么；发版/标完成前核对。
- **验收**：抽查 D1/D10/D37 均有对应 UI 描述且与真机一致。

---

## Prompt 运行时专项 D53

#### D53 — 分层 system prompt + 渐进式披露
- **原则**：提示词**拆开组装**，按需披露；禁止把 AGENTS.md / Skills 全文 / 模式说明永久糊进一份 `markdownDoc` 当唯一 system。对标 Grok Build：**模板+代码组装**，磁盘规则以可注入层进入上下文，而不是「读一份文档 = system prompt」。
- **通道（最低分层）**：

  | 层 | 内容 | 披露时机 |
  |----|------|----------|
  | **System 底座** | 身份、安全、tool-calling 规范、输出风格（短、稳定） | 每轮 / session 固定 |
  | **Env 前缀** | OS、shell、workspace 根、日期、可选 VCS 快照 | session / 工作区切换时刷新 |
  | **项目规则** | `AGENTS.md` / CLAUDE.md / rules（与 **D7** 发现） | 有则注入为独立上下文块（优先 reminder/user 层，勿无限膨胀 system） |
  | **Skills 目录** | 名称+一句话；**全文按需**（点名 skill / 工具拉取） | 渐进：目录常驻摘要，正文按调用披露 |
  | **Mode 覆盖** | Plan 模式等（与 **D2**） | **当轮 reminder**，退出即撤，不写死进底座 |
  | **用户话轮** | 明确包裹（如 `<user_query>` 等价） | 每条用户消息 |

- **可见**：同仓库有/无 `AGENTS.md`、开/关 Plan、绑/不绑 Skills 时行为可区分；**Agent Manager → Clutch Agent 详情右侧**展示「运行时提示词分层」（层名 + 字符量 + 当前 permission mode，可刷新）；`GET /api/agents/{id}/prompt-assembly` 同数据。
- **验收**：
  1. 底座变短稳定；换仓库后旧规则不残留。
  2. Skills 未调用时上下文只有目录级摘要，不整份 SKILL.md 塞满。
  3. Plan 模式开启时出现约束 reminder；退出后不再出现。
  4. 压缩/续聊后规则层可再注入（与 **D8** 对齐）。
- **实现落点**：`agent_prompt.compose_agent_prompt_assembly` + Skills 目录默认；`GET /api/agents/{id}/prompt-assembly`；**Agent Manager 右侧「运行时提示词分层」**。**PM 2026-07-24 点验通过**。
- **与 D7**：D7 = 发现与生效内容；**D53 = 组装架构与披露策略**。无 D53 时 D7 易退化成「全塞进 system」。

---

## 能力 → 前端交互映射（摘要）

| 能力期 | 必须看见的交互（最低） |
|--------|------------------------|
| D1 手脚 | D46 步骤条 + D47 产物芯片 + 通用审批（MCP 场景叠加 D41） |
| D2–D4 计划/Todo/问 | **D49** 对话内卡片（D2–D4 未带 D49 不算完成） |
| D5–D6 验证/Diff | **D50**（未嵌对话不算完成） |
| D9 停续/用量 | Chat 可见停止/继续控件 + 用量；与 D22 不矛盾 |
| D10 子任务 | **D48**（D10 无嵌套卡不算完成） |
| D11 后台 | 对话或面板有任务条 + 可点看输出 |
| D19 思考流 | 与 **D46** 合并交付亦可；禁止两套互斥 UI |
| D37+ MCP | D40 徽章 + D41 审批 + D46 显示 MCP 步骤 |
| D7 规则/Skills | **D53** 分层注入可见（有无规则行为差 + 可选组装摘要） |
| D2 Plan | Mode reminder 走 **D53**；对话卡走 **D49** |

---

## MCP 现状（为何要专项）

今天大致是：

- Hub 能注册/开关 stdio 服务器；后端 ReAct 在 **真有 `mcpServerIds`** 时能跑。
- **断点：** Agent Manager 的 MCP 绑定仍是 `UnderDevelopmentNotice`；保存会把 `mcpServerIds` **清空** → Chat 很少真正走到 MCP。
- SSE/HTTP 可登记；运行时走 **stdio 或 Streamable HTTP**。Env 可带 `Authorization` / `HEADER_*`。
- Hub/文档仍有「开发中」或超卖，和真实能力不一致。

因此 MCP **不能**只靠 D28（工具多时搜索）；必须先有 **D37 绑定可用**。

---

## MCP 专项 D37–D45（可独立验收）

#### D37 — 恢复 Agent↔Hub 绑定（最优先）
- **可见**：Clutch Agent 编辑页可勾选已启用 Hub 服务器 + local-fs；保存后重开仍在；详情显示已绑名称（无 UnderDevelopment 挡路）。
- **验收**：绑 `local-fs` → Chat 出现工具步骤；再保存 Agent 其他字段 → 绑定不丢。

#### D38 — Hub 可信状态
- **可见**：去掉误导性「开发中」横幅（CRUD 已可用时）；「测试连接」按钮；失败显示可读错误（非笼统灰点）。
- **验收**：坏命令的服务器点测试 → 明确失败原因；好服务器列出工具数。

#### D39 — 传输诚实 + 远程可用
- **可见**：Hub 可选 **stdio** 或 **HTTP**（Streamable HTTP URL）；Env 支持 `Authorization` / `HEADER_*`。
- **验收**：HTTP 填任意 MCP URL → Test 出工具列表；OAuth 远程（无 Env Key、401）会打开浏览器；配了 Key 的 HTTP 不走浏览器。

#### D40 — Chat 已绑 MCP 可见
- **可见**：Chat/顶栏有「已绑 N 个 MCP / 工具约 M」类提示；未绑时引导去绑定或一键启用。
- **验收**：绑定前后徽章数字变化；点开能看到服务器名。

#### D41 — MCP 专用审批体验
- **可见**：风险工具暂停时卡片含工具名、规范化路径、批准一次/拒绝；Terminal 文案对齐；同 run 内相同批准可记忆（与 permission 模式一致）。
- **验收**：写文件触发审批 → 路径可读；拒绝后不落盘。

#### D42 — 真实工具目录 UI（本表编号；≠ 仓库 DECISIONS「D42 路径预览」）
- **可见**：去掉假的 `mcpTools` 权限芯片；Agent/Hub 展示真实工具名与数量。
- **验收**：绑 filesystem 后能看到 `read_file`/`write_file` 等真实名，而非占位 permission key。

#### D43 — MCP Resources
- **可见**：服务器若暴露 resources，可浏览并选用注入上下文（对标 backlog B-28）。
- **验收**：带 resources 的测试服务器 → UI 列出 → Chat 能引用其内容。

#### D44 — 一键启用工作区工具
- **可见**：Agent 或 Chat 空态「启用工作区文件工具」一键绑定 local-fs（+ 与 D1 builtins 协同说明）。
- **验收**：新 Agent 一键后无需手勾即可 list/读工作区。

#### D45 — 文档与现实对齐
- **可见**：`PRODUCT_INTRO`、Epicode 指南、ROADMAP 不再写「已可绑定/HTTP 已通」若未通；通了则写准步骤。
- **验收**：按文档逐步操作能成功；PM 对照文档无踩坑。

**与 D28 关系：** D28（工具很多时搜索/选用）依赖 D37 绑定可用；排在 D37–D42 之后。

---

## 完整任务清单

### D0 — 决策落盘（写入仓库）✅
- **可见**：仓库内可打开权威表；`DECISIONS` / `ROADMAP` / `FILEMAP` 有入口。
- **验收（2026-07-24）**：
  1. ✅ 本文 `specs/core/clutch-agent-capability-plan.md`
  2. ✅ `DECISIONS.md` **D44**
  3. ✅ `ROADMAP.md` §Chat Clutch Agent
  4. ✅ `FILEMAP.md` + `AGENTS.md` 索引
- **说明**：仅改 `~/.cursor/plans/…` **不算** D0 完成（已过时）。

---

### 主线 D1–D13（先做完可对外宣称齐）

#### D1 — Agent 真会干活
- **可见**：读写/列表/搜索/改文件/跑命令；**D46** 工具轨迹；默认审批；**D47** 有改文件时出芯片。
- **验收**：Chat+Clutch Agent+workspace；改 README 真落盘；`pwd` 需批准；不再「纯文本无手脚」；步骤条可见。
- **交互先决**：同迭代或紧随交付 D46（+ 建议 D47）。

#### D2 — 先计划再动手
- **可见**：计划预览；批准 / 改意见 / 取消；未批准不改业务文件；简单任务可跳过。
- **验收**：「加登录」先出计划；批准后才有文件变更。
- **交互先决**：**D49**（计划卡在对话流）。
- **实现笔记（PM 2026-07-24 点验通过）**：builtin `propose_plan` 在写文件前 pause；批准后注入 tool result 继续 ReAct；修改意见走 `human_decision` retry；功能类请求注入 D2 reminder；计划正文仅 PlanCard，操作仅底部 dock。

#### D3 — Todo 面板
- **可见**：待办/进行中/完成；执行中勾选变化；刷新仍在。
- **验收**：多步任务 ≥3 条 Todo 且状态跟随。
- **交互先决**：**D49**。
- **实现笔记**：builtin `todo_write` → `ClutchState.agent_todos` 实时 + seal `ChatMessage.todoList`；FE `TodoCardView`。**`todo_write` 不走人工审批**（UI 元数据；`is_risky` 排除）。运行中未全部完成时 Chat 吸顶固定 Todo 卡；全部完成后取消固定并随 seal 气泡滚动。PM 2026-07-24 点验通过。

#### D4 — 结构化提问
- **可见**：选择题卡；答完按选择继续；明确需求不瞎问。
- **验收**：「加缓存」弹出选项；选 Redis 后路径一致。
- **交互先决**：**D49**。
- **实现笔记（PM 2026-07-24 点验通过）**：builtin `ask_user_question` → pause `kind: question` → seal `ChatMessage.questionCard`；FE `QuestionCardView`（可点选项）+ 共享 `chatAgentCard` 与 Plan/Todo 对齐 UI_UX_GUIDELINES；dock Cancel / 自定义；选完 resume `selected`；**不走**通用 MCP risky Allow 门。

#### D5 — 做完自检报告
- **可见**：验证步骤+通过/失败结论；失败可操作；Todo 未完不谎称完成。
- **验收**：故意验失败 → 失败报告而非沉默结束。
- **交互先决**：**D50**。
- **实现笔记（PM ✅ 2026-07-24 · `30d5f86`）**：builtin `submit_verification` → seal `ChatMessage.verificationReport`；FE `VerificationReportCardView`（步骤 + 通过/失败 chip + next actions + View changes）；incomplete todos 强制 failed；非 risky 门；`_merge_patch` 放行 `verification_report`。

#### D6 — Diff 审查
- **可见**：变更文件列表+可读 diff。
- **验收**：改 2 文件能点开差异。
- **交互先决**：**D50**（可与 Changes 页并存，但对话内须可达）。
- **实现笔记（PM ✅ 2026-07-24）**：edit 成功 → `ToolStep.fileDiff` + FE `AgentLiveActivity`/`InlineFileDiffCard`（文件名 + `+/-` hunk）；行级 append；Changes 推送同源 diffs；可选 `submit_diff_summary` 汇总卡。

#### D7 — 项目规则 + Skills
- **可见**：有 `AGENTS.md`/Skills 的仓库行为不同；换仓库恢复默认。
- **验收**：规则仓库遵守约束；无规则仓库不出现该约束。
- **组装先决**：**D53**（发现内容须按层注入 + 渐进披露；禁止整份永久糊进 system）。
- **实现笔记（PM ✅ 2026-07-25）**：对齐 Grok Build（DECISIONS **D45**）。规则：`git root → workspace` 串链 + `.grok/.claude/.cursor/rules`（更深优先；无 User home 规则）。Skills：开放 catalog（Enabled global∪project∪custom + 可选 Agent 绑定）；同名 project>custom>global；`read_skill` 按需正文；Custom SEARCH PATHS 换仓保留。PM：有规则仓 `RULE_TOKEN_ORANGE`；`read_skill`→`SKILL_BODY_LOADED`。

#### D8 — 长聊不丢任务态
- **可见**：压缩后仍答得上 Todo/计划要点；压缩发生时有提示。
- **验收**：触发压缩后问「还剩什么」答对。
- **实现笔记（PM ✅ 2026-07-25）**：`task_state` 层每轮注入；`/compact` 末尾 User 气泡 + 琥珀色摘要；压缩后问「还剩哪些 todo」答对。

#### D9 — 运行可控
- **可见**：停止、继续；熔断提示（自动化）；用量区在 Overview（占位 `—`）。
- **验收**：停得住、续得上。
- **实现笔记（PM ✅ Stop/Continue 2026-07-25）**：`run_control.py`；Stop→Continue；fuse 不点验；用量真值见 **Q-USAGE-1**。

#### D10 — 子任务委派
- **可见**：子任务状态与摘要回主 Chat。
- **验收**：先探查再改；子失败主可见。
- **交互先决**：**D48**（嵌套卡片）；无 D48 不算 D10 完成。
- **实现笔记（PM ✅ 2026-07-25）**：explore max_steps=16 / implement=12；嵌套卡 explore→done 即可；第二张 implement 卡非强制（父可自行改文件）。

#### D11 — 后台命令
- **可见**：后台跑、看输出、完成通知、杀掉；前台仍可聊。
- **验收**：`sleep`/短测后台时还能提问。
- **实现笔记（PM ✅ 2026-07-25）**：RUNNING 仅底栏；结束封 `msg.bgJob` 进对话；Kill 乐观、无失败 toast。

#### D12 — Git + 网页文档
- **可见**：status/diff；提交需审批；fetch URL 总结；步骤进 D46。
- **验收**：diff 真；commit 真；URL 能引用要点。
- **实现笔记（PM ✅ 2026-07-25）**：Ask 下 `git_commit` 审批后真实提交；`web_fetch` 可总结页面。

#### D13 — 权限规则设置
- **可见**：允许/询问/拒绝配置；危险命令强问；记住/清除。
- **验收**：拒规则生效；`rm` 类强问；记忆可关。
- **实现笔记（PM ✅ A 2026-07-25；B/C 不点验）**：危险命令 Full 下仍 force-ask；deny/clear 自动化覆盖。

---

### 旁路 D14（可选，不计自研覆盖）

#### D14 — 外挂 grok CLI
- **可见**：引擎列表可选 Grok；有外部轨迹。
- **验收**：能跑通一轮；不替代 D1–D13。

---

### 扩展 D15–D36（主线后做）

#### D15 — 联网搜索
- **可见**：Agent 能搜网页并引用结果（不只 fetch 已知 URL）。
- **验收**：「搜 X 最新做法并总结」→ 有来源摘要；可关联网。

#### D16 — 跨会话记忆
- **可见**：设置开/关 Memory；新会话能召回你之前定的约定。
- **验收**：会话 A 记下「提交用中文」；会话 B 无重述仍遵守；可一键清除。

#### D17 — Hooks 可配置
- **可见**：设置/项目里配 Pre/Post 工具钩子；违规调用被拒有说明。
- **验收**：Hook 拒绝某写操作 → Chat 可见拒绝原因。

#### D18 — Chat 斜杠命令
- **可见**：输入 `/` 出命令（如 `/plan` `/compact` `/todos`）；执行有反馈。
- **验收**：`/plan` 进入计划态；`/compact` 触发压缩且有提示。

#### D19 — 思考流 + 工具进度
- **可见**：推理可折叠展示；长命令有输出进度/片段。
- **验收**：跑长命令时 UI 不全白等；思考可展开/收起。
- **说明**：可与 **D46** 合并为同一 Chat 活动区，避免两套互斥控件。

#### D20 — 忙时消息排队
- **可见**：Agent 忙时发消息入队；提示队列位置；可取消排队。
- **验收**：执行中连发 2 条 → 第二条；完成后依次处理。

#### D21 — 忽略规则 + 沙箱模式
- **可见**：尊重 `.gitignore`/`.clutchignore`；设置里可选更严沙箱；误扫密钥目录减少。
- **验收**：忽略路径不被 list/grep；开严沙箱后出界命令失败且说明。

#### D22 — 用量看板
- **可见**：右侧 Overview Session Token Analytics（**暂占位 `—`**）。
- **验收（真值后）**：跑一轮后数字增加且可信；见开放问题 **Q-USAGE-1**。

#### D23 — 会话分支 + 文件回滚
- **可见**：从某条消息 fork 新会话；一键撤销 Agent 最近文件改动。
- **验收**：fork 后旧会话不变；rewind 后文件恢复，Chat 有记录。

#### D24 — LSP / 诊断回灌
- **可见**：改代码后诊断/类型错误进 Chat 或问题条，Agent 据此修。
- **验收**：引入语法错误 → 可见诊断 → Agent 下一轮能针对修。

#### D25 — 定时 / 循环任务
- **可见**：可创建间隔任务（默认关/需确认）；列表/删除；触发时有通知。
- **验收**：建一条短间隔任务 → 到点提醒或跑一轮 → 可删；默认不打扰。

#### D26 — 长任务监视
- **可见**：监视后台/子任务事件；完成或异常推到 Chat。
- **验收**：后台测挂了 → Chat 出现失败监视提示。

#### D27 — 模式 / 人设切换
- **可见**：一键切 Agent / Plan / Full / Ask；工具权限随模式变。
- **验收**：Ask 无法写文件；Agent/Full 可写。
- **实现笔记（D54）**：默认 Agent；Ask=只读；Explore 并入 Ask；UI 对标 Cursor。

#### D28 — MCP 工具很多时的发现
- **可见**：MCP 工具多时，Agent 先搜再选（或 UI 筛选）；不一次丢上百 tool。
- **验收**：挂多个 MCP → 仍能找到并调用目标工具；轨迹可读。

#### D29 — Goal 跟踪
- **可见**：当前目标条；Agent/用户可更新进度；完成可勾掉。
- **验收**：设目标「修登录」→ 执行中进度变化 → 完成后目标关闭。

#### D30 — 会话总览看板
- **可见**：本地 Chat 会话/分支列表（进行中、已完成、fork 关系）。
- **验收**：多会话时能从看板点回某一 run；fork 有父子标识。

#### D31 — 计划行内批注
- **可见**：计划预览里对某段留评论；批准时可「带评论批准」。
- **验收**：批注后 Agent 修订计划再执行。

#### D32 — Worktree 隔离试验
- **可见**：可选「在隔离 worktree 里改」；主工作区不被脏改；可合并/丢弃。
- **验收**：隔离改动在副目录/分支；丢弃后主仓干净。

#### D33 — 富文件阅读
- **可见**：让 Agent 读 PDF/图片（及常见办公格式若支持）并回答内容。
- **验收**：丢一个 PDF/截图问要点 → 回答基于文件而非瞎编。

#### D34 — 前台转后台
- **可见**：正在跑的前台命令可一键转后台（对标 Grok Ctrl+B）。
- **验收**：长命令执行中点转后台 → 可继续聊天 + 任务仍在 D11 列表。

#### D35 — 导入能力包
- **可见**：导入一份捆绑（Skills + Hooks + MCP 配置），不必去插件市场。
- **验收**：导入后 Skills/Hooks/MCP 立刻可用；可卸载。

#### D36 — 无 UI / CI 调用同一 Agent
- **可见**：文档+命令/API：脚本里跑同一 Clutch Agent（对标 `grok -p`）。
- **验收**：CI 或 CLI 跑一轮改文件+退出码；与 Chat 行为同核。

---

## Grok → 本表对照（抽查）

| Grok 能力 | 落点 |
|-----------|------|
| read/list/grep/edit/shell | D1 |
| plan enter/exit + 审批 | D2；批注 D31 |
| todo_write | D3 |
| ask_user_question | D4 |
| 验证/自检 | D5 |
| 变更可见 | D6 |
| AGENTS.md / Skills | D7（发现）；**D53**（分层注入 + 渐进披露）；能力包 D35 |
| compaction / 长会话 | D8；压缩后规则再注入属 **D53** |
| max-turns / 停续 / 防死循环 | D9 |
| task / subagents / personas·modes | D10；D27 |
| background / wait / kill / monitor | D11；D26；转后台 D34 |
| git + web_fetch | D12 |
| permissions / 危险命令 / 记忆批准 | D13 |
| web_search | D15 |
| memory | D16 |
| hooks | D17 |
| slash commands | D18 |
| 思考流 / 流式工具输出 | D19 |
| prompt queue | D20 |
| sandbox / ignore | D21 |
| usage dashboard | D22 |
| session fork / rewind | D23；看板 D30 |
| LSP | D24 |
| scheduler /loop | D25 |
| goals | D29 |
| worktree | D32 |
| 富读（PDF/图） | D33 |
| headless `-p` | D36 |
| 外挂 grok 二进制 | D14 |
| **运行时 system 分层组装** | **D53**（对标 Grok PromptContext + reminders，不嵌 Rust） |
| MCP Hub / 自定义模型 / 媒体模型 | **部分已有**；Hub 绑定与传输见 **D37–D45** |
| MCP 工具过多时的发现 | D28（先决 D37） |
| image_gen / video 工具 | **复用现有 Chat 媒体路径**，不另开 |
| workflow / deploy_app 工具 | **不做进 Agent**（编排/部署上层或外部） |
| TUI 主题/快捷键/ACP 深嵌/OTEL/Voice/插件市场/computer-hub | **有意不对齐** |

---

## 有意不对齐（永不进上表）

| 项 | 原因 |
|----|------|
| 嵌入 grok-build Rust | 栈/治理不匹配 |
| Grok 插件市场 / TUI 主题 / 全键位 | Clutch 自有 UX；用 D35 导入代替市场 |
| Voice | 非编码主路径 |
| 远程 computer-hub | 非本地优先 |
| Agent 内 `workflow`/`deploy_app` 工具 | 编排与部署不放进 Chat Agent 本体 |
| SOP 编排桥独立大项 | 编排在 Agent 之上 |
| 客户 OTEL 导出 | 可另开运维项，非 Agent 能力主路径 |
| ACP 深度 IDE 宿主 | 与 Clutch 桌面重复；D14 最多浅接 |

---

## 推荐顺序

```text
主线：  D0 → D1 → D2 → … → D13
MCP：   D37 → … → D45（与 D1 并行/紧挨）
Chat UX：D46（随 D1）→ D47 → D49（随 D2–D4）→ D50（随 D5–D6）→ D48（随 D10）→ D51 → D52
Prompt： D53（宜早：在 D7/D2 深化前定组装骨架；可与 D1 后并行）
旁路：  D14
扩展：  D15…D36
```

**第一期给 PM：** D1 + D37 + **D46**（能干、MCP 能绑、对话里能看见正在干嘛）。  
**紧随：** **D53**（提示词拆层 + 渐进披露），避免 D7/Skills 继续「全塞 system」。

---

## 每期完成定义

1. 上表验收脚本走通（**含前端可见**）。  
2. 若该能力在「能力→交互映射」有行，对应 D46–D51 交互必须可演示，否则不算完成。  
3. `PRODUCT_INTRO` / `CHANGELOG` 当前开发版本节（`## [Unreleased]`）。  
4. `./scripts/verify.sh`（或子集）通过——必要但不充分。

## 任务总数

- D0 ×1  
- 主线 D1–D13 ×13  
- 旁路 D14 ×1  
- 扩展 D15–D36 ×22  
- MCP D37–D45 ×9  
- **Chat UX D46–D52 ×7**  
- **Prompt 运行时 D53 ×1**  
- **合计：54**（D0–D53）

**结论：** 能力表 + MCP + 对话监督交互 + **分层提示词** 对齐「别的 agent」体验与 Grok 式组装；缺交互或缺组装纪律的能力不得单独标完成。

---

## 文档自检（本次核对）

| 检查项 | 结果 |
|--------|------|
| 正文 D0–D53 齐 | 通过（54 项） |
| 计数 1+13+1+22+9+7+1=54 | 通过 |
| 主线条目写明交互先决（D46/D48/D49/D50） | 已补 |
| D7 组装先决 D53 | 已补 |
| 本表 D42 vs DECISIONS D42 撞名 | **已标注区分**（MCP 工具目录 vs 路径预览） |
| 扩展章节误标「D15–D28」 | **已改为 D15–D36** |
| D1 误绑「必须 D41」 | **已改为**通用审批 + MCP 时叠加 D41 |
| D19 / D46 重叠 | **已说明可合并交付** |
| 有意不对齐清单 | 保留，避免假「100% Grok」 |
| 第一期 PM 演示 | D1 + D37 + D46；紧随 D53 |
