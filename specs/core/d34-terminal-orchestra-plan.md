# D34 · Terminal Orchestra 执行计划

> **Task 定义 + Verification 手册**（PTY 多 Lane + Handoff 派发）。  
> **UI 参考（非产品代码）：** [`experiments/d34_terminal_orchestra_ui/mock.html`](../../experiments/d34_terminal_orchestra_ui/mock.html)  
> **决策：** D34 · Q-D34-1~5 — [`memory/DECISIONS.md`](../../memory/DECISIONS.md)  
> **前置：** D33 终端模式（单 Lane · xterm · `INTERACTIVE_PTY`）已落地  
> **验收状态：** 仅 [`memory/ROADMAP.md`](../../memory/ROADMAP.md) — **本文件不维护 ✅/❌**

---

## 1. 范围

### 1.1 做什么

在 **Terminal 工作台**内叠加多 Agent PTY Lane、统一 **派发（Dispatch）** 原语、handoff 文件与可视化，**不替换**对话模式与工作流 SOP。

| 能力 | 说明 |
|------|------|
| Orchestrator Bar | Terminal 模式恢复底部输入（与 xterm 聚焦互斥） |
| 双模输入 | 自然语言 + 图语法 `from @A @B`；`@*.md` 文件引用 |
| 多 Lane | 对等 PTY，N≤4，Tab/分屏/折叠 |
| Handoff | `.clutch/handoffs/*.md`；Lane 间黑虚线 + 附件图标 |
| 派发记录 | Overview 紧凑时间线 + handoff 预览 / 发送到 Bar |
| 完成回传 | Toast + 草稿队列；**不**自动注入 PTY |

### 1.2 显式不做（首期）

- 工作流 session 内 Terminal 切换
- 即兴协作默认编译进 LangGraph SOP（仅可选「保存为工作流」）
- MCP / 超 `claude-cli` · `opencode-cli` 范围外的 CLI
- `window.alert` 成功提示（仅错误 dock 红条）
- 跨 Session 派发归档 UI（留历史会话；本期仅本 Session）

### 1.3 与现网代码关系

| 模块 | 现状 | D34 变更 |
|------|------|----------|
| `ChatFeed.tsx` | Terminal 模式隐藏 `ChatInputBar` | 恢复 **OrchestratorBar** |
| `ChatTerminalView.tsx` | 单 xterm · 单 `sessionRunId` | 多 Lane 容器 + 每 Lane attach |
| `interactive_pty_runtime.py` | 单 run PTY map | **PtyLaneManager** 多实例 |
| `ClutchState` | 无 `pty_lanes` / `dispatch_log` | 扩展 WS 投影字段 |
| `RightPanel` Overview | 占位或未接 dispatch | 派发记录 + handoff 操作 |

---

## 2. ClutchState 扩展（契约）

实现前在 `services/orchestrator/src/state.py`（或等价）定稿类型；前端 `types` / `clutchState.ts` 镜像。

```typescript
// 示意 — 以实现为准
interface PtyLane {
  lane_id: string;
  agent_type: string;       // claude-cli | opencode-cli
  label: string;
  status: 'booting' | 'running' | 'completed' | 'queued';
  focused: boolean;
  collapsed: boolean;
  run_id: string;           // 绑定 PTY run
}

interface DispatchLogEntry {
  id: string;
  timestamp: string;
  sources_label: string;    // "Claude Code" | "Claude Code + OpenCode" | "工作区"
  target: string;
  prompt: string;
  handoff_path: string;
  handoff_file: string;
  input_mode: 'natural' | 'graph';
  file_refs: string[];
}

interface DispatchEdge {
  sources: string[];
  target: string;
  handoff_file: string;
  source_lane_ids: string[];
  target_lane_id: string;
}

interface PendingHandoffDraft {
  id: string;
  label: string;
  text: string;
  suggested_target?: string;
  handoff_path?: string;
}

// ClutchState 增量字段
pty_lanes: PtyLane[];
dispatch_log: DispatchLogEntry[];
dispatch_edges: DispatchEdge[];
pending_handoff_drafts: PendingHandoffDraft[];
focused_lane_id: string | null;
```

**WS 事件（建议）：** `state_patch` 含上述字段；派发确认可走 `POST /api/runs/{id}/dispatch/preview` → `confirm` 或单通道 `dispatch` + 服务端解析。

---

## 3. Task 清单（D34-α → ε）

每个 Task：**原子 commit** → `./scripts/verify.sh` → 触及用户可见功能时更新 `docs/PRODUCT_INTRO.md`（D19）→ `memory/DELIVERABLES.md` → `memory/PROGRESS.md` → `memory/ROADMAP.md`。

