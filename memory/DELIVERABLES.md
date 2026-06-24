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
  - `apps/desktop/src/services/api.ts` — Sidecar WS 测试发送（`sendSidecarTestMessage`，已于 `2d85c14` 移除）
  - `apps/desktop/src/sidebar.tsx` — ~~[Test WS] 调试按钮~~（M0 联调用；`2d85c14` 移除，用户改由主聊天 `submitChatMessage`）

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

### M1-04 ✅
- **日期：** 2026-06-23
- **Commit：** `dc904dc` — feat(m1): add orchestrator edge-first routing with LLM fallback (M1-04)
- **Verification：** `uv run pytest tests/test_orchestrator_routing.py -v` → 7 passed；`./scripts/verify.sh` → 29 passed
- **证据：** `runs/verification/2026-06-23-m1-04-routing-pytest.log`
- **交付文件：**
  - `services/orchestrator/src/orchestrator/routing.py` — 边优先路由 + LLM 兜底
  - `services/orchestrator/src/compiler/compiler.py` — 条件边改走 `route_next`
  - `services/orchestrator/tests/test_orchestrator_routing.py` — 路由单元测试

### M1-05 ✅
- **日期：** 2026-06-23
- **Commit：** `1dadde3` — feat(m1): push run_completed over WebSocket on terminal status (M1-05)
- **Verification：** `uv run pytest tests/test_run_completed.py -v` → 3 passed；`./scripts/verify.sh` → 32 passed
- **证据：** `runs/verification/2026-06-23-m1-05-run-completed-pytest.log`
- **交付文件：**
  - `services/orchestrator/src/main.py` — `run_completed` 事件与 `ClutchState` 序列化
  - `services/orchestrator/tests/test_run_completed.py` — passed/failed 终态 WS 推送

### M1-08 ✅
- **日期：** 2026-06-23
- **Commit：** `63e1bde` — feat(m1): add LLM Provider Router with DeepSeek default (M1-08)
- **Verification：** `uv run pytest tests/test_llm_provider.py -v` → 7 passed；`./scripts/verify.sh` → 39 passed
- **证据：** `runs/verification/2026-06-23-m1-08-llm-provider-pytest.log`
- **交付文件：**
  - `services/orchestrator/src/llm/router.py` — Provider 抽象、默认 DeepSeek V4 Pro、可切换、按 Provider 分存 Key
  - `services/orchestrator/src/llm/__init__.py` — 包导出
  - `services/orchestrator/tests/test_llm_provider.py` — Router 与 orchestrator 路由集成测试

### M1-09 ✅
- **日期：** 2026-06-23
- **Commit：** `7048999` — feat(m1): add user workflow persistence API (M1-09)
- **Verification：** `uv run pytest tests/test_workflow_storage.py -v` → 5 passed；`./scripts/verify.sh` → 44 passed
- **证据：** `runs/verification/2026-06-23-m1-09-workflow-storage-pytest.log`
- **交付文件：**
  - `services/orchestrator/src/workflow_storage.py` — D5 内置模板只读 + 用户目录 CRUD
  - `services/orchestrator/src/main.py` — `/api/workflows/templates|user` 路由；`start_run` 走 `resolve_workflow`
  - `services/orchestrator/tests/test_workflow_storage.py` — 路径与 CRUD 集成测试

### M0-06 ✅
- **日期：** 2026-06-23
- **Commit：** 文档 commit — ClutchState 字段对齐复审
- **Verification：** 人工 diff `packages/shared-types/index.ts` ↔ `services/orchestrator/src/state.py`；`pnpm build` 无类型错误
- **证据：** 本节字段对照表；`./scripts/verify.sh` 通过
- **结论：** 9 个 `ClutchState` 字段与 `ClutchRunStatus` 枚举一致，无需代码变更

