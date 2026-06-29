# Clutch — OSR-xx 开源与 DMG 分发 Task 定义

> **Historical planning notes have been archived.**  
> Current execution status is maintained **ONLY** in [`memory/ROADMAP.md`](../memory/ROADMAP.md) §开源分发.  
> Do **not** record ✅/❌ status in this file.
>
> Archived narrative (readiness assessments, threat models, checklists): [`docs/archive/OPEN_SOURCE_RELEASE-planning-2026-Q2.md`](./archive/OPEN_SOURCE_RELEASE-planning-2026-Q2.md)

**铁律**仍以 [`CLAUDE.md`](../CLAUDE.md) 为准。用户可见能力见 [`PRODUCT_INTRO.md`](./PRODUCT_INTRO.md)。

### 读序

1. **本文 §7.2** — OSR-xx 编号、触发线、依赖  
2. [`memory/ROADMAP.md`](../memory/ROADMAP.md) §开源分发 — **唯一验收状态源**  
3. [`memory/FILEMAP.md`](../memory/FILEMAP.md) — 改代码路径  
4. 生态边界：[`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) · [`STABILITY.md`](./STABILITY.md) · [`EXTENSIBILITY.md`](./EXTENSIBILITY.md) · [`GOVERNANCE.md`](./GOVERNANCE.md)

---

## 7.1 触发线（T0–T3）

| 触发线 | 含义 | 典型时机 |
|--------|------|----------|
| **T0 · 持续** | 边做功能边做，低成本护栏 | 贯穿开发期 |
| **T1 · 公开仓库** | 仓库 public / 接受外部 PR | 核心路径可跑通 |
| **T2 · 首次 DMG 分发** | 陌生人安装 `.dmg` | Settings / Hybrid 体验定型 |
| **T3 · 生态成熟** | 跨平台、沙箱、自动更新 | 稳定 release 节奏后 |

---

## 7.2 OSR Task 定义表（权威）

| ID | 任务 | 触发线 | Phase | 估时 | 依赖 / 备注 |
|----|------|--------|-------|------|-------------|
| **OSR-00** | 外部视角审计（无指导安装全流程） | **T1 前** | 0 | 0.5–1d | 见归档 §7.6 |
| OSR-01 | 选定许可证 + 根目录 `LICENSE` | **T0** | — | 0.5d | MIT |
| OSR-02 | 仓库卫生（`.gitignore`、实验 runs） | **T0** | — | 0.5d | |
| OSR-03 | 文档与实现一致 | **T0** | — | 1d | 核对 `PRODUCT_INTRO` |
| OSR-04 | semver + `CHANGELOG.md` | **T0** | — | 0.5d | Release 硬门禁 |
| OSR-05 | 新代码安全护栏（review） | **T0** | — | 持续 | |
| **OSR-23** | `docs/PROJECT_SCOPE.md` | **T0** | — | 0.5d | |
| **OSR-24** | `docs/STABILITY.md` | **T0** | — | 0.5d | |
| **OSR-25** | `docs/EXTENSIBILITY.md` | **T0** | — | 0.5d | |
| OSR-06 | `SECURITY.md` + `CONTRIBUTING.md` + `CODE_OF_CONDUCT.md` | **T1** | 0 | 1–2d | |
| OSR-07 | Secret scanning CI（gitleaks） | **T1** | 0 | 0.5d | |
| OSR-08 | Sidecar session token 鉴权（HTTP + WS） | **T1** | 0 | 3–5d | |
| OSR-09 | CLI `--dangerously-skip-permissions` 策略 | **T1** | 0 | 2–3d | D30 披露 |
| OSR-10 | README + 源码构建 + 截图 | **T1** | 0 | 1d | |
| **OSR-26** | `docs/GOVERNANCE.md` | **T1** | 0 | 0.5d | |
| **OSR-27** | 兼容性矩阵 + `scripts/doctor.sh` | **T1** | 0 | 1d | |
| **OSR-28** | Issue / PR 模板 | **T1** | 0 | 0.5d | |
| OSR-11 | Apple 签名 + 公证 | **T2** | 1 | 2–3d | D31 可豁免 |
| OSR-12 | GitHub Actions Release DMG | **T2** | 1 | 2–3d | `release-preflight.sh` |
| OSR-13 | API Key → macOS Keychain + 迁移 | **T2** | 1 | 3–5d | |
| OSR-14 | 首次启动向导 | **T2** | 1 | 2–3d | |
| OSR-15 | `INSTALL.md` + `DATA_AND_PRIVACY.md` | **T2** | 1 | 1–2d | |
| OSR-16 | Debug API 收敛 + WebView CSP | **T2** | 1 | 1–2d | ✅ |
| OSR-17 | PyInstaller `console=False` | **T2** | 1 | 0.5d | ✅ |
| OSR-18 | OS 级沙箱 PoC（B-20） | **T3** | 2 | 2–4w | |
| OSR-19 | Windows MSI | **T3** | 2 | 1–2w | |
| OSR-20 | Tauri 自动更新 | **T3** | 2 | 3–5d | |
| OSR-21 | 工作流签名 / MCP 白名单 | **T3** | 2 | 1–2w | |
| OSR-22 | 外部安全审计 | **T3** | 2 | 外包 | |
| **OSR-29** | `docs/PERFORMANCE.md` 基线 | **T3** | 2 | 1–2d | |

---

## 7.4 Phase 对照

| Phase | 触发线 | 目标 |
|-------|--------|------|
| — | T0 | 持续护栏，不积累开源债 |
| Phase 0 | T1 | 可公开仓库 |
| Phase 1 | T2 | 可放心装 DMG |
| Phase 2 | T3 | 生态与深度加固 |

---

## 参考（规范 / 宪法 — 不归档）

| 资源 | 路径 |
|------|------|
| 验收状态（唯一） | [`memory/ROADMAP.md`](../memory/ROADMAP.md) §开源分发 |
| 交付证据 | [`memory/DELIVERABLES.md`](../memory/DELIVERABLES.md) · [`memory/archive/`](../memory/archive/) |
| Goals / Non-Goals | [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) |
| API 稳定性 | [`STABILITY.md`](./STABILITY.md) |
| 扩展边界 | [`EXTENSIBILITY.md`](./EXTENSIBILITY.md) |
| 维护者治理 | [`GOVERNANCE.md`](./GOVERNANCE.md) |
| 安装 / 隐私 | [`INSTALL.md`](./INSTALL.md) · [`DATA_AND_PRIVACY.md`](./DATA_AND_PRIVACY.md) |
| 架构 | [`ARCHITECTURE.md`](./ARCHITECTURE.md) |
| 历史规划全文 | [`archive/OPEN_SOURCE_RELEASE-planning-2026-Q2.md`](./archive/OPEN_SOURCE_RELEASE-planning-2026-Q2.md) |

---

*Task 定义变更时更新本文 §7.2；**禁止**在此维护验收勾选。*
