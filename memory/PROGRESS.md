# PROGRESS

> **生命周期：** 见 [`docs/document-governance.md`](../docs/document-governance.md) §文档生命周期。  
> 主文件仅保留当前状态 + 最近 10 次会话；更早记录见 [`archive/PROGRESS-2026-Q2.md`](./archive/PROGRESS-2026-Q2.md) · [`archive/PROGRESS-2026-Q3.md`](./archive/PROGRESS-2026-Q3.md)。

## Current Status

- **阶段：** **v1.0.2 已发布** · **v1.0.3 筹备中**（`dev` 含 Ollama 修复、README/安装渠道、发版文档；**未打 tag**）
- **Release：** [v1.0.2](https://github.com/fancy1108/Clutch/releases/tag/v1.0.2) — macOS DMG + Windows MSI/NSIS + updater + `SHA256SUMS.txt`
- **Git：** `dev` 本地超前 `origin/dev`（待 push）· Homebrew tap [fancy1108/homebrew-clutch](https://github.com/fancy1108/homebrew-clutch) 已建
- **开放：** [#23](https://github.com/fancy1108/Clutch/issues/23) Windows 实体机 smoke · v1.0.3 Loop 切片

### v1.0.3 候选（`dev` · `[Unreleased]`）

| 项 | 状态 |
|----|------|
| Ollama Models Config 本机同步 | ✅ commit `2257560` |
| #19 CLI 错误文案 | ✅ commit `2cb3016` |
| README / 新手引导 / 安装脚本 / Homebrew tap | ✅ commits `5cb8950`…`1a26ca0` |
| Loop 功能 | 待 `release/1.0.3-loop` |

## Next Actions

- **Push `dev`** — 同步 Ollama 修复与文档到 `origin`
- **v1.0.3 发版时** — CHANGELOG `[Unreleased]` → `## [1.0.3]` · `sync-homebrew-tap.sh` 或 CI PAT
- **`release/1.0.3-loop`：** 开工时 `git worktree add ../clutch-release-1.0.3-loop -b release/1.0.3-loop dev`
- **Windows smoke：** [#23](https://github.com/fancy1108/Clutch/issues/23)

## Recent Sessions

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
