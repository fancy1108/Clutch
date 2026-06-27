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

### D18 · DEV / DMG Sidecar 端口分离（2026-06-26）

- **背景**：D16 已将存储目录隔离为 `clutch_dev` / `clutch`，但 dev 与 DMG 前端均硬编码 `localhost:8123`。两者同时存在时，后启动的 sidecar 抢占端口，导致 DMG UI 读到 dev 会话（或反之）。
- **方案**：
  - 开发：`pnpm tauri dev` / Vite 代理 / 手动 `uvicorn` 使用 **8124**；仅清理 8124。
  - 打包 DMG：PyInstaller sidecar 固定 **8123**；仅清理 8123。
  - 前端 `sidecarUrl.ts`：dev 走相对路径（Vite 代理），production build 直连 `http://localhost:8123`。
- **影响**：dev 与 DMG 可同时运行且数据不串；E2E / CI 仍用 8123（prod 口径）。
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

### D18 · Tools 自动扫描扩容为 CLI + macOS 客户端双探测（2026-06-25）

- **背景**：`tools_status.py` 的 `TOOL_CATALOG` 写死 2 项（claude-cli、cursor），不在清单里的工具即便本机安装了也不会出现在 Tools 页面。
- **方案**：
  - 拆分为 `CLI_CANDIDATES`（9 个 CLI 二进制，`shutil.which` 探测）+ `CLIENT_CANDIDATES`（5 个 macOS `.app`，`Path.is_dir()` 探测）。
  - `list_tools_status()` 返回每项 `kind: "cli"|"client"` 和 `path`（解析到的绝对路径）。
  - Connect 仍为偏好 flag，暂不接入执行链路（那是后续 ADR）。
- **影响**：`tools_status.py` 重写；`toolsApi.ts` 类型扩展；`AiToolsManager.tsx` 卡片加 kind/path 显示。
- **决策状态**：`已落地`

### D19 · 双引擎工具分工与 Agent `mcpServerIds`（2026-06-25）

- **背景**：Clutch 同时支持 `Configured LLM`（内置 Clutch Agent 等）与 `Claude Code (Local CLI)` 两类执行路径；Skills Registry 与 MCP Hub 已持久化，但 Plain Chat 未接入。Agent Manager Module 4 原 `mcpTools` 为占位 permission key，非 Hub 真服务器。
- **方案（方案 A）**：
  1. **`Configured LLM` 路径**：注入 Agent 勾选的 **Skills Registry** `SKILL.md` 至 system prompt；按 Agent **`mcpServerIds`** 绑定 MCP Hub 服务器，经共享 `mcp_react` 执行 ReAct 工具循环。
  2. **`Claude Code (Local CLI)` 路径**：仅路由至本机 `claude` CLI；**不**叠加 Clutch MCP/Skills（用户 Claude Code 环境自带 Skill/MCP）。
  3. Agent schema 新增 **`mcpServerIds: string[]`**（Hub `server.id`）；`mcpTools` 保留占位，暂不参与执行。
- **影响**：`agent_skills.py`、`agent_mcp.py`、`mcp_react.py`；`main._llm_chat_reply`；`AgentManager` Module 4 改绑 Hub；`agent_executor` 复用 `mcp_react`。
- **决策状态**：`已落地`（P2-14…P2-19：Skills/MCP Plain Chat、实时 MCP 日志、高风险 MCP 审批门）

### D20 · Claude Code CLI 原生 Session 绑定 Clutch run_id（2026-06-25）

- **背景**：Plain chat 经 Claude CLI 时，每轮将完整历史塞进 `-p`，无法复用 Claude Code 工具上下文与 session cache；延迟与 token 成本随轮次线性增长。
- **方案**：
  1. `ClutchState` 持久化 `claude_session_id` + `claude_session_agent_id`（`sessions/states/{run_id}.json`）。
  2. **首轮**（或无 session id）：`claude -p <history|prompt> --session-id <uuid>`，uuid 由 Sidecar 生成并写回 state。
  3. **续轮**：`claude -p <当前句> --resume <uuid>`，不再重放全文历史；`system_prompt` 仅首轮注入。
  4. **Resume 失败**：回退历史重放 + 新 `--session-id`。
  5. **切换 Agent**：`claude_session_agent_id` 与当前 `agent_id` 不一致时丢弃旧 session id。
