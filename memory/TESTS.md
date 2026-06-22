# TESTS（测试状态追踪）

> **必须实际运行后才能标记通过。** 禁止在未执行校验命令的情况下将项标为 ✅。  
> 本表记**门禁级**验证状态，不抄 pytest 逐文件结果；详细报告见「报告/证据」列或 CI artifacts。

## 校验命令

见 [`CLAUDE.md`](../CLAUDE.md) §核心命令。本地一键：`./scripts/verify.sh`

## 测试清单

| 日期 | 范围 | 命令 | 结果 | 报告/证据 | 备注 |
|------|------|------|------|-----------|------|
| 2026-06-22 | 前端构建 | `pnpm build` | ✅ | — | 类型检查：`pnpm lint` |
| 2026-06-22 | 后端测试 | `cd services/orchestrator && uv run pytest` | ✅ 1 passed | — | |
| 2026-06-22 | 漂移机检 | `./scripts/check-doc-drift.sh` | ✅ | — | 见 DECISIONS D7 |
| 2026-06-22 | CI（GitHub Actions） | push/PR 触发 `.github/workflows/ci.yml` | ✅ | [CI #2](https://github.com/fancy1108/Clutch/actions) | `11e6d77`；见 D2、D7 |

## 格式说明

- **日期**：最后一次实际跑通并确认的日期（`YYYY-MM-DD`）
- **结果**：`✅` / `❌` / `待运行`
- **报告/证据**：本地路径（如 `runs/verification/2026-06-22-pytest/`）或 CI artifact 链接
- 前端 `pnpm test`：**D2 明确不纳入门禁**；有真实用例后再增行

## 待办

- [x] Push 后 CI 首次绿 → 更新上表 CI 行（2026-06-22）
- [ ] 前端有真实可测逻辑后：安装 vitest、增门禁行、再评估是否纳入 `CLAUDE.md` 会话校验
- [ ] D1 状态变为 `可执行` 后：建 `e2e/`、增 E2E 门禁行（禁止提前）
- [ ] 需要覆盖率报告时：输出到 `runs/verification/<date>-<scope>/`，在本表「报告/证据」列链接
