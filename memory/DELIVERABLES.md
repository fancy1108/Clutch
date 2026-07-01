# DELIVERABLES（Task 交付索引）

> **角色：** Task ID → Git commit → Verification → 证据路径。**不复制** `git diff`（代码真相在 Git）。  
> **何时写：** 每个**代码 Task** 完成并 commit 后，在 Check-out 追加一节（见 `CLAUDE.md` §Check-out）。  
> **生命周期：** 见 [`docs/document-governance.md`](../docs/document-governance.md) §文档生命周期；冷数据见 [`archive/`](./archive/)。  
> **逐文件 diff：** `git show <commit> --stat` / `git show <commit>`

## 填写模板（复制后改）

```markdown
### <Task-ID> ✅ | ⚠️ 部分 | ❌ 回滚
- **日期：** YYYY-MM-DD
- **Commit：** `<hash>` — `<git log -1 --format=%s>`
- **Verification：** `<命令>` → `<结果摘要>`
- **证据：** `runs/verification/<date>-<task-id>.log` 或 [CI #N](url) 或 `—`（门禁已覆盖）
- **交付文件：**（一行一个，只写路径 + 一句话职责；详情 `git show`）
  - `path/to/file` — …
```

**重定向示例（代码 Task 推荐）：**

```bash
cd services/orchestrator && uv run pytest tests/test_xxx.py -v \
  | tee "../../runs/verification/$(date +%Y-%m-%d)-M1-02-pytest.log"
```

---


## Active Deliverables

> 进行中 Task 的交付索引写在此处。完成后移入 **Recently Completed** 或归档。

### OSR-16 ✅ Debug API 收敛 + WebView CSP
- **日期：** 2026-06-29
- **Commit：** `—`（未 commit，工作区实现）
- **Verification：** `cd services/orchestrator && uv run pytest tests/test_z_release_hardening.py tests/test_run_debug_api.py tests/test_hybrid_audit_d29_regression.py tests/test_sidecar_auth.py -v` · `./scripts/verify.sh`
- **证据：** `—`
- **交付文件：**
  - `services/orchestrator/src/release_hardening.py` — frozen/debug/docs gate helpers
  - `services/orchestrator/src/main.py` — conditional OpenAPI + debug 404
  - `services/orchestrator/src/sidecar_auth.py` — public paths respect `api_docs_enabled()`
  - `services/orchestrator/tests/test_z_release_hardening.py` — frozen release regression tests
  - `apps/desktop/src-tauri/tauri.conf.json` — production CSP + `devCsp` for Vite HMR
  - `SECURITY.md` — debug API opt-in documented

### OSR-17 ✅ PyInstaller `console=False`
- **日期：** 2026-06-29
- **Commit：** `—`（未 commit，工作区实现）
- **Verification：** `./scripts/verify.sh` · `grep console=False services/orchestrator/clutch.spec`
- **证据：** `—`
- **交付文件：**
  - `services/orchestrator/clutch.spec` — `console=False` hides sidecar terminal on macOS

---

## Recently Completed（v1.0.0 · T2）

### Ollama Models Config 本机同步 ✅
- **日期：** 2026-07-01
- **Commit：** `2257560` — `fix(models): sync Settings Ollama list with local ollama list`
- **Verification：** `cd services/orchestrator && uv run pytest tests/test_models_config_api.py -q` → 21 passed · pre-commit `verify.sh` → build + vitest 48 + pytest 523 passed
- **证据：** `—`
- **交付文件：**
  - `services/orchestrator/src/models_config.py` — `local_ollama_tags` / sync / 可用性 / 隐藏未安装内置项 / `active_model_id` 回退
  - `services/orchestrator/src/main.py` — POST `/api/models/config` 激活前 sync
  - `services/orchestrator/tests/test_models_config_api.py` — 本机 tag 列表与回退测试
  - `docs/PRODUCT_INTRO.md` — §3.4 Model Provider Settings 行为说明
  - `CHANGELOG.md` — `[Unreleased]` Fixed 条目

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


---

## Archive Index

| 里程碑 | 路径 |
|--------|------|
| M0 | [`archive/DELIVERABLES-M0.md`](./archive/DELIVERABLES-M0.md) |
| M1 | [`archive/DELIVERABLES-M1.md`](./archive/DELIVERABLES-M1.md) |
| M2–M4 / P2 | [`archive/DELIVERABLES-M2-M4-P2.md`](./archive/DELIVERABLES-M2-M4-P2.md) |
| M3（工具链） | [`archive/DELIVERABLES-M3.md`](./archive/DELIVERABLES-M3.md) |
| D25 / 迭代 | [`archive/DELIVERABLES-POST-MVP.md`](./archive/DELIVERABLES-POST-MVP.md) |
| HRT | [`archive/DELIVERABLES-HRT.md`](./archive/DELIVERABLES-HRT.md) |
| OSR（历史） | [`archive/DELIVERABLES-OSR.md`](./archive/DELIVERABLES-OSR.md) |
| PROGRESS 会话 | [`archive/PROGRESS-2026-Q2.md`](./archive/PROGRESS-2026-Q2.md) |