| ID | 主题 | 依赖 | 交付摘要 | Verification |
|----|------|------|----------|--------------|
| **D34-00** | 计划与契约对齐 | D33 ✅ | 本文件 + DECISIONS/FILEMAP/ROADMAP 条目 | `check-doc-drift.sh` |
| **D34-α1** | `parse_dispatch_mentions` | D34-00 | Python 解析：target、sources、file_refs、input_mode；单元测试覆盖 §2.1–2.3 | `pytest tests/test_dispatch_parse.py` |
| **D34-α2** | OrchestratorBar 壳 + Terminal 恢复输入 | D33 | `ChatFeed` terminal 模式显示 Bar；与 xterm focus 互斥 | vitest + 手动切换 |
| **D34-α3** | 聚焦 Lane SSOT | α2 | `focused_lane_id`；点 Lane Tab 更新；派发默认 source=聚焦 Lane | pytest + 手动 |
| **D34-α4** | 派发 Preview API（无 handoff 写盘） | α1 | preview 返回 `{sources,target,task,chips}`；不发 PTY | pytest API |
| **D34-α5** | 确认卡 UI | α2, α4 | Bar 上方浮层；`from → to`；仅错误 dock 红条 | 对照 mock |
| **D34-β1** | PtyLaneManager 多 PTY | D33 PTY | ≤4 Lane；每 Lane 独立 run_id / attach token | pytest PTY |
| **D34-β2** | Lane Tab + 分屏布局 | β1 | layout 1/2/3；`ChatTerminalView` 多 pane | vitest + mock 对照 |
| **D34-β3** | A∥B 冷启动冒烟 | β1–β2, α4 | 连发 `@A` `@B`；sources=`[]`；两 Lane 独立 | §4.1 #1 |
| **D34-γ1** | handoff md 生成 | α1, α4 | 写 `.clutch/handoffs/{ts}-{sources}→{target}.md` | pytest + 读盘 |
| **D34-γ2** | 确认卡 chips + 双模输入 | γ1, α5 | 自然语言 + `@文件` + `from @A @B`；chips 可改 | §4.1 #2–4 |
| **D34-γ3** | Overview 派发记录 | γ1 | 时间线 + handoff 预览 / 发送到 Bar | §4.1 #5 |
| **D34-δ1** | Lane 完成 → 草稿队列 | β1 | `pending_handoff_drafts[]`；toast；不注入 PTY | §4.1 #6 |
| **D34-δ2** | A,B→C 多源整合 | γ1–γ2, β2 | 多 `@文件` 合并 sources；`A,B→C.md` | §4.1 #3 |
| **D34-ε1** | Handoff 连线层 | β2, γ1 | 黑虚线 + 小附件图标；有连线时 Lane 间距加宽 | 对照 mock |
| **D34-ε2** | Float rail 折叠 | β2 | 折叠不遮挡 xterm；点击展开 PTY 不断 | §4.1 #7 |
| **D34-ε3** | 超 N 排队 + Tab 折叠 | β1, ε2 | N=4；第 5 路排队 | §4.1 #8 |
| **D34-ε4** | E2E + 文档 | ε1–ε3 | Playwright 冒烟；PRODUCT_INTRO §Terminal Orchestra | `verify.sh --e2e` |

### 3.1 建议执行顺序

```
D34-00 → α1 → α2 → α3 → α4 → α5
              ↓
         β1 → β2 → β3
              ↓
         γ1 → γ2 → γ3
              ↓
         δ1 → δ2
              ↓
         ε1 → ε2 → ε3 → ε4
```

**首期 MVP 门禁（可对外演示）：** α 全线 + β3 + γ2 + γ3 + ε1（单条 A→B + Overview + 连线）。

---

## 4. 验收清单

证据写入 `runs/verification/YYYY-MM-DD-d34-*.md`（run_id、截图、pytest/vitest 输出）。

### 4.1 场景矩阵（必须全部通过方可标 ROADMAP ✅）

