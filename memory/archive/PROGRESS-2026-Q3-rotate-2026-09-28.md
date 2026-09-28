# Archive Notice

This file is archived and read-only.

Do not append new records here.

For current project state, see:

- memory/PROGRESS.md
- memory/DELIVERABLES.md
- memory/ROADMAP.md

Archived on: 2026-09-28
Reason: PROGRESS exceeded 10 sessions; rotated the 10 oldest (all from 2026-08-28) out of the main file.

---

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