### M1-07 ✅
- **日期：** 2026-06-23
- **Commit：** `b6584ef` — feat(m1): add workflow graph structure validation (M1-07)
- **Verification：** `uv run pytest tests/test_workflow_validator.py -k invalid -v` → 4 passed；`./scripts/verify.sh` → 47 passed
- **证据：** `runs/verification/`（verify.sh 全量）
- **交付文件：**
  - `services/orchestrator/src/workflow_validator.py` — `validate_workflow_graph` 中文图结构错误
  - `services/orchestrator/tests/test_workflow_validator.py` — 缺 start/end、孤立节点用例

---

## 待交付（下一 Task）

| Task | 焦点 | 状态 |
|------|------|------|
| **P2-03** | Theme 持久化 | 下一 |
| **P2-03** | Theme 持久化 | 待做 |
| **P2-04** | i18n 双语验收 | 待做 |
| **P2-05** | 侧栏 REPOSITORIES CRUD | 待做 |
| **P2-06** | General Settings | 待做 |
| **T-04** | 红队 / 体感审计 | 可选 |

### P2-01 ✅
- **日期：** 2026-06-24
- **Commit：** `a8bc6af` — feat(skills): add Sidecar skills registry with SKILL.md scanning (P2-01)
- **Verification：** `uv run pytest tests/test_skills_registry.py -v` → 3 passed；`./scripts/verify.sh` → 104 pytest + 7 Playwright
- **证据：** `runs/verification/2026-06-24-p2-01-skills-pytest.log`、`runs/verification/2026-06-24-p2-01-verify.log`
- **交付文件：**
  - `services/orchestrator/src/skills_storage.py` — Application Support 持久化
  - `services/orchestrator/src/skills_scanner.py` — `SKILL.md` 递归扫描
  - `services/orchestrator/src/main.py` — `/api/skills/*`
  - `services/orchestrator/tests/test_skills_registry.py` — P2-01 门禁
  - `apps/desktop/src/services/skillsApi.ts` — 前端 API 客户端
  - `apps/desktop/src/components/SkillsRegistry.tsx` — 去 localStorage，接 Sidecar
  - `apps/desktop/src/components/AgentManager.tsx` — Skills 从 Sidecar 同步
  - `memory/DECISIONS.md` D13 — P2 任务拆解

### P2-02 ✅
- **日期：** 2026-06-24
- **Commit：** （见本次 commit）
- **Verification：** `uv run pytest tests/test_mcp_registry.py -v` → 3 passed；`pnpm build` ✅
- **证据：** `runs/verification/`（pytest 本地）
- **交付文件：**
  - `services/orchestrator/src/mcp_storage.py` — MCP 服务器持久化 + status 聚合
  - `services/orchestrator/src/main.py` — `/api/mcp/servers/*`、增强 `/api/mcp/status`
  - `services/orchestrator/tests/test_mcp_registry.py` — P2-02 门禁
  - `apps/desktop/src/services/mcpApi.ts` — 前端 MCP API
  - `apps/desktop/src/components/McpServerHub.tsx` — 注册 / 启用 / 删除 UI

### cf342c6 — M2–M4 批量 ✅
- **日期：** 2026-06-23
- **Commit：** `cf342c6` — feat(m2-m4): complete supervision desk, toolchain, and release polish
- **Verification：** `./scripts/verify.sh` → 67 pytest + build + vitest + drift
- **证据：** 会话 19 verify 输出
- **交付文件：** `git show cf342c6 --stat`

### M4-04 + T-03 + M4-06 ✅
- **日期：** 2026-06-23
- **Commit：** `c1b16cf` — feat(mvp): Claude Code credentials, human-decision API, and T-03 closed-loop E2E
- **Verification：** `./scripts/verify.sh` → 70 pytest + 3 E2E；`apps/desktop` `pnpm tauri build`
- **证据：** `runs/verification/2026-06-23-e2e-smoke.log`、`runs/verification/2026-06-23-tauri-build.log`
- **交付文件：**
  - `services/orchestrator/src/credentials/claude_code.py` — 读取 Claude Code CLI `ANTHROPIC_AUTH_TOKEN`
  - `services/orchestrator/src/main.py` — `POST /api/runs/{id}/human-decision`、`GET /api/models/credentials`
  - `e2e/tests/mvp-closed-loop.spec.ts` — T-03 Playwright
  - `services/orchestrator/tests/test_mvp_closed_loop.py` — T-03 API

