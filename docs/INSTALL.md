# Clutch — 安装指南（macOS / Windows）

> **受众**：从 GitHub Releases 下载安装包的终端用户（非源码构建）。
> **开发者**：见 [`BUILD_FROM_SOURCE.md`](./BUILD_FROM_SOURCE.md)。  
> **隐私**：见 [`DATA_AND_PRIVACY.md`](./DATA_AND_PRIVACY.md)。

---

## 1. 系统要求

| 项 | 要求 |
|----|------|
| 操作系统 | **macOS 14+** 或 **Windows 10/11 x64** |
| 磁盘 | 建议 ≥ 500 MB 可用空间（含 Sidecar 与本地状态） |
| 网络 | 使用云端 LLM 时需联网；Ollama / 纯本地 CLI 可离线 |
| 可选 CLI | Claude Code、Codex、Ollama、Aider 等 — 在 Settings → Tools 中连接 |

环境自检（仅源码构建需要）：[`scripts/doctor.sh`](../scripts/doctor.sh)

---

## 2. 未签名应用说明（必读 · T1）

> **免责：** 当前 Clutch **没有 Apple 开发者签名与公证**（开源初期策略，见 D31）。  
> 若提示「**无法验证开发者**」或「**Clutch 已损坏，无法打开**」——**这是 macOS Gatekeeper 对未签名应用的正常行为，不是恶意软件，也不是 DMG 下载损坏。**

请先完成下方 §3 再使用应用。

---

## 3. 下载与安装

