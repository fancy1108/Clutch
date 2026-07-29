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
- **方案**：**可切换**多 Provider；**默认**为 **Agnes 2.0 Flash**（2026-07 自 DeepSeek V4 Pro 调整）；用户可在设置或 Agent 配置中改选。
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
- **决策状态**：`已落地`（P2-01…P2-05 ✅；**P2-06 见 D14 部分落地**）

### D14 · P2-06 General Settings 延后与部分落地（2026-06-24）

- **背景**：P2-01…P2-05 已交付；用户明确 **P2-06 核心（工作区默认、高危确认开关等）先不做**，优先 push / CI / 验收 DMG。但在后续迭代中，为了支持自定义用户头像偏好设置，已将部分设置项在 General 页实质落地。
- **方案**：`SystemPreferencesModal` General 页原「功能开发中」占位**替换为自定义用户头像配置**；工作区默认等其他高级设置项继续延后。
- **影响**：`ROADMAP.md` General Settings 状态更新为“部分落地”；`tasks.md` P2-06 部分勾选。
- **落地前提**：已完成用户头像定制偏好配置，其余项待进一步立项。
- **决策状态**：`部分落地`

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

### D30 · OSR-09 CLI 权限策略：维持 skip-permissions（2026-06-29）

- **背景**：OSR-09 要求门控或默认关闭 `--dangerously-skip-permissions`；Hybrid / 工作流依赖全自动 CLI turn，关闭后可能卡在 `TOOL_CONFIRM` 等人机等待（`pty-session.md` §2.0.2）。
- **方案（用户确认 · 选项 B）**：
  1. **维持现状**：`claude_cli_adapter` / `shell_exec_runtime` / `engine_router` 继续默认追加 `--dangerously-skip-permissions`。
  2. **文档披露**：`README.md` §安全与 CLI 权限 明确说明；`SECURITY.md` 交叉引用。
  3. **UI 不误导**：Permission 菜单标注主要作用于 MCP 门控（非 CLI skip 开关）；OSR-14 向导不承诺「ask = CLI 也会问」。
  4. **OSR-00**：外部无指导审计由维护者自行验收，不阻塞 T1 开发项。
- **影响**：`README.md` · `SECURITY.md` · OSR-09 标 ✅（披露型完成，非行为变更）。
- **决策状态**：`已落地`

### D31 · 未签名 DMG 经 GitHub Releases 分发（2026-06-29）

- **背景**：维护者暂无 Apple Developer 账号，无法完成 OSR-11 代码签名与公证；仍希望在 T1 公开仓库后向终端用户提供可安装的 macOS DMG（与多数开源桌面项目做法一致）。
- **方案（用户确认）**：
  1. **豁免 OSR-11**：不阻塞开源与首次 DMG 分发；获得 Developer 账号后再补签名/公证。
  3. **分发路径**：GitHub Releases 附 `.dmg`；Release 正文由 `scripts/render-release-notes.sh` 组装（`CHANGELOG` 变更摘要置顶，`.github/release-notes/` 含 Gatekeeper 等安装说明）；`README.md` §安装方式 与 `docs/INSTALL.md` 为完整用户文档。
  3. **Release CI**：`.github/workflows/release.yml` 在 `v*` tag 推送时于 `macos-latest` 构建**未签名** DMG 并上传 Release（OSR-12，不依赖 OSR-11）。
  4. **OSR-00**：维护者已于 2026-06-29 自行完成发布前验收，T1 开闸。
  5. **首发版本**：公开发布与首个 DMG tag 从 **`v1.0.0`** 起（非 `v0.1.0`）。
- **影响**：`README.md` · `docs/BUILD_FROM_SOURCE.md` · `docs/OPEN_SOURCE_RELEASE.md` §7.2/§7.7 · OSR-11 ⏭️ · OSR-12 ⚠️（workflow 已加，待首 tag 验证）。
- **决策状态**：`已落地`

### D32 · 暂不提供 Intel Mac 安装包（2026-07-01）

- **背景**：CI 仅构建 Apple Silicon DMG；Intel 需额外 sidecar 架构与 Release 资产，维护成本高，当前用户以 M 芯片为主。
- **方案（用户确认）**：
  1. **官方分发仅 aarch64 DMG**；README / INSTALL / PACKAGE_MANAGERS 标明 Intel **暂不支持**。
  2. Intel 用户可选源码自建（`BUILD_FROM_SOURCE.md`），不承诺体验。
  3. 后续有明确需求再单独立项 Intel CI。
- **影响**：`docs/PACKAGE_MANAGERS.md` · `README` · `install.sh` · Homebrew cask `depends_on arch: :arm64`。
- **决策状态**：`已落地`

### D54 · Ask = 只读对话；Explore 并入 Ask；默认 Agent（2026-07-25）

- **背景**：底栏 Explore / Ask 易混；产品期望 Ask = 对话只读；默认应对标 Cursor **Agent**（可动手）。
- **方案**：Ask 硬拦截写/变更 shell（原 Explore）；UI 去掉 Explore；`explore` → `ask`；UI 名 **Agent** = `auto_edit`（默认）；菜单序 Agent → Plan → Full → Ask；图标 ∞ / checklist / warning / chat。
- **影响**：新装默认可改文件；Ask 为只读对话。
- **决策状态**：`已落地`

## 开放问题

