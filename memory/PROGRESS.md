# PROGRESS

## 当前状态

- 阶段：**M2–M4 任务批量落地完成（待 M4-06 DMG 本机验证）**
- 说明：M0–M3 pytest/vitest/E2E Smoke 绿；工作区授权、Files 真目录、CLI/Evaluator、Agent/Models 持久化已接 Sidecar
- 焦点：**M4-06** `pnpm tauri build` 本机验收；**T-03** MVP 闭环 E2E
- Git HEAD：`3dd96be` + 本会话大量未提交改动

## 治理脚手架就绪标准（文档层 ✅）

- [x] Layer 1–3 治理文档 + Memory 六件套
- [x] 测试规范（D1/D2、TESTS、CI workflow、`verify.sh`）
- [x] Vibe 8.5 兜底（D7：Husky、漂移机检、truth-alignment 剧本、Layer 4 约束）
- [x] Task 交付索引（`DELIVERABLES.md` + Check-out 规则 + `runs/verification/README`）
- [x] 产品开放问题 Q1–Q4 → D3–D6 已决策

## 下次 Agent 启动必读

1. 读本文件（`PROGRESS.md`）
2. 读 `FAILURES.md`、`FILEMAP.md`、`DECISIONS.md`（D3–D8）、`specs/core/tasks.md`
3. 运行 `git log --oneline -10`
4. 运行 `./scripts/verify.sh`

## 待办（跨会话）

- [x] **M0–M1**：全部完成
- [x] **M2**：M2-01–14
- [x] **M3**：M3-01–07
- [x] **M4**：M4-01–05、07–09
- [ ] **M4-06**：`pnpm tauri build` → DMG 证据
- [ ] **T-03**：Playwright MVP 闭环

## 会话日志（最新在上）

### 2026-06-23 会话 19（M2–M4 全量落地）

- 完成：workspace/agent/models API；Files 真目录；M3 adapters/evaluator；`e2e/` Smoke 2 passed；vitest；67 pytest
- 校验：`./scripts/verify.sh`；`e2e` Smoke 绿（Sidecar + Playwright）
- 下次优先：**M4-06** DMG；**T-03** E2E 闭环

### 2026-06-23 会话 18（M2 批量推进）

- 完成：M2-03/08–07/13/14；interrupt_before
- 校验：56 passed
