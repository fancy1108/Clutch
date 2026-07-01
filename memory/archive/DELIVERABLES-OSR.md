# Archive Notice

This file is archived and read-only.

Do not append new records here.

For current project state, see:

- memory/PROGRESS.md
- memory/DELIVERABLES.md
- memory/ROADMAP.md

Archived on: 2026-06-29
Reason: OSR T0–T1 deliverables archived

---

# DELIVERABLES Archive — OSR

## 已交付（OSR · 开源排期）

### OSR-14 ✅ 首次启动向导
- **日期：** 2026-06-29
- **Commit：** `—`（未 commit，工作区实现）
- **Verification：** `cd services/orchestrator && uv run pytest tests/test_onboarding_preference.py` · `pnpm vitest run src/services/agentProvisioning.test.ts`
- **证据：** `—`
- **交付文件：**
  - `apps/desktop/src/components/onboarding/OnboardingWizard.tsx` — 7 屏状态机壳
  - `apps/desktop/src/services/agentProvisioning.ts` — Connect CLI 幂等建 Agent
  - `apps/desktop/src/services/onboardingApi.ts` — health / onboarding 偏好
  - `services/orchestrator/src/preferences_storage.py` — `onboarding_completed`（已存在）

### OSR-13 ✅ API Key → macOS Keychain + 明文迁移
- **日期：** 2026-06-29
- **Commit：** `ee91743` — feat(osr-13): store provider API keys in macOS Keychain
- **Verification：** `cd services/orchestrator && uv run pytest -q` → 486 passed · `./scripts/verify.sh` → OK
- **证据：** `—`（本地 pytest）
- **交付文件：**
  - `services/orchestrator/src/credentials/keychain_store.py` — Keychain 读写（`com.clutch.app`）
  - `services/orchestrator/src/credentials/credential_store.py` — 统一加载/持久化 + 迁移
  - `services/orchestrator/tests/test_keychain_store.py` — 迁移与不落盘断言
  - `services/orchestrator/src/models_config.py` — save/load 走 credential store
  - `SECURITY.md` · `docs/DATA_AND_PRIVACY.md` · `docs/PRODUCT_INTRO.md` — 文档对齐

