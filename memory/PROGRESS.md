# PROGRESS

> **生命周期：** 见 [`docs/document-governance.md`](../docs/document-governance.md) §文档生命周期。  
> 主文件仅保留当前状态 + 最近 10 次会话；更早记录见 [`archive/PROGRESS-2026-Q2.md`](./archive/PROGRESS-2026-Q2.md) · [`archive/PROGRESS-2026-Q3.md`](./archive/PROGRESS-2026-Q3.md)。

## Current Status

- **阶段：** **v1.2.2 已发布（macOS）**（2026-07-11）— Windows MSI/NSIS 已在 CI 构建成功，待挂到 Release（本机下载超时）
- **Release：** [v1.2.2](https://github.com/fancy1108/Clutch/releases/tag/v1.2.2) · tag on `main` @ `7fa6901`
- **Git：** `main` / `dev` @ `7fa6901`
- **macOS：** DMG + SHA256SUMS 已上传；Homebrew tap 已 bump
- **Windows：** Actions artifact `clutch-windows-x64` @ run [29158434326](https://github.com/actions/runs/29158434326) — 需 `gh release upload`

## Next Actions

- 挂 Windows MSI/NSIS 到 Release（网络恢复后）
- 等 updater assets workflow 完成
- Windows 实体机 smoke（可选）

## Recent Sessions

## 2026-07-12 会话（交接 Handoff 派发流程耗时优化与界面交互体验改进）

- **性能优化**：将 Handoff 派发时 LLM 生成 Smart Summary 的耗时从同步改成了非阻塞后台任务异步生成，结合最新 12,000 字符的智能输入截断策略，彻底解决了界面可能因云端模型慢响应而卡死的问题。
- **Handoff 质量提升（聊天上下文整合）**：将当前 Session 的完整聊天对话历史（`messages`）整合进了 Handoff 的 LLM 总结 Prompt 中（格式化为 `[User]/[Assistant]` 多轮对话），使总结不仅包含终端 PTY 原始日志，更包含了高层规划与用户讨论的过程上下文；同时将强超时限制从 `4.0` 秒放宽至 `10.0` 秒，在保证快响应的前提下给高质量大模型更充裕的生成时间。
- **TUI 精细清洗**：重构了 `clean_pty_transcript` 方法，精细清洗过滤了 horizontal 边框线（如 `━━━━`）、填充块（`████`）、键盘操作指南（`tab 切换模式`/`ctrl+p` 等）、无用 headers 等 TUI 画布冗余元数据，让交接生成的 Handoff 文本内容整洁易读。
- **状态机步骤渲染**：前端及后端增加了 `generating_handoff` -> `opening_terminal` -> `injecting_goal` -> `done` 的步骤流渲染，支持在卡片最底下一行完美呈现 Spinner 和国际化提示语，防止了头部 Badge 排版重叠。
- **面板秒折叠**：发送交接时，立即在前端触发 `from @agent1` 来源面板的折叠，使用户获得极速交互响应。
- **后台终端数修正与系统守护进程过滤**：在 `main.py` 中为 `list_alive_for_run` 传递了 `include_system=True` 以启用系统级 PTY/CLI 进程扫描；同时在 `interactive_pty_runtime.py` 的 `scan_system_cli_processes` 中增加了路径前缀过滤，排除了位于 `/usr/sbin/`、`/usr/libexec/`、`/System/` 和 `/sbin/` 的系统守护进程（如 `distnoted agent` 或 `cfprefsd agent`），确保后台终端统计仅精确匹配用户配置并运行的实际 CLI 智能体进程。
- **校验**：本地 `./scripts/verify.sh` 通过，所有单元测试通过。

## 2026-07-12 会话（修复 Codex 路径及多 CLI 终端消息注入时机问题）

- **修复**：更新了 `~/.local/bin/codex` 软链接至最新的 `/Applications/ChatGPT.app/Contents/Resources/codex`（最新版的 dmg 将 `Codex.app` 更名为 `ChatGPT.app`）。
- **优化**：在 `services/orchestrator/src/tools_status.py` 的 `_CLI_EXTRA_BIN_DIRS` 中增加了 `/Applications/ChatGPT.app/Contents/Resources` 和 `/Applications/Codex.app/Contents/Resources` 作为 fallback 路径。
- **修复**：在 `apps/desktop/src/services/terminalOrchestraUtils.ts` 中，为 `mimo-cli`、`codex-cli`、`claude-cli` 和 `codebuddy-cli` 等所有重型交互式终端补全了 PTY 启动就绪检测（精确匹配各种语言提示语如 `输入消息`/`ctrl+p`/`write tests for`/`ask a question`/`for shortcuts`）与 warmup 时间策略，解决了终端未完全就绪就注入消息导致消息丢失的问题。
- **验证**：本地运行 `./scripts/verify.sh` 校验成功。

## 2026-07-11 会话（v1.2.2 发版）

- PR [#60](https://github.com/fancy1108/Clutch/pull/60) merge → `main`；tag `v1.2.2`；`main`→`dev` 同步
- macOS `release.yml` ✅（含 Homebrew tap sync）
- Windows Build ✅；artifact 上传 Release 因本机下载超时未完成

### v1.2.1 发版清单

| 项 | 状态 |
|----|------|
| CHANGELOG + README + `docs/releases/v1.2.1.md` | ✅ |
| 版本号 bump | ✅ |
| PR merge `dev` → `main` (#48) | ✅ |
| `git tag v1.2.1` on `main` + push | ✅ |
| macOS DMG CI (`release.yml`) | ✅ [run](https://github.com/actions/runs/29136178177) |
| Homebrew tap sync | ✅（CI 缺 `HOMEBREW_TAP_GITHUB_TOKEN`，已手动 `sync-homebrew-tap.sh`） |
| macOS updater (`latest.json`) | ✅ [run](https://github.com/fancy1108/Clutch/actions/runs/29136334316) |

## Next Actions

- **v1.2.2 发版中** — `release/v1.2.2` → merge `main` → tag `v1.2.2` → macOS DMG CI + Windows Build 挂 Release → Homebrew tap + updater
- （可选）配置 `HOMEBREW_TAP_GITHUB_TOKEN`

## Recent Sessions

## 2026-07-11 会话（v1.2.2 发版准备）

- 版本 bump 1.2.1 → 1.2.2；CHANGELOG / README / releases 快照；**macOS + Windows**（patch 例外，对齐 Design Preview）
- 分支：`release/v1.2.2`

## 2026-07-11 会话（开放 PR 合入 + issues #55/#53/#52）

- 合入 #56/#58 → `main`，#57 → `dev`，并 sync `main`→`dev`
- **#55：** `getCanvasIncompatibilities` + JSON banner 点名节点/边
- **#53：** `file_exists` FORBIDDEN/resolved path 日志；schema + PRODUCT_INTRO
- **#52：** human_decision 锁、清 check_result、resume 时 `running`、HITL 按钮防抖
- **校验：** `./scripts/verify.sh` → 711 passed；vitest workflowFormat 4 passed
- **分支：** `fix/issues-55-53-52`

## 2026-07-11 会话（v1.2.x Windows parity · PR 准备）

- **同步** `win` fast-forward 到 upstream `dev` `3db7e03`，后续 merge 作者 v1.2.1 `e03aa64` 以解除 PR conflict；保留主工作区 `clutch_win_wuxian` 不变。
- **修复** Windows Design Preview：`.cmd` 命令解析、pnpm ignored-build policy、UTF-8 install output、preview process tree stop、重新生成前停止 preview、manifest replace 重试。
- **修复** Windows Tauri build/dev：desktop `tauri:dev` 走 Node wrapper；`beforeBuildCommand` 走 `scripts/run-build-sidecar.mjs`，不再依赖裸 `uv` 在 PATH。
- **验证** `pytest tests/test_design_service.py` 28 passed；真实 Design Preview smoke 通过；`pnpm build`、`pnpm test`、orchestrator 全量 pytest、`cargo check`、`pnpm tauri:build` 通过。

## 2026-07-11 会话（v1.2.1 发版完成）

- Merge #48 · tag `v1.2.1` · DMG + SHA256SUMS · Homebrew tap 手动 sync · updater workflow 已触发
- 用户从 1.2.0 经应用内全量更新拿修复；热更通道供后续后端热修

## 2026-07-11 会话（热更 D37 + v1.2.1 打包准备）

- D37 Sidecar 热更客户端 + Chat/Design/Models hotfix · verify ✅

## 2026-07-11 会话（v1.2.0 Chat 回归诊断 + 修复）

- Chat dict 崩溃根因与修复路径

## 2026-07-10 会话（v1.2.0 updater / 发版 / D36）

- 见 archive / 上文历史
