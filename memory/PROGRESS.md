# PROGRESS

> **生命周期：** 见 [`docs/document-governance.md`](../docs/document-governance.md) §文档生命周期。  
> 主文件仅保留当前状态 + 最近 10 次会话；更早记录见 [`archive/PROGRESS-2026-Q2.md`](./archive/PROGRESS-2026-Q2.md) · [`archive/PROGRESS-2026-Q3.md`](./archive/PROGRESS-2026-Q3.md)。

## Current Status

- **阶段：** **v1.1.0 待发版** — 代码与文档已 bump；Terminal Orchestra (D34) + CodeBuddy + OpenCode Zen + Agnes Video；线上仍为 v1.0.3
- **Release：** [v1.0.3](https://github.com/fancy1108/Clutch/releases/tag/v1.0.3) 当前线上 · 下一版 **v1.1.0**（CHANGELOG / `docs/releases/v1.1.0.md` / README 已更新）
- **Git：** `feat/d34-terminal-ux` · 版本号 `1.1.0`（package / tauri）
- **开放：** [#23](https://github.com/fancy1108/Clutch/issues/23) Windows 实体机 smoke

### v1.1.0 发版清单（进行中）

| 项 | 状态 |
|----|------|
| Terminal Orchestra D34 + UX polish | ✅ |
| 版本 bump → 1.1.0 | ✅ |
| CHANGELOG + `docs/releases/v1.1.0.md` + PRODUCT_INTRO | ✅ |
| README / README.zh-CN / GETTING_STARTED / INSTALL | ✅ |
| `release-preflight` v1.1.0 | ⏳ |
| `git tag v1.1.0` + push tag | ⏳ |

## Next Actions

- **merge `feat/d34-terminal-ux` → `dev`** → `release-preflight` → tag v1.1.0 on `main`
- **Homebrew** — 发版后：`CLUTCH_VERSION=v1.1.0 ./scripts/sync-homebrew-tap.sh`
- **Windows smoke：** [#23](https://github.com/fancy1108/Clutch/issues/23)

## Recent Sessions

## 2026-07-03 会话（v1.1.0 文档恢复）

- **恢复** CHANGELOG `[1.1.0]`、`docs/releases/v1.1.0.md`、README 双语 What's new、PRODUCT_INTRO 终端 dock / resume、GETTING_STARTED / INSTALL pin
- **版本** package / tauri / Cargo → `1.1.0`
- **分支** `feat/d34-terminal-ux` rebase 至 `dev`（#28）后 push

## 2026-07-01 会话（文档治理轮转）

- **PROGRESS** → `archive/PROGRESS-2026-Q3.md`（保留最近 10 次会话）
- **DELIVERABLES** 瘦身：Active 清空 · v1.0.3 未发版条目保留 · OSR-16/17 入 `DELIVERABLES-OSR.md`

## 2026-07-01 会话（发版与安装渠道文档）

- **方案：** curl + `homebrew-clutch` tap；winget / Intel 暂缓
- **已建** [fancy1108/homebrew-clutch](https://github.com/fancy1108/homebrew-clutch)
- **文档** `RELEASE_MAINTAINER.md`（发版 checklist · AI 协作话术 · PAT 可选）
- **CI** `release.yml` 可选自动 sync tap（`HOMEBREW_TAP_GITHUB_TOKEN`）

## 2026-07-01 会话（README 与新手引导）

- **README** 重写：`README.md`（EN）+ `README.zh-CN.md`（ZH），顶部语言切换 + 显眼链向新手指南
- **新增** `docs/GETTING_STARTED.md` — 安装、向导、首聊、常见配置、故障排除（中英双语）
- **索引** `docs/README.md` · `INSTALL.md` · `PRODUCT_INTRO.md` · `FILEMAP.md` · `CHANGELOG`

## 2026-07-01 会话（Ollama Models Config 本机同步）

- **问题：** Settings → Models Config 与 Create Agent 的 Ollama 列表不一致，跨 Mac 对话 404
- **修复：** `models_config.py` — 本机 tag 同步 / 可用性 / `active_model_id` 回退
- **Commit：** `2257560` · 测试 21 passed

## 2026-07-01 会话（HRT-F 验收）

- **F1/F2/G：** Pass · **F3–F5：** Skip/N/A · **#24** closed

## 2026-07-01 会话（worktree 清理）

- **已删除 worktree：** `clutch-release-1.0.2-*` · `clutch-review-pr16/17` · `clutch-release-1.0.3-loop`
- **注意：** `1.0.3-loop` WIP 已随 force remove 丢失；Loop 需从 `dev` 重新开工

## 2026-07-01 会话（v1.0.2 发版收尾）

- **Updater go-live：** workflow [28465904210](https://github.com/fancy1108/Clutch/actions/runs/28465904210) ✅
- **Windows 安装包** 上传 Release · `SHA256SUMS.txt` 三项
- **Rivet/tools** 纳入 v1.0.2 · `release/1.0.2-updater` 合入 `dev`

## 2026-06-30 会话（GitHub triage）

- **PR #22** → **B-33** 写入 `BACKLOG.md` · **#18/#19** Bug 登记 · **#20** 用法咨询已回复

## 2026-06-29 会话 26（OSR-16/17 · Release 硬化）

- **OSR-16/17**：`release_hardening.py` · CSP · `console=False` — commit `e410897`
- **验证**：`pytest tests/test_release_hardening.py` + `./scripts/verify.sh`

## 2026-06-29 会话 25（OSR-14 · 首次启动向导）

- **前端**：7 屏 `OnboardingWizard`；`agentProvisioning.ts`；`App.tsx` 全屏挂载
- **验证**：`pytest tests/test_onboarding_preference.py` · vitest · `./scripts/verify.sh`

## 2026-06-29 会话 23（OSR-12 · v1.0.0 Release 实跑 ✅）

- Release 资产：`Clutch_1.0.0_aarch64.dmg` · `SHA256SUMS.txt` · 构建修复 `dd9fa20`
