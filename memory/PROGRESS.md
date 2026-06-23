# PROGRESS

## 当前状态

- 阶段：**M0 核心完成 / M1 骨架启动**
- 说明：WebSocket `state_patch` 全链路打通；LangGraph 最小图 + `start_run` API 就绪
- 焦点：**M0-05** / **M1-06**（阻塞见 `FAILURES.md`）
- Git HEAD：`b6584ef`（M1-07）

## 治理脚手架就绪标准（文档层 ✅）

- [x] Layer 1–3 治理文档 + Memory 六件套
- [x] 测试规范（D1/D2、TESTS、CI workflow、`verify.sh`）
- [x] Vibe 8.5 兜底（D7：Husky、漂移机检、truth-alignment 剧本、Layer 4 约束）
- [x] Task 交付索引（`DELIVERABLES.md` + Check-out 规则 + `runs/verification/README`）
- [x] 产品开放问题 Q1–Q4 → D3–D6 已决策

## 下次 Agent 启动必读

1. 读本文件（`PROGRESS.md`）
2. 读 `FAILURES.md`、`FILEMAP.md`、`DECISIONS.md`（D3–D8）、`specs/core/tasks.md`；续作时扫一眼 `DELIVERABLES.md` 最后交付 commit
3. 运行 `git log --oneline -10`
4. 运行 `./scripts/verify.sh`

## 待办（跨会话）

### 规范 / 运维（无代码）

- [x] **Push + CI**：remote `git@github.com:fancy1108/Clutch.git`，Actions CI #2 绿，`TESTS.md` 已更新
- [ ] **M0 后**：CI 与 `check-doc-drift.sh` 启用 `CLUTCH_STRICT_MOCK=1`（收紧 App.tsx setTimeout）

### 写代码阶段

- [x] **M0-01–03**：Sidecar health、WS ping-pong、`ClutchState` 投影
- [x] **M0-04**：Vite 代理（`pnpm dev` 可连 Sidecar）
- [x] **M1 骨架**：LangGraph 最小图、`POST /api/runs/start`、`POST /api/runs/{id}/stop`
- [x] **M1-01**：Workflow JSON Schema 校验（`workflow_validator.py` + `/api/workflows/validate`）
- [x] **M1-02**：WorkflowCompiler → LangGraph + `tests/test_compiler.py`
- [x] **M1-03**：`start_run` 对接 WorkflowCompiler + `test_start_run` 增强断言
- [x] **M1-04**：Orchestrator 路由（边优先、LLM 兜底）+ `test_orchestrator_routing.py`
- [x] **M1-05**：`run_completed` WS 推送 + `test_run_completed.py`
- [ ] **M0-05**：Tauri 拉起 Sidecar — `[OPEN]` 无 Rust
- [x] **M0-06**：`ClutchState` 类型对齐复审
- [x] **M1-07**：图结构保存前校验
- [ ] **M1-06**：工作流编辑器保存/加载 — `[OPEN]` UI↔JSON 映射未定
- [x] **M1-08**：LLM Provider Router + `test_llm_provider.py`
- [x] **M1-09**：用户工作流持久化 API + `test_workflow_storage.py`
- [ ] **M2**：M2-01–14（见 `tasks.md` §M2）

## 会话日志（最新在上）

### 2026-06-23 会话 16（M1-09 / M1-07 / M0-06）

- 完成：M1-09 用户工作流 CRUD API（5 tests）；M1-07 图结构中文校验（+3 tests）；M0-06 类型对齐复审 ✅
- 阻塞：M0-05（无 Rust）；M1-06（WorkflowDef vs compiler JSON）→ `FAILURES.md`
- 证据：`runs/verification/2026-06-23-m1-09-workflow-storage-pytest.log`；verify.sh 47 passed
- 下次优先：解除 M0-05 / M1-06 阻塞后 → M2-01

### 2026-06-23 会话 15（M1-08 LLM Provider Router）

- 完成：`src/llm/router.py`（Provider 抽象、默认 DeepSeek V4 Pro、可切换、按 Provider 分存 API Key）；`test_llm_provider.py` 7 passed；`verify.sh` 39 passed
- 证据：`runs/verification/2026-06-23-m1-08-llm-provider-pytest.log`
- 下次优先：**M1-09** 或 **M0-05**

### 2026-06-23 会话 14（M1-05 run_completed）

- 完成：终态 `passed`/`failed` 经 WS 推送 `run_completed`（含完整 `ClutchState`）；`test_run_completed.py` 3 passed；`verify.sh` 32 passed
- 证据：`runs/verification/2026-06-23-m1-05-run-completed-pytest.log`
- 下次优先：**M1-08** 或 **M0-05**