- **影响**：`claude_cli_adapter.py`、`engine_router.py`、`main._handle_plain_chat`；`packages/shared-types` `ClutchState` 扩展字段。
- **决策状态**：`已落地`

### D21 · Codex 兼容 `apply_patch` 内置工具（2026-06-25）

- **背景**：官方 `@modelcontextprotocol/server-filesystem` 无 `delete_file`；Configured LLM 路径删除文件时模型退化为 `move_file` → `.deleted_*` 隐藏文件，与 Claude Code / Codex 体验不一致。
- **方案（借鉴 OpenAI Codex `codex-rs/apply-patch`）**：
  1. Sidecar 内置虚拟 MCP 服务器 **`clutch-tools`**，在 Agent 绑定 `local-fs` 时自动挂载。
  2. 提供 **`apply_patch`** 工具，支持 Codex patch 语法：`Add File` / `Delete File` / `Update File` / `Move to`。
  3. 在工作区白名单内执行真删除（`unlink`）、写入与 diff 更新；结果 JSON 含 `changed_paths` 驱动 `file_changed` 刷新。
  4. `apply_patch` 归类为高风险 MCP 工具，走现有 Supervisor 审批门。
- **影响**：`apply_patch.py`、`builtin_tools.py`、`mcp_react.py`、`agent_mcp.py`、`mcp_risk.py`、`main._compose_agent_system_prompt`。
- **决策状态**：`已落地`

### D23 · Flow 节点输入/输出接力（2026-06-26）

- **背景**：Multi-Agent Flow 中每个 `agent_task` 均读取同一份 `current_instruction`（用户首句），下游 Agent 收不到上游输出；Weather-to-Vision 等链式 SOP 无法跑通（Researcher 描述无法交给 Artist 生图）。单 Agent 已支持 `agentType: clutch` + `modelId` 绑模与生图，Flow 仍缺接力与逐步 UI 投影。
- **方案**：
  1. **`CompilerState.node_outputs`**：`dict[str, str]`，键为节点 `id`，值为该节点 `agent_task` 的文本输出。
  2. **输入解析（auto，首版无编辑器 UI）**：`resolve_agent_task_input(state, node, workflow)` — 若唯一上游为 `start`，输入 = 用户 `current_instruction`；否则输入 = 直接上游节点的 `node_outputs[upstream_id]`。节点 `data.instruction` 作为**补充前缀**（`{instruction}\n\n{body}`），不覆盖上游正文。
  3. **执行对齐单 Agent**：Flow 内 Clutch Agent 注入 `markdownDoc`；`agentType: clutch` + image `modelId` 走生图；非 image 有 `mcpServerIds` 时走 `mcp_react`（与 Plain Chat 一致）。
  4. **逐步监督**：每个 `agent_task` 完成后增量 `state_patch`（消息 + `active_agent` + `active_node_id`），Chat 逐步回显；整图仍单次 `invoke`，不在本决策内拆 HTTP。
  5. **Weather-to-Vision 首版**：Researcher 可先靠 `markdownDoc` 生成视觉描述（不接真实天气 API）；Artist 绑定 Agnes Image；线性边 `start → researcher → artist → end`。
- **影响**：`compiler/compiler.py`、`compiler/node_input.py`（新）、`agent_executor.py`、`workflow_projection.py`、`main.py`（增量 patch）、`apps/desktop` Chat/Flow UI；Task 清单见 `specs/core/tasks.md` §M3-F。
- **决策状态**：`已落地`（M3-F01–F09；用户 2026-06-26 手动 Weather-to-Vision E2E 通过）

