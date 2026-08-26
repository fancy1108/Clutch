# ROADMAP

> **Default FAIL：** 所有功能项默认 ❌，必须实际验证通过后才能标记 ✅。  
> 验证证据记入 `TESTS.md` 或 `runs/verification/`。  
> 任务拆解见 [`specs/core/tasks.md`](../specs/core/tasks.md)。

## 功能清单

| 模块 | 优先级 | 里程碑 | 状态 | 任务 ID |
|------|--------|--------|------|---------|
| 工作流画布 | P0 | M1 | ✅ | M1-01/06/07/09 |
| 运行监督台 | P0 | M2 | ✅ | M2-01–14 |
| 编排引擎 | P0 | M1 | ✅ | M1-02~05、M1-08/09 |
| 人工干预 | P0 | M2 | ✅ | M2-04, M2-05, M2-12 |
| 桌面基座（Tauri + Sidecar + WS） | P0 | M0 | ✅ | M0-01–06 |
| LLM Provider | P1 | M1 | ✅ | M1-08（D4）；M4-09 |
| CLI 工具接入 | P1 | M3 | ✅ | M3-01, M3-07 |
| 文件变更与 Diff | P1 | M3 | ✅ | M3-02（`file_changed` 投影） |
| Cursor 唤起 + 自动检查 | P1 | M3 | ✅ | M3-03, M3-04, M3-05 |
| Agent 配置 | P1 | M4 | ✅ | M4-02 |
| MCP 管理 | P2 | M4 | ✅ | M4-03（filesystem 状态） |
| Skills 注册（后端同步） | P2 | P2 | ✅ | P2-01 |
| 全量 MCP 配置 | P2 | P2 | ✅ | P2-02 |
| Theme 持久化 | P2 | P2 | ✅ | P2-03 |
| i18n 双语 | P2 | P2 | ✅ | P2-04 |
| 侧栏 REPOSITORIES CRUD | P2 | P2 | ✅ | P2-05 |
| General Settings | P2 | P2 | ✅ | P2-06 + **FM-01**（D56） |
| 内置模板 | P1 | M4 | ✅ | M4-01 |
| 运行历史 | P0 | M2 | ✅ | M2-07（D3）+ D11 对话持久化 |
| 文件浏览（Files 面板） | P0 | M2 | ✅ | M2-11 |
| Token / 校验结果展示 | P0 | M2 | ✅ | M2-13, M2-14 |
| 工作区授权 | P0 | M2 | ✅ | M2-09；M4-05 |
| E2E / 前端单测 | P0 | M2 | ✅ | M2-10, T-01–03（D1）；D12 桌面 E2E 7/7 |
| macOS 打包 | P1 | M4 | ✅ | M4-06 |
| **MVP 闭环** | — | M3 | ✅ | proposal §10.1；T-03 |
| **Design 模式（D36）** | P1 | Design | ✅ | 见下 §Design 模式；PM 2026-08-24 |

## Chat Clutch Agent 能力（DECISIONS D44 · 默认 FAIL）

> 权威任务表：[`specs/core/clutch-agent-capability-plan.md`](../specs/core/clutch-agent-capability-plan.md)（交付期 D0–D53）。未 PM 验收不得标 ✅。  
> 编号：下表 Dn = 交付期，**不是** DECISIONS Dx。

