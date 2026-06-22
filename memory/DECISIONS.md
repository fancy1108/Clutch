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

## 开放问题（自 proposal 迁入，待决策）

| # | 问题 | 建议决策时间 | 状态 |
|---|------|--------------|------|
| Q1 | 运行历史是否纳入 MVP | M2 结束前 | 待决策 |
| Q2 | 默认 LLM 用 Claude 还是可切换 | M1 开始前 | 待决策 |
| Q3 | Workflow 文件存放于项目内还是应用数据目录 | M1 开始前 | 待决策 |
| Q4 | Evaluator 默认检查规则库如何维护 | M3 开始前 | 待决策 |
