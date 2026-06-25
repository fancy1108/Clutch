# DECISIONS（决策记录与开放问题）

> 格式：**日期 · 背景 · 方案 · 影响 · 落地前提 · 决策状态**  
> 本项目**唯一**的开放问题 / 待决策事项汇总地。禁止在其他文档另开新的开放问题列表。
>
> **决策状态：** `已记录`（原则已定，前提未满足）→ `可执行`（可动手实现）→ `已落地`（目录/CI/代码已存在）

## 已记录决策

### D16 · DEV 与 PROD 环境本地存储目录隔离（2026-06-25）

- **背景**：原设计中，无论是开发测试环境（DEV/TEST）还是打包后的生产发布环境（PROD），都统一使用了 `Application Support/clutch` 或类似的用户目录。这会导致开发调试和测试期间产生的假数据与用户实际的使用配置/会话历史发生冲突或相互污染。
- **方案**：
  - 引入统一的后端 `storage_helper.py` 来处理底层的存储根目录获取逻辑。
  - 在开发测试状态（非打包，`sys.frozen` 为 False）下，本地存储目录名定义为 `clutch_dev`；而在生产打包运行状态（`sys.frozen` 为 True）下，使用 `clutch` 目录。
  - 允许使用环境变量 `CLUTCH_STORAGE_DIR` 覆盖绝对存储路径。
- **影响**：后端所有的 `storage` 系统均重构为引用 `storage_helper.get_storage_dir()`；测试中隔离更干净。
- **决策状态**：`已落地`

### D17 · 前端侧栏自定义 Pointer 拖动（2026-06-25）

- **背景**：Tauri 桌面端或嵌套 iframe 下原生 HTML5 `Drag-and-Drop` 的兼容度、动效定制、以及 drop target 状态判断不够稳定，导致拖拽工作区到分组中时易失灵或视觉高亮不够灵敏。
- **方案**：
  - 弃用 HTML5 原生 `draggable="true"` 行为。
  - 基于 React 实现一整套自定义 `pointerdown` -> `pointermove` -> `pointerup` 全局坐标监听的拖动机制。
  - 在 `pointermove` 过程中利用 `document.elementFromPoint(clientX, clientY)` 实时解析下方带有 `data-drop-group-id` 的元素，实现更平滑与可靠的拖拽分组高亮及投递。
- **影响**：`apps/desktop/src/sidebar.tsx` 与 `App.tsx` 交互重构。
- **决策状态**：`已落地`

### D1 · E2E 测试范围与目录（2026-06-22）

- **背景**：E2E 若测 mock 编排，与「React 只投影 WebSocket ClutchState、禁止 mock 模拟编排」红线冲突；且需跨 Sidecar + UI 两进程，本质是跨包集成测试。
- **方案**：
  - 范围：全链路集成测试，禁止 mock 编排逻辑
  - 目录：顶层 `e2e/`（Playwright），**不**放在 `apps/desktop/`
  - 分级：Smoke（M0 后，health + WS `state_patch`）→ 闭环（M2–M3 后，对齐 proposal §10.1 MVP）
- **影响**：未来 E2E 依赖、CI job、TESTS.md 门禁均按此执行；`memory/ROADMAP.md` 前提行与 D1 联动。
- **落地前提**（已满足）：
  1. M0：前端收到真实 `state_patch` ✅
  2. M2：去除 mock，Terminal / Chat 为真数据 ✅
- **建议落地阶段**：M2 完成后启动 `e2e/` 包；Smoke 用例可在 M0 后首条添加，闭环用例对齐 M3。
- **决策状态**：`已落地`（`e2e/` + Playwright Smoke + vitest 首条用例）

### D2 · CI 门禁范围（2026-06-22）

- **背景**：无 CI 时测试报告仅存在于本地，协作中不可追溯；当前已有 `pnpm build` 与 `uv run pytest`，成本最低。
- **方案**：GitHub Actions 跑 `pnpm build` + `uv run pytest`；报告产物上传为 workflow artifacts（coverage 等后续再加）。
- **影响**：`.github/workflows/ci.yml`；TESTS.md 增 CI 行；**不**将 `pnpm test` 纳入 commit 门禁直至前端有真实用例（见 D1 同类原则：禁止形式完整掩盖实质空白）。
- **落地前提**：无（可立即执行）。
- **决策状态**：`已落地`