| ID | 问题 | 选项 | 默认 |
|----|------|------|------|
| Q-USAGE-1 | Overview 用量真值 | A) 继续词数估算 B) 接供应商 `usage`（真 input/output）+ 模型价表；估计算 fallback | **B 后续优化**；UI 暂显示 `—`（2026-07-25） |
| Q-HRT-1 | 多 session 并发策略 | A) 全 run 串行队列 B) 同 workspace 串行 C) 拒绝+提示（pty §2.1） | **C**（与 POC 一致）直至 HRT-08 立项 |
| Q-HRT-2 | 诊断导出形态 | A) 仅 API B) API + 桌面「复制诊断」按钮 | **B**（HRT-07） |
| Q-D34-1 | Terminal 并行 Lane 上限 N | A) 2 B) 4 C) 8 | **B**（4，见 D34 §2） |
| Q-D34-2 | handoff 正文生成方 | A) Clutch 内置编排 B) 调用 Matt Pocock handoff skill C) 主 Agent CLI 自写 | **A** 首期；B 可作为 skill 插件对齐 |
| Q-D34-3 | 超 N 时行为 | A) 拒绝新 Lane B) 排队 C) Tab 折叠旧 Lane | **B+C** 组合（排队 + 折叠展示） |
| Q-D34-4 | 多 Lane 同时完成回传 | A) 各一路独立草稿 B) 自动合并一条 C) 仅提醒不预填 | **A**（独立草稿队列；用户可自行合并编辑） |
| Q-D34-5 | handoff sources 默认 | A) 仅聚焦 Lane B) 最近派发到该 target 的 sources C) 空 | **A**；显式 `from @A @B` 覆盖；发送前 chips 可改（见 D34 §2） |
| Q-UI-1 | Chat 流式回复滚不上来 | A) 调整 `<section>` flex/overflow 布局让 `scrollHeight` 可靠 B) 用 `bottomRef` rect 算偏移绕过 `scrollHeight`（已试无效）C) 重构 ChatFeed 容器层级 | **待诊断 CSS 布局后定** |

> **Q-UI-1 现象详情（2026-07-29 诊断）**：纯 LLM 对话（`isPlainLlmChat=true`）工具审批通过后，最终 assistant 回复已在 DOM 渲染，但被卡在可视区下方，看不到；下一次发任意消息才被顶上来。流式期间（`isRunning && !awaitingHuman`）也出现。
>
> **滚动相关代码**：`apps/desktop/src/components/ChatFeed.tsx`
> - 滚动入口 `scrollChatToBottom`（`:1048`）：`bottomRef.current?.scrollIntoView({ behavior, block: 'end' })`
> - 触发 effect 依赖（`:1062`）：`[messages, clutchStatus, showThinking, pendingMessages.length, scrollChatToBottom]`
> - 下哨兵 `bottomRef`（`:1805`）：`<div ref={bottomRef} style={{ scrollMarginBottom: chatScrollBottomPad }} className="h-2 shrink-0" />`
> - 滚动容器（`:1234`）`<section>`：`className="flex-1 min-h-0 flex flex-col box-border transition-all duration-300 bg-background ... overflow-y-auto overscroll-contain"`
> - 父链均为 `h-screen overflow-hidden flex flex-col`（`App.tsx:1913 / :2113`）
>
> **实测数据**（往 `scrollChatToBottom` 注入诊断日志测得，已撤回）：
> - 从 `<section>` 到 `<html>` 全部 `scrollHeight == clientHeight == 768`，全部不可滚动；祖先链：`SECTION.flex-1.min-h-0 ov=auto sh=768 ch=768 st=0` → `DIV.flex-1.min-w-0 ov=hidden sh=768 ch=768 st=0` → `DIV.flex-1.flex ov=hidden sh=768 ch=768 st=0` → `DIV.relative.h-screen ov=hidden sh=768 ch=768 st=0` → `BODY ov=hidden sh=768 ch=768 st=0` → `HTML ov=visible sh=768 ch=768 st=0`。
> - `bottomRef` 真实 rect y 一路下到 `918`（`bottom: 918`），但 `<section>` `scrollHeight` 偶尔报 `1272` 之后又跌回 `768`：`scrollTo({top: scrollHeight})` 当 scrollHeight=768 时不动；偶发 scrollHeight=1272 时才滚一次。
> - 显式 `bottomRef.rect` 算偏移的改进已实测无效（layout 被压缩，rect 也未反映真实溢出）。
>
> **建议后续**：先 DevTools Computed 面板点 `<section>` 截 `height`/`max-height`/`min-height`/`overflow-y`/`display`/`flex`/`flex-basis`，确认为何 section 子项被压成等高（`scrollHeight == clientHeight`）；再决定是改 CSS 布局还是重构容器层级。

### D26 · 用户自定义头像替换与存储（2026-06-27）

- **背景**：原系统 User 消息气泡统一指向静态 Unsplash 网页地址，不支持自定义用户配置，在 General 设置里也没有对应的偏好配置，缺乏个性化表现。
- **方案**：
  1. **默认用户头像**：将用户提供的猪玩偶插图以 `default_avatar.jpg` 打包进应用静态资源。
  2. **偏好机制**：在 `preferences.json` 偏好中增加 `"user_avatar"` 属性，采用 base64 DataURL 方式对本地更换的头像图片进行持久化，避免配置和资源文件存放在不同目录导致的路径查找问题。
  3. **头像分发与广播**：应用启动时在 `App.tsx` 中 hydrate 并通过 state 分发到 chat bubble 以及 settings UI。
