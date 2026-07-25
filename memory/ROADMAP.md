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
| General Settings | P2 | P2 | ✅ 部分落地 | P2-06（D14；支持用户头像定制） |
| 内置模板 | P1 | M4 | ✅ | M4-01 |
| 运行历史 | P0 | M2 | ✅ | M2-07（D3）+ D11 对话持久化 |
| 文件浏览（Files 面板） | P0 | M2 | ✅ | M2-11 |
| Token / 校验结果展示 | P0 | M2 | ✅ | M2-13, M2-14 |
| 工作区授权 | P0 | M2 | ✅ | M2-09；M4-05 |
| E2E / 前端单测 | P0 | M2 | ✅ | M2-10, T-01–03（D1）；D12 桌面 E2E 7/7 |
| macOS 打包 | P1 | M4 | ✅ | M4-06 |
| **MVP 闭环** | — | M3 | ✅ | proposal §10.1；T-03 |
| **Design 模式（D36）** | P1 | Design | ❌ | 见下 §Design 模式 |

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
| D8 长聊不丢任务态 | P0 | ❌ | 压缩保留 Todo/计划 + task_state 层；待 PM（`7936786`） |
| D9 运行可控 | P0 | ❌ | Stop/Continue + loop fuse + Chat Steps/tok；待 PM |
| D10∥D48 子任务委派 | P0 | ❌ | `delegate_subtask` + 嵌套卡；待 PM |
| D11 后台命令 | P0 | ❌ | bg_jobs + Chat 任务条；待 PM（非 session 持久化） |
| D12 Git + 网页 | P0 | ❌ | git_* + web_fetch；待 PM（非桌面 E2E） |
| D13 权限规则 | P0 | ❌ | allow/ask/deny + 危险强问 + 清记忆；待 PM |
| D14 外挂 grok CLI | P2 | ❌ | 旁路引擎；待实现/PM |
| D15 联网搜索 | P1 | ❌ | web_search；待实现/PM |
| D16 跨会话记忆 | P1 | ❌ | Memory 开关；待实现/PM |
| D17 Hooks | P1 | ❌ | Pre/Post tool；待实现/PM |
| D18 斜杠命令 | P1 | ❌ | `/plan` `/compact` `/todos`；待 PM |
| D19 思考流 | P1 | ❌ | reasoning + D46；待实现/PM |
| D20 忙时排队 | P1 | ❌ | Agent busy queue；待实现/PM |
| D21 ignore/沙箱 | P1 | ❌ | gitignore/clutchignore；待实现/PM |
| D22 用量看板 | P1 | ❌ | 历史用量面板；待实现/PM |
| D23 fork/rewind | P1 | ❌ | 会话分支+文件回滚；待实现/PM |
| D24 诊断 MVP | P2 | ❌ | tsc/ruff 回灌；待实现/PM |
| Cap-D25 定时任务 | P2 | ❌ | 扩展定时/循环（≠ Hybrid D25）；待实现/PM |
| D26 长任务监视 | P1 | ❌ | bg 失败监视；待实现/PM |
| D27 模式/人设 | P1 | ❌ | explore/plan/implement；待实现/PM |
| D28 MCP 工具发现 | P1 | ❌ | 多工具时搜索；待实现/PM |
| D29 Goal 跟踪 | P1 | ❌ | 目标条；待实现/PM |
| D30 会话看板 | P1 | ❌ | 会话总览；待实现/PM |
| D31 计划批注 | P1 | ❌ | 行内评论批准；待实现/PM |
| D32 worktree | P2 | ❌ | 隔离试验；待实现/PM |
| D33 富读 PDF/图 | P1 | ❌ | read_file 富媒体；待实现/PM |
| D34 前台转后台 | P1 | ❌ | Ctrl+B 式；待实现/PM |
| D35 能力包导入 | P2 | ❌ | skills+hooks+mcp；待实现/PM |
| D36 headless Agent | P2 | ❌ | CI/`-p` 同核（≠ Design D36）；待实现/PM |
| D37 MCP Agent↔Hub 绑定 | P0 | ✅ | Module 4 Hub 勾选 + `mcpServerIds`；PM 2026-07-24 点验通过 |
| D38 Hub 可信状态 | P1 | ❌ | Test connection + 去开发中横幅；待 PM（`b2d8f49`） |
| D39 传输诚实 | P1 | ❌ | stdio-only + Env 表单；待 PM（`092ee91`） |
| D40 Chat MCP 徽章 | P1 | ❌ | N MCP · ~M / Bind CTA；待 PM（`724c26c`） |
| D41 MCP 审批体验 | P1 | ❌ | 既有 Allow/Reject + 路径；待 PM 对照 `D41.md` |
| D42 真实工具名 UI | P1 | ❌ | 去掉假 permission 芯片；待 PM |
| D43 MCP Resources | P1 | ❌ | Browse + Pin for Chat；待 PM |
| D44 一键 local-fs | P1 | ❌ | Module 4「启用工作区文件工具」；待 PM |
| D45 文档对齐 | P1 | ❌ | PRODUCT_INTRO 已跟 stdio/徽章；待 PM |
| D46 对话实时步骤条 | P0 | ✅ | 持久 verb_group + seal `toolSteps`；PM 2026-07-24 点验通过 |
| D47 中间产物芯片 | P0 | ✅ | seal `filesChanged` + FilesChangedChips → D42 预览；PM 2026-07-24 点验通过 |
| D49 计划嵌对话流 | P0 | ✅ | PlanCard + TodoCard + QuestionCard；PM 2026-07-24（D2/D3/D4） |
| D50 验证报告嵌对话 | P0 | ✅ | VerificationReport（D5）+ Cursor Diff 卡（D6）；PM 2026-07-24 |
| D48 子任务嵌套卡 | P0 | ❌ | 随 D10；待 PM |
| D51 Chat ↔ Terminal 同步 | P1 | ❌ | View in Terminal → 日志高亮 / lane focus；待 PM（`ee4e2a2`） |
| D52 能力↔交互对照门禁 | P1 | ❌ | PRODUCT_INTRO 对照表 + INV-D52 机检；待 PM |
| D53 分层 prompt + 渐进披露 | P0 | ✅ | 分层组装 + Agent Manager 分层摘要面板；PM 2026-07-24 点验通过 |

