# Archive Notice

This file is archived and read-only.

Do not append new records here.

For current project state, see:

- memory/PROGRESS.md
- memory/DELIVERABLES.md
- memory/ROADMAP.md

Archived on: 2026-06-29
Reason: milestone M0 completed

---

# DELIVERABLES Archive — M0

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

### M0-06 ✅