| 交付期 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| D0 决策落库 | P0 | ✅ | specs + DECISIONS D44 + 本表 + FILEMAP |
| D1 Agent 真会干活 | P0 | ✅ | clutch-tools builtins + 默认挂载；PM 2026-07-24 点验通过 |
| D2 先计划再动手 | P0 | ✅ | `propose_plan` + PlanCard；PM 2026-07-24 点验通过（须同验 D49） |
| D3 Todo 面板 | P0 | ✅ | `todo_write` + TodoCard；PM 2026-07-24 点验通过（须同验 D49） |
| D4 结构化提问 | P0 | ✅ | `ask_user_question` + QuestionCard；PM 2026-07-24 点验通过（须同验 D49） |
| D5 自检报告 | P0 | ✅ | `submit_verification` + VerificationReport；PM 2026-07-24 点验通过（须同验 D50） |
| D6 Diff 审查 | P0 | ✅ | Cursor 式 edit Diff 卡 + Changes 同步；PM 2026-07-24 点验通过（须同验 D50） |
| D7 项目规则 + Skills | P0 | ✅ | Grok 对齐：规则链 + 开放 Skills catalog；PM 2026-07-25 点验通过 |
| D8 长聊不丢任务态 | P0 | ✅ | `/compact`→末尾摘要；压缩后答还剩 todo；PM 2026-07-25 点验通过 |
| D9 运行可控 | P0 | ✅ | Stop/Continue PM ✅ 2026-07-25；熔断不点验；用量见 D22 / Q-USAGE-1 |
| D10∥D48 子任务委派 | P0 | ✅ | PM ✅ 2026-07-25；explore 16 步；implement 卡非强制 |
| D11 后台命令 | P0 | ✅ | PM ✅ 2026-07-25；RUNNING 底栏 / 结束进对话；Kill 乐观 |
| D12 Git + 网页 | P0 | ✅ | PM ✅ 2026-07-25；commit 真（bcfc099 d12-pm-test）；web_fetch 总结 |
| D13 权限规则 | P0 | ✅ | PM ✅ A 2026-07-25；B/C 不点验；危险 Full 仍强问 |
| D14 外挂 grok CLI | P2 | ✅ | Agent 自验 2026-07-25（`AGENT-PM-2026-07-25.md`） |
| D15 联网搜索 | P1 | ✅ | Agent 自验 2026-07-25 |
| D16 跨会话记忆 | P1 | ✅ | Agent 自验 2026-07-25 |
| D17 Hooks | P1 | ✅ | Agent 自验 2026-07-25 |
| D18 斜杠命令 | P1 | ✅ | Agent 自验 2026-07-25 |
| D19 思考流 | P1 | ✅ | Agent 自验 2026-07-25 |
| D20 忙时排队 | P1 | ✅ | Agent 自验 2026-07-25 |
| D21 ignore/沙箱 | P1 | ✅ | Agent 自验 2026-07-25 |
| D22 用量看板 | P1 | ✅ | Overview 步数/tokens；供应商真值优先，否则 `~` 估算；费用 `—`（Q-USAGE-1 2026-08-25） |
| D23 fork/rewind | P1 | ✅ | Agent 自验 2026-07-25 |
| D24 诊断 MVP | P2 | ✅ | Agent 自验 2026-07-25 |
| Cap-D25 定时任务 | P2 | ✅ | Agent 自验 2026-07-25（≠ Hybrid D25） |
| D26 长任务监视 | P1 | ✅ | Agent 自验 2026-07-25 |
| D27 模式/人设 | P1 | ✅ | Agent/Plan/Full/Ask；Ask=只读（D54）；Agent 自验 2026-07-25 |
| D28 MCP 工具发现 | P1 | ✅ | Agent 自验 2026-07-25 |
| D29 Goal 跟踪 | P1 | ✅ | Agent 自验 2026-07-25 |
| D30 会话看板 | P1 | ✅ | Agent 自验 2026-07-25 |
| D31 计划批注 | P1 | ✅ | Agent 自验 2026-07-25 |
| D32 worktree | P2 | ✅ | Agent 自验 2026-07-25 |
| D33 富读 PDF/图 | P1 | ✅ | Agent 自验 2026-07-25 |
| D34 前台转后台 | P1 | ✅ | Agent 自验 2026-07-25 |
| D35 能力包导入 | P2 | ✅ | Agent 自验 2026-07-25 |
| D36 headless Agent | P2 | ✅ | Agent 自验 2026-07-25（≠ Design D36） |
| D37 MCP Agent↔Hub 绑定 | P0 | ✅ | Module 4 Hub 勾选 + `mcpServerIds`；PM 2026-07-24 点验通过 |
| D38 Hub 可信状态 | P1 | ✅ | Agent 自验 2026-07-25 |
| D39 传输诚实 | P1 | ✅ | Agent 自验 2026-07-25 |
| D40 Chat MCP 徽章 | P1 | ✅ | Agent 自验 2026-07-25 |
| D41 MCP 审批体验 | P1 | ✅ | Agent 自验 2026-07-25（Ask≠写审批；见 D41.md） |
| D42 真实工具名 UI | P1 | ✅ | Agent 自验 2026-07-25 |
| D43 MCP Resources | P1 | ✅ | Agent 自验 2026-07-25 |
| D44 一键 local-fs | P1 | ✅ | Agent 自验 2026-07-25 |
| D45 文档对齐 | P1 | ✅ | Agent 自验 2026-07-25 |
| D46 对话实时步骤条 | P0 | ✅ | 持久 verb_group + seal `toolSteps`；PM 2026-07-24 点验通过 |
| D47 中间产物芯片 | P0 | ✅ | seal `filesChanged` + FilesChangedChips → D42 预览；PM 2026-07-24 点验通过 |
| D49 计划嵌对话流 | P0 | ✅ | PlanCard + TodoCard + QuestionCard；PM 2026-07-24（D2/D3/D4） |
| D50 验证报告嵌对话 | P0 | ✅ | VerificationReport（D5）+ Cursor Diff 卡（D6）；PM 2026-07-24 |
| D48 子任务嵌套卡 | P0 | ✅ | 随 D10 PM ✅ 2026-07-25 |
| D51 Chat ↔ Terminal 同步 | P1 | ✅ | Agent 自验 2026-07-25 |
| D52 能力↔交互对照门禁 | P1 | ✅ | Agent 自验 2026-07-25 |
| D53 分层 prompt + 渐进披露 | P0 | ✅ | 分层组装 + Agent Manager 分层摘要面板；PM 2026-07-24 点验通过 |