- **影响**：`preferences_storage.py`，`main.py` 偏好端点，前端 `clutchState` / `SystemPreferencesModal`。
- **决策状态**：`已落地`

### D19 · 新增 CLI / 模型 Provider 须同步更新文档（2026-07-02）

- **背景**：OpenCode Zen 文本模型接入后，产品说明（`PRODUCT_INTRO.md`）、上手指南（`GETTING_STARTED.md`）与 `FILEMAP` 一度滞后，用户难以自助配置。
- **方案**：凡新增或显著变更 **CLI 工具路由**（`codebuddy-cli`、`opencode-cli` 等）或 **内置文本/多模态 Provider**（如 OpenCode Zen），在同一 Task 内至少更新：
  1. `docs/PRODUCT_INTRO.md` — 用户可见能力与设置路径；
  2. `docs/GETTING_STARTED.md` — 配置步骤（中英表格各一处）；
  3. `memory/FILEMAP.md` — 新增/变更的源码路径映射（若涉及新模块）；
  4. `CHANGELOG.md` — `[Unreleased]` 条目（发版前合并进版本节）；
  5. `README.md` / `README.zh-CN.md` — **「最新更新」**一节：只写**用户可见**的单一版本要点列表（不按 commit / 开发进度分段）；发版时整节替换为新版本，历史见 `CHANGELOG.md`；
  6. `apps/desktop/src/services/cliInstallGuides.ts` — 安装指引与 `RECOMMENDED_CLI_IDS`（若列为推荐）；
  7. `.cursor/rules/cli-whitelist-docs.mdc` — 本清单的权威副本。
- **影响**：Agent 与用户约定「加 CLI / Provider」时默认包含文档 diff，不单改代码。
- **决策状态**：`已落地`

### D33 · Chat / Terminal 双模式与 `INTERACTIVE_PTY`（2026-07-02）

- **背景**：用户希望在保留现有监督对话的前提下，于主工作台嵌入完整 Claude Code / OpenCode 交互 TUI。
- **方案**：
  1. **默认对话模式**：`workspaceViewMode=chat`；未切换时 UI 与 `SHELL_EXEC` headless 路径与现网一致。
  2. **终端模式 opt-in**：用户点击切换后 `pty_attach` → 独立 `interactive_pty_runtime.py`（**不修改** `shell_exec_runtime` 默认分支）。
  3. **输入互斥**：终端模式活跃时隐藏 `ChatInputBar`；`pty_detach` 不杀 CLI 进程。
  4. **首期范围**：Single Agent plain chat；工作流 session 禁用切换。
  5. **PTY 事件**：`pty_output` / `pty_input` / `pty_resize` / `pty_attach` / `pty_detach` / `pty_session_status`（附加 WS 通道，不改现有 `state_patch` / `message`）。
- **证据**：`experiments/tui_embed_poc/RESULTS.md`（bash smoke Go）；产品实现 `ChatFeed` + `ChatTerminalView` + `interactive_pty_runtime.py`。
- **决策状态**：`已落地`

### D34 · Terminal 多 Agent 协作编排（PTY Lane + Handoff）（2026-07-02）

