# PROGRESS

> **生命周期：** 见 [`docs/document-governance.md`](../docs/document-governance.md) §文档生命周期。  
> 主文件仅保留当前状态 + 最近 10 次会话；更早记录见 [`archive/PROGRESS-2026-Q2.md`](./archive/PROGRESS-2026-Q2.md) · [`archive/PROGRESS-2026-Q3.md`](./archive/PROGRESS-2026-Q3.md) · [`archive/PROGRESS-2026-Q3-late.md`](./archive/PROGRESS-2026-Q3-late.md)。

## Current Status

- **阶段：** **v1.4.1** 发版中（CHANGELOG 已冻结、版本号已 bump；待 merge `main` 打 tag）。主线 D8–D13 ✅；扩展/MCP **D14–D52 Agent 代 PM ✅**；Desktop E2E ✅；**Design D36 PM ✅**
- **Git / PM 索引：** [`runs/verification/pm-acceptance/AGENT-PM-2026-07-25.md`](../runs/verification/pm-acceptance/AGENT-PM-2026-07-25.md)
- **下次优先：** v1.4.1 tag 推送后等 CI 出 DMG，同步 Homebrew tap；后续用户可见变更写入 `CHANGELOG.md` `## [Unreleased]`。
- **本会话：** 发版 v1.4.1（Agnes 3.0 / Image 2.5 / Video 2.5 Flash + D68 回复风格 + Windows CI ping 修复）。

## Next Actions

- **B-52 流程图共享不开工**（需求池候选，等人再开）
- 重启 Sidecar / App 后用 Clutch Agent 问一句排错题，确认第一句是动作或结论、没有配图
- v1.4.1 GitHub Release 资产就绪后同步 Homebrew tap
- 用户可见变更写入 `CHANGELOG.md` `## [Unreleased]`

## Recent Sessions

## 2026-09-10 会话（B-52 流程图共享入池）

- **做了：** 评估 TeamAI 后，产品确认流程图（SOP）跟仓走暂不立项。记 `BACKLOG.md` **B-52**（候选）。共享对象是流程图 + Agent 规矩，不是 Skill。
- **下次：** 不要把 B-52 当本迭代任务。

## 2026-09-10 会话（D69 目标版本 1.4.1）

- **做了：** CHANGELOG 从空 `[Unreleased]` 改为 `## [1.4.1] - Unreleased`。1.4.0 之后的提交都记这一节。未 bump `package.json`。
- **下次：** 后续用户可见改动继续写 1.4.1 节；打 tag 时再改日期并 bump 版本号。

## 2026-09-10 会话（D68 默认回复风格）

- **做了：** Clutch Agent 默认 prompt 增加 `style` 层三正一禁。`i-have-adhd` 不整份写入。文档 D68 / PRODUCT_INTRO / CHANGELOG 已同步。
- **测：** `./scripts/verify.sh` — vitest 248 · pytest 1025 passed / 7 skipped。
- **下次：** 重启 App 后点验排错回复是否直接给下一步。

## 2026-09-10 会话（Agnes 免费模型换代）

- **做了：** 内置目录改为 `agnes-3.0-flash` / `agnes-image-2.5-flash` / `agnes-video-2.5-flash`。视频适配器改走 2.5 Flash（`mode`/`seconds`/`size=720P`，轮询带 `model_name`）。旧 id 别名 remap。文档 D19 已同步。
- **测：** `./scripts/verify.sh` vitest 248 · pytest 1024 passed / 7 skipped。
- **下次：** 重启 App 点验 Models 目录与三类生成。

## 2026-08-28 会话（仓库文件归类）

- **做了：** 本地缓存移出 git（`.reasonix/`、`e2e-sandbox/`、`.impeccable/`）；`PROGRESS.md` 轮转至 `archive/PROGRESS-2026-Q3-late.md`；补全 `docs/README.md` / `FILEMAP.md` / `AGENTS.md` 索引；去掉已删的 `mockData.ts` 指针。未改业务逻辑。
- **下次：** 需要的话再 commit 本批整理。

