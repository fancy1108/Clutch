# PROGRESS

## 当前状态

- 阶段：**M0–M4 MVP 验收形态就绪**
- 说明：Claude Code CLI 凭证自动导入、`POST /api/runs/{id}/human-decision`、T-03 MVP 闭环 E2E、`verify.sh` 含 E2E 门禁；73 pytest + 3 Playwright 绿
- 焦点：用户本机验收 DMG；工作区多项目 WIP（未提交）；可选 push 触发 CI
- Git HEAD：`2d85c14`（+ 工作区未提交改动）

## 治理脚手架就绪标准（文档层 ✅）

- [x] Layer 1–3 治理文档 + Memory 六件套
- [x] 测试规范（D1/D2、TESTS、CI workflow、`verify.sh` + `run-e2e.sh`）
- [x] Vibe 8.5 兜底（D7：Husky、漂移机检、truth-alignment 剧本、Layer 4 约束）
- [x] Task 交付索引（`DELIVERABLES.md` + Check-out 规则 + `runs/verification/README`）
- [x] 产品开放问题 Q1–Q4 → D3–D6 已决策

## 下次 Agent 启动必读

1. 读本文件（`PROGRESS.md`）
2. 读 `FAILURES.md`、`FILEMAP.md`、`DECISIONS.md`（D3–D8）、`specs/core/tasks.md`
3. 运行 `git log --oneline -10`
4. 运行 `./scripts/verify.sh`

## 待办（跨会话）

- [x] **M0–M4**：MVP 任务清单（P2 Skills 延后；单 Agent 不开发见 D10）
- [x] **M4-06**：`pnpm tauri build` → DMG 证据 `runs/verification/2026-06-23-tauri-build.log`
- [x] **T-03**：MVP 闭环 E2E + `test_mvp_closed_loop.py`
- [ ] **T-04**：红队 / 体感审计（可选）
- [ ] Push 至 `origin` 触发 CI

## 会话日志（最新在上）

### 2026-06-23 会话 21（移除 [Test WS] 调试 UI）

- 完成：识别侧栏 `[Test WS]` 为 M0-02 开发联调遗留；移除按钮与 `sendSidecarTestMessage`；同步 `DELIVERABLES` / `tasks.md` / `PROGRESS`
- 校验：`2d85c14` pre-commit `verify.sh` ✅；Check-out 时 WIP `main.py:133` SyntaxError 致 pytest 失败（与本次无关）
- Commit：`2d85c14`
- 下次优先：继续工作区多项目 WIP 并提交；用户 DMG 验收；push CI

### 2026-06-23 会话 20（MVP 验收收尾）

- 完成：Claude Code 凭证 `credentials/claude_code.py`；`human-decision` HTTP；T-03 Playwright + pytest；`run-e2e.sh` 接入 `verify.sh`
- 校验：`./scripts/verify.sh` → build + vitest + 70 pytest + drift + 3 E2E ✅；`apps/desktop` `pnpm tauri build` → DMG ✅
- 下次优先：用户验收；push CI

### 2026-06-23 会话 19（M2–M4 全量落地）

- 完成：workspace/agent/models API；Files 真目录；M3 adapters/evaluator；`e2e/` Smoke；67 pytest
- Commit：`cf342c6`
