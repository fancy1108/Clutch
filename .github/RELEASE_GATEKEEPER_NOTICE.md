## ⚠️ 未签名 macOS 应用 — 首次安装必读

当前 Clutch **没有 Apple 开发者签名与公证**（开源初期常见做法，见仓库 `memory/DECISIONS.md` D31）。  
**这不是病毒，也不是安装包损坏。** macOS Gatekeeper 对未签名应用会显示误导性提示。

### 你可能看到的提示（均属正常现象）

- 「无法打开，因为无法验证开发者」
- 「Clutch 已损坏，无法打开。你应该将它移到废纸篓。」
- 双击无反应

### 解决方法（任选其一，复制即用）

**方式 A — Finder（推荐）**

1. 打开 **应用程序**
2. **右键** `Clutch.app` → **打开**
3. 在对话框中再次点 **打开**

**方式 B — 终端（一键去除隔离属性）**

```bash
xattr -cr /Applications/Clutch.app && open -a Clutch
```

仅需在**首次**启动时操作一次。

### 验证安装成功

启动后约 5 秒，在终端执行：

```bash
curl -s http://127.0.0.1:8123/health
```

应返回：`{"status":"ok"}`

### 校验下载完整性（可选）

同目录下的 `SHA256SUMS.txt` 可与 DMG 一并校验：

```bash
shasum -a 256 -c SHA256SUMS.txt
```

### 更多说明

- 完整安装步骤：[`docs/INSTALL.md`](docs/INSTALL.md)
- 数据与隐私：[`docs/DATA_AND_PRIVACY.md`](docs/DATA_AND_PRIVACY.md)
- 从源码构建：[`docs/BUILD_FROM_SOURCE.md`](docs/BUILD_FROM_SOURCE.md)

---

**English (short):** This DMG is **unsigned**. Gatekeeper warnings are expected. Right-click → Open, or run `xattr -cr /Applications/Clutch.app && open -a Clutch` once.

---

## ⚠️ Windows 安装包 — 测试范围说明

自 **v1.0.2** 起提供 Windows 10/11 x64 **MSI** 与 **NSIS (.exe)** 安装包（若本 Release 附件中有 `*-setup.exe` / `*.msi`）。

| 项 | 说明 |
|----|------|
| **CI** | GitHub Actions `Windows Build` workflow 构建并通过 pytest / 打包 |
| **人工验收** | **维护者尚未在实体 Win10/11 上完成完整 smoke**（Chat、Hybrid、Tools 等） |
| **代码签名** | 当前**未** Windows 代码签名；SmartScreen 可能提示「未知发布者」——请先核对 SHA-256 与 Release 来源 |
| **反馈** | 欢迎 [提交 Issue](https://github.com/fancy1108/Clutch/issues/new/choose) 标注平台与安装包文件名 |

**English (short):** Windows installers are **CI-built** but **not yet fully smoke-tested by maintainers on physical hardware**. Verify checksums; report issues on GitHub.
