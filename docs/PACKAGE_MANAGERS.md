# 安装渠道说明 — Homebrew · winget · 平台支持

> **读者：** 产品 / 运营看「你需要做什么」；工程看下文技术细节。  
> **相关：** [`INSTALL.md`](./INSTALL.md) · [`scripts/install.sh`](../scripts/install.sh) · [`scripts/install.ps1`](../scripts/install.ps1)

---

## 你需要做什么（产品 / 维护者）

代码里已经写好 Homebrew、winget 的「安装说明书」文件，但**用户还不能像装 Codex 那样一条命令全局安装**，除非你完成下面两件事。不做也没关系 — 用户仍可下载 DMG / EXE 或跑 `curl | bash`。

### 一、Homebrew（Mac 用户想 `brew install`）

**现状：** 只有「说明书」在 Clutch 主仓库里；Homebrew 官方不会自动读这个仓库。

**你要做的（一次性，约 15 分钟）：**

1. 在 GitHub 上**新建一个空仓库**，名字必须是：`homebrew-clutch`（完整地址：`github.com/fancy1108/homebrew-clutch`）。
2. 在这个新仓库里建文件夹 `Casks/`，把主仓库里的文件 **复制过去**（不是移动）：
   - 源文件：`Clutch/packaging/homebrew/Casks/clutch.rb`
   - 目标：`homebrew-clutch/Casks/clutch.rb`
3. 提交并 push。

**之后用户就能：**

```bash
brew tap fancy1108/clutch
brew install --cask clutch
```

**每次发新版本你要做的（约 5 分钟）：**

1. 等 GitHub Release 上传完 DMG，打开 Release 里的 `SHA256SUMS.txt`，找到 `Clutch_x.x.x_aarch64.dmg` 那一行的哈希值。
2. 打开 `homebrew-clutch` 仓库里的 `Casks/clutch.rb`，改两行：
   - `version "x.x.x"`
   - `sha256 "那一长串哈希"`
3. 提交 push。不用发 Clutch 主版本也能单独更新 tap。

**不用做的：** 不必去申请 Homebrew 官方大仓库（审核慢）；自建 tap 就够用了。

---

### 二、winget（Windows 用户想 `winget install Clutch`）

**现状：** 安装清单写在 Clutch 主仓库 `packaging/winget/`；微软的「应用商店命令行」里**还没有** Clutch。

**你要做的（一次性，约 30–60 分钟 + 等审核）：**

1. 把电脑上的 [winget](https://learn.microsoft.com/en-us/windows/package-manager/winget/) 装好（Windows 10/11 一般已有）。
2. Fork 微软仓库：[microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs)（很大，只 fork 一次）。
3. 把主仓库里的文件夹 **复制** 到 fork 里对应位置（路径要对）：
   - 源：`Clutch/packaging/winget/manifests/f/fancy1108/Clutch/1.0.2/`（三个 yaml 文件）
   - 目标：`winget-pkgs/manifests/f/fancy1108/Clutch/1.0.2/`
4. 在 fork 上提 Pull Request 给微软仓库，标题类似：`Add Fancy1108.Clutch 1.0.2`。
5. 等机器人检查和维护者合并（通常几天）。

**合并之后用户就能：**

```powershell
winget install --id Fancy1108.Clutch
```

**每次发新版本你要做的：**

1. 在新版本 Release 的 `SHA256SUMS.txt` 里找到 `Clutch_x.x.x_x64-setup.exe` 的哈希。
2. 在 `winget-pkgs` 里复制上一版文件夹，改成新版本号，更新 yaml 里的版本号、下载链接、哈希。
3. 再提一个 PR。

**注意：** Windows 安装包我们**还没在实体机上完整验收**（Issue [#23](https://github.com/fancy1108/Clutch/issues/23)）。上 winget 前建议先让人在真 Win10/11 上装一遍，避免大量用户踩坑。

---

### 三、Intel 芯片 Mac — **暂不做**

**产品决定（2026-07）：** 只发 **Apple Silicon（M 系列）** DMG，**不提供 Intel Mac 安装包**。

| 用户类型 | 怎么办 |
|----------|--------|
| M1/M2/M3 Mac | 正常下载 DMG / Homebrew / `curl \| bash` |
| Intel Mac | **暂不支持**；可自行按源码编译（见 [`BUILD_FROM_SOURCE.md`](./BUILD_FROM_SOURCE.md)），不承诺体验 |

原因简述：要多打一套安装包和后台程序，还要维护两套更新，当前用户量不值得投入。以后有需求再立项。

---

## 渠道总览（给用户看的）

| 渠道 | 状态 | 用户怎么装 |
|------|------|------------|
| **macOS DMG**（M 芯片） | ✅ 主要渠道 | [Releases](https://github.com/fancy1108/Clutch/releases) · `curl \| bash` 脚本 |
| **macOS Intel** | ❌ **暂不支持** | 仅源码自建 |
| **Windows 安装包** | ⚠️ 有包、**未实体机验收** | Releases · `install.ps1` |
| **Homebrew** | 📋 清单已有 · **等你建 tap** | 见上文 §一 |
| **winget** | 📋 清单已有 · **等你提 PR** | 见上文 §二 |

Clutch 是**桌面软件**（像装微信 / VS Code），不是命令行工具，所以**没有** `npm install -g clutch`。

---

## 技术附录（工程）

### Homebrew Cask 源文件

[`packaging/homebrew/Casks/clutch.rb`](../packaging/homebrew/Casks/clutch.rb)

克隆主仓库本地试装：

```bash
brew install --cask ./packaging/homebrew/Casks/clutch.rb
```

### winget 清单

[`packaging/winget/manifests/f/fancy1108/Clutch/`](../packaging/winget/manifests/f/fancy1108/Clutch/)

本地试装：

```powershell
winget install --manifest .\packaging\winget\manifests\f\fancy1108\Clutch\1.0.2
```

### 与 Codex / Reasonix 的区别

那些是 **Node 命令行工具** → `npm install -g` 很自然。  
Clutch 是 **带界面的桌面应用 + 内置 Python 服务** → 包管理器只是帮你下载同一个 DMG/EXE。