### 2026-06-23 会话 13（M1-04 Orchestrator 路由）

- 完成：`src/orchestrator/routing.py`（边优先、LLM 兜底）；compiler 接入；`test_orchestrator_routing.py` 7 passed；`verify.sh` 29 passed
- 证据：`runs/verification/2026-06-23-m1-04-routing-pytest.log`
- 下次优先：**M1-05** `run_completed`

### 2026-06-23 会话 12（M1-03 start_run 对接编译图）

- 完成：`start_run` 改走 `run_workflow`；`test_start_run` 增 `active_node_id` 断言；`verify.sh` 22 passed
- 证据：`runs/verification/2026-06-23-m1-03-start-run-pytest.log`
- 下次优先：**M1-04** Orchestrator 路由节点

### 2026-06-23 会话 11（M1-02 WorkflowCompiler）

- 完成：`src/compiler/`（五类节点 handler + 条件边）；`tests/test_compiler.py` 6 passed；`verify.sh` 21 passed
- 证据：`runs/verification/2026-06-23-m1-02-compiler-pytest.log`
- 遗留：`start_run` 仍走 `run_minimal_graph`（M1-03 对接编译图）
- 下次优先：**M1-03** 编译图执行 + `test_start_run` 增强断言

### 2026-06-23 会话 10（DELIVERABLES 交付索引）

- 完成：新建 `memory/DELIVERABLES.md`；回填 M0-01~M1-01；`CLAUDE.md` Check-out、`tasks.md`、`FILEMAP`、`TESTS` 联动；`runs/verification/README.md`
- 标注：M0-06 / M1-03 ⚠️ 待复审
- 下次优先：**M1-02**；完成后按模板写入 `DELIVERABLES.md` + 可选 pytest log

### 2026-06-23 会话 9（Prototype 全覆盖审计）

- 完成：对照 `apps/desktop/src` 补 task M2-11~14、M4-09；`tasks.md` §Prototype → Task 映射；`ROADMAP` / `ARCHITECTURE` §7 / `FILEMAP` 对齐
- 结论：Prototype 所有 MVP 能力均有 task；i18n / 主题 / Skills / 单 Agent / 侧栏文件夹 CRUD 明确标 P2
- 下次优先：**M1-02** WorkflowCompiler + `test_compiler.py`

### 2026-06-23 会话 8（tasks 验收补强 + 文档同步）

- 完成：`tasks.md` 增补 Verification 列与新 task（M1-08/09、M2-08~10、M3-07、M4-08、T-01~04）；`ROADMAP` / `PROGRESS` / `TESTS` / `FILEMAP` / `ARCHITECTURE` §13 对齐
- 遗留：M1-03 骨架未按新 Verification 复审；待建 pytest 文件均未创建
- 下次优先：**M1-02** WorkflowCompiler + `test_compiler.py`（Red 阶段）

### 2026-06-22 会话 7（M1-01 Schema 校验）

- 完成：`workflow_validator.py`、`POST /api/workflows/validate`、`start_run` 前置校验；15 pytest 绿
- 下次优先：**M1-02** WorkflowCompiler

### 2026-06-22 会话 6（M0-03 + M1 骨架）

- 完成：`ClutchState` 共享类型、WS `state_patch`、`useClutchState` store、LangGraph 最小图、`start_run`/`stop_run` API；7 pytest 绿
- 下次优先：**M1-01** Schema 校验 + WorkflowCompiler

### 2026-06-22 会话 5（Push + CI 绿）

- 完成：SSH push、pnpm 版本冲突修复（`11e6d77`）、CI #2 绿、`TESTS.md` / `PROGRESS` 更新
- 下次优先：**M0-01**

### 2026-06-22 会话 4（Vibe 8.5 验收期真相对齐）

- 完成：D7/D8；`check-doc-drift.sh`、Husky pre-commit、truth-alignment 剧本、`CLAUDE.md` Layer 4 约束与按需路由、FILEMAP/TESTS/CI 更新
- 下次优先：**M0-01** 或 Push 验证 CI

### 2026-06-22 会话 3（决策关闭 + 表述修正）

- 完成：D3–D6（Q1–Q4）；`PROGRESS` 改为「治理脚手架就绪」，避免「规范封板」误解
- 下次优先：**M0-01** 或 Push 验证 CI

### 2026-06-22 会话 2（第 6 步 · 任务拆解）

- 完成：`tasks.md`、`design.md`、ROADMAP、FILEMAP

### 2026-06-22 会话 1（测试治理）

- 完成：D1/D2、CI、`verify.sh`

### 2026-06-22 会话 0（Initializer）

- 完成：Pro 级 Agent OS 脚手架