**D2 遗留待办：**

- [x] Push 后确认 GitHub Actions 首次绿，更新 `TESTS.md` CI 行（2026-06-22，CI #2）
- [ ] 有覆盖率需求时：pytest-cov / vitest coverage + CI artifacts 上传

### D3 · 运行历史纳入 MVP（2026-06-22）

- **背景**：Q1 指**运行历史**（过往 `run_id`、工作流、状态、时间等可回溯记录），不是单指 Terminal 实时日志；用户需要用于**排查问题**与**续聊**。
- **方案**：MVP 纳入运行历史；侧栏可查看历史运行列表；与单次运行的 Terminal 审计日志（`log` 事件）互补。**对话正文**见 **D11**（`states/{run_id}.json`）。
- **影响**：`tasks.md` §M2 增任务；`sidebar.tsx` 接历史 API；Sidecar 本地持久化（`history.json` + `states/`）。
- **落地前提**：M2 监督台去 mock 阶段。
- **决策状态**：`已落地`（元数据 M2-07；对话 D11）

### D4 · LLM 提供方可切换（2026-06-22）

- **背景**：Q2 — Orchestrator / Agent 推理所用模型是否固定 Claude。
- **方案**：**可切换**多 Provider；**默认**为 **DeepSeek V4 Pro**；用户可在设置或 Agent 配置中改选。
- **影响**：M1 引擎需 Provider 抽象（Router）；API Key 按 Provider 分别配置；`ARCHITECTURE.md` ADR 待实现时对齐。
- **落地前提**：M1。
- **决策状态**：`已记录`（原 Q2 关闭）

### D5 · Workflow 文件存放（2026-06-22）

- **背景**：Q3 — 用户编辑的工作流 JSON 存项目仓库还是应用目录。
- **方案**（混合，Agent 代决）：
  1. **内置只读模板**：仓库 `workflows/`（随应用分发，已有 schema + 示例）
  2. **用户创建/编辑的工作流**：**Tauri 应用数据目录**（如 macOS `Application Support/clutch/workflows/`）
  3. **可选**：导出/导入 JSON 到项目内 `.clutch/workflows/`（便于 git 版本管理），**非**默认保存路径
- **理由**：工作流是应用级 SOP，常跨多个工作区复用；默认不写进用户项目 git，避免污染仓库。
- **影响**：M1 保存/加载 API 与 `WorkflowOrchestration.tsx` 读写应用数据目录；模板从 `workflows/` 复制。
- **落地前提**：M1。
- **决策状态**：`已记录`（原 Q3 关闭）

### D6 · Evaluator 检查由用户 Agent 配置驱动（2026-06-22）

- **背景**：Q4 — 是否维护系统级「默认检查规则库」。
- **方案**：**不维护**系统侧规则库。审核要求由用户在 **创建/编辑 Agent**（`AgentManager`）时写入 **Prompt + Skills + Deliverables**；Evaluator 节点执行该 Agent 配置，而非内置规则表。
- **开发**：实现检查执行能力（如 `file_exists`、`shell`、基于 Agent prompt 的 LLM 校验）；**不** curate 默认规则内容。Prototype `mockData` / `AgentManager` 中的 Evaluator 示例可作为开发期 mock 种子。
- **影响**：M3 Evaluator 任务聚焦执行管线，非规则 CMS；`tasks.md` §M3-05 按此调整。
- **落地前提**：M3。
- **决策状态**：`已记录`（原 Q4 关闭）

### D7 · 执行性兜底与 Layer 4 剧本（2026-06-22）

