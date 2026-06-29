# Clutch 文档索引

> 仓库根目录只保留 **GitHub 社区约定**与 **Agent 治理入口**；产品与架构长文集中在本目录。  
> 五层文档治理见 [`document-governance.md`](./document-governance.md)。

---

## 快速导航

| 你是谁 | 先读 |
|--------|------|
| 新用户 / 评估产品 | [`PRODUCT_INTRO.md`](./PRODUCT_INTRO.md) |
| 安装 DMG | [`INSTALL.md`](./INSTALL.md) |
| 从源码开发 | [`BUILD_FROM_SOURCE.md`](./BUILD_FROM_SOURCE.md) |
| 贡献代码 | 根目录 [`CONTRIBUTING.md`](../CONTRIBUTING.md) + [`CLAUDE.md`](../CLAUDE.md) |
| 前端 UI 开发 | [`UI_UX_GUIDELINES.md`](./UI_UX_GUIDELINES.md) |
| 架构与数据流 | [`ARCHITECTURE.md`](./ARCHITECTURE.md) |

---

## 产品与架构

| 文档 | 用途 |
|------|------|
| [`PRODUCT_INTRO.md`](./PRODUCT_INTRO.md) | 定位、痛点、功能清单、运行机制 |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | 系统架构、LangGraph 工作流、WebSocket、ADR |
| [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) | Goals / Non-Goals |
| [`EXTENSIBILITY.md`](./EXTENSIBILITY.md) | 官方扩展点与禁止替换区域 |
| [`STABILITY.md`](./STABILITY.md) | API / Schema 稳定性承诺 |
| [`PERFORMANCE.md`](./PERFORMANCE.md) | 性能基线与 benchmark 说明 |

---

## 安装、隐私与构建

| 文档 | 用途 |
|------|------|
| [`INSTALL.md`](./INSTALL.md) | DMG 安装、Gatekeeper、首次使用、卸载 |
| [`BUILD_FROM_SOURCE.md`](./BUILD_FROM_SOURCE.md) | 克隆、依赖、`pnpm tauri:dev`、本地打包 |
| [`DATA_AND_PRIVACY.md`](./DATA_AND_PRIVACY.md) | 本地数据目录、第三方 LLM、用户权利 |

---

## 开源、安全与治理

| 文档 | 用途 |
|------|------|
| [`OPEN_SOURCE_RELEASE.md`](./OPEN_SOURCE_RELEASE.md) | OSR-xx 开源排期与验收 |
| [`GOVERNANCE.md`](./GOVERNANCE.md) | 维护者决策与合并政策 |
| [`document-governance.md`](./document-governance.md) | 五层架构、权威真相（SoT）、文档生命周期与归档 |
| 根目录 [`SECURITY.md`](../SECURITY.md) | 漏洞私密报告（GitHub 约定放根目录） |
| 根目录 [`CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md) | 社区行为准则 |
| 根目录 [`CHANGELOG.md`](../CHANGELOG.md) | 版本变更记录（Release 硬门禁） |
| [`releases/`](./releases/) | 各版本产品快照（历史；当前见 `PRODUCT_INTRO.md`） |

---

## 前端与设计

| 文档 | 用途 |
|------|------|
| [`UI_UX_GUIDELINES.md`](./UI_UX_GUIDELINES.md) | React + Tailwind 组件与视觉规范（权威） |
| [`specs/core/design.md`](../specs/core/design.md) | 视觉设计历史快照 → 以上规范 |

---

## Agent 运行态与任务（`memory/` · `specs/`）

| 文档 | 用途 |
|------|------|
| [`memory/PROGRESS.md`](../memory/PROGRESS.md) | 跨会话进度接力 |
| [`memory/FILEMAP.md`](../memory/FILEMAP.md) | 改代码去哪个文件 |
| [`memory/DECISIONS.md`](../memory/DECISIONS.md) | 架构决策与开放问题 |
| [`specs/core/tasks.md`](../specs/core/tasks.md) | M0–M4 开发任务清单 |
| [`specs/core/hybrid-runtime-plan.md`](../specs/core/hybrid-runtime-plan.md) | D25 Hybrid Runtime（HRT-xx） |

---

## 调研与参考（非权威 · 只读）

| 文档 | 用途 |
|------|------|
| [`research/`](./research/) | 探索性设计笔记 — **Research Notice**，非真相源 |
| [`archive/`](./archive/) | 历史叙事（规划、handover）— **Archive Notice** |
| [`agents/`](./agents/) | Issue tracker / triage 技能说明 |

---

*仓库入口：[`README.md`](../README.md) · 治理权威：[`CLAUDE.md`](../CLAUDE.md)*
