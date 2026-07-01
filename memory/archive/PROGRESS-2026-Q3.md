# Archive Notice

This file is archived and read-only.

Do not append new records here.

For current project state, see:

- memory/PROGRESS.md
- memory/DELIVERABLES.md
- memory/ROADMAP.md

Archived on: 2026-07-01
Reason: PROGRESS quarterly rotation — sessions beyond recent 10 moved from main file

---

# PROGRESS Archive — 2026 Q3（轮转）

> 从 `memory/PROGRESS.md` 轮转出的会话记录（2026-06-29 会话 16–22 及附记）。

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

## 附记（原 PROGRESS 游离条目 · OSR-13）

- **Sidecar**：`keyring` 存 Provider API Key（service `com.clutch.app`）；macOS 默认启用，`CLUTCH_USE_KEYCHAIN=0` 回退明文 `models.json`
- **迁移**：加载 `models.json` 时把 legacy `api_keys` 写入 Keychain 并从文件剥离
- **验证**：`uv run pytest` → 486 passed · `./scripts/verify.sh` → OK
- **Commit：** `ee91743` — feat(osr-13): store provider API keys in macOS Keychain
