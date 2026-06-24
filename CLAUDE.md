# Clutch — Tauri · React 19 · FastAPI + LangGraph · 本地零代码多 Agent 编排

> **Canonical 权威源**：本文件为治理规则与开发纪律的**唯一完整条文**。其他 AI 指令文件（`AGENTS.md`、`.cursor/rules/*.mdc`、`.github/copilot-instructions.md`）仅作索引或精简指针，不得另行维护冲突规则。

## 📍 项目定位

**Pitch：** 面向开发者与技术运营人员的桌面应用，可视化编排、运行和监督 AI 多 Agent 工作流；用户零代码拖拽 SOP，系统调度本地 CLI / MCP / Cursor，统一监督执行与人工审批。

**栈：** Tauri 2.x · React 19 + Vite · Tailwind CSS 4 · Motion · React Flow · pnpm | Python 3.11+ · FastAPI · LangGraph · uv

**约束：** 必须桌面端、LangGraph 为唯一编排引擎、用户零代码；前端仅 `apps/desktop/src`，Python 仅 `services/orchestrator/src`；前端禁止访问 DB 或执行系统命令；React 只投影 WebSocket `ClutchState`，禁止 `setTimeout` / mock 模拟编排；Sidecar 仅 `localhost:8123`；单次 ≤3 新文件、≤200 行；新依赖须人类批准。

**Vibe：** 业务语言优先 · 监督而非黑盒 · 失败可操作 · 渐进复杂度 · 本地优先

---

## ⛔ 铁律

- 原子提交：每完成一个原子 task 立即 commit，禁止提交 broken 代码。
- 禁止猜测文件路径；找不到时读 `memory/FILEMAP.md` 或列目录确认。
- 禁止同时处理多个功能；一次一个 task，commit 后再下一个。
- 禁止在未实际运行校验命令的情况下标记功能完成。
- 禁止在未更新 `specs/` 或 `memory/DECISIONS.md` 的情况下做架构级业务变更。
- 禁止硬编码 API Key 或密钥；禁止将密钥写入日志。
- 禁止扩展 Prototype mock 编排逻辑（`setTimeout`、`mockData` 等）；去 mock 化须接真实 Sidecar 事件。

---

## ⚡ 核心命令

| 操作 | 命令 |
|------|------|
| 前端开发 | `pnpm dev` |
| 前端构建（校验） | `pnpm build` |
| 后端启动 | `cd services/orchestrator && uv run uvicorn src.main:app --reload --port 8123` |
| 后端测试（校验） | `cd services/orchestrator && uv run pytest` |
| 本地一键校验（轻量） | `./scripts/verify.sh` |
| 本地全量校验（含 E2E） | `./scripts/verify.sh --e2e` |
| 文档↔代码漂移（机检） | `./scripts/check-doc-drift.sh` |

**会话校验（commit 前必跑）：** `./scripts/verify.sh`（含 build + pytest + vitest + 漂移机检，默认排除重型 E2E 以免卡顿）

**Push 前推荐手动全量校验：** `./scripts/verify.sh --e2e`（含全部轻量校验及完整 E2E）

**Git pre-commit（Husky）：** 仅当 staged 触及 `apps/desktop/src/`、`services/orchestrator/src/`、`packages/` 时跑 `verify.sh`；触及 `.claude/workflows/` 时跑 `check-doc-drift.sh`；纯 `memory/`、`specs/`、`docs/` 改动放行。

---

## 🔄 Long-Running Agent 规则

**新会话 Check-in（按序）：**

1. 读 `memory/PROGRESS.md` — 了解上次做到哪
2. 读 `memory/FAILURES.md` — 避开已知陷阱
3. 读 `memory/FILEMAP.md` — 定位文件，禁止猜路径
4. 读 `memory/DECISIONS.md` — 确认最新决策与开放问题
5. 运行 `git log --oneline -10`
6. 运行会话校验命令，确认环境干净

**会话结束 Check-out（必须）：**

1. 所有修改已 git commit
2. 更新 `memory/PROGRESS.md`（完成了什么 + 下次优先做什么）
3. **代码 Task 完成时**：在 `memory/DELIVERABLES.md` 追加一节（Commit hash、Verification 命令与结果、证据路径、`git show --stat` 所列交付文件）；重要验证输出写入 `runs/verification/`
4. 卡壳超过 10 分钟的问题记入 `memory/FAILURES.md`（`[OPEN]`）
5. 新架构决策记入 `memory/DECISIONS.md`；开放问题只维护于此，禁止在其他文档另开列表

### Layer 4 操作剧本（`.claude/workflows/`、`.cursor/`）

Layer 4 为**操作规程**，不是权威来源。冲突时以本文 §铁律 与 `memory/DECISIONS.md` 为准。

