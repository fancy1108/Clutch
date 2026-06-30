# Clutch — 应用内自动更新（OSR-20）

> **状态：v1.0.2 切片** — branch `release/1.0.2-updater`；与 **Windows 安装包**（PR #17，已合 `main`）同属 **v1.0.2 发版**。Loop 见 `release/1.0.3-loop`（v1.0.3）。

---

## 0. 准备 vs 上线

| 阶段 | 用户可见 | 维护者动作 |
|------|----------|------------|
| **Prep（当前）** | 无横幅（GitHub 尚无 `latest.json`） | 合入代码；可选配置 Secret；**勿**跑 updater workflow |
| **Go-live** | 1.0.x 旧用户仍须手动装一次；之后可应用内更新 | 完成 §3 清单 → 发版 → 手动跑 `Release (updater assets)` |

**v1.0.0 / v1.0.1** 安装包内**没有** updater，永远无法应用内升级；需手动安装首个带 updater 的 DMG 一次。

---

## 1. 已完成的准备工作

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

客户端行为（Prep 阶段）：打包版启动约 4 秒后 `check()`；若 `latest.json` 不存在或拉取失败，**静默忽略**，不打扰用户。

---

## 2. 维护者：签名密钥（Go-live 前配置）

私钥**勿提交仓库**。公钥已写入 `apps/desktop/src-tauri/tauri.conf.json` → `plugins.updater.pubkey`。

本地密钥（生成于 prep 会话）：

| 文件 | 用途 |
|------|------|
| `~/.clutch-updater-keys` | 私钥 |
| `~/.clutch-updater-keys.pub` | 公钥（与 `tauri.conf.json` 一致） |

GitHub **Settings → Secrets → Actions**：

| Secret | 值 |
|--------|-----|
| `TAURI_SIGNING_PRIVATE_KEY` | `cat ~/.clutch-updater-keys` 全文 |

Prep 阶段可先写入 Secret，但**不要**跑 updater workflow，避免在未就绪的 Release 上挂 `latest.json`。

---

## 3. Go-live 清单（专门发 updater 版本时执行）

- [ ] 本版 DMG 已通过常规 `release.yml`（push `v*` tag）发布
- [ ] `TAURI_SIGNING_PRIVATE_KEY` 已配置且与嵌入公钥配对
- [ ] Actions → **Release (updater assets)** → 输入**同一** `release_tag`
- [ ] Release 页存在：`latest.json`、`*.app.tar.gz`、`.sig`（macOS）
- [ ] 验证：
  ```bash
  curl -sL https://github.com/fancy1108/Clutch/releases/latest/download/latest.json | python3 -m json.tool
  ```
- [ ] 更新 `CHANGELOG.md`、`docs/releases/`、`PRODUCT_INTRO.md`（用户可见能力）
- [ ] Release 说明：v1.0.0/1.0.1 用户须手动安装本版一次

---

## 4. 工作原理（Go-live 后）

1. 客户端请求 `…/releases/latest/download/latest.json`
2. 远程 semver **大于** 当前版本 → 显示更新横幅
3. 下载 `.tar.gz`，公钥验签 → 安装 → 重启

配置：`tauri.conf.json` → `plugins.updater.endpoints`。

---

## 5. 相关 Task

- **OSR-20** — 应用内自动更新 · macOS（Prep ✅ · Go-live ❌）
- **OSR-19** — Windows 桌面分发 → **`dev` 上合入 PR #17**，不在本 worktree
