# TESTS（测试状态追踪）

> **必须实际运行后才能标记通过。** 禁止在未执行校验命令的情况下将项标为 ✅。  
> 本表记**门禁级**验证状态，不抄 pytest 逐文件结果；详细报告见「报告/证据」列或 CI artifacts。  
> **各 task 的 Verification 命令**见 [`specs/core/tasks.md`](../specs/core/tasks.md)；**待建 pytest 文件清单**见同文件 §待建 pytest 文件。

## 校验命令

见 [`CLAUDE.md`](../CLAUDE.md) §核心命令。本地一键：`./scripts/verify.sh`（含 `run-e2e.sh`）

## 测试清单

| 日期 | 范围 | 命令 | 结果 | 报告/证据 | 备注 |
|------|------|------|------|-----------|------|
| 2026-06-22 | 前端构建 | `pnpm build` | ✅ | — | 类型检查：`pnpm lint` |
| 2026-06-23 | 后端测试 | `cd services/orchestrator && uv run pytest` | ✅ 70 passed | verify.sh 全量 | 含 `test_mvp_closed_loop`、`test_claude_code_credentials` |
| 2026-06-23 | 前端单测 | `pnpm test`（vitest） | ✅ 1 passed | verify.sh | `workflowFormat.test.ts` |
| 2026-06-23 | E2E | `./scripts/run-e2e.sh` | ✅ 3 passed | `runs/verification/2026-06-23-e2e-smoke.log` | Smoke + MVP 闭环 |
| 2026-06-23 | macOS 打包 | `cd apps/desktop && pnpm tauri build` | ✅ | `runs/verification/2026-06-23-tauri-build.log` | DMG `Clutch_0.0.0_aarch64.dmg` |
| 2026-06-22 | 漂移机检 | `./scripts/check-doc-drift.sh` | ✅ | — | 见 DECISIONS D7 |
| 2026-06-22 | CI（GitHub Actions） | push/PR 触发 `.github/workflows/ci.yml` | ✅ | [CI #2](https://github.com/fancy1108/Clutch/actions) | `11e6d77`；见 D2、D7 |

## 里程碑级验收（tasks §测试与验收）

| ID | 触发 | 状态 | 关联 task / 证据 |
|----|------|------|------------------|
| T-01 | M2 完成 | ✅ | `api.ts` 无 mock 编排；`verify.sh` 绿 |
| T-02 | M2 完成 | ✅ | E2E Smoke 3 passed（`verify.sh` 自动起 Sidecar） |
| T-03 | M3 完成 | ✅ | `mvp-closed-loop.spec.ts` + `test_mvp_closed_loop.py` |
| T-04 | M4 前 | 待运行 | 红队 / 体感审计 |

## 格式说明

- **日期**：最后一次实际跑通并确认的日期（`YYYY-MM-DD`）
- **结果**：`✅` / `❌` / `待运行`
- **报告/证据**：本地路径（如 `runs/verification/2026-06-22-pytest/`）或 CI artifact 链接
- 前端 `pnpm test`：**D2 明确不纳入门禁**；M2-10 完成后增 vitest 门禁行

## 待办

- [x] Push 后 CI 首次绿 → 更新上表 CI 行（2026-06-22）
- [x] **M1-02**：`tests/test_compiler.py` 绿后更新后端测试行备注
- [x] **M2-10**：vitest + Playwright；E2E 门禁行
- [x] **T-01~03**：里程碑完成后标 ✅ 并链 `runs/verification/`
- [ ] **T-04**：红队 / 体感审计
- [ ] Push 本会话 commit 后更新 CI 行