### OSR-12 ✅ Release CI + 发版敏感信息门禁（v1.0.0 实跑验证）
- **日期：** 2026-06-29
- **Commit：** `109d427`（workflow）· 构建修复 `dd9fa20`
- **Verification：** [Actions #28358384072](https://github.com/fancy1108/Clutch/actions/runs/28358384072) → success
- **证据：** [Release v1.0.0](https://github.com/fancy1108/Clutch/releases/tag/v1.0.0) — `Clutch_1.0.0_aarch64.dmg` · `SHA256SUMS.txt`
- **交付文件：**
  - `.github/workflows/release.yml` — gitleaks · preflight · DMG · SHA256SUMS · workflow_dispatch
  - `scripts/release-preflight.sh` — INV-R1～R4
  - `apps/desktop/src/components/ui/UnderDevelopmentNotice.tsx` — CI 构建修复

### OSR-15 ✅ 安装与隐私文档
- **日期：** 2026-06-29
- **Commit：** `04d6b30` — `docs(osr): add INSTALL and DATA_AND_PRIVACY guides (OSR-15)`
- **Verification：** `./scripts/verify.sh` → pass
- **交付文件：**
  - `docs/INSTALL.md` — DMG 用户安装全流程
  - `docs/DATA_AND_PRIVACY.md` — 本地数据与第三方数据流
  - `README.md` · `SECURITY.md` · `BUILD_FROM_SOURCE.md` 交叉引用

### OSR-08 ✅ Sidecar session token 鉴权
- **日期：** 2026-06-29
- **Commit：** `5744142` — `feat(osr): add sidecar session token auth for HTTP and WebSocket (OSR-08)`
- **交付文件：**
  - `services/orchestrator/src/sidecar_auth.py` · `main.py` middleware + WS gate
  - `services/orchestrator/tests/test_sidecar_auth.py`
  - `apps/desktop/src-tauri/src/lib.rs` · `Cargo.toml`
  - `apps/desktop/src/services/sidecarUrl.ts` + API 服务层 `sidecarFetch`
  - `docs/BUILD_FROM_SOURCE.md` — token 说明

### OSR-09 ✅ CLI 权限策略（D30 披露型）
- **日期：** 2026-06-29
- **Commit：** `6e4f634` — `docs(osr): document default CLI skip-permissions policy (OSR-09, D30)`
- **交付文件：**
  - `README.md` §安全与 CLI 权限
  - `SECURITY.md` · `memory/DECISIONS.md` D30

### OSR-10 ✅ README + 源码构建 + 产品截图
- **日期：** 2026-06-29
- **Commit：** `54714bd` — `docs(osr): add README screenshots, unsigned DMG release CI, and v1.0.0`
- **交付文件：**
  - `docs/images/Clutch_1.png` · `Clutch_2.png` — 产品截图
  - `README.md` — §产品截图 · §安装方式（未签名 DMG）
  - `docs/BUILD_FROM_SOURCE.md` — D31 交叉引用
  - `.github/workflows/release.yml` — 未签名 DMG Release CI（OSR-12 部分）
  - `memory/DECISIONS.md` D31 · BACKLOG/ROADMAP/OPEN_SOURCE_RELEASE 勾选同步

### OSR-10（部分）README + 源码构建
- **日期：** 2026-06-29
- **Commit：** `6178bc5` — `docs(osr): add BUILD_FROM_SOURCE and README install paths (OSR-10)`
- **Verification：** `./scripts/verify.sh` → pass
- **证据：** —
- **交付文件：**
  - `docs/BUILD_FROM_SOURCE.md` — 源码构建全流程
  - `README.md` — DMG vs 源码分叉（截图由后续 commit 补齐）

### OSR-07 ✅ Secret scanning CI
- **日期：** 2026-06-29
- **Commit：** `62542ca` — `ci(osr): add gitleaks secret scanning workflow (OSR-07)`
- **Verification：** `./scripts/verify.sh` → pass
- **证据：** —
- **交付文件：**
  - `.github/workflows/secret-scan.yml` — gitleaks on push/PR
  - `.gitleaks.toml` — test fixture allowlist

### OSR-06 ✅ 社区与健康文件
- **日期：** 2026-06-29
- **Commit：** `95a93f4` — `docs(osr): add SECURITY.md and CODE_OF_CONDUCT.md (OSR-06)`
- **Verification：** `./scripts/verify.sh` → pass
- **证据：** —
- **交付文件：**
  - `SECURITY.md` — 漏洞私密报告、响应 SLA、范围与已知限制
  - `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1
  - `CONTRIBUTING.md` — 链至 SECURITY.md
  - `.github/ISSUE_TEMPLATE/security_report.md` — 链至 SECURITY.md
  - `README.md` — 文档地图补充
  - `memory/BACKLOG.md` · `memory/ROADMAP.md` · `docs/OPEN_SOURCE_RELEASE.md` §7.7 — OSR-06 勾选

### OSR-16 / OSR-17 ✅ Debug API 收敛 + Sidecar 无控制台
- **日期：** 2026-06-29
- **Commit：** `e410897` — `feat(osr-16,osr-17): gate debug API in release and hide sidecar console`
- **Verification：** `pytest tests/test_z_release_hardening.py` + `./scripts/verify.sh`
- **证据：** `—`
- **交付文件：**
  - `services/orchestrator/src/release_hardening.py` — frozen/debug/docs gate helpers
  - `services/orchestrator/src/main.py` — conditional OpenAPI + debug 404
  - `services/orchestrator/src/sidecar_auth.py` — public paths respect `api_docs_enabled()`
  - `services/orchestrator/tests/test_z_release_hardening.py`
  - `apps/desktop/src-tauri/tauri.conf.json` — production CSP + `devCsp`
  - `services/orchestrator/clutch.spec` — `console=False`
  - `SECURITY.md` — debug API opt-in documented

---

