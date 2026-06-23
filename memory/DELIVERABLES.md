# DELIVERABLES（Task 交付索引）

> **角色：** Task ID → Git commit → Verification → 证据路径。**不复制** `git diff`（代码真相在 Git）。  
> **何时写：** 每个**代码 Task** 完成并 commit 后，在 Check-out 追加一节（见 `CLAUDE.md` §Check-out）。  
> **逐文件 diff：** `git show <commit> --stat` / `git show <commit>`

## 填写模板（复制后改）

```markdown
### <Task-ID> ✅ | ⚠️ 部分 | ❌ 回滚
- **日期：** YYYY-MM-DD
- **Commit：** `<hash>` — `<git log -1 --format=%s>`
- **Verification：** `<命令>` → `<结果摘要>`
- **证据：** `runs/verification/<date>-<task-id>.log` 或 [CI #N](url) 或 `—`（门禁已覆盖）
- **交付文件：**（一行一个，只写路径 + 一句话职责；详情 `git show`）
  - `path/to/file` — …
```

**重定向示例（代码 Task 推荐）：**

```bash
cd services/orchestrator && uv run pytest tests/test_xxx.py -v \
  | tee "../../runs/verification/$(date +%Y-%m-%d)-M1-02-pytest.log"
```

---

## 已交付（代码 Task · 自 Git 回填）

### M0-01 ✅
- **日期：** 2026-06-22
- **Commit：** `56dd9e9` — feat(orchestrator): add basic FastAPI and WebSocket endpoint（health 初版见 `4aefaac`）
- **Verification：** `uv run pytest tests/test_health.py -v`
- **证据：** `memory/TESTS.md` 2026-06-22 后端测试行；无独立 log 文件（回填前未归档）
- **交付文件：** `git show 56dd9e9 --stat`
  - `services/orchestrator/src/main.py` — `/health`、CORS、WS 端点骨架
  - （`test_health.py` 初版在 `4aefaac` bootstrap）

### M0-02 ✅
- **日期：** 2026-06-22
- **Commit：** `b600acc` — feat(desktop): wire WebSocket ping-pong test for M0-02
- **Verification：** `uv run pytest tests/test_ws_state_patch.py -v`（WS 全链路在 M0-03 commit 补强）
- **证据：** 同上；`test_ws_state_patch.py` 在 `42f9423` 完善
- **交付文件：**
  - `apps/desktop/src/services/api.ts` — Sidecar WS 测试发送
  - `apps/desktop/src/sidebar.tsx` — [Test WS] 按钮

### M0-03 ✅
- **日期：** 2026-06-22
- **Commit：** `42f9423` — feat(m0): project ClutchState from WebSocket state_patch
- **Verification：** `pnpm build`；`uv run pytest tests/test_ws_state_patch.py -v`
- **证据：** `memory/TESTS.md`；`ROADMAP` E2E 前提第一行 ✅
- **交付文件：**
  - `apps/desktop/src/services/clutchState.ts` — `useClutchState` / WS store
  - `apps/desktop/src/App.tsx` — 投影 `ClutchState`；移除 mock 驱动编排
  - `packages/shared-types/index.ts` — 共享 `ClutchState` 类型
  - `services/orchestrator/src/state.py` — Python 侧状态
  - `services/orchestrator/src/main.py` — `state_patch` 推送
  - `services/orchestrator/tests/test_ws_state_patch.py` — WS 集成测试

### M0-04 ✅
- **日期：** 2026-06-22（bootstrap，无独立 feat commit）
- **Commit：** `4aefaac` — chore: bootstrap project governance structure
- **Verification：** `pnpm dev` + `curl -s http://127.0.0.1:8123/health`
- **证据：** `—`（手动验证，未归档 log）
- **交付文件：**
  - `apps/desktop/vite.config.ts` — `/api`、`/ws` 代理 → 8123

### M0-06 ⚠️ 部分（待复审）
- **日期：** 2026-06-22
- **Commit：** `42f9423`（与 M0-03 同提交）
- **Verification：** 待跑 `packages/shared-types` ↔ `state.py` 字段人工 diff + `pnpm build`
- **证据：** —
- **备注：** 类型已引入，**未**按 `tasks.md` M0-06 完成「对齐复审」