**首期目标：** D1 + D37 + D46 ✅（PM 2026-07-24）。  
**扩展/MCP：** Agent 代 PM 自验 2026-07-25（见 `runs/verification/pm-acceptance/AGENT-PM-2026-07-25.md`）；Desktop Tauri E2E ✅；真连 acceptance Skip（缺 DeepSeek/Agnes 密钥）。

## Agent Harness（B-34 · 默认 FAIL）

> 书 06 · **Q-AGENT-1 = C**。定义与「做了/没做」：[`specs/core/tasks.md`](../specs/core/tasks.md) §Agent Harness。不升 D54+。  
> **维护者尺子，无界面。** 未挪本机时间 / Todo（仍在 system 前缀 `env` / `task_state`）。预期布局见 **B-35** / **Q-AGENT-2**。不请 PM 点验。

| 验收项 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| 静态层快照确定性（排除 env 时钟） | P0 | ✅ | pytest 2026-08-24；`env` 仍含 Local time，只是不进指纹 |
| 契约：Ask 只读 / todo 在 task_state / 特性请求 propose_plan | P0 | ✅ | pytest 2026-08-24 |
| 本机 Agnes live 小集 | P1 | ✅ | `CLUTCH_AGENT_EVAL_LIVE=1` 3 passed（CC Switch Agnes） |

## Agent eval ablation（B-48 · 默认 FAIL）

> 书 06 · B-34 之后。定义：[`specs/core/tasks.md`](../specs/core/tasks.md) §Agent eval ablation。不升 D54+。  
> **维护者尺子，无界面。** 不请 PM 点验 Chat。

| 验收项 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| 消融闸可关掉可选层 | P0 | ✅ | pytest 2026-08-24 `test_agent_eval_b48`：`tools` 层消失且指纹变 |
| trajectory JSONL 落盘且去密钥 | P0 | ✅ | 同上；写 `runs/archive/eval/`（测试用 tmp） |

## Agent status（B-35 · 默认 FAIL）

> 书 02 · **Q-AGENT-2 = A**。定义：[`specs/core/tasks.md`](../specs/core/tasks.md) §Agent status。  
> 时钟与完整 Todo 离开 system 前缀，进对话末尾 `<agent_status>`（每轮整换）。Agent Manager「运行时提示词分层」会出现 `agent_status`，`env` 不再含 Local time。