### D24 · CLI Session 字段泛化与 Cursor GUI 路由移除（2026-06-26）

- **背景**：`claude_session_id` 被 `antigravity-cli` 复用但命名误导；`cursor-workspace` / `cursor-app` / `cursor_adapter` 已退出产品面（`CLIENT_CANDIDATES` 为空，前端 `AGENT_TYPE_OPTIONS` 仅四类），`engine_router` 中相关分支为死代码。
- **方案**：
  1. `ClutchState` 写入 `cli_session_id` + `cli_session_agent_id`；`read_cli_session_*` 读盘兼容旧 `claude_session_*`。
  2. `EngineResult.cli_session_id` 取代 `claude_session_id`。
  3. 删除 `cursor_adapter.py`、`POST /api/tools/open-cursor`、`engine_router` cursor-workspace 分支、`agent_type` legacy `cursor-workspace` 映射。
  4. 前端 Workflow `aiTool` 下拉与 AI Tools 文案对齐四类 CLI 路由；`ChatFeed` 移除 Cursor 引擎标签。
- **影响**：`state.py`、`engine_router.py`、`main.py`、`packages/shared-types`、`WorkflowOrchestration.tsx`、`AiToolsManager.tsx`、`ChatFeed.tsx`；PTY 调研见 `docs/research/pty-session.md`。
- **决策状态**：`已落地`

### D25 · ShellSession + `SHELL_EXEC` 为 CLI Runtime 默认（2026-06-26）

- **背景**：Step 0 三路线实验（`experiments/pty_poc/`）：Route A（pexpect 驱动 Claude Ink TUI）严格 5/5 失败；Route C（长驻 bash PTY + `claude -p`）5/5 通过。
- **方案**：
  1. **否决**全量 Claude TUI PTY（`INTERACTIVE_PTY` 非 Claude 默认）。
  2. 第二阶段默认 **`ShellSession`**（长驻 bash）+ 每轮 **exec**（`claude -p` / `agy -p` / `codex exec`）。
  3. 引入 **`RuntimeStrategy`** 枚举（`SHELL_EXEC` · `INTERACTIVE_PTY` · `HTTP_DAEMON` · `SDK_NATIVE`）；EngineRouter 第三阶段改为 `strategy = provider.runtime_strategy`，禁止 `if provider == "claude"` 扩散。
  4. **`HumanInputKind`**（`BOOT_TRUST` · `TOOL_CONFIRM` · `TEXT` · `AUTH`）为 Runtime 一级概念；禁止 Provider 字符串特判。
  5. **Context Continuity**（§2.6）：工作环境 vs AI 记忆分离；`SessionSnapshot` + 换班机制排 **Step 3**。
  6. **上线安全**（§1.4）：`runtime.mode` 默认 `legacy`；Hybrid Beta + 单轮自动降级；Step 1 仅 Plain Chat + `claude-cli`。
- **影响**：`docs/research/pty-session.md` v5；Step 1 `ShellSessionManager`；Step 3 `SessionSnapshot` / 继续工作。
- **决策状态**：`已决策`（文档 + Step 0 证据；Sidecar Step 1–4 代码已落地；**产品验收见 HRT-04**）

### D27 · Hybrid Step 5 命名与范围拆分（2026-06-27）

- **背景**：`pty-session.md` §Step 5 含「多 run 并发 + 操作日志审计 + 池化」；`PROGRESS.md` 曾将「池上限 + Snapshot prune」标为 Step 5，易造成「Step 5 已完成」误解。
- **方案**：
  1. **HRT-S5-partial**（已落地）：`CLUTCH_SHELL_MAX_SESSIONS`、`CLUTCH_SHELL_SNAPSHOT_MAX_AGE_DAYS`。
  2. **HRT-05 ~ HRT-10**（未落地）：审计 JSONL、debug API、多 session 治理、POC #6/#10 — 权威 Task 表见 [`specs/core/hybrid-runtime-plan.md`](../specs/core/hybrid-runtime-plan.md)。
  3. `pty-session.md` Step 5 保留设计叙事；执行状态以 HRT 表为准。
