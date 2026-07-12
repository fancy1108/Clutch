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

## 2026-07-12 会话（修复 Codex CLI 路径找不到问题）

- **修复**：更新了 `~/.local/bin/codex` 软链接至最新的 `/Applications/ChatGPT.app/Contents/Resources/codex`（最新版的 dmg 将 `Codex.app` 更名为 `ChatGPT.app`）。
- **优化**：在 `services/orchestrator/src/tools_status.py` 的 `_CLI_EXTRA_BIN_DIRS` 中增加了 `/Applications/ChatGPT.app/Contents/Resources` 和 `/Applications/Codex.app/Contents/Resources` 作为 fallback 路径，提高 CLI 分离运行下的鲁棒性。
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
