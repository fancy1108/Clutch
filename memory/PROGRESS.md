# PROGRESS

> **生命周期：** 见 [`docs/document-governance.md`](../docs/document-governance.md) §文档生命周期。  
> 主文件仅保留当前状态 + 最近 10 次会话；更早记录见 [`archive/PROGRESS-2026-Q2.md`](./archive/PROGRESS-2026-Q2.md) · [`archive/PROGRESS-2026-Q3.md`](./archive/PROGRESS-2026-Q3.md) · [`archive/PROGRESS-2026-Q3-late.md`](./archive/PROGRESS-2026-Q3-late.md)。

## Current Status

- **阶段：** **v1.4.1** 已发（2026-09-21，macOS + Windows；DMG/MSI/NSIS + updater 资产齐了，tap 已同步 1.4.1）。主线 D8–D13 ✅；扩展/MCP **D14–D52 Agent 代 PM ✅**；Desktop E2E ✅；**Design D36 PM ✅**
- **Git / PM 索引：** [`runs/verification/pm-acceptance/AGENT-PM-2026-07-25.md`](../runs/verification/pm-acceptance/AGENT-PM-2026-07-25.md)
- **下次优先：** 后续用户可见变更写入 `CHANGELOG.md` `## [Unreleased]`；需要应用内更新时手动跑 `Release (updater assets)`。
- **本会话：** 修复 Design 模式两个回归（生成页黑白不渲染 / modify 不切换版本）+ `prune_orphan_session_dirs` 数据丢失守护（commit `c12ddba` / `d8dd342`）。

## Next Actions

- **B-52 流程图共享不开工**（需求池候选，等人再开）
- 重启 Sidecar / App 后用 Clutch Agent 问一句排错题，确认第一句是动作或结论、没有配图
- 用户可见变更写入 `CHANGELOG.md` `## [Unreleased]`

## Recent Sessions

## 2026-09-22 会话（Task-center 任务总览增强）

- **做了：** 继续扩展任务中心：为 `SessionOverviewBoard` 增加状态汇总卡片（Running / Waiting / Failed / Done / Idle），让用户一眼看见热点与风险项，不再只看单条 badge；并补齐更明确的操作语义，等待与失败态都显示 `Review` / `Inspect` 之类的 action pill，方便直接切到对应会话。
- **落地：** `apps/desktop/src/components/SessionOverviewBoard.tsx` 新增 `summarizeSessionBoardStatus()` 与 `getSessionBoardActionLabel()`；`SessionOverviewBoard` 顶部展示汇总计数，并在行级展示明确 CTA，保留原有筛选与去重逻辑。
- **测：** `pnpm --filter @clutch/desktop test -- --run src/components/SessionOverviewBoard.test.ts` ✅（9/9 passed）。
- **下次：** 继续下一步任务项：审批流交互/UX 的更细化反馈（如批准/拒绝的动作态势与重试说明），并把这批信号继续接入真实会话状态流。 

## 2026-09-21 会话（Design 回归修复：黑白页 / modify 版本 / prune 守护）

- **做了：** ① 「生成的 Design 页面黑白无样式」——根因不是 LLM 也不是 CDN：画布卡片与侧栏缩略图用**超大 srcDoc iframe**（如 1440px 宽再 scale 缩小），Chromium 与 WKWebView 都会把 paint 冻结在 Tailwind CDN 运行时注入样式之前的初始帧；磁盘上的 HTML 与 `src=` 加载均正常。修复：卡片与缩略图改走 sidecar 预览 URL（`src=`），仅 Pick-element 模式保留 srcDoc（需同源 DOM）。commit `c12ddba`。② 「modify 不切换版本」——后端 `iterate_session` modify 分支原地覆写 `_r0.html`，从不产生新 round；改为走 `_record_screen_round` 记录 `_r1/_r2/…`，与 add/duplicate/delete 对齐。③ `prune_orphan_session_dirs` 守护：注册表为空但磁盘有产物时整体跳过；24 小时内修改过的目录不删。commit `d8dd342`。
- **⚠️ 事故披露：** 排查期间我用 dev sidecar（`clutch_dev` store）打开用户工作区，`prune_orphan_session_dirs` 因跨 store 注册表不匹配**误删了用户 4 个测试 Design 会话**（磁盘目录被清）。补救：为验证修复重建了 1 个会话；被删的 4 个为测试会话无法恢复，已向用户披露；③ 的守护即为防复发（空 keep 集跳过 + 24h 宽限期 + 回归测试）。
- **测：** `verify.sh` ✅（vitest 248 · pytest 1029 passed / 7 skipped · doc-drift 0 error）；`test_design_service.py` 42 passed（含新增 prune 守护用例）；浏览器实测画布卡片与侧栏缩略图均正常上色。
- **下次：** 用户重启 App 后点验 Design 生成页配色与 Rounds 切换；modify 的端到端 UI 点验需重启 sidecar 后做一次。

