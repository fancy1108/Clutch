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

> 进行中 Task 的交付索引写在此处。完成后移入 **Recently Completed** 或归档。

_（当前无进行中代码 Task — v1.0.3 Loop 开工后在此登记。）_

---

## Recently Completed（v1.0.3 · dev · 未发版）

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