| 验收项 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| system 前缀不含 Local time / 完整 Todo | P0 | ✅ | pytest 2026-08-24 |
| 末尾 `<agent_status>` 每轮整换不堆历史 | P0 | ✅ | pytest `attach_trailing_status` |
| Agent Manager 分层可见 `agent_status` | P1 | ✅ | 2026-08-24 PM 点开 Clutch Agent 详情：`agent_status` 157 · `env` 82（无时钟） |

## Agent context layers（B-36 · 默认 FAIL）

> 书 02。定义：[`specs/core/tasks.md`](../specs/core/tasks.md) §Agent context layers。  
> 工具结果：落盘 → 去噪声 → 阈值批量压 → 全量 `/compact` 熔断。L1–L3 无新气泡。

| 验收项 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| 大工具结果落盘且消息只留指针 | P0 | ✅ | pytest 2026-08-24 `test_context_layers_b36` |
| 噪声删除 + 超阈值只压旧工具 | P0 | ✅ | 同上 |
| `/compact` 全量熔断仍可用 | P0 | ✅ | `test_compaction` + B-36 阈值回归 |

## Agent archived tool markers（B-44 · 默认 FAIL）

> 书 02。定义：[`specs/core/tasks.md`](../specs/core/tasks.md) §Agent archived tool markers。  
> 落盘指针标明来源与截断；无新 Chat 卡片。

| 验收项 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| 指针含 `source=tool truncated=yes` | P0 | ✅ | pytest 2026-08-24 `test_context_layers_b36`；PM 读 `CHANGELOG.md` 全文 |

## Agent verification gate（B-37 · 默认 FAIL）

> 书 01+05 · **Q-AGENT-3 = C**。定义：[`specs/core/tasks.md`](../specs/core/tasks.md) §Agent verification gate。  
> 有测套先跑；再核对产物在不在。仍是原来的验证报告卡。

| 验收项 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| 测套失败时验证卡不能绿 | P0 | ✅ | pytest 2026-08-24 `test_verify_harness_b37` |
| 列出的文件不在磁盘时不能绿 | P0 | ✅ | 同上 |
| 无工作区时 D5 自报不变 | P0 | ✅ | 同上 |

## Agent progress loop（B-38 · 默认 FAIL）

> 书 01。定义：[`specs/core/tasks.md`](../specs/core/tasks.md) §Agent progress loop。  
> 同一读/搜空转则停，Continue 与 D9 相同。

| 验收项 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| 同一文件读三次会停 | P0 | ✅ | pytest 2026-08-24 `test_progress_loop_b38` |
| 停住后可点 Continue | P0 | ✅ | 同上 + `should_offer_continue` |

## Agent workspace memory（B-39 · 默认 FAIL）

> 书 03+08 · **Q-AGENT-4 = C 用 B**。定义：[`specs/core/tasks.md`](../specs/core/tasks.md) §Agent workspace memory。

| 验收项 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| Files 能打开 MEMORY.md | P0 | ✅ | PM 2026-08-24：记住后 Files 可见 |
| 新会话仍记得 | P0 | ✅ | 同上 |

## Agent verification notes（B-40 · 默认 FAIL）

> 书 08。定义：[`specs/core/tasks.md`](../specs/core/tasks.md) §Agent verification notes。

| 验收项 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| 验证通过写入 Worked | P0 | ✅ | PM 2026-08-24：绿卡 + MEMORY.md `Worked: 验证报告` |

## Agent memory poison（B-45 · 默认 FAIL）

> 书 03。定义：[`specs/core/tasks.md`](../specs/core/tasks.md) §Agent memory poison。

| 验收项 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| 请记住+URL 不入库 | P0 | ✅ | PM 2026-08-24：remember_preference 红叉，未说已保存 |

## Spurious verification card（D5 · 默认 FAIL）

> 记住 / 问答不得把上一轮验证卡贴到新回复。定义：[`specs/core/tasks.md`](../specs/core/tasks.md) §Spurious verification card。

| 验收项 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| 记住后不出现验证卡 | P0 | ✅ | PM 2026-08-24：记住回合无卡、不多 `Worked:` |
| 旧卡不复制到后一轮 | P0 | ✅ | 同上 |