| # | 场景 | 操作 | 通过标准 |
|---|------|------|----------|
| 1 | **A∥B 冷启动** | 无聚焦，连发 `@Claude …`、`@OpenCode …` 并确认 | 两 Lane 并行；handoff sources=工作区/空；`dispatch_log` 两条；无错误 alert |
| 2 | **聚焦 A → 派 B** | 聚焦 Lane A，`@OpenCode …`（自然语言，可无 `from`） | 确认卡 `Claude Code → OpenCode`；生成 handoff；B Lane booting；**黑虚线**可见 |
| 3 | **A,B → C 整合** | `@Claude …` + 多 `@文件` 或 `from @A @B` | sources 含 A+B；`A,B→C.md`；C Lane 收到；连线 a→c、b→c |
| 4 | **仅 B → C** | `@C from @B：…` | 仅 B 在 sources chips；handoff 文件名含 B→C |
| 5 | **Overview 派发记录** | 完成 #2 后看右侧 Overview | 时间线条目含 `sources → target`；handoff **预览** + **发送到 Bar** 可用 |
| 6 | **完成草稿** | Lane 标记完成 | Toast；Bar 预填草稿；**未**自动写入 PTY；用户编辑后发送才派发 |
| 7 | **Lane 折叠** | 折叠 running Lane | 进入 float-rail；xterm 不被挡；展开后输出连续 |
| 8 | **超 N 排队** | 尝试第 5 路 Lane | 排队或 Tab 提示；不 crash |
| 9 | **D33 回归** | 单 Lane、Chat/Terminal 切换、HITL | 与现网 `PRODUCT_INTRO` §3.1 一致 |
| 10 | **对话模式回归** | 工作流 session 仅 Chat | 无 Terminal 切换；无 Orchestrator Bar |

### 4.2 解析器单测（α1 门禁）

| 输入 | 期望 target | 期望 sources |
|------|-------------|--------------|
| `@OpenCode 实现 API`（聚焦 Claude） | OpenCode | [Claude Code] |
| `@OpenCode … @20260702-claude→opencode-api.md` | OpenCode | [Claude Code]（自文件元数据） |
| `@Claude Code from @OpenCode @Claude Code：整合` | Claude Code | [OpenCode, Claude Code] |
| `@OpenCode 实现 CRUD`（无聚焦） | OpenCode | [] / 工作区 |
| 无 `@Agent` | — | 解析失败 → dock 错误红条 |

### 4.3 UI 对照（mock）

| Mock 元素 | 产品组件 |
|-----------|----------|
| `#orchestratorInput` + `#sendBtn` | `OrchestratorBar` |
| `#dispatchPreview` | `DispatchConfirmCard` |
| `#terminalStage` + layout class | `TerminalLaneGrid` |
| `#handoffLinksLayer` | `HandoffLinkOverlay` |
| `#floatRail` | `TerminalLaneFloatRail` |
| `#historyList` | `OverviewDispatchLog` |

---

## 5. 文件落点（拟议）

| 区域 | 路径 |
|------|------|
| 派发解析 | `services/orchestrator/src/dispatch_parse.py` |
| Handoff 生成 | `services/orchestrator/src/handoff_writer.py` |
| Lane 管理 | `services/orchestrator/src/pty_lane_manager.py`（或扩展 `interactive_pty_runtime.py`） |
| API | `services/orchestrator/src/main.py`（dispatch preview/confirm） |
| Orchestrator Bar | `apps/desktop/src/components/OrchestratorBar.tsx` |
| 派发确认 | `apps/desktop/src/components/DispatchConfirmCard.tsx` |
| 多 Lane 终端 | `apps/desktop/src/components/TerminalLaneGrid.tsx` |
| Handoff 连线 | `apps/desktop/src/components/HandoffLinkOverlay.tsx` |
| Float rail | `apps/desktop/src/components/TerminalLaneFloatRail.tsx` |
| Overview | 扩展 `RightPanel` overview 面板 |
| 类型 | `apps/desktop/src/types/dispatch.ts` |

> 新建文件 >3 或单 Task >200 行须拆 Task；上表可在 α 立项时写入 `memory/FILEMAP.md`。

---

## 6. 开放项（实现前确认）

| ID | 问题 | 默认 |
|----|------|------|
| O-D34-1 | handoff 正文模板字段 | Clutch 内置摘要 + Lane 审计指针（D34-2=A） |
| O-D34-2 | 同 agent 多 Lane（两个 Claude Code） | `lane_id` 区分；handoff registry 绑 `source_lane_ids` |
| O-D34-3 | Overview 是否独立 Tab 还是并入现有 Overview | 并入现有 Overview（与 mock 一致） |

---

## 7. 立项 Checklist（D34-α 开工前）

- [ ] `memory/ROADMAP.md` 增加 D34 行（默认 FAIL）
- [ ] `memory/TESTS.md` 预留 D34 验收行
- [ ] 人类确认首期 MVP 范围（§3.1 加粗线）
- [ ] `D34-00` commit：本文件 + FILEMAP + ROADMAP 指针
