# 安装渠道 — Clutch 采用方案

> **结论（2026-07）：** 不追求 Codex 级「官方 brew 一条命令」，但让 Mac 用户**尽量省事**、维护成本**尽量低**。  
> **发版 / AI 代劳：** [`RELEASE_MAINTAINER.md`](./RELEASE_MAINTAINER.md)  
> **用户安装：** [`INSTALL.md`](./INSTALL.md) · [`scripts/install.sh`](../scripts/install.sh)

---

## 我们选定的方案

| 平台 | 给用户推荐的方式 | 维护成本 |
|------|------------------|----------|
| **macOS（M 芯片）** | ① `curl \| bash` ② `brew tap fancy1108/clutch` + `brew install --cask clutch` | 发版后 AI 或 CI 同步 tap（见 [`RELEASE_MAINTAINER.md`](./RELEASE_MAINTAINER.md)） |
| **Windows** | 下载 exe / `irm` 脚本 | 暂不上 winget（[#23](https://github.com/fancy1108/Clutch/issues/23)） |
| **Intel Mac** | 不支持安装包 | 无 |

**刻意不做（以后再说）：** Homebrew 官方 cask · winget 官方 · `npm install -g` · Intel DMG

---

## 用户怎么装

### macOS · Apple Silicon

```bash
curl -fsSL https://raw.githubusercontent.com/fancy1108/Clutch/main/scripts/install.sh | bash
```

```bash
brew tap fancy1108/clutch
brew install --cask clutch
```

Tap：[github.com/fancy1108/homebrew-clutch](https://github.com/fancy1108/homebrew-clutch)

### Windows

```powershell
irm https://raw.githubusercontent.com/fancy1108/Clutch/main/scripts/install.ps1 | iex
```

或 [Releases](https://github.com/fancy1108/Clutch/releases) 下载（**未实体机全量验收**）。

---

## 维护者（发版 + tap）

**完整步骤、AI 协作话术、CI 自动同步：** [`RELEASE_MAINTAINER.md`](./RELEASE_MAINTAINER.md)

摘要：

1. 对 AI 说「帮我发 vX.Y.Z」→ CHANGELOG、版本号、verify、tag（你确认后 push）
2. CI 打 DMG 后同步 tap：`CLUTCH_VERSION=vX.Y.Z ./scripts/sync-homebrew-tap.sh`（**AI 可代跑**）
3. 可选：在 GitHub 配 `HOMEBREW_TAP_GITHUB_TOKEN`，`release.yml` 自动 bump tap

---

## 平台说明

- **Intel Mac：** 暂不支持 DMG（**D32**）→ [`BUILD_FROM_SOURCE.md`](./BUILD_FROM_SOURCE.md)
- **winget：** 清单在 `packaging/winget/`，等 #23 后再提 PR
- **桌面应用 vs CLI：** 装的是 DMG/EXE，不是 `npm install -g`

---

## 技术附录

| 文件 | 用途 |
|------|------|
| [`RELEASE_MAINTAINER.md`](./RELEASE_MAINTAINER.md) | 发版 checklist · AI 协作 · PAT 配置 |
| [`packaging/homebrew/Casks/clutch.rb`](../packaging/homebrew/Casks/clutch.rb) | cask 模板 |
| [`scripts/sync-homebrew-tap.sh`](../scripts/sync-homebrew-tap.sh) | bump tap |
| [`packaging/winget/`](../packaging/winget/) | 未来 winget |
