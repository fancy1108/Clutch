# 发版与安装渠道维护指南

> **读者：** 维护者（含通过 Cursor / Claude 代劳发版）。  
> **相关：** [`PACKAGE_MANAGERS.md`](./PACKAGE_MANAGERS.md) · [`UPDATES.md`](./UPDATES.md) · [`INSTALL.md`](./INSTALL.md)

---

## 一句话

**你对 AI 说「帮我发 v1.0.3」** → AI 改版本/CHANGELOG/校验/打 tag；CI 打 DMG；然后同步 Homebrew tap（可自动）。

你只需：**确认版本号**、**同意 push/tag**。

---

## 发版 checklist（macOS DMG）

| 步骤 | 谁做 | 说明 |
|------|------|------|
| 1. `CHANGELOG.md` 增加 `## [x.y.z]` | AI | `release-preflight.sh` 会检查（INV-R5） |
| 2. 版本号 `tauri.conf.json` / `package.json` | AI | 与 tag 一致 |
| 3. `./scripts/verify.sh` | AI | 通过后再 tag |
| 4. `git tag vX.Y.Z` + push tag | AI 准备，**你确认** | 触发 [`.github/workflows/release.yml`](../.github/workflows/release.yml) |
| 5. CI 上传 DMG + `SHA256SUMS.txt` | GitHub Actions | 约 15–30 分钟 |
| 6. 同步 Homebrew tap | AI 或 CI | 见下文 §Homebrew |
| 7. macOS 应用内更新（可选） | 你或 AI | 见 [`UPDATES.md`](./UPDATES.md) — 跑 `Release (updater assets)` |

Windows 安装包由 [`.github/workflows/windows-build.yml`](../.github/workflows/windows-build.yml) 构建；发版时确认 Release 页资产齐全。

---

## 跟 AI 协作怎么说

示例（复制到对话）：

```text
帮我发 v1.0.3：更新 CHANGELOG、版本号、跑 verify，我确认后再打 tag 和 push。
发完后同步 homebrew-clutch tap。
```

AI 通常会：

1. 编辑 `CHANGELOG.md`、`apps/desktop/src-tauri/tauri.conf.json`、`apps/desktop/package.json`
2. 跑 `./scripts/verify.sh`
3. commit（你要求时）
4. 等你回复「可以发了」后 `git tag` + `git push origin vX.Y.Z`
5. 等 Release 就绪后执行 `CLUTCH_VERSION=vX.Y.Z ./scripts/sync-homebrew-tap.sh`

**你不要自己记** `sync-homebrew-tap` 命令 — 交给 AI 即可。

---

## Homebrew tap 同步

**Tap 仓库：** [github.com/fancy1108/homebrew-clutch](https://github.com/fancy1108/homebrew-clutch)

用户安装：

```bash
brew tap fancy1108/clutch
brew install --cask clutch
```

### 方式 A — 手动 / AI 代跑（默认）

DMG 出现在 GitHub Release 后：

```bash
CLUTCH_VERSION=v1.0.3 ./scripts/sync-homebrew-tap.sh
```

要求：本机 `gh auth login`，对 `fancy1108/homebrew-clutch` 有 push 权限。

### 方式 B — CI 自动同步（推荐，一次性配置）

在 **Clutch 仓库** Settings → Secrets → Actions 添加：

| Secret 名 | 内容 |
|-----------|------|
| `HOMEBREW_TAP_GITHUB_TOKEN` | GitHub PAT，`fancy1108/homebrew-clutch` 的 **Contents: Read and write** |

创建 PAT：GitHub → Settings → Developer settings → Fine-grained token → 只勾选 `homebrew-clutch` 仓库。

配置后，每次 `push` 版本 tag，[`release.yml`](../.github/workflows/release.yml) 在 DMG 上传成功后会自动 bump tap。  
**未配置 Secret 时该步骤跳过**，不影响发版。

### 发版后自检

```bash
brew tap fancy1108/clutch
brew upgrade --cask clutch   # 或新机器上 install
```

---

## 用户安装方式（维护者不用重复解释）

详见 [`PACKAGE_MANAGERS.md`](./PACKAGE_MANAGERS.md)。

| 平台 | 推荐命令 |
|------|----------|
| macOS M 芯片 | `curl -fsSL …/install.sh \| bash` 或 `brew tap` + `brew install --cask clutch` |
| Windows | `irm …/install.ps1 \| iex` 或 Releases 下载（**未实体机全量验收**） |
| Intel Mac | **不支持** DMG（D32） |

---

## 刻意暂缓

| 项 | 原因 |
|----|------|
| Homebrew **官方** cask | 审核慢；未签名 DMG 易被拒 |
| **winget** 官方仓库 | Windows [#23](https://github.com/fancy1108/Clutch/issues/23) 未实体机验收 |
| **Intel Mac** DMG | 产品决定暂不投入（D32） |

---

## 文件索引

| 路径 | 用途 |
|------|------|
| [`scripts/release-preflight.sh`](../scripts/release-preflight.sh) | tag 前 CHANGELOG 等门禁 |
| [`scripts/sync-homebrew-tap.sh`](../scripts/sync-homebrew-tap.sh) | bump `homebrew-clutch` |
| [`scripts/install.sh`](../scripts/install.sh) / [`install.ps1`](../scripts/install.ps1) | 用户一键安装 |
| [`packaging/homebrew/Casks/clutch.rb`](../packaging/homebrew/Casks/clutch.rb) | cask 模板（与 tap 保持一致） |
| [`.github/workflows/release.yml`](../.github/workflows/release.yml) | DMG CI + 可选 tap 同步 |