- **背景**：Vibe 8.5 验收期真相对齐；`CLAUDE.md` 会话校验与 Check-out 仅靠 Agent 自觉，缺 git/CI 强制力；意图层漂移无法单靠 grep。
- **方案**：
  1. **Husky** `pre-commit`：触及 `apps/desktop/src/`、`services/orchestrator/src/`、`packages/` 时跑 `verify.sh`；触及 `.claude/workflows/` 时跑 `check-doc-drift.sh`；纯文档改动放行
  2. **CI**：在 D2 基础上增 `scripts/check-doc-drift.sh` step
  3. **漂移机检 v1**：`scripts/check-doc-drift.sh`（可机检不变量表；M0 后 `CLUTCH_STRICT_MOCK=1` 收紧 App.tsx setTimeout）
  4. **人工剧本**：`.claude/workflows/truth-alignment.md`；Layer 4 通用约束见 `CLAUDE.md` §Layer 4
- **影响**：`CLAUDE.md`、`FILEMAP.md`、`verify.sh`、`.husky/pre-commit`、`.github/workflows/ci.yml`；`TESTS.md` 增漂移行
- **落地前提**：无
- **决策状态**：`已落地`

### D9 · 工作流编辑器双模式（画布 + JSON）（2026-06-23）

- **背景**：M1-06 阻塞 — Prototype 画布用 `WorkflowDef/steps`，执行引擎用 compiler `nodes/edges`；用户希望简单流程拖拽、复杂流程（检查/审批/循环）直接写 JSON。
- **方案**：
  1. **JSON 为执行 SSOT**：保存/加载一律走 M1-09 API 与 compiler JSON Schema + 图结构校验
  2. **画布模式（简单）**：仅当工作流为**线性** `agent_task` 链 + 单一 `end`、无条件边时可双向转换（`workflowFormat.ts`）
  3. **JSON 模式（高级）**：始终可用；含 `check` / `human_gate` / 条件边 / 分支时自动禁用画布或只读提示，用户直接编辑 JSON
  4. **内置模板只读**：编辑后通过「另存为副本」写入用户目录（D5）
- **影响**：`WorkflowOrchestration.tsx`、`WorkflowJsonPanel.tsx`、`workflowFormat.ts`、`workflowApi.ts`；复杂能力不强行塞进画布
- **落地前提**：M1-09 ✅
- **决策状态**：`可执行`

### D11 · 会话消息持久化（2026-06-23）

- **背景**：D3/M2-07 仅持久化运行元数据（`run_id`、标题、状态）；用户期望 Cursor 式「点历史看完整对话并续聊」。
- **方案**：按 `run_id` 将完整 `ClutchState`（至少 `messages` + `terminal_logs`）写入 `sessions/states/{run_id}.json`；`_get_or_create_run` 启动时从磁盘加载；前端切换会话时 `GET /api/runs/{id}/state` hydrate 后再连 WS。
- **影响**：`run_state_store.py`；`main.py` `_commit_run_state`；`runApi.fetchRunState`；`clutchState.setPendingHydrate`。
- **落地前提**：M2-07 元数据持久化 ✅
- **决策状态**：`已落地`

### D12 · 桌面 E2E 全链路（2026-06-23）

- **背景**：用户要求界面全操作覆盖、一次性纳入门禁、禁止占位/mock；测试不得触碰用户真实项目。
- **方案**：
  - `tauri-plugin-playwright`（`e2e-testing` feature）+ 顶层 `e2e/tests/desktop/`
  - `scripts/e2e-sandbox-setup.sh` 在 `/tmp/clutch-e2e.*` 生成假项目；`CLUTCH_E2E_SANDBOX` 注入工作区
  - `scripts/run-e2e.sh`：API 冒烟 + 桌面全 UI（`verify.sh` 门禁）
  - 占位 UI（Branch 菜单、Terminal Clear）改为真实行为；`data-testid` 供 E2E 选择
- **影响**：新 Rust/npm 依赖；`withGlobalTauri: true`；`playwright:default` capability
- **决策状态**：`已落地`（`./scripts/verify.sh` 7/7 Playwright 绿，2026-06-23）

### D10 · 单 Agent 模式不开发（2026-06-23）