## Agent tool ACI（B-41 · 默认 FAIL）

> 书 04。定义：[`specs/core/tasks.md`](../specs/core/tasks.md) §Agent tool ACI。  
> 按文件名查存在走 `list_dir`；步骤条 **List**，不是 Search。PM 2026-08-24 点验通过。

| 验收项 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| 文件名查询不 grep 内容 | P0 | ✅ | pytest + PM 2026-08-24：List .，未 grep |
| 步骤条显示 List | P0 | ✅ | PM 2026-08-24：Listed 1 dir，不是 Search |

## Design 模式（D36 · 默认 FAIL）

> Header Coding/Design + 工作区 Design 会话 + 原型交互画布。PM 2026-08-24 点验通过。

| 验收项 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| Header Coding \| Design；语言在 Settings General | P0 | ✅ | PM 2026-08-24 |
| Design 无独立项目左栏；会话按 mode 过滤 | P0 | ✅ | PM 2026-08-24 |
| 欢迎页 → 无限画布 | P0 | ✅ | PM 2026-08-24 |
| 先规范卡 → 再界面描绘动画 | P0 | ✅ | PM 2026-08-24 |
| 底部 NL 修改闭环 | P0 | ✅ | PM 2026-08-24 |
| `DESIGN.md` / spec / screens 落盘 | P0 | ✅ | PM 2026-08-24 |
| Approve → UI code → preview → Send to Coding | P0 | ✅ | Preview Demo → Coding；D41 确定性导出；PM 2026-08-24 |
| `design-to-code` 工作流模板 | P1 | ✅ | PM 2026-08-24 |

## E2E 落地前提（关联 DECISIONS D1）

| 前提 | 关联里程碑 | 状态 | 验证证据 |
|------|------------|------|----------|
| 前端收到真实 `state_patch` | M0 | ✅ | `test_ws_state_patch.py` |
| Terminal / Chat 无 mock，为真数据 | M2 | ✅ | M2-01/02/06 + `verify.sh` |
| CLI 真实执行跑通 | M3 | ✅ | `test_cli_adapter.py` |

## 待办（开发里程碑）

- [x] **M0**：M0-01–06
- [x] **M1**：M1-01–09
- [x] **M2**：M2-01–14
- [x] **M3**：M3-01–07（pytest）
- [x] **M4**：M4-01–09（含 M4-06 DMG）
- [x] **T-03**：MVP 闭环 E2E（proposal §10.1）
- [x] **D12**：桌面全 UI E2E（`tauri-playwright`）

## 待验证前提（来自 proposal §13 依赖与前提）

| 假设 | 待验证内容 | 关联 task |
|------|-----------|-----------|
| Python 3.11+ 可运行 | 开发期用户环境；发布期内嵌 runtime 可行性 | M4-06 ✅ |
| Claude API Key / Claude Code 已登录 | 自动读取 `~/.claude/settings.json` | M4-04 ✅ |
| 目标项目已 clone 并授权为工作区 | 工作区路径白名单机制 | M2-09, M4-05 ✅ |
| macOS 12+ 为第一平台 | Tauri 打包与 Sidecar 生命周期 | M0-05 ✅, M4-06 ✅ |

---

## D25 · Hybrid Runtime（`CLUTCH_RUNTIME_MODE=hybrid`）

> **Task 权威表**：[`specs/core/hybrid-runtime-plan.md`](../specs/core/hybrid-runtime-plan.md)（HRT-xx）  
> **设计参考**：[`docs/research/pty-session.md`](../docs/research/pty-session.md)

