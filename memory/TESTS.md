# TESTS（测试状态追踪）

> **必须实际运行后才能标记通过。** 禁止在未执行校验命令的情况下将项标为 ✅。  
> 本表记**门禁级**验证状态，不抄 pytest 逐文件结果；详细报告见「报告/证据」列或 CI artifacts。  
> **各 task 的 Verification 命令**见 [`specs/core/tasks.md`](../specs/core/tasks.md)；**待建 pytest 文件清单**见同文件 §待建 pytest 文件。

## 校验命令

见 [`CLAUDE.md`](../CLAUDE.md) §核心命令。本地一键校验（轻量）：`./scripts/verify.sh`；全量校验（含 E2E）：`./scripts/verify.sh --e2e`

## 测试清单

| 日期 | 范围 | 命令 | 结果 | 报告/证据 | 备注 |
|------|------|------|------|-----------|------|
| 2026-06-25 | Git 分支 footer + 日志时间戳 + Models/MCP/Video Core 批次 | `./scripts/verify.sh` | ✅ 218 pytest + 1 vitest | pre-commit `7ee8f43` | `/api/workspace/git`；`stamp_log_line` CST；`run_log_forwarder`；CC Switch 模型；MCP mock 隔离；Video Core 测试 |
| 2026-06-25 | E2E workspace git API + 沙箱 git init | `e2e/tests/workspace-git.spec.ts`（需 `run-e2e.sh`） | 待运行 | `—` | 沙箱 `git init -b main`；Playwright 断言 footer 分支与 API 一致 |
| 2026-06-25 | Engine Router + agent_id 聊天路由 | `./scripts/verify.sh` | ✅ 138 pytest + 1 vitest | pre-commit `6cc6c6b` | `engine_router` / `claude_cli_adapter` 分流；内置 Agent 可编辑；WS `agent_id` + system prompt 注入；`CLUTCH_STORAGE_DIR` 测试隔离 |
| 2026-06-25 | 存储隔离与指针拖拽及LLM运行优化 | `./scripts/verify.sh` | ✅ 119 pytest + 1 vitest | `runs/verification/2026-06-25-storage-drag-verify.log` | DEV/PROD存储路径隔离、自定义Pointer拖拽、ChatFeed普通LLM消息提示及停止运行校验 |
| 2026-06-24 | 分组移动与管理优化 | `./scripts/verify.sh` | ✅ 116 pytest + 1 vitest | `runs/verification/2026-06-24-group-drag-verify.log` | 分组文件夹图标区分、虚拟默认分组折叠、原生拖放及右键菜单移动项目校验 |
| 2026-06-24 | 自定义弹窗与删除修复 | `./scripts/verify.sh` | ✅ 116 pytest + 1 vitest | `runs/verification/2026-06-24-custom-dialog-verify.log` | 自定义 PromptModal 代替原生 window.prompt/confirm 并修复删除项目 |
| 2026-06-24 | 删除与跳转优化 | `./scripts/verify.sh` | ✅ 116 pytest + 1 vitest | `runs/verification/2026-06-24-delete-navigation-verify.log` | 新建会话惰性加载与删除会话自动跳转跳转规则校验 |
| 2026-06-24 | 右键&思考动效 | `./scripts/verify.sh` | ✅ 116 pytest + 1 vitest | `runs/verification/2026-06-24-rightclick-thinking-verification.log` | 右键自定义 Reload 与 LLM 思考中动画校验 |
| 2026-06-24 | UI/后端修复 | `./scripts/verify.sh` | ✅ 116 pytest + vitest | `runs/verification/2026-06-24-ui-fixes-verify.log` | UI 与后端交互修复校验 |
| 2026-06-22 | 前端构建 | `pnpm build` | ✅ | — | 类型检查：`pnpm lint` |
| 2026-06-23 | 后端测试 | `cd services/orchestrator && uv run pytest` | ✅ 104 passed | `runs/verification/2026-06-24-p2-01-verify.log` | 含 `test_skills_registry`（P2-01） |
| 2026-06-24 | E2E 全量 | `./scripts/verify.sh` | ✅ 7 Playwright + 104 pytest | `runs/verification/2026-06-24-p2-01-verify.log` | P2-01 Check-out |
| 2026-06-26 | macOS 打包（latest） | `cd apps/desktop && pnpm tauri build` | ✅ | `runs/verification/2026-06-26-tauri-build.log` | DMG `runs/verification/2026-06-26-clutch-latest.dmg`（含 compaction + ShellSession POC） |
| 2026-06-24 | macOS 打包（P2） | `cd apps/desktop && pnpm tauri build` | ✅ | `runs/verification/2026-06-24-tauri-build-p2.log` | DMG `runs/verification/2026-06-24-clutch-p2.dmg`（含最新分组移动与管理功能） |
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
- [x] **D12 桌面 E2E**：`run-e2e.sh` 7 用例全绿（2026-06-24 verify）
- [ ] Push P2-01 commit 后更新 CI 行