- **背景**：Prototype 含 Single / Multi Agent 切换（`isMultiAgent`、FR-02-09）；产品聚焦多 Agent 工作流编排，轻量对话式单 Agent 与定位重叠且增加维护面。
- **方案**：**不开发**单 Agent 模式；产品仅保留 Multi Agent（工作流 + Flow + 多角色监督）。Prototype 残留 props 可保留至后续清理，默认 `isMultiAgent=true`，不实现模式切换 UI 与 Single 专属路径。
- **影响**：自 `ROADMAP`、`tasks.md` §P2 移除该任务；`proposal.md` FR-02-09 视为废止；`ARCHITECTURE.md` §7.1 以 Multi Agent 为唯一运行模式。
- **落地前提**：无
- **决策状态**：`已记录`

### D8 · PR-Agent / DangerJS 暂缓（2026-06-22）

- **背景**：Vibe 8.5 兵器库含 PR 对照与 PR 结构合规工具；当前无逐功能 `design.md`（`specs/core/design.md` 仅为视觉快照）、无多人 PR 协作流。
- **方案**：**暂不引入**。等多人协作走 PR 流程且功能级 spec 成熟后再评估。
- **影响**：无新增依赖；避免维护成本大于收益
- **落地前提**：GitHub PR 工作流成为常态 + 功能级 design 文档层就绪
- **决策状态**：`已记录`

### D13 · P2 任务拆解与执行顺序（2026-06-24）

- **背景**：M0–M4 MVP 已完成；用户要求按 `tasks.md` §P2 交付 Skills 后端、全量 MCP、i18n、Theme 持久化、侧栏 REPOSITORIES CRUD、General Settings。
- **方案**（一次一个 task，原子 commit）：
  1. **P2-01** Skills Registry — Sidecar 持久化 + `SKILL.md` 扫描；`SkillsRegistry` / `AgentManager` 去 `localStorage`
  2. **P2-02** MCP Hub — 用户配置 stdio/SSE 多服务器 CRUD + 状态聚合（filesystem 保留）
  3. **P2-03** Theme — 活跃主题写入应用数据目录（与 D5 路径一致）
  4. **P2-04** i18n — Header en/zh 切换 + 监督台关键路径文案双语验收
  5. **P2-05** 侧栏 REPOSITORIES — 分组 filter / new folder CRUD + 持久化
  6. **P2-06** General Settings — 替换占位页为实质配置（工作区默认、高危确认开关等）
- **影响**：`tasks.md` §P2 升格为带 ID 任务；`ROADMAP.md` Skills 行改进行中；存储路径 `Application Support/clutch/skills/`、`preferences/`
- **落地前提**：M4-02 agent 持久化模式可复用；**P2-01 已落地**
- **决策状态**：`已落地`（P2-01…P2-05 ✅；**P2-06 见 D14 延后**）

### D14 · P2-06 General Settings 延后（2026-06-24）

- **背景**：P2-01…P2-05 已交付；用户明确 **P2-06 先不做**，优先 push / CI / 验收 DMG，勿反复询问是否启动 P2-06。
- **方案**：`SystemPreferencesModal` General 页「功能开发中」占位**保留**；P2-06 从当前冲刺移除，待用户重新立项后再执行。
- **影响**：`ROADMAP.md` General Settings 标 ⏸️；`tasks.md` P2-06 标延后；验收范围不含 General 实质配置。
- **落地前提**：用户重新要求交付 P2-06 或写入新的 task ID。
- **决策状态**：`已记录`（主动延后，非取消）

### D15 · E2E 移出 Pre-commit 门禁（2026-06-24）

- **背景**：原 Husky pre-commit 钩子调用的 `verify.sh` 会自动触发完整的 E2E 测试（`run-e2e.sh`）。E2E 测试耗时较长、环境依赖多，阻塞了正常的本地 commit，导致提交速度过于缓慢。
- **方案**：
  - 将 E2E 校验从默认的本地 pre-commit 中剥离。
  - 修改 `scripts/verify.sh`：默认仅运行轻量校验（build + vitest + pytest + drift），仅当传入 `--e2e` 参数时才运行 E2E。
  - 推荐在 Push 前或在 CI 流程中手动运行 `./scripts/verify.sh --e2e` 进行全量校验。
- **影响**：`scripts/verify.sh`、`CLAUDE.md`、`memory/TESTS.md`。
- **决策状态**：`已落地`

## 开放问题

（暂无 — 原 Q1–Q4 已于 2026-06-22 关闭，见 D3–D6。）