- **影响**：`memory/ROADMAP.md` · `memory/PROGRESS.md` · `specs/core/hybrid-runtime-plan.md`。
- **决策状态**：`已落地`（文档）

### D28 · Hybrid 可排查性：审计日志与 debug API（2026-06-27）

- **背景**：Hybrid 验收依赖用户截图 Terminal；`terminal_logs` 虽持久化于 `states/{run_id}.json`，但无结构化 turn 审计、无按 run 查询 API、无导出路径。`pty-session.md` §2.4.2 要求操作日志必含 `run_id` / `source` 等字段。
- **方案**：
  1. **HRT-05**：每 hybrid turn 追加 JSONL 行（`logs/hybrid/{date}.jsonl`）— marker、duration_ms、result、cli_session_id。
  2. **HRT-06**：`GET /api/runs/{run_id}/debug` — status、末 N 条 terminal_logs、最近 audit 行。
  3. **HRT-07**：UI「导出诊断」或 `scripts/export-run-debug.sh`（不含密钥）。
  4. turn 失败/超时须写 audit + 尽量恢复 `status: idle`（与 HRT-01 一并验收）。
- **影响**：`shell_exec_runtime.py` · `main.py` · 可选 `ChatFeed` / Settings。
- **决策状态**：`可执行`（Task HRT-05~07；HRT-04 已通过）

### D29 · Hybrid 执行顺序：先 debug 基建、后并发（2026-06-27）

- **背景**：HRT-04 单 session 验收已通过；HRT-05~07（审计/debug）与 HRT-08~10（并发）均可立项。用户确认：排查能力应像测试一样长期维护，随需求与代码变动迭代。
- **方案**：
  1. **固定顺序**：HRT-05 → HRT-06 → HRT-07 → HRT-08~10 → 评估 HRT-05~07 是否需增补。
  2. **维护习惯**：任何触及 hybrid turn / shell / parser / router 的 commit，Check-out 时检查 audit JSONL 与 debug API 是否仍覆盖新路径（类比「改代码看测试」）。
  3. HRT-08 完成后对 audit 做一轮回归（新 failure mode 必须可查询，禁止回到截图排查）。
- **影响**：`specs/core/hybrid-runtime-plan.md` §2.1 · Agent Check-out 纪律。
- **决策状态**：`已落地`（文档）

## 开放问题

| ID | 问题 | 选项 | 默认 |
|----|------|------|------|
| Q-HRT-1 | 多 session 并发策略 | A) 全 run 串行队列 B) 同 workspace 串行 C) 拒绝+提示（pty §2.1） | **C**（与 POC 一致）直至 HRT-08 立项 |
| Q-HRT-2 | 诊断导出形态 | A) 仅 API B) API + 桌面「复制诊断」按钮 | **B**（HRT-07） |

### D26 · 用户自定义头像替换与存储（2026-06-27）

- **背景**：原系统 User 消息气泡统一指向静态 Unsplash 网页地址，不支持自定义用户配置，在 General 设置里也没有对应的偏好配置，缺乏个性化表现。
- **方案**：
  1. **默认用户头像**：将用户提供的猪玩偶插图以 `default_avatar.jpg` 打包进应用静态资源。
  2. **偏好机制**：在 `preferences.json` 偏好中增加 `"user_avatar"` 属性，采用 base64 DataURL 方式对本地更换的头像图片进行持久化，避免配置和资源文件存放在不同目录导致的路径查找问题。
  3. **头像分发与广播**：应用启动时在 `App.tsx` 中 hydrate 并通过 state 分发到 chat bubble 以及 settings UI。
- **影响**：`preferences_storage.py`，`main.py` 偏好端点，前端 `clutchState` / `SystemPreferencesModal`。
- **决策状态**：`已落地`