## 2026-09-21 会话（Chat 历史自动压缩误折叠修复）

- **做了：** 修复「发出第二问后第一条回答从 feed 消失」。根因：`compaction.should_compact` 用 lifetime 累计 `session_tokens`（每轮全量上下文 input 累加，mcp_react 跨 ReAct 步求和）对比固定 15k 阈值 → 正常聊天几轮即触发 L4 全量折叠，可见消息被换成 首条+近4条+digest。真实会话 `run_muao447c` 折叠时当前上下文仅 ~7.8k tokens。修复：触发改为 `estimate_context_tokens`（可见消息文本 chars/2 + 系统提示常量 6k），默认阈值 100k（`CLUTCH_COMPACT_THRESHOLD` 可覆盖）；手动 `/compact` 与折叠形态不变。commit `9570832`。
- **测：** `verify.sh` ✅（vitest 248 · pytest 1028 passed / 7 skipped · doc-drift 0 error）；真实会话归档回放：旧逻辑折叠、新逻辑不折；新增 3 个回归测试（阈值守卫 / 两轮 patch 保留首答 / WS 重连保留首答）。
- **下次：** 重启 Sidecar 后 Chat 连续多问几句确认历史常驻；超长会话（当前上下文 >100k）点验一次自动折叠 digest 是否正常。

## 2026-09-21 会话（清 dependabot  backlog）

- **做了：** 合并全部 14 个 dependabot PR（含 major：vitest 5.0.1、motion 13.4.0、@types/node 26.6.1）。`windows-build.yml`/`ci.yml` 全绿后逐个 merge；dependabot 分支合并即自动删除，远端只剩 main/dev/win。
- **坑：** Tauri 版本守卫要求 NPM 包与 Rust crate 同 major/minor → updater/dialog 这类双侧 PR 必须先合 NPM 侧（#135→#130），否则 `build` 报 version mismatched；rebase 早于配对合并产生的失败是陈旧检查，重 rebase 即消。
- **测：** 合并后 `dev` 本地 `verify.sh` ✅（pytest 1025 passed / 7 skipped）。
- **下次：** 这批依赖升级随下个版本发布；点验时留意 motion 13 动画回归。

## 2026-09-21 会话（发版 v1.4.1）

- **做了：** 提交 docs/memory 批次（`7043ac6`）→ bump + 冻结 CHANGELOG（`9bdca8b`）→ PR [#144](https://github.com/fancy1108/Clutch/pull/144) CI 全绿后 merge → `main` 打 tag `v1.4.1` → CI 出 DMG → 手动同步 Homebrew tap（`3eff0ed`）→ 手动触发 `Release (updater assets)`，`latest.json`/`Clutch.app.tar.gz`/`.sig` 已挂 Release。
- **测：** `verify.sh` pytest 1025 passed / 7 skipped；`release-preflight.sh v1.4.1` ✅；updater workflow run 35554855630 ✅。
- **发现：** ① CI tap 自动同步的 `HOMEBREW_TAP_GITHUB_TOKEN` 未配置（自 v1.2.1 起 tap 一直靠手动）；② `docs/releases/README.md` 原称 patch 可免快照，与 INV-R6 门禁矛盾，已改为「patch 必须快照」；③ `windows-build.yml` 监听所有 `v*` tag，patch 也自动出 Windows 安装包——`RELEASE_MAINTAINER.md`「patch 只发 macOS」过时，已按现实改写（v1.4.1 实为 macOS + Windows）。
- **下次：** 考虑配 `HOMEBREW_TAP_GITHUB_TOKEN` 省掉手动同步。

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
