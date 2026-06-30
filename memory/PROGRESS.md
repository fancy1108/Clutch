# PROGRESS — release/1.0.2-updater

> **发版：** v1.0.2 · **分支：** `release/1.0.2-updater`  
> **路径：** `/Users/fancy/clutch-release-1.0.2-updater`

## 本分支切片（仅 OSR-20 · 应用内更新）

- UpdateBanner、`appUpdater.ts`、Tauri `plugin-updater` + `plugin-process`
- `release-updater.yml`（macOS · 手动 workflow）
- `docs/UPDATES.md`、`tauri.conf.json` → `plugins.updater`
- UX：失败提示、ready 无「稍后」、横幅动态顶距（`--clutch-update-banner-h`）

**不在本分支：** Windows 安装包 → 已合 `main`（PR #17）

## v1.0.2 vs v1.0.3

| 切片 | 版本 |
|------|------|
| Windows（#17）+ Updater（本分支） | **v1.0.2** |
| Loop 工作流 | **v1.0.3**（`release/1.0.3-loop` · `../clutch-release-1.0.3-loop`） |

## Next Actions

- [x] Sync `origin/main`
- [x] `verify.sh` + DMG 冒烟（Prep：无横幅）
- [x] UX 改进 + 静态预览
- [x] **OSR-20 prep commit**
- [ ] 合入 `dev` → tag **v1.0.2**（不含 loop）
- [ ] Go-live：`docs/UPDATES.md` §3