**首期目标：** D1 + D37 + D46 ✅（PM 2026-07-24）。  
**下一批（防返工顺序）：** D8（待 PM）→ D9 → D10∥D48 → D11 → D12 → D13；用例见 `runs/verification/pm-acceptance/`

## Design 模式（D36 · 默认 FAIL）

> Header Coding/Design + 工作区 Design 会话 + 原型交互画布；未实际验证不得标 ✅。

| 验收项 | 优先级 | 状态 | 说明 |
|--------|--------|------|------|
| Header Coding \| Design；语言在 Settings General | P0 | ❌ | 人工 |
| Design 无独立项目左栏；会话按 mode 过滤 | P0 | ❌ | 工作区历史 |
| 欢迎页 → 无限画布 | P0 | ❌ | 原型设计主路径 |
| 先规范卡 → 再界面描绘动画 | P0 | ❌ | 两阶段 generate |
| 底部 NL 修改闭环 | P0 | ❌ | iterate |
| `DESIGN.md` / spec / screens 落盘 | P0 | ❌ | `.clutch/design/sessions/<run_id>/` |
| Approve → UI code → preview → Send to Coding | P0 | ✅ | Preview Demo → Coding；D41 确定性导出 |
| `design-to-code` 工作流模板 | P1 | ❌ | 内置 SOP |

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

## 开源 / DMG 分发（OSR-xx）

> **Task 定义：** [`docs/OPEN_SOURCE_RELEASE.md`](../docs/OPEN_SOURCE_RELEASE.md) §7.2  
> **验收状态（唯一）：** 本节 — 不在 OPEN_SOURCE_RELEASE 勾选
> **Default FAIL：** 未实际验收不得标 ✅

| 阶段 | 触发线 | 目标 | 状态 | 备注 |
|------|--------|------|------|------|
| T0 护栏 | 持续 | 许可证、文档边界、semver | ⚠️ | OSR-01～04、23～25 ✅；OSR-05 🔄 |
| **T1 可公开仓库** | **公开 repo 前** | 社区文件、Sidecar 鉴权、CLI 策略 | ✅ | OSR-00/06～10、26～28 已验收（D31） |
| T2 可放心装 DMG | 陌生人分发前 | 未签名 DMG、Keychain、安装向导 | ⚠️ | OSR-12～17 ✅ |
| T3 生态成熟 | 按需 | 沙箱、Windows、自动更新 | ⚠️ | OSR-19/20 ✅ v1.0.2；OSR-18/21/22/29 待做 |

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

### T1 开闸信号（§7.5）

- [ ] 主路径：工作区 → 聊天/工作流 → 审批 可稳定复现
- [ ] 近 2 周无大规模 Settings / API 路由重构
- [ ] 愿意处理外部 Issue