### M1-03 ⚠️ 骨架（待 Verification 复审）
- **日期：** 2026-06-22
- **Commit：** `f45172c` — feat(m1): add minimal LangGraph runtime and start_run API
- **Verification：** `uv run pytest tests/test_start_run.py tests/test_graph.py -v` — **仅**断言 `run_id` / 桩图 `n1`，未接 Compiler
- **证据：** `memory/TESTS.md` 7 passed → 15 passed（M1-01 后）
- **交付文件：**
  - `services/orchestrator/src/graph.py` — 最小 LangGraph（START→orchestrator→END）
  - `services/orchestrator/src/main.py` — `POST /api/runs/start`、`/stop`
  - `services/orchestrator/tests/test_start_run.py` — API smoke
  - `services/orchestrator/tests/test_graph.py` — 桩图节点断言

### M1-01 ✅
- **日期：** 2026-06-22
- **Commit：** `5367020` — feat(m1): add workflow JSON schema validation (M1-01)
- **Verification：** `uv run pytest tests/test_workflow_validator.py tests/test_validate_api.py -v` → 15 passed 总计
- **证据：** `memory/TESTS.md`；[CI #2](https://github.com/fancy1108/Clutch/actions)（`11e6d77` 前后）
- **交付文件：**
  - `services/orchestrator/src/workflow_validator.py` — 加载与校验 `workflows/*.json`
  - `services/orchestrator/src/main.py` — `POST /api/workflows/validate`；`start_run` 前置校验
  - `services/orchestrator/tests/test_workflow_validator.py` — Schema / video-production 用例
  - `services/orchestrator/tests/test_validate_api.py` — HTTP API 用例
  - `workflows/workflow.schema.json` — schema 小改

### M1-02 ✅
- **日期：** 2026-06-23
- **Commit：** `ea5e648` — feat(m1): add WorkflowCompiler for video-production JSON (M1-02)
- **Verification：** `uv run pytest tests/test_compiler.py -v` → 6 passed；`./scripts/verify.sh` → 21 passed
- **证据：** `runs/verification/2026-06-23-m1-02-compiler-pytest.log`
- **交付文件：**
  - `services/orchestrator/src/compiler/__init__.py` — 导出 WorkflowCompiler API
  - `services/orchestrator/src/compiler/compiler.py` — JSON → LangGraph 编译、五类 handler、条件边
  - `services/orchestrator/tests/test_compiler.py` — 节点/边/类型与 video-production.json 一致

---

## 文档 / 治理（非代码 Task）

| 会话 | 状态 | 说明 |
|------|------|------|
| 会话 8–10（2026-06-23） | ✅ `0a24a7b` | `tasks.md`、`ROADMAP`、`DELIVERABLES`、Check-out 规则、`ARCHITECTURE` §7/§13 |
| D7 验收兜底 | ✅ `cba4094` | `check-doc-drift.sh`、Husky、truth-alignment |
| D1/D2 测试治理 | ✅ 多 commit | `verify.sh`、`.github/workflows/ci.yml` |

### M1-03 ✅
- **日期：** 2026-06-23
- **Commit：** `3c45ad0` — feat(m1): wire start_run to WorkflowCompiler (M1-03)
- **Verification：** `uv run pytest tests/test_start_run.py -v` → 3 passed；`./scripts/verify.sh` → 22 passed
- **证据：** `runs/verification/2026-06-23-m1-03-start-run-pytest.log`
- **交付文件：**
  - `services/orchestrator/src/compiler/compiler.py` — 新增 `run_workflow`
  - `services/orchestrator/src/main.py` — `start_run` 改走编译图
  - `services/orchestrator/tests/test_start_run.py` — `active_node_id` 变化断言

---

## 待交付（下一 Task）

| Task | 焦点 |
|------|------|
| **M1-04** | Orchestrator 路由节点 + `test_orchestrator_routing.py` |
| **M0-05** | `src-tauri/` Sidecar 生命周期 |
| **M0-06** | 类型对齐复审结论写入本节 |