| 模块 | 优先级 | 里程碑 | 状态 | Task ID |
|------|--------|--------|------|---------|
| ShellSession + SHELL_EXEC 核心 | P0 | D25-S1 | ✅ 代码 | HRT-S1 |
| agy Hybrid + baseline | P1 | D25-S2 | ✅ 代码 | HRT-S2 |
| Snapshot + 侧栏 ↻ + PTY 恢复 | P1 | D25-S3 | ✅ 代码 | HRT-S3 |
| runtime_registry 分发 | P1 | D25-S4 | ✅ 代码 | HRT-S4 |
| 池上限 + Snapshot 保留 | P2 | D25-S5-partial | ✅ 代码 | HRT-S5-partial |
| **基础 Plain Chat 产品验收** | **P0** | **D25** | **✅** | **HRT-04**（2026-06-27 用户 A–E） |
| Hybrid 审计 JSONL + debug API | P1 | D25 | ✅ | HRT-05~07 · `446b7a0` |
| 诊断导出 | P2 | D25 | ✅ | HRT-07 · `export-run-debug.sh` |
| 多 session 并发治理 | P1 | D25 | ✅ | HRT-08~10 代码 ✅ · §F 人工 [#24](https://github.com/fancy1108/Clutch/issues/24) F1/F2/G ✅（2026-07-01） |
| POC #6/#10 自动化 | P1 | D25 | ✅ | HRT-10 · `test_hybrid_poc_acceptance.py` |

### D25 人工验收（HRT-04 门禁 · 默认 FAIL）

- [x] **A** 首轮气泡仅 assistant 文本（无 shell / snapshot 泄漏）
- [x] **B** 第二轮续聊正常 + 发送键恢复
- [x] **C** 旧 session 侧栏 ↻
- [x] **D** 回复后 idle；可切 session；无永久 Thinking
- [x] **E** Terminal 有 `[HYBRID]` + `[CHAT] ... chars`
- [x] **F** 多 session 并发（F1/F2/G ✅ · F3–F5 skip — 证据 [`runs/verification/2026-07-01-hrt-f-multi-session.md`](../runs/verification/2026-07-01-hrt-f-multi-session.md) · [#24](https://github.com/fancy1108/Clutch/issues/24)）
- [x] **G** 后台 hydrate（HRT-09；F 表内 F5 与 export 脚本覆盖排查）

证据：`runs/verification/2026-06-27-hrt-04-acceptance.md`

---

## Frontend modules（FM-xx · D56 · 默认 FAIL）

> **Task 定义：** [`specs/core/frontend-modules-plan.md`](../specs/core/frontend-modules-plan.md)  
> **点验剧本：** [`docs/FRONTEND_MODULES_ACCEPTANCE.md`](../docs/FRONTEND_MODULES_ACCEPTANCE.md)（桌面入口、步骤、期望；本表仍是唯一 ✅/❌）  
> **决策：** D56。未点验不得标 ✅。一次一个模块。

| ID | 主题 | 状态 |
|----|------|------|
| FM-01 | General：默认工作区 / 高危确认 / 版本 | ✅ 人工点验 2026-08-26 |
| FM-02 | MCP / 工作流本机信任（OSR-21） | ✅ 人工点验 2026-08-26 |
| FM-03 | Exec policy UI（B-21；OSR-18 界面） | ✅ |
| FM-04 | Codex 只读扫描 | ✅ |
| FM-05a | Aider 只读扫描 | ✅ |
| FM-05b | CodeBuddy 只读扫描 | ✅ |
| FM-05c | Antigravity 只读扫描 | ✅ |
| FM-05d | Rivet 只读扫描 | ✅ |
| FM-05e | Ollama 只读扫描 | ✅ |
| FM-05f | ZCode 只读扫描 | ✅ |
| FM-06 | Orchestra 队列与草稿 | ✅ |
| FM-07 | 派发保存为工作流 | ✅ |
| FM-08 | 对话模式 handoff | ✅ |
| FM-09 | 主控分派横幅（B-01） | ✅ |
| FM-10 | 画布 tool 选择（B-04） | ✅ |
| FM-11 | 并行 worktree（B-08） | ✅ |
| FM-12 | 记忆检索（B-10） | ✅ |
| FM-13 | 事件 Channel（B-42） | ✅ |
| FM-14 | notify_user（B-46） | ✅ |
| FM-15 | 新信息门禁（B-43） | ✅ |
| FM-16 | Design 视觉审查（B-49） | ✅ |
| FM-17 | 解释器错误卡（B-47） | ✅ |
| FM-18 | 校验失败可读条（B-05） | ✅ |
| FM-19 | Planner/Executor 分模型（B-06） | ✅ |
| FM-20 | PERFORMANCE.md 测量（OSR-29） | ✅ |
| FM-21 | Apple 签名公证（OSR-11） | ✅ |
| FM-22 | 外部安全审计（OSR-22） | ✅ |

---

## 开源 / DMG 分发（OSR-xx）

> **Task 定义：** [`docs/OPEN_SOURCE_RELEASE.md`](../docs/OPEN_SOURCE_RELEASE.md) §7.2  
> **验收状态（唯一）：** 本节 — 不在 OPEN_SOURCE_RELEASE 勾选
> **Default FAIL：** 未实际验收不得标 ✅

| 阶段 | 触发线 | 目标 | 状态 | 备注 |
|------|--------|------|------|------|
| T0 护栏 | 持续 | 许可证、文档边界、semver | ⚠️ | OSR-01～04、23～25 ✅；OSR-05 🔄 |
| **T1 可公开仓库** | **公开 repo 前** | 社区文件、Sidecar 鉴权、CLI 策略 | ✅ | OSR-00/06～10、26～28 已验收（D31） |
| T2 可放心装 DMG | 陌生人分发前 | 未签名 DMG、Keychain、安装向导 | ⚠️ | OSR-12～17 ✅ |
| T3 生态成熟 | 按需 | 沙箱、Windows、自动更新 | ⚠️ | OSR-19/20 ✅ v1.0.2；OSR-18→FM-03 · OSR-21→FM-02 · **OSR-29 ✅ FM-20** · **OSR-11 流程 FM-21（未公证）** · **OSR-22 流程 FM-22（未外包）** |

### T1 检查清单（公开仓库前 · 默认 FAIL）

- [x] **OSR-00** 外部视角审计（维护者自验通过 2026-06-29，D31）
- [x] **OSR-06** `SECURITY.md` + `CODE_OF_CONDUCT.md` + `CONTRIBUTING.md`
- [x] **OSR-07** Secret scanning CI
- [x] **OSR-08** Sidecar session token 鉴权
- [x] **OSR-09** CLI 权限策略（D30：维持 skip + README 披露）
- [x] **OSR-10** README + `BUILD_FROM_SOURCE.md` + 产品截图（`docs/images/`）
- [x] **OSR-26** `GOVERNANCE.md`（草案 v0.1）
- [x] **OSR-27** 兼容性矩阵 + `doctor.sh`
- [x] **OSR-28** Issue / PR 模板

### T2 检查清单（DMG 分发前 · 默认 FAIL）

- [x] **OSR-12** GitHub Actions Release DMG + preflight
- [x] **OSR-13** API Key → macOS Keychain
- [x] **OSR-14** 首次启动向导
- [x] **OSR-15** `INSTALL.md` + `DATA_AND_PRIVACY.md`
- [x] **OSR-16** Debug API 收敛 + WebView CSP
- [x] **OSR-17** PyInstaller `console=False`
- [ ] **OSR-11** Apple 签名 + 公证 — **D31 豁免**；流程 [`docs/APPLE_NOTARIZATION.md`](../docs/APPLE_NOTARIZATION.md)（FM-21 ✅）；账号到位前仍发未签名 DMG

### T3 检查清单（生态成熟 · 默认 FAIL）

- [x] **OSR-19** Windows MSI（v1.0.2）
- [x] **OSR-20** Tauri 自动更新（v1.0.2）
- [x] **OSR-29** `PERFORMANCE.md` 本机测量（FM-20 · 2026-08-26）
- [ ] **OSR-22** 外部安全审计 — 委托与报告入口 [`docs/EXTERNAL_AUDIT.md`](../docs/EXTERNAL_AUDIT.md)（FM-22 ✅）；**尚无外包报告**

### T1 开闸信号（§7.5）

- [ ] 主路径：工作区 → 聊天/工作流 → 审批 可稳定复现
- [ ] 近 2 周无大规模 Settings / API 路由重构
- [ ] 愿意处理外部 Issue