- **背景**：D33 终端模式为 **单 Agent · 单 PTY · 隐藏 ChatInputBar**，无法在 Terminal 工作台内做 `@派发`、多路并行与跨 CLI 上下文接力。用户场景 **不固定拓扑**（可能是 A∥B 冷启动并行，再把结果交给 C；可能是 A→B→C 链式；可能是多路回传到任意 Agent），需要 **统一派发原语** 与 **可解释的 handoff 来源规则**。
- **方案（产品原则，**在 D33 上叠加、不替换对话模式与工作流 SOP**）**：
  1. **唯一用户原语：派发（Dispatch）**
     - 用户在 **Orchestrator Bar**（或当前聚焦 Lane 的对话流）输入 **`@目标Agent` + 需求描述** → 确认发送 → Clutch **派发到目标 Lane**（新建或聚焦已有 PTY）。
     - **双模输入（聊天优先，图语法保留）**：
       - **自然语言（默认）**：口语化描述即可，例如 `@OpenCode 去写个 API，参考 handoff @20260702-claude→opencode-api.md`。系统后台将用户输入 **编译为 dispatch graph**（`target`、`sources`、`file_refs`），无需手写 `from`。
       - **图语法（高级 / 精确）**：`@C from @A @B：…` 显式指定 sources；与自然语言 **等价**，仅表达方式不同。
       - **`@文件` 引用**：消息内 `@*.md` 或 Overview **「发送到 Bar」** 插入的文件名，均绑定 handoff 元数据（`sources → target`、路径）；确认卡展示引用清单，用户可见 **具体哪个文件、来自谁**。
       - **sources 推断优先级（自然语言）**：① `@文件` 元数据（可多个文件合并 sources）② 当前聚焦 Lane ③ 工作区冷启动 `[]`；图语法下显式 `from` 优先，可与 `@文件` 合并。
     - **不预设 primary / delegate 角色**；Lane 是对等 PTY，关系由 **派发历史（有向边）** 记录，而非写死树形主子。
     - 各 Lane 内 xterm 仍可原生 TUI 多轮对话；Bar 负责 **跨 Lane 编排**。
  2. **Handoff 回答「谁交给谁」**
     - **交给谁（target）**：消息中 **第一个（或唯一）被 @ 的 Agent** = 派发目标 = handoff 接收方。
     - **谁交出（sources）**：写入 handoff 的上游上下文，按 **优先级** 解析（实现须可测、UI 须可预览）：
       1. **显式**：`@C from @A @B：…` / `@C（综合 @A @B）…` → sources = `{A, B}`，生成 **`A,B→C.md`**（多源合并摘要 + 各 Lane 审计指针）。
       2. **聚焦 Lane**：仅一个 `@C` 且未写 from → sources = **当前聚焦的 xterm Lane**（若有）；生成 **`{focused}→C.md`**。
       3. **无上游（冷启动 / 并行开局）**：无聚焦、无 from → sources = `[]`，handoff 仅含 **工作区摘要 + 用户当条需求**（如 `@A` 与 `@B` 各发一条各自开工，互不依赖）。
       4. **发送前 UI 确认（推荐默认展示）**：解析出 target + 推断的 sources 后，派发前展示可编辑 chips：`上下文来自：[x] Lane-A [x] Lane-B [ ] 工作区`，用户可增删再发送（避免 silently 丢上下文或误带上下文）。
     - 产物路径：**`.clutch/handoffs/{timestamp}-{sourcesLabel}→{target}-{slug}.md`**；目标 Lane 首条 prompt **只引用路径**，由接收方 CLI `read`。
  3. **PTY Lane 模型（2-B）——对等 Lane + 派发图**
     - 一个 `run_id` 下 **至多 N=4** 路并行 PTY（首期 CLI 类型仍 `claude-cli` · `opencode-cli`；同类型可多 Lane，按 `lane_id` 区分）。
     - 每条 Lane：`lane_id`、`agent_type`、`label`（子任务标题）、`status`；**可选** `dispatch_edges[]` 记录 `sources → target`（用于审计与草稿建议，非权限树）。
     - UI：分屏 / Tab；**聚焦**决定默认 handoff source；**Lane 折叠**为终端 **右侧独立栏**（`float-rail`，与 xterm **不重叠**）内堆叠紧凑胶囊：`rounded-xl` · `shadow-sm` · 品牌 LOGO + 一行子任务摘要；`running`/`booting` 仅 spinner，`completed` 仅 LOGO 角标绿点；点击展开，PTY 不断开。
  4. **典型场景（须全部支持，非穷举）**
     | 场景 | 用户操作 | handoff |
     |------|----------|---------|
     | A、B 并行冷启动 | 连发 `@A …`、`@B …` | 两次 sources=`[]`，各 Lane 独立 |
     | A 做着，派 B | 聚焦 A，`@B 子任务…` | `A→B.md` |
     | A∥B 后交给 C | `@C from @A @B：整合…` 或 chips 选 A+B | `A,B→C.md` |
     | 只要 B 的结果给 C | `@C from @B：…` | `B→C.md` |
     | B 做完通知任意人 | 完成提醒 + 预填草稿（用户改 @ 与正文） | 生成 `B→*.md` 建议，**用户定 target** |
     - **不要求**结果必须回 primary；**回谁由用户下一次 `@` 决定**。
  5. **完成 / 回传交互（用户确认发送）**
     - Lane 标记完成或弱检测 idle → **提醒** + **预填 Orchestrator Bar 草稿**（建议 target、摘要、handoff 路径）；**不自动注入任何 PTY**。
     - 草稿 **可编辑** `@`、正文、合并多路；多路完成 → `pending_handoff_drafts[]` 队列。
     - 派发与回传 **对称**：均可能预填草稿，均需用户发送。
  6. **状态与 SSOT**
     - `pty_lanes[]`、`dispatch_edges[]`、`pending_handoff_drafts[]`、handoff 路径 → **`ClutchState`**（WS 投影）；Lane 生命周期由 **PTY Lane Manager** 管理。
     - **Dispatch graph 与 Handoffs 列表**：**不单独占右侧栏**——`dispatch_edges[]` 与 handoff 路径折叠进 **派发记录时间线**（每条即 `sources → target`）；**最新 handoff 挂在目标 Lane 标题栏**（预览 / 发送到 Bar），用户按终端对应操作；跨 Session 完整归档在历史会话中查看。
     - **派发历史**：Overview **仅保留本 Session 紧凑时间线**（`dispatch_log[]`：时间、`sources→target`、截断 prompt）；点击条目可聚焦目标 Lane；确认派发后写入并跳转 Overview，**禁止** `window.alert`。
     - **Handoff md**：**不占用 Lane 标题栏**；有 `from→to` 时在终端 Lane 间绘制**箭头连线**，线中 **📎 附件图标** 悬浮显示文件名卡片（预览 / 发送到 Bar）。右侧派发记录同步保留 handoff 文件操作。
     - **派发确认 UI**：贴在 **Orchestrator Bar 上方**（`surface-container-low` 卡片 + 主/次按钮），不得阻断终端中部阅读区。
     - 即兴协作 **不**默认编译进 LangGraph SOP；可 **可选**「保存为工作流」。
  7. **与 D33 关系**
     - 单 Lane = N=1 退化；恢复 Orchestrator Bar（与 xterm **聚焦互斥**，非隐藏 Bar）。
     - 工作流 session 仍不展示 Terminal 切换。