**约束（每个 Layer 4 剧本均适用）：**

1. **不扩权**：不得定义新铁律、架构红线或开放问题；仅描述步骤、触发条件与证据要求。
2. **文件头**：开头须含层级声明（见下方模板）；禁止省略。
3. **可发现性**：新增剧本须在 `memory/FILEMAP.md` 登记「想做什么 → 路径」。
4. **按需路由**：非每次 Check-in 必读的剧本，须在本文或 `FILEMAP` 写明**触发条件**（不得隐式存在）。

**`.cursor/rules/*.mdc`**：仅允许**指针型**规则（见 `base.mdc`）；禁止写入与本文冲突或扩权的铁律。

**文件头模板（复制后改标题）：**

```markdown
> Layer 4 操作剧本 · 不扩权。铁律见 `CLAUDE.md`；决策见 `memory/DECISIONS.md`。
> 本文件不定义新规则，仅描述 `<场景>` 的操作步骤。
```

### 验收期真相对齐（按需）

**触发条件**（满足任一）：

- 用户反馈「做的和说的不一样」、验收项与预期不符
- `memory/ROADMAP.md` 某项验收失败
- `scripts/check-doc-drift.sh` 报漂移

**执行**：先读并按 [`.claude/workflows/truth-alignment.md`](./.claude/workflows/truth-alignment.md) 做物理诊断；未完成工具调用与证据收集前，禁止改业务代码。本剧本不定义新铁律。

---

## 📁 Memory 六件套

- `PROGRESS.md` — 进度接力棒，每次会话必读必写
- `DELIVERABLES.md` — **Task 交付索引**（Commit / Verification / 证据路径；Check-out 必填，见上）
- `FAILURES.md` — 防坑手册，踩坑即写（`[OPEN]` / `[RESOLVED]`）
- `FILEMAP.md` — 文件路径速查表（五层索引 + 路径映射），第 6 步填实
- `DECISIONS.md` — 决策记录与**唯一**开放问题汇总地
- `ROADMAP.md` — 功能清单（Default FAIL，验证通过才能 ✅）
- `TESTS.md` — 测试状态追踪（门禁级；列：日期 / 范围 / 命令 / 结果 / 报告证据；必须实际运行后才能标 ✅）

---

## 🪤 已知陷阱

（持续追加，格式：`踩过的错 → 怎么避免`）

> **触发规则：** 每次 `FAILURES.md` 新增一条 `[RESOLVED]` 记录时，必须同步补一行到此处；否则该列表永久空置无意义。

- tauri-playwright 对 `<textarea>` 用 `fill`/`type` 会报 `HTMLInputElement` setter 错 → 用 `evaluate` + `HTMLTextAreaElement.prototype.value` + 派发 `input`
- 桌面 E2E 侧栏 hydrate 后 `getByText` 易超时 → 先 `waitForSelector` 等 Chat DOM，或延长 `expect` timeout
- API E2E 在 Chromium 里起 WebSocket 不稳定 → 用 `e2e/helpers/ws.ts`（Node 原生 WS），禁止 `chromium.launch()` 测 WS

---

## 📝 日志与事件字段规范

所有自定义日志与事件输出（Python `logger`、WebSocket 推送、Terminal 审计行）必须包含以下最小字段：

| 字段 | 说明 |
|------|------|
| `run_id` | 当前运行 ID |
| `node_id` | LangGraph / 工作流节点 ID |
| `source` | 来源模块（如 `orchestrator`、`cli_adapter`、`ws`） |
| `level` | `debug` / `info` / `warn` / `error` |
| `message` | 人类可读描述 |
| `timestamp` | ISO 8601 或 Unix ms |

WebSocket 信封格式（事件名在 `event`，载荷在 `data`）：

```json
{
  "event": "state_patch",
  "data": {
    "run_id": "run_xxx",
    "patch": { "status": "running" }
  }
}
```

事件命名参考：`state_patch` · `message` · `log` · `file_changed` · `validation_result` · `human_required` · `run_completed`

---

## 架构红线（摘要）

- **LangGraph 是唯一 SSOT**；React 仅渲染 WebSocket 推送的 `ClutchState`。
- 前后端仅通过 `localhost:8123` HTTP/WebSocket 通信。
- 前端：pnpm · Tailwind v4 · lucide-react · Motion · `@xyflow/react`。
- 后端：uv · asyncio · type hints · LangGraph。
- UI/UX 见 [`UI_UX_GUIDELINES.md`](./UI_UX_GUIDELINES.md)。
- 产品命名：**Clutch** / **ClutchState**（禁止旧称 Vibe Workspace / VibeState）。

---

## Agent skills

### Issue tracker

Issues tracked in GitHub (fancy1108/Clutch) via `gh` CLI. External PRs are NOT a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
