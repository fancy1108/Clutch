# PM 验收用例（Agent 自测后待你点验）

> 每项实现后已跑自动化自测并单独 commit；**ROADMAP 仍标 ❌ 直至你点验通过**。

## Composer UI（验收前必读）

Chat 输入框默认仅 **`+` · 模式 pill · 发送/Stop**（Cursor/Copilot 风格）。下列能力均在 **+** 菜单内（分区 **Add to input** / **Session tools**），**不再**堆在输入框上方：

| 能力 | 用例 | 入口 |
|------|------|------|
| Usage / Steps | D9 · D22 | 右侧 **Overview** → Session Token Analytics（数值暂 `—`，真值见 Q-USAGE-1） |
| Session overview | D30 | **+** → Session overview |
| Rewind | D23 | **+** → Rewind file changes |
| MCP 徽章 | D40 | **+** → Bind MCP / `N MCP` |
| Scheduled tasks | Cap-D25 | **+** → Scheduled tasks |
| Enable worktree | D32 | **+** → Enable worktree（启用后上方出状态条） |
| 权限模式 | D27 | 底栏模式 pill（Explore → Plan → Ask → Edit → Full） |

仍会出现在输入框**上方**的，仅限真实状态：排队消息（D20）、Background jobs（D11/D26）、Foreground shell（D34）、已启用 worktree 条（D32）、HITL Allow/Reject 等。

## 主线 / MCP / Chat UX（先批）

| 交付期 | 用例文件 | Commit |
|--------|----------|--------|
| D8 长聊不丢任务态 | [D08.md](./D08.md) | `7936786` · **PM ✅ 2026-07-25** |
| D9 运行可控 | [D09.md](./D09.md) | `bef9b75` · **PM ✅ Stop/Continue 2026-07-25**（熔断跳过；用量 Q-USAGE-1） |
| D10∥D48 子任务 | [D10.md](./D10.md) | `25dc5dc` · **PM ✅ 2026-07-25**（explore done；implement 卡非强制） |
| D11 后台命令 | [D11.md](./D11.md) | `59b45ee` · **PM ✅ 2026-07-25** |
| D12 Git + 网页 | [D12.md](./D12.md) | `194d33a` |
| D13 权限规则 | [D13.md](./D13.md) | `ed7c568` |
| D51 Chat ↔ Terminal | [D51.md](./D51.md) | `ee4e2a2` |
| D52 能力↔交互门禁 | [D52.md](./D52.md) | `1365f6d` |
| D38 Hub 可信状态 | [D38.md](./D38.md) | `b2d8f49` |
| D39 传输诚实 | [D39.md](./D39.md) | `092ee91` |
| D40 Chat MCP 徽章 | [D40.md](./D40.md) | `724c26c` |
| D41 MCP 审批 | [D41.md](./D41.md) | 既有 HITL；待点验 |
| D42 真实工具名 | [D42.md](./D42.md) | `24f0e31` |
| D43 MCP Resources | [D43.md](./D43.md) | `4462570` |
| D44 一键 local-fs | [D44.md](./D44.md) | `24f0e31` |
| D45 文档对齐 | [D45.md](./D45.md) | `24f0e31` |

## 扩展 D14 + D15–D36（本轮交付）

| 交付期 | 用例文件 | Commit |
|--------|----------|--------|
| D14 外挂 grok CLI | [D14.md](./D14.md) | `5d65a68` |
| D15 联网搜索 | [D15.md](./D15.md) | `0c0c095` |
| D16 跨会话记忆 | [D16.md](./D16.md) | `930f9a5` |
| D17 Hooks | [D17.md](./D17.md) | `68a05a8` |
| D18 斜杠命令 | [D18.md](./D18.md) | `518b8d0` |
| D19 思考流 | [D19.md](./D19.md) | `3f3e66e` |
| D20 忙时排队 | [D20.md](./D20.md) | `94fdc8f` |
| D21 ignore/沙箱 | [D21.md](./D21.md) | `6733b15` |
| D22 用量看板 | [D22.md](./D22.md) | UI 占位；后续真值 Q-USAGE-1 |
| D23 fork/rewind | [D23.md](./D23.md) | `bc67e30` |
| D24 诊断 MVP | [D24.md](./D24.md) | `605d0fc` |
| Cap-D25 定时任务 | [Cap-D25.md](./Cap-D25.md) | `05547b8` |
| D26 长任务监视 | [D26.md](./D26.md) | `8be7f06` |
| D27 模式切换 | [D27.md](./D27.md) | `a269764` |
| D28 MCP 工具发现 | [D28.md](./D28.md) | `cc2662e` |
| D29 Goal 跟踪 | [D29.md](./D29.md) | `96c13d3` |
| D30 会话看板 | [D30.md](./D30.md) | `1d88b02` |
| D31 计划批注 | [D31.md](./D31.md) | `d2f2b2f` |
| D32 worktree | [D32.md](./D32.md) | `9a863ae` |
| D33 富读 PDF/图 | [D33.md](./D33.md) | `bec5dbb` |
| D34 前台转后台 | [D34.md](./D34.md) | `5679a1b` |
| D35 能力包 | [D35.md](./D35.md) | `5de258d` |
| D36 headless Agent | [D36-headless.md](./D36-headless.md) | `e42ba01` |