- **分期**
  - **D34-α**：Orchestrator Bar + `@` 派发 / 聚焦 Lane；handoff sources 规则 §2（1–3）。
  - **D34-β**：多 Lane 并行 UI + 多 PTY；**A∥B 冷启动**冒烟。
  - **D34-γ**：handoff md 生成；派发前 **sources chips** 预览（§2-4）。
  - **D34-δ**：完成提醒 + 草稿队列；**`@C from @A @B`** 多源合并冒烟。
  - **D34-ε**：与对话模式 handoff 互通；超 N 排队 / Tab 折叠。
- **影响**：PTY Lane Manager、handoff 解析器（`parse_dispatch_mentions`）、`ClutchState`、`ChatFeed` lane 容器、`docs/PRODUCT_INTRO.md`（D19）。
- **证据（待补）**：`A∥B` 冷启动、`A,B→C` 整合、完成草稿用户发送 — `runs/verification/`。
- **决策状态**：`已记录`（原则已定；实现待 D34-α 立项）

### D35 · 内建 Design 模式（原型画布 + 预览沙箱）（2026-07-10）

- **背景**：Clutch 强于 Coding 编排与监督，弱于 Coding 前的需求/UI 验证；需求不确定导致反复修正。对标高保真原型设计（多屏原型）与可运行前端代码预览沙箱，需在本地优先、LangGraph SSOT 约束下内建 Design 能力，而非做成又一个 Lovable。
- **方案**：（已被 **D36** 修订产品形态；两层流水线与产物原则仍有效）
  1. ~~侧栏一级入口 + Design 项目 CRUD~~ → 见 D36。
  2. **两层流水线**：Prototype（规范→界面）→ Approve → UI code（Vite+React+TW）→ Send to Coding。
  3. **产物路径**：授权工作区 `.clutch/design/...`；Sidecar 为 SSOT。
  4. **架构**：独立 `services/orchestrator/src/design/`；可选 SOP `design-to-code`。
  5. **非目标**：全栈 Auth/DB、云 Figma、替代 Cursor 写业务逻辑。
- **决策状态**：`已修订`（见 D36）

### D36 · Design = 工作区会话 + Header 模式切换 + 原型交互画布（2026-07-10）

- **背景**：D35 首版做成独立 Design 项目左栏 + 三栏工具台，与 Chat 会话模型不一致，且 Prototype 体验不够闭环（缺乏：欢迎大输入 → 无限画布 → 先规范卡再描绘界面 → 底部 NL 修改的连贯交互）。
- **方案**：
  1. **会话模型**：`SessionRecord.mode: 'coding' | 'design'`（缺省 `coding`）；Design 挂在当前授权工作区下，与 Chat 一样「新建会话」；侧栏历史按 mode 过滤。
  2. **Header**：右上角 `Coding | Design` 切换（替换原中英文切换）；语言移入 Settings → General。
  3. **UI**：无 Design 独立项目栏；欢迎页 + React Flow 无限画布；过程卡 →（可选）**参考源卡**（Design.md / 网址 / 图片）→ **设计规范卡** → **界面卡（描绘动画）** → 底部浮动 NL 修改条；欢迎态 `+` 菜单支持上传 Design.md（自动填提示）、网站网址、参考图。画布**选中**卡片进入底栏上下文；iterate 按文案 **modify/add**（未知→add）；⌘C/V 复制粘贴 UI；UI 内 **点选元素**。右侧 Overview/Files/Changes/Terminal **在 Design 可用，默认收缩**；Files 展示 `.clutch` 产物。出码/交接入口为 Preview Demo → Coding（Approve / Send to Coding）。
  4. **API**：session-scoped `POST /api/design/sessions`、`.../generate`（`reference_image` / `reference_md` / `reference_url` 可选；两阶段 spec→UI）、`.../iterate`（`target_kind` / `target_id` / `element_*` / `mode`）；产物 `.clutch/design/sessions/<run_id>/`（含 `reference.<ext>`、`reference_design.md`、`url_snapshot.json`、`thumbnail.svg`、多屏 `screens/`）；`artifact_paths` 供 Changes 列表。
  5. **非目标（本轮）**：账号/云协作、完整矢量编辑、真实 Figma 导出、语音输入。
- **影响**：`Header`、`App` `appMode`、`DesignWorkspace`、`run_history`/`runApi` mode、`PRODUCT_INTRO` §3.5、`ROADMAP`、`FILEMAP`。
- **决策状态**：`可执行`

### D37 · Sidecar 热更（独立 patch_id · 静默下载 · 挂起应用）（2026-07-11）

