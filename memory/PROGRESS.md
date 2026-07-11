# PROGRESS

> **生命周期：** 见 [`docs/document-governance.md`](../docs/document-governance.md) §文档生命周期。  
> 主文件仅保留当前状态 + 最近 10 次会话；更早记录见 [`archive/PROGRESS-2026-Q2.md`](./archive/PROGRESS-2026-Q2.md) · [`archive/PROGRESS-2026-Q3.md`](./archive/PROGRESS-2026-Q3.md)。

## Current Status

- **阶段：** **v1.2.1 准备完成**（Chat/Design/Models hotfix + Sidecar 热更 D37）— `./scripts/verify.sh` ✅；待 commit → PR `dev`→`main` → tag
- **版本号：** `1.2.1`（package / tauri / Cargo / cask version；cask sha256 待 DMG 后 sync）
- **Release：** 上一版 [v1.2.0](https://github.com/fancy1108/Clutch/releases/tag/v1.2.0)；Win 继续 [v1.1.1](https://github.com/fancy1108/Clutch/releases/tag/v1.1.1)
- **Windows：** 本版不发安装包

## Next Actions

- Commit → PR `dev`→`main` → 确认后 tag `v1.2.1` → DMG + updater + Homebrew sha
- **#23** — Windows smoke 继续用 v1.1.1

## Recent Sessions

## 2026-07-11 会话（热更 D37 + v1.2.1 打包准备）

- **D37** Sidecar 热更：Application Support 补丁、静默下载、Settings 旁「更新已就绪」、仅重启 sidecar
- **文档** DECISIONS / UPDATES §5 / PRODUCT_INTRO / FILEMAP / `write-sidecar-patch-manifest.sh`
- **UX** 与全量 Update 互斥；预览 `docs/previews/sidecar-hotpatch-ux-preview.html`
- **发版策略** 本次 bugfix仍走 **1.2.1 全量更新**（1.2.0 无热更客户端）
- **校验** `./scripts/verify.sh` ✅（build + vitest 128 + pytest 679 + doc-drift）

## 2026-07-11 会话（v1.2.0 Chat 回归诊断 + 修复）

- **现象** 1.2.0 DMG Chat 气泡：`expected string or bytes-like object, got 'dict'`
- **根因** Design 把 `http_chat_complete` 改为返回 dict；`sanitize_engine_output` → `re.sub` 收到 dict
- **修复** `extract_content` 解包；Design 底栏 / 调色板；Agnes `/models` probe

## 2026-07-10 会话（v1.2.0 updater assets）

- **Release (updater assets)** `release_tag=v1.2.0` ✅ — `latest.json` · `Clutch.app.tar.gz` · `.sig`

## 2026-07-10 会话（v1.2.0 发版完成）

- **#47** merge · tag `v1.2.0` · DMG + SHA256SUMS · Homebrew · macOS-only

## 2026-07-10 会话（D36 Design 会话模型 + 原型交互画布重做）

- **决策** D36：Design = 工作区 session；Header Coding/Design；语言进 Settings

## 2026-07-10 会话（D35 Design 模式落地 · 已被 D36 修订）

- D35 内建 Design — 形态已由 D36 替换

## 2026-07-06 会话（MiMo Code CLI + v1.1.2 发版准备）

- MiMo / Cursor Agent CLI · v1.1.2 发版材料

## 2026-07-04 会话（#30 merge + 平台 chrome 拆分）

- 见 archive