### UI 清理 — 移除 M0 [Test WS] 调试按钮 ✅
- **日期：** 2026-06-23
- **Commit：** `2d85c14` — fix(desktop): remove M0 WebSocket debug button from sidebar
- **Verification：** `2d85c14` pre-commit：`./scripts/verify.sh` → build + 73 pytest + 3 E2E + drift ✅
- **证据：** commit hook 输出（`2d85c14`）；Check-out 时工作区 WIP 致 pytest 收集失败，与本次变更无关
- **交付文件：** `git show 2d85c14 --stat`
  - `apps/desktop/src/sidebar.tsx` — 移除侧栏 `[Test WS]` 按钮
  - `apps/desktop/src/services/clutchState.ts` — 删除 `sendSidecarTestMessage`
  - `apps/desktop/src/services/api.ts` — 移除对应 export
  - `scripts/run-e2e.sh` — E2E 门禁（自动起 Sidecar）

### D11 · 会话消息持久化 + 历史 hydrate ✅
- **日期：** 2026-06-23
- **Commit：** `9e509c3`
- **Verification：** `./scripts/verify.sh` → 101 pytest + 7 Playwright ✅
- **证据：** `runs/verification/2026-06-23-e2e-full.log`
- **交付文件：**
  - `services/orchestrator/src/run_state_store.py` — `states/{run_id}.json` 读写
  - `services/orchestrator/src/main.py` — `_commit_run_state` / `_get_or_create_run` 磁盘加载
  - `services/orchestrator/tests/test_run_state_store.py` — 持久化 + plain chat 落盘
  - `services/orchestrator/tests/conftest.py` — 全量测试隔离 `CLUTCH_RUN_HISTORY_DIR`
  - `services/orchestrator/src/models_config.py` — `CLUTCH_E2E_FAKE_LLM` Echo 路由
  - `apps/desktop/src/services/runApi.ts` — `fetchRunState`
  - `apps/desktop/src/services/clutchState.ts` — `setPendingHydrate`、WS 切换修复
  - `apps/desktop/src/App.tsx` — `handleSelectSession` hydrate
  - `apps/desktop/src/sidebar.tsx` — `data-testid="sidebar-session-{run_id}"`
  - `e2e/tests/session-history.spec.ts` — API：plain chat → GET state（Node WS）
  - `e2e/tests/desktop/session-history.spec.ts` — 桌面：侧栏点选恢复对话（待绿）
  - `scripts/e2e-sandbox-setup.sh` — `CLUTCH_E2E_FAKE_LLM=1`
  - `docs/ARCHITECTURE.md` §6.3.1 — 持久化叙事
  - `memory/DECISIONS.md` D11；`specs/core/tasks.md` M2-07 / M2-10 更新

### D12 · 桌面 E2E 全链路（tauri-playwright）✅
- **日期：** 2026-06-23
- **Commit：** `9e509c3`
- **Verification：** `./scripts/verify.sh` → **7/7 Playwright** + 101 pytest ✅
- **证据：** `runs/verification/2026-06-23-e2e-full.log`；`e2e/test-results/desktop-*/`
- **已交付（代码在工作区）：**
  - `apps/desktop/src-tauri/` — `e2e-testing` feature、`tauri-plugin-playwright`、`clutch_e2e_sandbox`、`spawn_dev_sidecar` 转发 `CLUTCH_*`
  - `apps/desktop/package.json` — `tauri:e2e`
  - `e2e/playwright.config.ts` — `api` + `desktop`（`mode: 'tauri'`）projects
  - `e2e/helpers/ws.ts`、`tauri.ts`、`seed.ts`
  - `e2e/fixtures/desktop.ts`、`e2e/tests/desktop/all-ui.spec.ts`
  - `scripts/run-e2e.sh` — API → 杀端口 → Tauri → `wait_tauri_ready` → Desktop
  - UI：`data-testid`、Branch 菜单、Terminal Clear 去占位
- **待完成：**（无 — 2026-06-23 门禁全绿）