1. 打开 [GitHub Releases](https://github.com/fancy1108/Clutch/releases)
2. 下载最新 **`Clutch_*_aarch64.dmg`**（Apple Silicon）或对应架构的 DMG
3. 打开 DMG，将 **Clutch** 拖入 **Applications**

当前发布包为**未签名**构建（见 [`memory/DECISIONS.md`](../memory/DECISIONS.md) **D31**）。获得 Apple Developer 账号后可升级为签名/公证版本（OSR-11）。

### Windows

下载 `Clutch_*_x64-setup.exe`（推荐）或 `Clutch_*_x64_en-US.msi` 并按向导安装（**自 v1.0.2 起**；Release 页若未附 Windows 资产，见 [Actions → Windows Build](https://github.com/fancy1108/Clutch/actions/workflows/windows-build.yml) 或维护者说明）。当前安装包未进行 Windows 代码签名；SmartScreen 提示“未知发布者”时，请先核对下载来源和 SHA-256，再选择“更多信息 → 仍要运行”。

> **测试范围：** Windows 安装包由 GitHub CI 构建并通过自动化测试；**维护者尚未在实体 Windows 10/11 上完成完整人工验收**。遇到问题请 [提交 Issue](https://github.com/fancy1108/Clutch/issues/new/choose) 并注明安装包文件名与 Windows 版本。

安装后从开始菜单启动 Clutch。

---

## 4. 首次打开（Gatekeeper）

macOS 可能提示「无法验证开发者」或「**应用已损坏**」。**均属正常现象。**

**方式 A — Finder（推荐）**

1. 打开 **应用程序**
2. **右键** Clutch → **打开**（不要双击）
3. 在对话框中再次点 **打开**

**方式 B — 终端（复制粘贴）**

```bash
xattr -cr /Applications/Clutch.app && open -a Clutch
```

仅需在**首次**启动时操作一次。若仍失败，确认 DMG 架构与 Mac 芯片一致（Apple Silicon → `aarch64`）。

---

## 5. 验证 Sidecar 已就绪

打包版 Sidecar 监听 **`127.0.0.1:8123`**（仅本机，不对外网开放）。

启动 Clutch 后约 **5 秒内**执行：

```bash
curl -s http://127.0.0.1:8123/health
```

期望输出：

```json
{"status":"ok"}
```

若超时：见下方 [故障排除](#8-故障排除)。

---

## 6. 首次使用 checklist

首次打开 Clutch 时会自动进入**设置向导**（Welcome → 工作区 → 模型 / CLI → Flow 引导 → 权限说明 → 启动）。按向导完成即可跑通主路径。

若跳过向导或需重新配置，可在 **Settings** 中手动完成下表步骤：

**开发调试 — 一键切换向导：**

```bash
./scripts/onboarding-pref.sh reset      # 下次启动重新出现向导
./scripts/onboarding-pref.sh complete   # 标记已完成，跳过向导
./scripts/onboarding-pref.sh status     # 查看当前状态
```

Sidecar 已运行时也可用 HTTP（开发端口 8124）：

```bash
curl -sX POST http://localhost:8124/api/preferences/onboarding-reset
curl -sX POST http://localhost:8124/api/preferences/onboarding-complete
```

改完后**重启 Clutch**（或刷新 `tauri:dev`）生效。

| 步骤 | 操作 |
|------|------|
| 1 | **Settings → General**：确认语言、主题（可选） |
| 2 | **授权工作区**：选择已 clone 的项目目录（Clutch 仅在该目录内读写） |
| 3 | **Settings → Models**：配置至少一个模型的 API Key，或导入 CC Switch |
| 4 | **Settings → Tools**：扫描并 **Connect** 已安装的本地 CLI（如 Claude Code） |
| 5 | **聊天或工作流**：侧栏 New Chat，或 Settings → Workflows SOP 运行模板 |

**CLI 权限说明**：Clutch 对部分 CLI 默认使用 `--dangerously-skip-permissions`（工作流自动跑通）。使用前请阅读 [`README.md`](../README.md) §安全与 CLI 权限。

---

## 7. 数据存储位置

| 模式 | 路径 |
|------|------|
| DMG 安装版 | `~/Library/Application Support/clutch/` |
| 源码开发版 | `~/Library/Application Support/clutch_dev/` |
| Windows 安装版 | `%APPDATA%\clutch\` |

可通过环境变量 `CLUTCH_STORAGE_DIR`（绝对路径）覆盖。

详见 [`DATA_AND_PRIVACY.md`](./DATA_AND_PRIVACY.md)。

---

## 8. 故障排除

| 现象 | 处理 |
|------|------|
| 无法打开 / 已损坏 | 使用 §4 Gatekeeper 步骤；确认 DMG 与芯片架构匹配 |
| 升级时「**Clutch 正在使用中**」 | 见 [§10 升级](#10-升级)：`Cmd+Q` 完全退出 → 活动监视器结束 `Clutch` / `orchestrator` 后再拖入 Applications |
| `curl` 健康检查失败 | 完全退出 Clutch 后重开；检查 8123 端口是否被占用：`lsof -iTCP:8123 -sTCP:LISTEN` |
| 文件夹选择器无响应 | 必须使用 **Clutch.app**，不要用浏览器单独打开 `pnpm dev` |
| API Key 无效 | Settings → Models 检查 Key；确认 Provider 端点可达 |
| CLI 未连接 | Settings → Tools → Rescan；确认 CLI 在终端 `PATH` 中可用 |

仍无法解决：使用 [安装问题模板](https://github.com/fancy1108/Clutch/issues/new?template=installation_issue.yml) 提交 Issue（勿附 API Key 或 `models.json`）。

---

## 9. 卸载

1. 退出 Clutch（菜单栏或 `Cmd+Q`）
2. 将 `/Applications/Clutch.app` 移入废纸篓
3. （可选）删除本地数据以清除 API Key 与会话：

```bash
rm -rf ~/Library/Application\ Support/clutch/
```

卸载不会删除你授权工作区内的项目文件。

Windows 用户通过 **设置 → 应用 → 已安装的应用 → Clutch → 卸载**；如需清除本地状态，再删除 `%APPDATA%\clutch`。API Key 位于 Windows 凭据管理器中，可按服务名 `com.clutch.app` 删除。

---

## 10. 升级

1. 从 [Releases](https://github.com/fancy1108/Clutch/releases) 下载新版本 DMG
2. **先完全退出 Clutch**（见下方「正在使用中」）
3. 打开 DMG，将 **Clutch** 拖入 **Applications** 覆盖旧版
4. 从 **应用程序** 文件夹启动（不要长期从 DMG 卷内直接运行）
5. 本地 `Application Support/clutch/` 数据通常保留；重大版本请查看 [`CHANGELOG.md`](../CHANGELOG.md)

### 提示「Clutch 正在使用中，无法完成此操作」

macOS **不允许在应用仍在运行时替换** `/Applications/Clutch.app`。Clutch 关闭窗口后，后台 **Sidecar**（`orchestrator`）有时仍会占用文件，因此拖入 Applications 会失败。

**普通用户按此顺序操作（无需终端）：**

1. 若 Clutch 窗口还在 → 菜单栏 **Clutch → 退出 Clutch**，或按 **`Cmd+Q`**（不要只点窗口左上角红点，那可能只是关窗口）
2. 等待 **3～5 秒**
3. 再次从 DMG 拖入 **Applications**
4. 若仍提示「正在使用」→ 打开 **活动监视器**（Spotlight 搜索「活动监视器」或「Activity Monitor」）
   - 右上角搜索 **`Clutch`** → 若有进程 → 选中 → 点工具栏 **×** → **退出**
   - 再搜索 **`orchestrator`** → 同样 **退出** 所有匹配项
5. 回到 DMG，再次拖入 Applications

**开发者可选（一条命令清理残留 Sidecar）：**

```bash
killall Clutch 2>/dev/null; pkill -f "/Applications/Clutch.app/Contents/MacOS/orchestrator"
```

维护者发版：打 tag `v1.0.0`（或后续 `v1.x.x`）触发 [`.github/workflows/release.yml`](../.github/workflows/release.yml) 自动构建并上传 DMG；发版前会跑 **gitleaks** 与 [`scripts/release-preflight.sh`](../scripts/release-preflight.sh)（禁止把 `models.json`、`.env` 等打进仓库或 DMG）。

同版本重打 DMG：在 GitHub Actions 手动运行 **Release** workflow，填写已有 tag（如 `v1.0.0`），会覆盖上传同名 DMG 附件。

下载后校验（可选）：

```bash
shasum -a 256 -c SHA256SUMS.txt
```
