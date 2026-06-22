# PROGRESS

## 当前状态

- 阶段：Phase 0（治理脚手架 + 测试基础设施）
- 焦点：测试三层治理（DECISIONS / ROADMAP / TESTS）与 CI 已就绪；E2E 待 M0–M2 前提
- 上次更新：2026-06-22
- Git HEAD：`1d663fe` — test governance + CI（主改动 `78b9a89`）

## 下次 Agent 启动必读

1. 读本文件（`PROGRESS.md`）
2. 读 `FAILURES.md`、`FILEMAP.md`、`DECISIONS.md`（注意 D1 决策状态 `已记录`，勿提前建 `e2e/`）
3. 运行 `git log --oneline -10`
4. 运行 `./scripts/verify.sh` 或 `pnpm build && cd services/orchestrator && uv run pytest`

## 待办（跨会话）

- [ ] **Push + CI**：push 到 remote，确认 Actions 绿，更新 `TESTS.md` CI 行
- [ ] **M0 开发**：Sidecar + WebSocket 真实 `state_patch`（最高优先，见 `ROADMAP.md` §待办）
- [ ] **第 6 步**：拆解 `specs/core/tasks.md`，填实 `ROADMAP.md` 功能清单与 `FILEMAP.md` 业务路径
- [ ] **开放问题**：M1 前决策 Q2、Q3；M2 前 Q1；M3 前 Q4（见 `DECISIONS.md`）
- [ ] **勿提前**：D1 为 `已记录` 时禁止建 `e2e/`、禁止为凑覆盖写空测试

## 会话日志（最新在上）

### 2026-06-22 会话 1（测试治理）

- 完成：
  - `DECISIONS.md` D1（E2E 范围/目录 + 落地前提 + 决策状态）、D2（CI 门禁）
  - `ROADMAP.md` E2E 落地前提表（关联 D1）
  - `TESTS.md` 新格式 + 本地 build/pytest 验证通过
  - `.github/workflows/ci.yml`、`scripts/verify.sh`
  - `runs/verification/`、`.gitignore` 报告目录
  - `document-governance.md`、`FILEMAP.md`、`README.md` 同步
- 遗留：CI 待 push 后首次绿；`pnpm test`  intentionally 未纳入门禁
- 下次优先：M0 开发（Sidecar + WebSocket `state_patch`）或第 6 步 tasks 拆解

### 2026-06-22 会话 0（Initializer）

- 完成：安装 Pro 级 Agent OS（`specs/`、`memory/` 六件套、`CLAUDE.md`、`.cursor/rules/base.mdc`、`docs/document-governance.md`）
- 遗留：无
