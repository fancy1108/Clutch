# 安装渠道 — Clutch 采用方案

> **结论（2026-07）：** 不追求 Codex 级「官方 brew 一条命令」，但让 Mac 用户**尽量省事**、维护成本**尽量低**。  
> **相关：** [`INSTALL.md`](./INSTALL.md) · [`scripts/install.sh`](../scripts/install.sh)

---

## 我们选定的方案

| 平台 | 给用户推荐的方式 | 维护成本 |
|------|------------------|----------|
| **macOS（M 芯片）** | ① 一条命令安装（`curl \| bash`）<br>② 已用 brew 的用户：`brew tap` + `brew install --cask` | 发版后跑脚本同步 tap（约 1 分钟） |
| **Windows** | 下载 exe / `irm` 脚本 | 暂不上 winget（[#23](https://github.com/fancy1108/Clutch/issues/23) 未实体机验收） |
| **Intel Mac** | 不支持安装包 | 无 |

**刻意不做的（以后再说）：**

- 不进 Homebrew **官方** cask 仓库（审核慢、未签名 DMG 容易被卡）
- 暂不进 **winget** 官方仓库（Windows 还没验完）
- 不做 `npm install -g`（我们是桌面应用，不是 CLI）

这和 Codex（CLI + 官方 `brew install --cask codex`）不是同一条路，但对 Clutch 当前阶段更合适。

---

## 用户怎么装（直接复制到 README）

### macOS · Apple Silicon

**方式 1 — 一条命令（推荐给所有人）：**

```bash
curl -fsSL https://raw.githubusercontent.com/fancy1108/Clutch/main/scripts/install.sh | bash
```

**方式 2 — 已装 Homebrew 的用户：**

```bash
brew tap fancy1108/clutch
brew install --cask clutch
```

Tap 仓库：[github.com/fancy1108/homebrew-clutch](https://github.com/fancy1108/homebrew-clutch)

### Windows

```powershell
irm https://raw.githubusercontent.com/fancy1108/Clutch/main/scripts/install.ps1 | iex
```

或从 [Releases](https://github.com/fancy1108/Clutch/releases) 下载安装包。**尚未在实体 Windows 机上完整验收。**

---

## 维护者：每次发新版 macOS 后要做什么

发完 GitHub Release（含 DMG + `SHA256SUMS.txt`）后，在本仓库执行：

```bash
CLUTCH_VERSION=v1.0.3 ./scripts/sync-homebrew-tap.sh
```

脚本会更新 [homebrew-clutch](https://github.com/fancy1108/homebrew-clutch) 里的 `version` / `sha256` 并 push。

（首次需已 `gh auth login`；tap 会 clone 到 `../homebrew-clutch`，可用 `HOMEBREW_TAP_DIR` 覆盖。）

---

## 平台说明

### Intel Mac — 暂不支持

只发 M 芯片 DMG。Intel 用户仅可自行源码编译，见 [`BUILD_FROM_SOURCE.md`](./BUILD_FROM_SOURCE.md)。决策：**D32**。

### winget — 暂缓

清单已写在 [`packaging/winget/`](../packaging/winget/)，等 Windows 实体机验收通过后再提 [winget-pkgs](https://github.com/microsoft/winget-pkgs) PR。

### 和命令行工具的区别

Codex / Reasonix 是 **终端 CLI** → `npm install -g` 很常见。  
Clutch 是 **桌面应用 + 内置 Sidecar** → 装的是 DMG/EXE，包管理器只是下载器。

---

## 技术附录

| 文件 | 用途 |
|------|------|
| [`packaging/homebrew/Casks/clutch.rb`](../packaging/homebrew/Casks/clutch.rb) | 主仓库里的 cask 模板（与 tap 同步） |
| [`scripts/sync-homebrew-tap.sh`](../scripts/sync-homebrew-tap.sh) | 发版后 bump tap |
| [`packaging/winget/`](../packaging/winget/) | 未来 Windows winget 用 |
