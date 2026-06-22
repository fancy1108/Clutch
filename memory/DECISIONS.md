# DECISIONS（决策记录与开放问题）

> 格式：**日期 · 背景 · 方案 · 影响 · 落地前提 · 决策状态**  
> 本项目**唯一**的开放问题 / 待决策事项汇总地。禁止在其他文档另开新的开放问题列表。
>
> **决策状态：** `已记录`（原则已定，前提未满足）→ `可执行`（可动手实现）→ `已落地`（目录/CI/代码已存在）

## 已记录决策

### D1 · E2E 测试范围与目录（2026-06-22）

- **背景**：E2E 若测 mock 编排，与「React 只投影 WebSocket ClutchState、禁止 mock 模拟编排」红线冲突；且需跨 Sidecar + UI 两进程，本质是跨包集成测试。
- **方案**：
  - 范围：全链路集成测试，禁止 mock 编排逻辑
  - 目录：顶层 `e2e/`（Playwright），**不**放在 `apps/desktop/`
  - 分级：Smoke（M0 后，health + WS `state_patch`）→ 闭环（M2–M3 后，对齐 proposal §10.1 MVP）
- **影响**：未来 E2E 依赖、CI job、TESTS.md 门禁均按此执行；`memory/ROADMAP.md` 前提行与 D1 联动。
- **落地前提**（未满足前**禁止**建 `e2e/` 或安装 Playwright）：
  1. M0：前端收到真实 `state_patch`（proposal §10.2）
  2. M2：去除 mock，Terminal / Chat 为真数据
- **建议落地阶段**：M2 完成后启动 `e2e/` 包；Smoke 用例可在 M0 后首条添加，闭环用例对齐 M3。
- **决策状态**：`已记录`

### D2 · CI 门禁范围（2026-06-22）

- **背景**：无 CI 时测试报告仅存在于本地，协作中不可追溯；当前已有 `pnpm build` 与 `uv run pytest`，成本最低。
- **方案**：GitHub Actions 跑 `pnpm build` + `uv run pytest`；报告产物上传为 workflow artifacts（coverage 等后续再加）。
- **影响**：`.github/workflows/ci.yml`；TESTS.md 增 CI 行；**不**将 `pnpm test` 纳入 commit 门禁直至前端有真实用例（见 D1 同类原则：禁止形式完整掩盖实质空白）。
- **落地前提**：无（可立即执行）。
- **决策状态**：`已落地`

**D2 遗留待办：**

- [ ] Push 后确认 GitHub Actions 首次绿，更新 `TESTS.md` CI 行
- [ ] 有覆盖率需求时：pytest-cov / vitest coverage + CI artifacts 上传

### D3 · 运行历史纳入 MVP（2026-06-22）

- **背景**：Q1 指**运行历史**（过往 `run_id`、工作流、状态、时间等可回溯记录），不是单指 Terminal 实时日志；用户需要用于**排查问题**。
- **方案**：MVP 纳入运行历史；侧栏可查看历史运行列表；与单次运行的 Terminal 审计日志（`log` 事件）互补。
- **影响**：`tasks.md` §M2 增任务；`sidebar.tsx` 接历史 API；Sidecar 本地持久化（SQLite 或等价方案，M2 实现时定）。
- **落地前提**：M2 监督台去 mock 阶段。
- **决策状态**：`已记录`（原 Q1 关闭）

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

## 开放问题

（暂无 — 原 Q1–Q4 已于 2026-06-22 关闭，见 D3–D6。）