- **背景**：全量 Tauri updater 按 app semver 比较，且产物约 39MB（含 sidecar）。后端-only 热修若强制升版，用户成本高；游戏式「热补丁」需要独立通道。
- **方案**：
  1. **范围（v1）**：仅热更 `orchestrator`；**macOS**；不热更前端 / 不 bsdiff / 不 Windows。
  2. **版本**：`patch_id` 与 app semver **独立**；manifest 含 `min_app_version`（过低忽略）。
  3. **存放**：`~/Library/Application Support/clutch/patches/`（**禁止**写入 `.app`）；启动时优先加载已校验补丁。
  4. **完整性（v1）**：manifest 内 **SHA256** 校验（HTTPS + GitHub Release）；minisign 同钥验签为后续增强，非 v1 门禁。
  5. **应用**：只重启 sidecar，不关整个 App；IPC：`download` / `apply`（restart）/ `status`。
  6. **UX**：默认 **静默下载** → Settings 旁极小 **「更新已就绪」** → 确认后 apply；与全量 Update 并存时 **只显示全量**。`severity: critical|major` 进度 UI 可后置。
  7. **分发**：Release 资产 `sidecar-patch.json` + `orchestrator-darwin-aarch64`；客户端拉 `…/latest/download/sidecar-patch.json`（404=无补丁）。
- **影响**：`lib.rs` / `sidecar_patch.rs`、`sidecarPatch.ts`、`SidecarPatchReady`、`docs/UPDATES.md`、维护脚本。
- **决策状态**：`可执行`

### D38 · Stable Context Boundary：Code Decomposition Principles（2026-07-12）

- **背景**：项目中的 `main.py`（5118 行）、`design/service.py`（3959 行）、`clutchState.ts`（1212 行）等文件在 AI 辅助开发中频繁撑爆上下文，导致修改准确率下降。**目标不是减少文件行数，而是建立稳定的上下文边界（Stable Context Boundary），让 AI 与开发者在修改功能时只需加载最相关的模块，从而降低上下文噪音，提高修改准确率和长期可维护性。**
- **方案**：遵循以下 6 条原则进行文件拆分：

  1. **不以行数作为拆分标准。** 大文件不是问题，多职责才是问题。
  2. **One Reason to Change。** 一个模块只有一个稳定的变化原因。如果修改 A 不需要理解 B，就应该拆开。
  3. **Similar Change Rate。** 只有变化节奏不同的职责才值得拆。经常一起改的内容留在一起；很少一起改的分开。
  4. **保留编排层，拆实现层。** 允许编排层（如 `DesignService`）了解完整流程，但具体实现下放给独立模块。编排层只做协调，不做实现。
  5. **优先拆高频修改、跨团队影响大的模块。** 不改动的代码再大也不是瓶颈。
  6. **不为了拆而拆。** 如果多个职责具有相同的变化原因、相似的变化节奏，并且始终一起演进，则保持在同一模块。减少无意义的文件跳转。

- **优先级：**

  | 优先级 | 模块 | 原因 |
  |--------|------|------|
  | P0 | `design/service.py`（3959 行） | 高频修改、多职责、变化节奏不同 |
  | P0 | `main.py`（5118 行） | FastAPI 标准入口，路由职责边界清晰 |
  | P0 | `clutchState.ts`（1212 行） | 全局状态影响范围最大，容易增加上下文噪音 |
  | P1 | `DesignWorkspace.tsx`（2804 行） | 先拆 Hooks（逻辑），再拆 Nodes（展示） |
  | P2 | `App.tsx`（2569 行） | 保持启动流程清晰，避免过度抽象 |

- **执行方式：** 每次只拆一个文件，不改变业务逻辑。**完成标准：**
  - 原文件职责减少，形成明确边界
  - 对外 API 保持兼容
  - `pnpm build` 通过
  - `pnpm test` 通过
  - `pytest` 通过
  - Git Diff 主要为文件移动与引用调整，而非业务逻辑修改

  任何验证失败**立即回退**，不保留半完成状态。
- **影响**：降低 AI 辅助开发中每次加载的上下文噪音；提高修改准确率；团队有统一的拆分判断标准。
- **决策状态**：`已完成`

### D39 · Design 出码/交接唯一 SSOT = Path A（react/ + 门禁链）（2026-07-18）

- **背景**：Design 同时存在 Path A（`approve-prototype` → `generate-react` → Vite preview → `approve-react` → `send-to-coding`，产物 `react/`）与 Path B（PreviewDemo `/generate-code/write` → `generated/` + contract）。后端门禁完整但画布 UI 曾卸下托盘；PreviewDemo 旁路可写码却不进 Coding handoff，文档仍按「单一闭环」描述 → 产品正确性分叉。
- **方案**：
  1. **唯一 SSOT**：`react/` + 双 Approve 门禁链为正式出码/预览/交接路径；入口为 **Preview Demo → Coding**（画布底栏不放「UI code」），接通 `onSendToCoding`。
  2. **Contract 并入 Path A**：`generate_react` 读取 `interaction_contract.json`（若存在）注入导航约束；PreviewDemo「Generate Code」改为走 Path A API（必要时先 approve-prototype），不再以 `generated/` 为交接目录。
  3. **Path B 兼容**：`/generate-code/write` 委托 Path A（要求/自动对齐 `prototype_approved`），写入 `react/` 并更新 manifest；`generated/` 不再作为 handoff 目标。
  4. **非目标**：不接入 Google Stitch MCP / 云 projectId。
- **影响**：`PreviewDemo` Coding 入口 + `DesignHandoffTray`、`service.generate_react`、`router` generate-code、`PRODUCT_INTRO` §2.10–2.11、`DESIGN_WORKSPACE_GUIDE`。
- **决策状态**：`可执行`

### D40 · Design Spec 软确认关卡 + 流程纪律（2026-07-18；默认改关 2026-07-24）

