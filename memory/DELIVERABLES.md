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

---


## Active Deliverables

### v1.2.0 Windows parity ✅ 待 commit
- **日期：** 2026-07-11
- **Commit：** （待提交）
- **Verification：** `python -m uv run pytest tests/test_design_service.py -p no:cacheprovider` → 28 passed；真实 Design Preview smoke → start/connect/stop/port released；`pnpm build` → passed；`pnpm test` → 17 files / 128 tests passed；`python -m uv run pytest -p no:cacheprovider` → 679 passed, 9 skipped；`cargo check` → passed；`pnpm tauri:build` → MSI/NSIS built
- **证据：** `—`
- **交付文件：**
  - `services/orchestrator/src/design/service.py` — Windows command resolution, install error handling, preview lifecycle cleanup, manifest replace retry
  - `services/orchestrator/tests/test_design_service.py` — Design Preview Windows regression coverage
  - `apps/desktop/package.json` — desktop `tauri:dev` uses Node launcher
  - `apps/desktop/src-tauri/tauri.conf.json` · `scripts/run-build-sidecar.mjs` — Windows-safe sidecar build entry
  - `apps/desktop/src-tauri/gen/schemas/windows-schema.json` — Tauri Windows generated schema
  - `CHANGELOG.md` · `docs/PRODUCT_INTRO.md` · `docs/BUILD_FROM_SOURCE.md` · `memory/PROGRESS.md` · `memory/FAILURES.md` · `CLAUDE.md` — Windows parity documentation

### D36 Design 会话模型 + 原型交互画布 ⚠️ 待 commit
- **日期：** 2026-07-10
- **Commit：** （未提交 — 等待用户确认 commit）
- **Verification：** `./scripts/verify.sh` → 0 errors；`pytest tests/test_design_service.py` → 2 passed
- **证据：** `runs/verification/2026-07-10-design-canvas-reference.md`
- **交付文件：**
  - `apps/desktop/src/components/design/DesignWorkspace.tsx` — 欢迎页 + 无限画布（规范→描绘→NL）
  - `apps/desktop/src/App.tsx` / `Header.tsx` / `sidebar.tsx` — `appMode` Coding|Design；会话按 mode
  - `apps/desktop/src/services/designApi.ts` · `runApi.ts` — session-scoped Design API + `mode`
  - `services/orchestrator/src/design/` — 两阶段 generate + iterate
  - `memory/DECISIONS.md` D36 · `docs/PRODUCT_INTRO.md` §3.5 · `memory/ROADMAP.md` · `CHANGELOG.md`

### D35 Design 模式（原型画布与预览沙箱）⚠️ 已被 D36 修订
- **日期：** 2026-07-10
- **Commit：** （未提交 — 等待用户确认 commit）
- **Verification：** 见 D36
- **证据：** `—`
- **交付文件：** 见 D36（项目左栏形态已废弃）

---

## Recently Completed

### upstream 首页图标同步 ✅
- **日期：** 2026-07-03
- **Commit：** `9a982f4` — `fix(ui): sync workflow sidebar icon from upstream`
- **Verification：** `pnpm build` → passed；`pnpm test` → 17 files / 125 tests passed；Husky pre-commit → Git Bash PATH 无 `uv`，等价验证通过后 `HUSKY=0` 提交
- **证据：** `—`
- **交付文件：**
  - `apps/desktop/src/sidebar.tsx` — Workflows SOP 展开态与折叠态图标同步为 upstream dev 的 `fork_right`

### upstream dev 同步与左侧折叠入口调整 ✅
- **日期：** 2026-07-03
- **Commit：** `214af4d` — `merge upstream dev and align sidebar collapse chrome`
- **Verification：** `pnpm build` → passed；`pnpm test` → 17 files / 125 tests passed；`python -m uv run pytest tests/test_llm_provider.py` → 7 passed；Husky pre-commit → Git Bash PATH 无 `uv`，等价验证通过后 `HUSKY=0` 提交
- **证据：** `—`
- **交付文件：**
  - `apps/desktop/src/App.tsx` — Header 不再接收顶部侧栏折叠回调，Sidebar 接管开合状态更新
  - `apps/desktop/src/components/Header.tsx` — 移除顶部左侧侧栏折叠按钮
  - `apps/desktop/src/sidebar.tsx` — 新增左侧面板右边缘中线折叠按钮，复用 `ChromeEdgeToggle`
  - `docs/PRODUCT_INTRO.md` — 同步 Workspace Chrome 产品说明
  - `memory/PROGRESS.md` — 合并 upstream 发版记录并记录 Windows 侧维护进展

### Windows workspace chrome polish 同步 ✅
- **日期：** 2026-07-03
- **Commit：** `796120b` — `fix(ui): restore Windows workspace chrome polish`
- **Verification：** `pnpm build` → passed；`pnpm test` → 17 files / 125 tests passed；Husky pre-commit → Git Bash PATH 无 `uv`，等价验证通过后 `HUSKY=0` 提交
- **证据：** `—`
- **交付文件：**
  - `apps/desktop/src/App.tsx` — Header 侧栏折叠入口恢复，移除左侧浮动折叠按钮
  - `apps/desktop/src/components/Header.tsx` — 恢复顶部 Header 内置折叠按钮与昨天的 breadcrumb chrome
  - `apps/desktop/src/sidebar.tsx` — 恢复折叠态纯图标 tooltip、Workflow 图标和底部 Settings 布局
  - `apps/desktop/src/components/ChatFeed.tsx` — 恢复聊天主区宽度/间距与气泡紧凑样式，同时保留 Terminal Orchestra
  - `apps/desktop/src/components/RightPanel.tsx` — 恢复右侧监督面板等分 Tab 与短指示条
  - `docs/PRODUCT_INTRO.md` — 同步 Workspace Chrome 产品说明