## 2026-08-28 会话（撤回 FM-06）

- **做了：** 确认卡、排队条、Complete 草稿 UI 都去掉。FM-06 🚫 D67。同 CLI `@` 复用已有 Lane。
- **下次：** 重启 App 后 `@OpenCode 只回复 pong` 应直接进终端。

## 2026-08-28 会话（D66 去掉派发确认卡）

- **做了：** Orchestrator Bar 发送即派发。跨 Agent 用 `@C from @A`。随后 D67 连排队和草稿一起撤。
- **下次：** 重启 App 后点 `@OpenCode 只回复 pong`。

## 2026-08-28 会话（Wave 4 Agent 点验并提交）

- **做了：** FM-10 去掉 Node engine，引擎跟 Assigned Agent。FM-18 Chat 失败气泡补 `validation-failure-chat`。连同 D64（撤 FM-15、解释器超时出卡）一起提交。
- **测：** `./scripts/verify.sh` vitest 248 · pytest 1021 passed / 7 skipped。
- **下次：** Wave 3 Orchestra（要 CLI）或 FM-16 Design。

## 2026-08-28 会话（D65 节点引擎跟随 Agent）

- **做了：** 去掉 Edit Node 的 Node engine 下拉。引擎、模型、MCP 跟 Assigned Agent。编译不再写节点 `tool`。
- **下次：** 完全退出再开 App，点验 FM-10。

## 2026-08-28 会话（撤回 FM-15；FM-17 去预览）

- **做了：** 并行 `delegate_subtask` 不再弹确认。+ 去掉两张样式预览。超时杀进程组并返回 `Interpreter timeout`，Chat 出卡。
- **下次：** 重启 App 看 + 菜单；FM-17 不要求人工点验。

## 2026-08-28 会话（禁止连开同一条 shell）

- **做了：** 同一 Chat 里已在跑的命令再开会被拒绝；前台超时转入后台；Kill 杀进程组（eslint 子进程）。
- **下次：** 完全退出再开 App；Kill 残留进程后再点验 lint。

## 2026-08-28 会话（Files/Changes 跟随 worktree）

- **做了：** 右侧 Files/Changes 按底栏所选 worktree 拉 `tree`/`changes`/`file`（`wt_id`）。底栏 Branch 仍走主仓 `GET /api/workspace/git`。切树会刷新；提交后 Changes 从 git 重拉。预览/打开文件走当前检出。
- **测：** `uv run pytest tests/test_worktree_isolation_d32.py tests/test_run_state_store.py` 17 passed。
- **下次：** 完全退出再开 App，按 playbook 5b 点验。不要标 ROADMAP，等你过。

## 2026-08-28 会话（底栏自适应）

- **做了：** 底栏 `Active Agent` 改为 `Agent`；容器查询藏标签、截断长值、空闲 Worktree/Workflow 先收；版本号 `shrink-0` 贴右。
- **下次：** 缩小窗口点验版本号不被裁切。

## 2026-08-28 会话（Worktree 底栏选择）

- **做了：** Worktree 选择挪到应用 Footer，紧挨 Branch；去掉输入框上方天蓝条。菜单与 Branch/Model 同一套 chrome。
- **下次：** 重启 App 后点验底栏 Worktree；再测 FM-11 写文件隔离。

## 2026-08-28 会话（修 D32 worktree cwd）

- **做了：** Enable 后 Agent 仍写主仓。会话恢复丢掉 `worktree_isolation`；整轮 Chat 才绑定 worktree cwd；绝对路径会落到父仓。未 commit。
- **测：** `uv run pytest tests/test_worktree_isolation_d32.py tests/test_run_state_store.py tests/test_apply_patch.py` 29 passed。
- **下次：** 完全退出再开 App，重新 Enable，复测 `clutch-fm11.txt` 只出现在 `.clutch/worktrees/wt_…`。
