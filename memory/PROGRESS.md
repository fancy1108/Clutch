# PROGRESS

## 当前状态

- 阶段：**M0 核心完成 / M1 骨架启动**
- 说明：WebSocket `state_patch` 全链路打通；LangGraph 最小图 + `start_run` API 就绪
- 焦点：**M1-02** WorkflowCompiler 对接 `video-production.json`
- 上次更新：2026-06-22
- Git HEAD：见 `git log -1`

## 治理脚手架就绪标准（文档层 ✅）

- [x] Layer 1–3 治理文档 + Memory 六件套
- [x] 测试规范（D1/D2、TESTS、CI workflow、`verify.sh`）
- [x] Vibe 8.5 兜底（D7：Husky、漂移机检、truth-alignment 剧本、Layer 4 约束）
- [x] `specs/core/tasks.md`、`design.md`、`ROADMAP` 功能清单、`FILEMAP` 路径
- [x] 产品开放问题 Q1–Q4 → D3–D6 已决策

## 下次 Agent 启动必读

1. 读本文件（`PROGRESS.md`）
2. 读 `FAILURES.md`、`FILEMAP.md`、`DECISIONS.md`（D3–D8）、`specs/core/tasks.md`
3. 运行 `git log --oneline -10`
4. 运行 `./scripts/verify.sh`

## 待办（跨会话）

### 规范 / 运维（无代码）

- [x] **Push + CI**：remote `git@github.com:fancy1108/Clutch.git`，Actions CI #2 绿，`TESTS.md` 已更新
- [ ] **M0 后**：CI 与 `check-doc-drift.sh` 启用 `CLUTCH_STRICT_MOCK=1`（收紧 App.tsx setTimeout）

### 写代码阶段

- [x] **M0-01–03**：Sidecar health、WS ping-pong、`ClutchState` 投影
- [x] **M1 骨架**：LangGraph 最小图、`POST /api/runs/start`、`POST /api/runs/{id}/stop`
- [x] **M1-01**：Workflow JSON Schema 校验（`workflow_validator.py` + `/api/workflows/validate`）
- [ ] **M1-02**：WorkflowCompiler → LangGraph
- [ ] **M0-05**：Tauri 拉起 Sidecar
- [ ] **M2**：去 mock，Chat/Terminal 接真实事件

## 会话日志（最新在上）

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