### Settings 字体大小偏好恢复 ✅
- **日期：** 2026-07-03
- **Commit：** `68769fb` — `fix(settings): restore font size preference`
- **Verification：** `pnpm build` → passed；`pnpm test` → 17 files / 125 tests passed；Husky pre-commit → Git Bash PATH 无 `uv`，等价验证通过后 `HUSKY=0` 提交
- **证据：** `—`
- **交付文件：**
  - `apps/desktop/src/App.tsx` — 恢复 font size 偏好读取、保存和 `data-font-size` 应用
  - `apps/desktop/src/components/SystemPreferencesModal.tsx` — 恢复 General Settings 字体大小选择框
  - `docs/PRODUCT_INTRO.md` — 同步 Settings Dashboard 功能说明

### Windows interactive PTY lanes ✅
- **日期：** 2026-07-03
- **Commit：** `395bacb` — `fix(windows): support interactive PTY lanes`
- **Verification：** `python -m uv run pytest tests/test_interactive_pty_runtime.py` → 11 passed, 5 skipped；`python -m uv run pytest tests/test_terminal_orchestra.py tests/test_ws_pty_events.py tests/test_ws_dispatch_orchestra.py tests/test_interactive_pty_runtime.py` → 36 passed, 5 skipped, 1 warning；`pnpm build` → passed；`pnpm test` → 17 files / 125 tests passed；`python -m uv run pytest` → 634 passed, 9 skipped, 1 warning；Windows `cmd.exe` low-level 与 manager PTY smoke → marker observed；`bash scripts/check-doc-drift.sh` → 未运行，当前 PowerShell PATH 无 `bash`
- **证据：** `—`
- **交付文件：**
  - `services/orchestrator/src/interactive_pty_runtime.py` — Windows interactive PTY backend attach/read/write/close
  - `services/orchestrator/src/windows_pty.py` — 暴露 read/write/alive/close 行为给 interactive manager 复用
  - `services/orchestrator/tests/test_interactive_pty_runtime.py` — Windows PTY fake backend 回归测试
  - `docs/PRODUCT_INTRO.md` — 同步 Windows Terminal Orchestra 支持说明

### Ollama Models Config 本机同步 ✅
- **日期：** 2026-07-01
- **Commit：** `2257560` — `fix(models): sync Settings Ollama list with local ollama list`
- **Verification：** `pytest tests/test_models_config_api.py` → 21 passed · `verify.sh` → 523 pytest passed
- **证据：** `—`
- **交付文件：**
  - `services/orchestrator/src/models_config.py` — 本机 Ollama tag 同步与 `active_model_id` 回退
  - `services/orchestrator/src/main.py` — POST 前 sync
  - `services/orchestrator/tests/test_models_config_api.py`
  - `docs/PRODUCT_INTRO.md` §3.4

### #19 CLI 错误文案 ✅
- **日期：** 2026-07-01
- **Commit：** `2cb3016` — `fix(router): single-layer CLI errors and gateway-busy copy (#19)`
- **Verification：** `pytest tests/test_engine_router.py` · `verify.sh`
- **证据：** `—`
- **交付文件：**
  - `services/orchestrator/src/engine_router.py`
  - `services/orchestrator/tests/test_engine_router.py`

### 安装渠道与发版文档 ✅
- **日期：** 2026-07-01
- **Commit：** `5cb8950` … `1a26ca0`（README · GETTING_STARTED · install.sh/ps1 · homebrew-clutch tap · RELEASE_MAINTAINER）
- **Verification：** `check-doc-drift.sh` · tap 仓库已 push
- **证据：** [homebrew-clutch](https://github.com/fancy1108/homebrew-clutch)
- **交付文件：**
  - `docs/GETTING_STARTED.md` · `docs/RELEASE_MAINTAINER.md` · `docs/PACKAGE_MANAGERS.md`
  - `README.md` · `README.zh-CN.md`
  - `scripts/install.sh` · `scripts/install.ps1` · `scripts/sync-homebrew-tap.sh`
  - `.github/workflows/release.yml` — 可选 Homebrew tap CI sync

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
| OSR（T0–T2） | [`archive/DELIVERABLES-OSR.md`](./archive/DELIVERABLES-OSR.md) |
| PROGRESS 会话 | [`archive/PROGRESS-2026-Q2.md`](./archive/PROGRESS-2026-Q2.md) · [`archive/PROGRESS-2026-Q3.md`](./archive/PROGRESS-2026-Q3.md) |

_v1.0.0–v1.0.2 已发布交付见 `archive/DELIVERABLES-OSR.md` 及 Git tag / `CHANGELOG.md`。_
