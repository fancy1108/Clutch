# PROGRESS

> **生命周期：** 见 [`docs/document-governance.md`](../docs/document-governance.md) §文档生命周期。  
> 主文件仅保留当前状态 + 最近 10 次会话；更早记录见 [`archive/PROGRESS-2026-Q2.md`](./archive/PROGRESS-2026-Q2.md)。

## Current Status

- **阶段：** **v1.0.2 已完整发布** — [Release](https://github.com/fancy1108/Clutch/releases/tag/v1.0.2) 含 macOS DMG + Windows MSI/NSIS + updater 资产 + `SHA256SUMS.txt`
- **Git：** `dev` 已 push · [#18](https://github.com/fancy1108/Clutch/issues/18) 已关闭
- **Windows：** CI run [28462065330](https://github.com/fancy1108/Clutch/actions/runs/28462065330) ✅；Release 已含 `Clutch_1.0.2_x64_en-US.msi` + `Clutch_1.0.2_x64-setup.exe`
- **Updater go-live：** ✅ run [28465904210](https://github.com/fancy1108/Clutch/actions/runs/28465904210) — `latest.json` + 签名 bundle 已挂 Release

### v1.0.2 范围（已定）

| 切片 | 状态 |
|------|------|
| Windows（#17，PR #17） | ✅ Release 已发布 |
| OSR-20 应用内更新 | ✅ Go-live（macOS） |
| #18 Sidecar 生命周期（`lib.rs`） | ✅ 在 `dev` |
| Rivet CLI + Tools 白名单扩展 | ✅ 在 `dev`（进 1.0.2） |
| Loop | **v1.0.3**（`release/1.0.3-loop`） |

## Next Actions

- **`release/1.0.3-loop`：** v1.0.3 发版时合入 `dev`
- **Windows 实体机 smoke：** 维护者验收 — [#23](https://github.com/fancy1108/Clutch/issues/23)（`ready-for-human`）

## Recent Sessions

## 2026-07-01 会话（v1.0.2 发版收尾）

- **Updater go-live：** 修复 `TAURI_SIGNING_PRIVATE_KEY`（`gh secret set` 从 `~/.clutch-updater-keys`）→ workflow [28465904210](https://github.com/fancy1108/Clutch/actions/runs/28465904210) ✅
- **Windows 安装包：** 从 CI artifact 上传至 v1.0.2 Release；`SHA256SUMS.txt` 含三项校验和
- **文档：** `docs/UPDATES.md`、`docs/releases/v1.0.2.md`、`PRODUCT_INTRO.md`、`INSTALL.md` 同步
- **下次优先：** v1.0.3 Loop 切片

- **Rivet/tools** 纳入 v1.0.2（用户确认）
- **`release/1.0.2-updater`** 合入 `dev`（OSR-20 + #18 `lib.rs`）
- **下次优先：** verify + DMG smoke → tag v1.0.2

## 2026-06-30 会话（GitHub triage）

- **PR #22** → **B-33** 写入 `BACKLOG.md` Active 候选池（非待办、非 merge 决策）
- **#18 / #19** — Issue 评论已发；Bug 登记见 BACKLOG §待修复 Bug
- **#20** — 用法咨询已回复

## 2026-06-29 会话 26（OSR-16/17 · Release 硬化）

- **OSR-16**：`release_hardening.py` — frozen sidecar 默认关闭 debug API 与 OpenAPI；`CLUTCH_DEBUG_API=1` 可 opt-in；`tauri.conf.json` 生产 CSP + `devCsp`（Vite HMR :3000）
- **OSR-17**：`clutch.spec` `console=False` — 打包 sidecar 无终端黑窗
- **验证**：`pytest tests/test_release_hardening.py` + 既有 debug/auth 回归 · `./scripts/verify.sh`
- **下次优先**：HRT-F 多 session 人工验收

## 2026-06-29 会话 25（OSR-14 · 首次启动向导）

- **后端**（已存在）：`onboarding_completed` preference + `POST /api/preferences/onboarding-complete` + pytest
- **前端**：7 屏 `OnboardingWizard`（Welcome/health → Workspace → Models → Tools 二选一门禁 → Flow 引导 → Permissions 只读 → Ready）；`agentProvisioning.ts` Connect 幂等建 Agent；`App.tsx` 全屏挂载
- **E2E**：`CLUTCH_E2E_SKIP_ONBOARDING=1` + sandbox `preferences.json` 种子
- **验证**：`pytest tests/test_onboarding_preference.py` 3 passed · `./scripts/verify.sh` → build + 41 vitest + 490 pytest OK
- **下次优先**：OSR-16

- **Sidecar**：`keyring` 存 Provider API Key（service `com.clutch.app`）；macOS 默认启用，`CLUTCH_USE_KEYCHAIN=0` 回退明文 `models.json`
- **迁移**：加载 `models.json` 时把 legacy `api_keys` 写入 Keychain 并从文件剥离
- **验证**：`uv run pytest` → 486 passed · `./scripts/verify.sh` → OK
- **下次优先**：OSR-14 首次启动向导

## 2026-06-29 会话 23（OSR-12 · v1.0.0 Release 实跑 ✅）

- merge `cursor/refine-auto-continue-i18n-chat-fixes` → `main`；首跑缺 `UnderDevelopmentNotice` → `dd9fa20` 修复后重打 tag
- Release 资产：`Clutch_1.0.0_aarch64.dmg`（~37 MB）· `SHA256SUMS.txt`
- stash `wip: i18n/settings UI` 保留，未 pop 到 main

## 2026-06-29 会话 22（OSR-12 · 已 commit `109d427`）

- **`scripts/release-preflight.sh`**：发版前检查无 `models.json`/`.env`/Application Support 路径入 git
- **`release.yml`**：gitleaks · preflight · SHA256SUMS · `workflow_dispatch` 同版本重打
- **`.gitignore`**：`models.json`

## 2026-06-29 会话 21（OSR-15 · 已 commit `04d6b30`）

- **`docs/INSTALL.md`**：DMG 安装、Gatekeeper、健康检查、首次 checklist、卸载
- **`docs/DATA_AND_PRIVACY.md`**：本地存储表、第三方数据流、用户权利、合规说明
- **交叉引用**：`README.md` 文档地图 · `SECURITY.md` 支持版本 1.0.x

## 2026-06-29 会话 20（OSR-10 截图 · OSR-00 验收 · D31 未签名 DMG）

- **产品截图**：`docs/images/Clutch_1.png`、`Clutch_2.png` → README §产品截图
- **OSR-00**：维护者自验通过（用户确认）
- **D31**：无 Apple Developer 账号 → 未签名 DMG 经 GitHub Releases + README；OSR-11 ⏭️
- **Release CI**：`.github/workflows/release.yml`（`v*` tag → macOS DMG）

## 2026-06-29 会话 19（OSR-08 Sidecar session token 鉴权）

- **`CLUTCH_SIDECAR_TOKEN`**：Tauri 启动时生成 UUID，注入 sidecar 环境；`clutch_sidecar_token` command 供 WebView。
- **后端**：`sidecar_auth.py` + HTTP middleware + WS `?token=`；`/health` 公开；`CLUTCH_E2E_SANDBOX` 跳过鉴权。
- **前端**：`sidecarFetch` / 异步 `sidecarWebSocketUrl` 全服务接入。
- **验证**：`./scripts/verify.sh`（483 pytest passed）。

## 2026-06-29 会话 18（OSR-09 CLI 权限策略 · D30）

- **D30**：维持 `--dangerously-skip-permissions`；`README.md` §安全与 CLI 权限 · `SECURITY.md`。
- **OSR-00**：维护者自行发布前验收。

## 2026-06-29 会话 18b（OSR-10 README + 源码构建 · 已 commit `6178bc5`）

- **`docs/BUILD_FROM_SOURCE.md`** · README §安装方式；缺产品截图。

## 2026-06-29 会话 17（OSR-07 Secret scanning CI）

- **`.github/workflows/secret-scan.yml`**：`gitleaks/gitleaks-action@v3`，`push`/`pull_request` 触发。
- **`.gitleaks.toml`**：测试目录与合成 key 允许列表。
- **验证**：`./scripts/verify.sh`。
- **下次优先**：OSR-10 或 OSR-08/09（待产品决策）。

## 2026-06-29 会话 16（OSR-06 社区与健康文件）

- **SECURITY.md**：私密漏洞报告渠道（GitHub Private Vulnerability Reporting）、响应时间线、范围与已知 OSR 加固项索引。
- **CODE_OF_CONDUCT.md**：Contributor Covenant 2.1。
- **链接**：`CONTRIBUTING.md`、`.github/ISSUE_TEMPLATE/security_report.md`、`README.md` 文档地图。
- **验证**：`./scripts/verify.sh`。
- **下次优先**：OSR-07 Secret scanning CI。
