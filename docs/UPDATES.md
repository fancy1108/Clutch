# Clutch — 应用内自动更新（OSR-20）

> **状态：Go-live ✅（v1.0.2，2026-07-01）** — [Release](https://github.com/fancy1108/Clutch/releases/tag/v1.0.2) 已挂 `latest.json`、`Clutch.app.tar.gz`、`.sig`。Loop 见 `release/1.0.3-loop`（v1.0.3）。

---

## 0. 准备 vs 上线

| 阶段 | 用户可见 | 维护者动作 |
|------|----------|------------|
| **Prep** | 无横幅（GitHub 尚无 `latest.json`） | 合入代码；配置 Secret；**勿**跑 updater workflow |
| **Go-live（v1.0.2 起）** | 有新版本时显示更新横幅；安装后重启 | 常规 `release.yml` 发 DMG → 手动跑 `Release (updater assets)` |

**v1.0.0 / v1.0.1** 安装包内**没有** updater，永远无法应用内升级；需**手动安装**首个带 updater 的 DMG（v1.0.2+）一次。

**Windows：** v1.0.2 提供 MSI/NSIS，但**无**应用内自动更新；请从 [Releases](https://github.com/fancy1108/Clutch/releases) 手动下载新版本。

---

## 1. 已实现组件

| 项 | 路径 |
|----|------|
| Tauri updater 插件 + 进程重启 | `apps/desktop/src-tauri/` |
| 更新横幅 UI | `apps/desktop/src/components/UpdateBanner.tsx` |
| 检查 / 下载 / 安装逻辑 | `apps/desktop/src/services/appUpdater.ts` |
| 设计 token 样式 | `surfaceStyles.ts` → `BANNER_*` |
| 中英文文案 | `LanguageContext.tsx` |
| 静态预览 | `docs/previews/update-banner-preview.html` |
| `latest.json` 合并脚本 | `scripts/merge-updater-manifest.sh` |
| Updater 专用 CI（**仅手动**） | `.github/workflows/release-updater.yml` |
| 常规 DMG Release（不变） | `.github/workflows/release.yml` |

**客户端行为：** 打包版启动约 4 秒后 `check()`；若远程 semver 大于当前版本 → 显示横幅；拉取失败时**静默忽略**。

---

## 2. 维护者：签名密钥

私钥**勿提交仓库**。公钥已写入 `apps/desktop/src-tauri/tauri.conf.json` → `plugins.updater.pubkey`。

本地密钥：

| 文件 | 用途 |
|------|------|
| `~/.clutch-updater-keys` | 私钥 |
| `~/.clutch-updater-keys.pub` | 公钥（与 `tauri.conf.json` 一致） |

GitHub **Settings → Secrets → Actions**：

| Secret | 值 |
|--------|-----|
| `TAURI_SIGNING_PRIVATE_KEY` | `cat ~/.clutch-updater-keys` 全文 |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | （可选）生成密钥时若设密码则必填 |

**写入 Secret 推荐方式（避免格式错误）：**

```bash
gh secret set TAURI_SIGNING_PRIVATE_KEY --repo fancy1108/Clutch < ~/.clutch-updater-keys
```

**故障排查：** CI 报 `failed to decode base64 secret key: Invalid symbol 37`（`%`）时，Secret 内容格式错误。请删除并重建 `TAURI_SIGNING_PRIVATE_KEY`：粘贴 `~/.clutch-updater-keys` 的**完整原文**（minisign 私钥，首行 `untrusted comment: rsign encrypted secret key`），**不要**用 `.pub` 文件、不要加引号、不要 URL 编码。修复后重跑 **Release (updater assets)**。

---

## 3. Go-live 清单（每个带 updater 的版本）

以 **v1.0.2** 为例（已完成）：

- [x] 本版 DMG 已通过常规 `release.yml`（push `v*` tag）发布 — tag `v1.0.2`
- [x] `TAURI_SIGNING_PRIVATE_KEY` 已配置且与嵌入公钥配对
- [x] Actions → **Release (updater assets)** → `release_tag=v1.0.2` — [run #28465904210](https://github.com/fancy1108/Clutch/actions/runs/28465904210) ✅
- [x] Release 页存在：`latest.json`、`Clutch.app.tar.gz`、`Clutch.app.tar.gz.sig`
- [x] 验证：
  ```bash
  curl -sL https://github.com/fancy1108/Clutch/releases/latest/download/latest.json | python3 -m json.tool
  ```
- [x] 更新 `CHANGELOG.md`、`docs/releases/v1.0.2.md`、`PRODUCT_INTRO.md`
- [x] Release 说明：v1.0.0/1.0.1 用户须手动安装本版一次

**下一版（如 v1.0.3）重复：** 打 tag → 确认 DMG 在 Release → 跑 updater workflow（同一 `release_tag`）→ 验证 `latest.json` → 更新 CHANGELOG / 快照。

---

## 4. 工作原理

1. 客户端请求 `…/releases/latest/download/latest.json`
2. 远程 semver **大于** 当前版本 → 显示更新横幅
3. 下载 `.tar.gz`，公钥验签 → 安装 → 重启

配置：`tauri.conf.json` → `plugins.updater.endpoints`。

---

## 5. 相关 Task

- **OSR-20** — 应用内自动更新 · macOS（Prep ✅ · Go-live ✅ v1.0.2）
- **OSR-19** — Windows 桌面分发 → v1.0.2 Release 已含 MSI/NSIS