- **背景**：对照 Stitch skills 后，Clutch Spec→UI 自动连跑会让坏 Spec 污染全部屏幕；iterate 模式偏启发式；brief 缺少结构化增强。产品 vibe 要求「监督而非黑盒」，不宜默认自治 baton。
- **方案**：
  1. **Spec 软确认（默认关）**：提示词后 Spec→UI **连跑**，不弹出确认按钮。需要人工审 Spec 时设 `CLUTCH_DESIGN_SPEC_CONFIRM=1`：Spec/`DESIGN.md` 写盘后 `status=awaiting_spec_confirm`，用户确认后再批量出 UI；`POST .../confirm-spec` 继续生成。
  2. **Brief 增强**：generate 前结构化 brief（platform / page structure / UI terms），不依赖外部云服务。
  3. **显式 iterate mode**：API/UI 声明 `modify|add|variant|revise_spec`，启发式仅兜底；默认 edit-over-regenerate。
  4. **多页 baton**：仅 opt-in，本轮不做默认自治 loop。
- **影响**：`generator.generate_session`、`confirm_spec`、`DesignWorkspace` Spec 确认 CTA、`designApi`、文档与测试 fixture。
- **决策状态**：`可执行`

### D41 · Generate UI code = 确定性保真出前端工程（禁 LLM 重画）（2026-07-20）

- **背景**：D39 Path A 曾用 LLM 将 Prototype HTML「翻译」为 TSX，预览与定稿 UI 不一致；产品目标是定稿+连线后前端 UI/导航基本完成，后续接后端与联调。
- **方案**：
  1. **`generate_react` 禁止 LLM 重画**：机械 HTML→JSX（`class`→`className` 等），保留 DOM 与 Tailwind class。
  2. **样式同源**：生成工程 `index.html` 使用与 Prototype 相同的 Tailwind CDN + 抽出的 `tailwind.config`；`<style>` 写入 `src/index.css`。
  3. **交互进源码**：`interaction_contract.json` 转为 React Router `<Link to="/…">`。
  4. **交付定义**：每屏真实 `.tsx` + Vite 可跑工程；Atomic 拆分非本门禁目标。Send to Coding 指令强调接 API、勿重设计。
- **影响**：`design/fidelity_export.py`、`service.generate_react`、Preview Demo Coding 托盘文案、`PRODUCT_INTRO` / `DESIGN_*`。
- **决策状态**：`可执行`

### D42 · Coding 发图 + 中间产物预览（2026-07-20；2026-07-24 修订）

- **背景**：Coding Chat/Terminal 需要粘贴图片给 Agent「看见」；CLI 输出中的文件名应可点开预览，体验接近 IDE。
- **方案**：
  1. **发图入口**：仅 Clutch 底栏（`ChatInputBar` / `OrchestratorBar`），不进 xterm。
     - **Chat → 云端/本地 Chat LLM**：先 multimodal 发图；仅当软拒绝视觉或 API 拒图时，再降级本地 OCR/调色板（Coding 专用 fragment，禁止 Design 调色板硬约束）。
     - **Chat → 本地 CLI（Mimo / Claude Code 等）**：把 `[image: data:…]` **落盘** `.clutch/attachments/`，prompt/history 注入 `@path` / `[file: path]`，让 CLI **自己读图**；禁止把 base64 塞进 argv。仅当 CLI 输出像视觉拒绝时，再降级 OCR。
     - **Terminal OrchestratorBar**：同样先落盘再注入路径（默认 `analyze=false`，不预塞 OCR）；发送中 Loading 防连按。附件目录自动 `.gitignore`=`*`；≥~100MB 时删 >3 天旧图。
  2. **预览**：共享 path helper + `GET /api/workspace/file/resolve`（精确 → basename 唯一模糊）；不追踪 xterm CWD。Chat fence/路径/`[file:]`/`@` 与 xterm `ILinkProvider`、派发 history 共用 resolve → `previewFile`；大内容 plain view。
- **影响**：`chat_content` / `chat_runner`、`workspace_attachments`、`OrchestratorBar`、`chatContentRender`、`TerminalLanePane`、`PRODUCT_INTRO`。
- **决策状态**：`已落地`

### D43 · Workspace id 路径稳定 + 防 clutch_dev 被测试污染（2026-07-24）

- **背景**：侧栏会话按 `workspace_id` 挂载；`workspaces.json` 曾用随机 uuid。列表被 e2e/临时目录授权或非原子写覆盖后，同路径重加得到新 id → 历史「消失」。桌面 E2E 曾未向 `tauri:e2e` 传入 `CLUTCH_STORAGE_DIR`。
- **方案**：
  1. **稳定 id**：`ws_` + `sha256(resolved_path)[:12]`；加载时把旧随机 id 迁到稳定 id，并 `remap_workspace_ids` 写回 `history.json`。
  2. **原子写**：`workspaces.json.tmp` → `os.replace`；损坏文件隔离为 `.corrupt`。
  3. **防污染**：默认 Application Support 存储拒绝 ephemeral/`tmp*` 授权（`CLUTCH_STORAGE_DIR` / `CLUTCH_E2E_SANDBOX` / `CLUTCH_ALLOW_TEMP_WORKSPACE=1` 可放行）；`run-e2e.sh` 桌面段传入 `CLUTCH_STORAGE_DIR`。
- **影响**：`workspace.py`、`run_history.remap_workspace_ids`、`scripts/run-e2e.sh`、`test_workspaces_api.py`。
- **决策状态**：`已落地`

### D44 · Chat Clutch Agent 能力补齐（适配 Grok · 不嵌 Rust）（2026-07-24）

- **背景**：Chat 模式自研 Clutch Agent（`agentType: clutch`）默认接近纯 LLM；手脚、Plan/Todo、自检、生命周期、MCP 绑定 UI、对话内「正在干嘛」等相对 Grok Build / 同类 Agent 缺口大。编排（SOP/LangGraph）在 Agent 之上，本决策只定 **Agent 本体**。
- **方案**：
  1. **适配不嵌入**：对齐 Grok 行为与工具语义，实现落在 Python `clutch-tools` + `mcp_react` + WS `ClutchState`；禁止 submodule/链入 `grok-build` Rust。
  2. **权威任务表**：[`specs/core/clutch-agent-capability-plan.md`](../specs/core/clutch-agent-capability-plan.md) 交付期 **D0–D53**（主线 D1–D13、扩展 D15–D36、MCP D37–D45、Chat UX D46–D52、**Prompt 分层 D53**；旁路 D14=可选 grok CLI）。本文交付期编号 **≠** DECISIONS Dx。
  3. **验收铁律**：每期须 PM 在 Chat 可见；缺对应前端交互不得标完成；用户可见行为同步 `PRODUCT_INTRO`。
  4. **首期**：交付表 D1（手脚）+ D37（MCP 绑定 UI）+ D46（实时步骤条）。
  5. **提示词（2026-07-24 补）**：**D53** — 运行时分层组装 + **渐进式披露**（system 底座 / env / 项目规则 / skills 目录按需全文 / mode reminder）；禁止把 `markdownDoc` 或整份 AGENTS.md 当作唯一 system。D7=发现内容，D53=组装架构。
  6. **Harness 纪律（2026-07-25 补）**：对齐 Grok Build「有工具就必须进循环」——按意图覆盖 network / workspace_read|write / git / shell；零 `tool_calls` 时注入族级 nudge 并以 `tool_choice=required` 重试一次（拒绝话术另走 generic）；目录诚实：偏好关闭时隐藏 `web_search` / `remember_preference`；`Allow network` 默认开。
  7. **联网停搜纪律（2026-07-25 补）**：对齐主流 Agent（ChatGPT/Perplexity/Cursor）「搜一次 → 抓 1–2 页 → 答」——`web_search`/`web_fetch` 软上限 3、硬上限 5；软上限注入 stop-search nudge；硬上限拒绝继续联网工具；禁止 `web_fetch` 搜索引擎 SERP；总步数 24 仍为写代码熔断，不充当联网预算。
- **影响**：`builtin_tools` / `agent_mcp` / `chat_runner` / `mcp_react` / `agent_prompt` / `tool_use_policy` / AgentManager MCP UI / ChatFeed 活动条；`ROADMAP` §Chat Clutch Agent。
- **决策状态**：`可执行`

### D54 · Chat 交付物目录与真实出图（2026-07-27）

- **背景**：Chat Agent 常把「信息图 / 图片」写成根目录 `.html`，并污染用户仓库根；业界常见做法是把 Agent 产出放进专用目录（Claude `.claude/`、agentic `_agentic_output/`），Clutch 已有 `.clutch/generated/videos`、attachments、handoffs。
- **方案**：
  1. **真实出图/出视频**：Chat 内置 `generate_image` / `generate_video`；回合结束 harness **自动调用**设置里已配置的 image/video 模型（如 Agnes），无需切换 footer 当前聊天模型；落盘 `.clutch/generated/images|videos/`；未配置 Key 时对话明确写「最后一步失败」。
  2. **禁 HTML 冒充**：intent=image/video/answer/code 时拒绝写 `.html`。
  3. **产物隔离**：Chat 研究/展示类新文件自动改写到 `.clutch/artifacts/`。
  4. **意图**：`infographic` / 信息图 / 可视化 → image。
- **影响**：`deliverable_intent` · `artifact_layout` · `media_deliverable` · `builtin_tools` · PRODUCT_INTRO。
- **决策状态**：`已落地`

### D45 · D7 项目规则 + Skills 对齐 Grok Build（2026-07-24）

- **背景**：能力期 D7；对照本地 `grok-build` 与 docs.x.ai project-rules。User 级规则（`~/.grok/AGENTS.md` 等）本期不做。
- **方案**：
  1. **Skills 开放 catalog**：Enabled 的 global∪project∪custom 自动进 skills 层；Agent `skills[]` 为可选强制包含；正文仅 `read_skill`。`isActiveGlobally`=Enabled（新发现默认 True；旧库全 False 时视为全开）。
  2. **同名 dedupe**：短名冲突时 **project > custom Mount > global**（Grok：local/repo > user）。
  3. **嵌套规则**：`git root → workspace_path` 串链注入 `AGENTS.md`/`CLAUDE.md` 等 + `.grok/.claude/.cursor/rules`；更深优先；无 User home 规则。
  4. **Custom SEARCH PATHS** 永不因换仓卸挂；仅 `auto_workspace_mounts` 轮换。
- **影响**：`agent_prompt`、`agent_skills`、`skills_storage`、`skills_scanner`；PRODUCT_INTRO / capability-plan D7。
- **决策状态**：`可执行`
