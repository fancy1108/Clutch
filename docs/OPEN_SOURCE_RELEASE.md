# Clutch 开源与 DMG 本地分发准备指南

> **版本**：v0.1（2026-06-27）  
> **读者**：维护者、安全评审、潜在贡献者  
> **状态**：规划文档（非权威治理规则；铁律仍以 [`CLAUDE.md`](../CLAUDE.md) 为准）

### 给其他 Agent 的读序

1. **本文** — 任务编号 OSR-xx、T0/T1/T2/T3 触发线、检查清单  
2. [`memory/FILEMAP.md`](../memory/FILEMAP.md) — 改代码去哪个路径  
3. [`CLAUDE.md`](../CLAUDE.md) — 铁律与 `./scripts/verify.sh`  
4. 按 OSR 跳转：[`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) · [`STABILITY.md`](./STABILITY.md) · [`EXTENSIBILITY.md`](./EXTENSIBILITY.md) · [`GOVERNANCE.md`](./GOVERNANCE.md) · [`CONTRIBUTING.md`](../CONTRIBUTING.md)

---

## 1. 执行摘要

Clutch 已具备 **Tauri + PyInstaller Sidecar 打包为 DMG** 的基础能力（`pnpm tauri build` → 内嵌 `orchestrator` 监听 `127.0.0.1:8123`），产品定位为 **本地优先、零遥测**，在架构层面适合开源与私有化安装。

但若要让 **陌生用户** 从 GitHub 下载 DMG、放心本地使用，仍需补齐四类工作：

| 类别 | 紧迫度 | 核心问题 |
|------|--------|----------|
| **法律与仓库卫生** | P0 | ~~无 `LICENSE`~~ → T0 已加 MIT；`SECURITY.md` / `CODE_OF_CONDUCT.md` 留 T1；实验 runs 已 gitignore |
| **分发可信度** | P0 | 无 Apple 签名与公证；Release CI 待首 tag；版本 **1.0.0**（T0） |
| **安全加固** | P0–P1 | API Key 明文落盘（与文档不符）；Sidecar API/WS 无鉴权；CLI 默认 `--dangerously-skip-permissions` |
| **隐私与透明** | P1 | 无隐私政策；无数据目录说明与「导出/删除」指引；第三方数据流未集中披露 |

**建议路径**：先完成 P0 安全与法律底座 → 建立签名 DMG Release 流水线 → 再迭代 OS 级沙箱与跨平台。

---

## 2. 当前就绪度评估

### 2.1 已具备的优势

| 能力 | 实现位置 | 说明 |
|------|----------|------|
| 本地回环通信 | `sidecar_entry.py`、`lib.rs` | Sidecar 仅绑定 `127.0.0.1`（dev `8124` / prod `8123`） |
| DEV/PROD 数据隔离 | `storage_helper.py` | 开发用 `clutch_dev`，DMG 用 `clutch`；支持 `CLUTCH_STORAGE_DIR` 覆盖 |
| 工作区白名单 | `workspace.py` | `resolve_allowed_path()` 禁止越界访问；用户显式授权目录 |
| 权限模式 | `preferences_storage.py`、`mcp_react.py` | `ask` / `auto_edit` / `plan` / `full` 四级人机门控 |
| 审计与脱敏 | `hybrid_audit_log.py` | Hybrid 命令摘要对 prompt 做 `[redacted]`；JSONL 本地落盘 |
| 无遥测 | 全仓库检索 | 无 Sentry / PostHog / 分析 SDK；数据默认不出本机 |
| 凭证来源透明 | `credentials/sources.py` | 展示 Key 来自 Clutch / Claude Code / CC Switch / 环境变量 |
| 打包链路 | `build-sidecar.sh`、`tauri.conf.json` | PyInstaller onefile + Tauri `externalBin` 已打通 |

### 2.2 文档与实现（T0 已对齐 — 2026-06-27）

| 主题 | 文档表述（当前） | 实现 | 后续 |
|------|------------------|------|------|
| API Key 存储 | macOS Keychain（`com.clutch.app`）；`models.json` 仅模型元数据；首次加载自动迁移明文 Key | ✅ 一致（OSR-13） | 非 macOS 仍可用 `CLUTCH_USE_KEYCHAIN=0` |
| Sidecar 仅 localhost | ✅ | ✅ | — |
| `full` 模式灾难命令拦截 | 文档不夸大；MCP 门控见 `permission_mode` | 部分 | 持续加固 |

T0 策略：**修订文档 + 明确风险**，Keychain 与 Sidecar 鉴权留 T1/T2，见 §5。

### 2.3 仓库卫生

- **`experiments/pty_poc/runs/`**：已 gitignore；本地 POC 产物勿提交（T0）
- **`.claude/settings.local.json`**：已 gitignore；见 `.claude/settings.local.json.example`
- **`LICENSE`**：MIT（T0）

---

## 3. 开源治理清单

### 3.1 法律与许可（P0）

| 任务 | 说明 |
|------|------|
| 选定开源许可证 | 建议 **Apache-2.0** 或 **MIT**（与 Tauri/React 生态常见）；若含 GPLv3 依赖需做法务核对 |
| 添加 `LICENSE` | 根目录 + 各子包如需要 |
| 添加 `NOTICE` / 第三方许可 | PyInstaller 打包的 Python 依赖、前端 npm 依赖、品牌 Logo SVG |
| `SECURITY.md` | 漏洞报告邮箱、响应 SLA、**不在 Issue 公开 0-day** |
| `CONTRIBUTING.md` | 开发环境、`./scripts/verify.sh`、原子 commit、PR 规范 |
| `CODE_OF_CONDUCT.md` | 社区行为准则（可用 Contributor Covenant 模板） |
| 商标策略 | 「Clutch」名称与图标是否允许衍生产品使用；在 README 声明 |

### 3.2 仓库公开前审计（P0）

```bash
# 建议执行的公开前扫描（示例）
git log -p | rg -i 'sk-|api[_-]?key|password|secret|token' 
rg -l '/Users/' --glob '!experiments/**'
rg 'fancy1108|@.*\.com' 
```

| 检查项 | 动作 |
|--------|------|
| `.env*` | 已在 `.gitignore` ✅ |
| 硬编码密钥 | `CLAUDE.md` 铁律禁止；CI 可加 gitleaks |
| 个人路径 / 会话转储 | 清理 `experiments/` runs 或改为 synthetic fixtures |
| Agent 内部文档 | `memory/` 可保留（透明开发）或精简敏感决策 |

### 3.3 用户向文档（P1）

| 文档 | 内容 |
|------|------|
| `README.md` 增强 | 截图、系统要求（macOS 版本、磁盘、依赖 CLI）、**一键 DMG 安装** vs **源码构建** 分叉 |
| `docs/INSTALL.md` | DMG 安装、首次启动、Gatekeeper 提示、健康检查 `curl http://127.0.0.1:8123/health` |
| `docs/BUILD_FROM_SOURCE.md` | Node / uv / Rust 版本锁定、`pnpm tauri build` 全流程 |
| `docs/DATA_AND_PRIVACY.md` | 见 §6 |
| `CHANGELOG.md` | 按 semver 记录安全修复 |

---

## 4. DMG 分发与安装体验

### 4.1 当前打包流程

```bash
cd apps/desktop && pnpm tauri build
```

`beforeBuildCommand` 依次：Vite 构建 → `scripts/build-sidecar.sh`（PyInstaller → `binaries/orchestrator-{triple}`）。

**验收标准**（已有）：安装 DMG 后约 5s 内 `curl http://127.0.0.1:8123/health` 返回 `{"status":"ok"}`。

### 4.2 必须补齐的分发能力（P0）

#### 4.2.1 Apple 代码签名与公证（Notarization）

当前 `clutch.spec` 中 `codesign_identity=None`，Tauri 发布包 **未签名**。陌生用户安装时会遇到：

- 「无法验证开发者」
- 需右键 → 打开，或 `xattr -cr`（极不友好）
- 企业环境可能直接被 MDM 拦截

**改造项**：

| 项 | 说明 |
|----|------|
| Apple Developer Program | 年费账号，创建 Developer ID Application 证书 |
| 签名 Sidecar 二进制 | PyInstaller 产物需单独 `codesign`（含 hardened runtime） |
| 签名 `.app` | Tauri `bundle.macOS.signingIdentity` |
| Entitlements | 最小权限：`com.apple.security.cs.allow-unsigned-executable-memory` 等按实际需求；**避免**过度宽泛的 `disable-library-validation` |
| `notarytool` 公证 + staple | CI 或 release 脚本自动化 |
| DMG 签名 | 可选但对企业分发有帮助 |

#### 4.2.2 Release CI（GitHub Actions）

当前 `.github/workflows/ci.yml` 仅 `ubuntu-latest` 跑 build + pytest，**不产出 DMG**。

建议新增 `release.yml`：

```yaml
# 示意 — 需在 macOS runner 上构建
on:
  push:
    tags: ['v*']
jobs:
  build-macos:
    runs-on: macos-14
    steps:
      - uses: actions/checkout@v4
      - # pnpm, uv, rust toolchain
      - run: cd apps/desktop && pnpm tauri build
      - # codesign + notarytool
      - uses: softprops/action-gh-release@v2
        with:
          files: apps/desktop/src-tauri/target/release/bundle/dmg/*.dmg
```

附带 **SHA256 checksum** 与 **SBOM**（可选，`syft` / `cyclonedx`）。

#### 4.2.3 版本与更新策略

| 项 | 现状 | 建议 |
|----|------|------|
| 版本号 | ~~全局 `0.0.0`~~ → **1.0.0**（T0）；后续单一来源同步 Tauri / Cargo / Python |
| 自动更新 | 无 | 开源初期可 **手动下载**；后期可选 Tauri updater plugin + 签名 manifest |
| 降级/迁移 | 无 | `storage_helper` 数据目录在 major 升级时提供迁移说明 |

### 4.3 安装体验优化（P1）

| 项 | 说明 |
|----|------|
| 首次启动向导 | 工作区授权、API Key 配置、权限模式说明（默认 `ask`） |
| Sidecar 健康失败 UX | 当前仅超时错误；应展示日志路径、重启按钮 |
| PyInstaller `console=True` | Sidecar 可能弹出终端窗口 → 发布改为 `console=False` 或 windowed bootloader |
| 磁盘占用说明 | onefile 解压临时目录、审计日志、会话 state 增长预估 |
| 卸载指引 | 删除 `/Applications/Clutch.app` + `~/Library/Application Support/clutch/` |

### 4.4 跨平台（P2）

| 平台 | 状态 | 开源分发建议 |
|------|------|--------------|
| macOS DMG | ✅ 主路径 | 优先打磨 |
| Windows MSI | 架构预留 | 需测试 PyInstaller win + WebView2 引导 |
| Linux | 未主打 | AppImage/deb 可作为社区贡献，非首发承诺 |

---

## 5. 安全改造（重点）

Clutch 是 **高权限本地 Agent 编排器**：可执行 shell、改文件、调外部 LLM。开源后攻击面包括 **恶意本地进程**、**恶意工作流 JSON**、**供应链投毒** 三类。

### 5.1 威胁模型（简版）

```
┌─────────────────────────────────────────────────────────────┐
│  用户 Mac                                                    │
│  ┌──────────────┐    loopback     ┌─────────────────────┐ │
│  │ Clutch.app   │ ───────────────► │ Sidecar :8123       │ │
│  │ (WebView)    │   无鉴权 HTTP/WS │ FastAPI + LangGraph │ │
│  └──────────────┘                  └──────────┬──────────┘ │
│         │                                      │            │
│         │ 任意本地进程也可 ──────────────────────┘            │
│         ▼                                      ▼            │
│   Keychain/明文 models.json              工作区文件 / shell   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    外部 LLM API（用户自备 Key）
```

### 5.2 P0 — 发布阻断项

#### 5.2.1 API Key 安全存储

**现状**：`~/Library/Application Support/clutch/models.json` 明文存储，`chmod 600` 仅防其他 Unix 用户，**不防同用户进程**。

**目标**（对齐 M4-04 / `ARCHITECTURE.md`）：

1. 引入 `tauri-plugin-stronghold` 或 macOS Keychain（通过 Tauri command 封装）
2. Sidecar **不持久化明文 Key**；运行时通过 IPC 向 Tauri 请求解密
3. 日志与 debug API **永不返回** Key；`GET /api/models` 仅返回 `configured: true/false` 与 source 标签
4. 提供 **一次性迁移**：读取旧 `models.json` → 导入 Keychain → 擦除明文文件

#### 5.2.2 Sidecar API / WebSocket 鉴权

**现状**：`@app.websocket("/ws/runs/{run_id}")` 与大量 `/api/*` 路由 **无 token**；任何本机进程可：

- 读写工作流与用户数据
- 触发 Agent 执行
- 读取 `/api/runs/{run_id}/debug`（含审计与日志）

**目标**：

1. Tauri 启动 Sidecar 时生成 **随机 session token**（一次性，存内存 + 可选 Keychain）
2. Sidecar 要求 `Authorization: Bearer <token>` 或 WebSocket 子协议携带 token
3. Token 仅注入 Tauri WebView（不暴露给外部网页）；CORS 保持 localhost 白名单
4. 对 **非 Tauri 客户端**（如开发者 `curl`）可通过 `CLUTCH_DEV_BYPASS_TOKEN` 仅 debug 构建启用

#### 5.2.3 CLI `--dangerously-skip-permissions` 策略

**现状**：`shell_exec_runtime.py`、`claude_cli_adapter.py`、`agy_cli_adapter.py` 默认追加该 flag，等于 **绕过 Claude Code / agy 内置安全提示**。

**开源分发建议**：

| 模式 | 行为 |
|------|------|
| 默认（`ask`） | **禁止** skip-permissions；保留 CLI 原生确认 |
| `full` + 显式二次确认 | 用户勾选「我理解风险」后可启用 |
| 设置页 | 用 plain language 解释该 flag 含义 |

这与产品「监督而非黑盒」定位一致，也是对外安全叙事的关键。

#### 5.2.4 内容安全策略（CSP）

**现状**：`tauri.conf.json` → `"csp": null`。

**建议**：为 WebView 配置严格 CSP，禁止远程脚本加载（本地 app 仅加载 `asset:` / `tauri://`）。

### 5.3 P1 — 强化项

#### 5.3.1 OS 级沙箱（对齐 Backlog B-20）

工作区白名单仅约束 **Clutch 内置工具路径**；Hybrid shell 调用的 **外部 CLI** 仍可访问用户整盘（受 CLI 自身权限限制）。

可选方案（需专项调研）：

- macOS：Seatbelt / sandbox-exec 配置文件，限制子进程 `filesystem` + `network`
- Linux：`bubblewrap`
- Windows：`windows-sandbox-rs`

落地前在 `SECURITY.md` 明确：**当前版本信任用户所选工作区与外部 CLI 权限模型**。

#### 5.3.2 Shell / 命令执行治理

| 项 | 建议 |
|----|------|
| 命令 allowlist / denylist | 拦截 `rm -rf /`、`mkfs`、`curl \| sh` 等（落实注释中的「灾难操作」承诺） |
| 工作目录强制 | 子进程 `cwd` 必须在工作区内 |
| 网络出口提示 | `full` 模式下对首次外连域名弹窗（可选） |
| PTY 会话上限 | 已有 `CLUTCH_SHELL_MAX_SESSIONS` ✅；文档化 |

#### 5.3.3 Debug API 收敛

`GET /api/runs/{run_id}/debug` 暴露 hybrid 审计、日志摘要。

- Release 构建默认 **禁用** 或需鉴权 + `CLUTCH_ENABLE_DEBUG_API=1`
- 响应中继续脱敏 prompt / system / API Key

#### 5.3.4 依赖与供应链

| 项 | 动作 |
|----|------|
| `pnpm audit` / `uv pip audit` | 纳入 CI |
| Lockfile | `pnpm-lock.yaml`、`uv.lock` 提交仓库 ✅ |
| PyInstaller 供应链 | 固定版本；Reproducible build 可选 |
| GitHub Dependabot | 启用安全更新 PR |

#### 5.3.5 Tauri 权限最小化

**现状**：`capabilities/default.json` 已限制 `shell:allow-execute` 仅 sidecar ✅。

复查：

- `dialog:allow-open` 是否足够（文件选择 vs 目录）
- 是否需要 `fs` scope 显式声明
- 移除 `e2e-testing` feature 出 Release 构建

### 5.4 P2 — 深度防御

- **工作流签名**：用户工作流 JSON 可选 Ed25519 签名，防篡改
- **MCP Server 白名单**：仅允许用户注册的 MCP 端点
- **Secret scanning CI**：gitleaks + 自定义 `sk-` 规则
- **渗透测试清单**：OWASP Desktop / 本地提权场景

---

## 6. 隐私与合规

### 6.1 数据清单（用户应被告知）

所有数据默认 **仅本机**，存储根目录：

| 平台 | 路径 |
|------|------|
| macOS（DMG） | `~/Library/Application Support/clutch/` |
| macOS（开发） | `~/Library/Application Support/clutch_dev/` |
| 覆盖 | 环境变量 `CLUTCH_STORAGE_DIR` |

| 数据类型 | 相对路径 | 内容 | 是否含敏感信息 |
|----------|----------|------|----------------|
| 模型配置 | `models.json` | API Key（明文）、模型选择 | **高** |
| 偏好 | `preferences/preferences.json` | 主题、语言、权限模式、昵称、头像 base64 | 中 |
| 工作区列表 | `workspaces.json` | 授权目录绝对路径 | 中 |
| 会话状态 | `states/{run_id}.json` | 对话、工具输出、终端日志 | **高** |
| 运行历史 | `history.json` | 元数据 | 低–中 |
| Hybrid 审计 | `logs/hybrid/*.jsonl` | 命令摘要（已部分脱敏） | 中 |
| Shell 快照 | `shell_snapshots/` | PTY 会话恢复数据 | **高** |
| 用户工作流 | `workflows/user/*.json` | 用户编排 | 中 |

### 6.2 离开本机的数据流

| 目的地 | 触发条件 | 传输内容 | 用户控制 |
|--------|----------|----------|----------|
| Anthropic / OpenAI / DeepSeek / Google 等 | 用户配置 API Key 并发起对话 | Prompt、工具结果、工作区文件片段 | 可选 Provider；`plan` 模式减少写入 |
| 本地 Ollama | 选择 Ollama 模型 | 同上，不出公网 | 完全本地 |
| 本地 CLI（Claude Code、agy 等） | Hybrid / CLI 节点 | 由 CLI 自身决定外连 | 用户安装与登录 CLI |
| MCP Server | 用户配置 | 取决于 MCP 实现 | 用户启用/禁用 |

**无**：项目自有后端、遥测、崩溃上报（截至 2026-06-27）。

### 6.3 隐私政策与用户权利（P1）

建议新增 `docs/DATA_AND_PRIVACY.md`（或站内 Settings → Privacy），包含：

1. **我们不收集什么**（无账号体系、无云同步）
2. **本地存储什么**（上表）
3. **第三方处理器**（各 LLM Provider 链接到其隐私政策）
4. **用户权利**：导出（zip `Application Support/clutch`）、删除（卸载指引）、更正（Settings）
5. **GDPR/CCPA 说明**：纯本地工具通常无数据控制者义务，但若未来加快捷登录/云同步需重新评估

### 6.4 日志脱敏（持续）

已有：

- `hybrid_audit_log.summarize_shell_command()` 脱敏 `CLUTCH_P`、system prompt ✅

待加强：

- Terminal 面板 / `terminal_logs` 全链路 `sk-`、Bearer token 扫描
- `engine_router` 的 `sanitize_engine_output` 目前做品牌替换，非安全脱敏 → 扩展为密钥模式 redaction
- 用户导出 debug 包时默认脱敏

### 6.5 未成年人与敏感场景

产品面向开发者；README 声明 **不面向 13 岁以下**。Agent 可处理用户代码与业务数据 — 提醒用户 **勿将 regulated 数据（HIPAA/PCI）** 送入第三方 LLM，除非有合规 BAA。

---

## 7. 分期排期与触发条件

> **原则**：不必等功能 100% 做完；也不必在功能冲刺期上马全部分发/安全项。按 **触发线** 分批启动，与功能开发并行。  
> **生态边界**（Goals/Non-Goals、稳定性、扩展点）见 §7.6 与 [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) 等 — **开源长期可维护往往败在边界不清，而非技术**。

### 7.1 四条触发线

| 触发线 | 含义 | 典型时机 |
|--------|------|----------|
| **T0 · 持续** | 边做功能边做，成本低、防返工 | **现在起**，贯穿整个开发期 |
| **T1 · 公开仓库** | 仓库设为 public / 接受外部 PR | 核心路径可跑通，愿意被 fork 时 |
| **T2 · 首次 DMG 分发** | 给陌生人或非开发者安装 `.dmg` | Settings / Hybrid 体验基本定型后 |
| **T3 · 生态成熟期** | 用户量上来、需长期维护与合规背书 | 有稳定 release 节奏、或企业用户诉求时 |

**与功能开发的关系**：

```
现在（功能优化中）          核心功能稳定              首次对外发布
      │                         │                         │
 T0 ───┼─────────────────────────┼─────────────────────────┼──► 持续
      │                         │                         │
      │                    T1 公开 repo                    │
      │                         ├────────────────────────►│
      │                         │                         │
      │                    T2 发 DMG                       │
      │                         ├────────────────────────►│
      │                                                   │
 T3 ──────────────────────────────────────────────────────┼──► 按需
```

### 7.2 排期总表（可贴入 Backlog）

| ID | 任务 | 触发线 | Phase | 估时 | 依赖 / 备注 |
|----|------|--------|-------|------|-------------|
| **OSR-00** | **外部视角审计**（陌生人无指导安装全流程） | **T1 前** | 0 | 0.5–1d | 见 §7.6；公开前最有价值的一步 |
| OSR-01 | 选定许可证 + 根目录 `LICENSE` | **T0** | — | 0.5d | 不挡功能；Apache-2.0 / MIT 二选一 |
| OSR-02 | 仓库卫生：`.gitignore` 补全、清理 `experiments/` 个人路径 | **T0** | — | 0.5d | 公开前必做；可随 commit 零散清 |
| OSR-03 | 文档与实现一致（API Key 存哪、权限模式真实行为） | **T0** | — | 1d | 每改 Settings/凭证逻辑时核对 `PRODUCT_INTRO` |
| OSR-04 | semver 版本号 + `CHANGELOG.md` 起步 | **T0** | — | 0.5d | 从 **1.0.0** 起；与功能迭代同步打 tag |
| OSR-05 | 新功能安全护栏：新 API 不裸奔、日志不写 Key | **T0** | — | 持续 | Code review 检查项，无单独立项 |
| **OSR-23** | **`docs/PROJECT_SCOPE.md`**（Goals / Non-Goals） | **T0** | — | 0.5d | **P0**；减少重复解释型 Issue |
| **OSR-24** | **`docs/STABILITY.md`**（模块 / API 稳定性） | **T0** | — | 0.5d | **P0**；含 0.x breaking 政策 |
| **OSR-25** | **`docs/EXTENSIBILITY.md`**（官方扩展点） | **T0** | — | 0.5d | **P0** |
| OSR-06 | `SECURITY.md` + `CONTRIBUTING.md` + `CODE_OF_CONDUCT.md` | **T1** | 0 | 1–2d | public 前一周即可 |
| OSR-07 | Secret scanning CI（gitleaks 等） | **T1** | 0 | 0.5d | 与 T1 同批上线 |
| OSR-08 | Sidecar session token 鉴权（HTTP + WS） | **T1** | 0 | 3–5d | 会动前后端；避免 Settings 大改期间做 |
| OSR-09 | 默认关闭或门控 `--dangerously-skip-permissions` | **T1** | 0 | 2–3d | Hybrid 验收通过后再定 UX |
| OSR-10 | `README` 增强 + 源码构建说明 | **T1** | 0 | 1d | 公开仓库的门面 |
| **OSR-26** | **`docs/GOVERNANCE.md`**（BDFL / PR 边界） | **T1** | 0 | 0.5d | **P1** |
| **OSR-27** | **兼容性矩阵** + **`scripts/doctor.sh`** | **T1** | 0 | 1d | **P1**；见 README |
| **OSR-28** | **Issue / PR 模板**（`.github/ISSUE_TEMPLATE/`） | **T1** | 0 | 0.5d | **P1** |
| OSR-11 | Apple 签名 + 公证（notarytool） | **T2** | 1 | 2–3d | 需 Apple Developer 账号；**D31 豁免**，不阻塞未签名 DMG |
| OSR-12 | GitHub Actions `release.yml`（macOS runner 打 DMG） | **T2** | 1 | 2–3d | **未签名** DMG；不依赖 OSR-11（D31） |
| OSR-13 | API Key → macOS Keychain（Tauri IPC）+ 迁移 | **T2** | 1 | 3–5d | Models Settings UI 稳定后 |
| OSR-14 | 首次启动向导（工作区 / Key / 权限模式） | **T2** | 1 | 2–3d | 依赖 OSR-13、OSR-09 |
| OSR-15 | `docs/INSTALL.md` + `docs/DATA_AND_PRIVACY.md` | **T2** | 1 | 1–2d | 功能列表冻结一版后再写 |
| OSR-16 | Release 收敛 debug API + WebView CSP | **T2** | 1 | 1–2d | |
| OSR-17 | PyInstaller `console=False` / Sidecar 无黑窗 | **T2** | 1 | 0.5d | 分发体验 |
| OSR-18 | OS 级沙箱 PoC（B-20） | **T3** | 2 | 2–4w | 与功能正交；安全评审驱动 |
| OSR-19 | Windows MSI 安装包 | **T3** | 2 | 1–2w | macOS DMG 稳定后 |
| OSR-20 | Tauri 自动更新 | **T3** | 2 | 3–5d | 有连续 release 再值得做 |
| OSR-21 | 工作流签名 / MCP 白名单 | **T3** | 2 | 1–2w | 社区贡献多时再上 |
| OSR-22 | 外部安全审计 | **T3** | 2 | 外包 | 企业客户或融资合规时 |
| **OSR-29** | **`docs/PERFORMANCE.md`** 基线 + 可选 benchmark | **T3** | 2 | 1–2d | **P2** |

### 7.3 生态与社区文档优先级（外部开发者视角）

| 优先级 | 文档 / 动作 | OSR | 状态 |
|--------|-------------|-----|------|
| **P0** | Goals / Non-Goals | OSR-23 → [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) | ✅ 草案 |
| **P0** | API / Schema 稳定性 | OSR-24 → [`STABILITY.md`](./STABILITY.md) | ✅ 草案 |
| **P0** | 扩展边界 | OSR-25 → [`EXTENSIBILITY.md`](./EXTENSIBILITY.md) | ✅ 草案 |
| **P0** | 公开前敌对审视 | OSR-00 | ✅ 维护者自验（D31） |
| **P1** | 治理模型 | OSR-26 → [`GOVERNANCE.md`](./GOVERNANCE.md) | ✅ 草案 |
| **P1** | 兼容性矩阵 + doctor | OSR-27 | ✅ 草案 |
| **P1** | Issue / PR 模板 | OSR-28 | ✅ 草案 |
| **P2** | 性能基线 | OSR-29 → [`PERFORMANCE.md`](./PERFORMANCE.md) | ✅ 草案 |
| **P2** | Release 生命周期 | 并入 [`STABILITY.md`](./STABILITY.md) §3 | ✅ 草案 |

### 7.4 Phase 与触发线对照

| Phase | 名称 | 对应触发线 | 目标 | 建议工期 |
|-------|------|------------|------|----------|
| **—** | 持续护栏 | T0 | 不积累开源/安全债 | 零散，贯穿开发 |
| **Phase 0** | 可公开仓库 | **T1** | fork 不丢人、漏洞有渠道、Sidecar 不裸奔 | 2–3 周（集中做 OSR-06～10） |
| **Phase 1** | 可放心装 DMG | **T2** | 陌生人双击能装、Key 不落明文、有隐私说明 | 3–4 周（OSR-11～17） |
| **Phase 2** | 生态与加固 | **T3** | 跨平台、沙箱、自动更新 | 持续 / 按需 |

### 7.5 与当前阶段（功能优化期）的具体建议

你正处于 **Hybrid 验收 + 功能优化** 阶段时：

| 做 | 不做（暂排） |
|----|----------------|
| OSR-01～05、**OSR-23～25**（T0 护栏 + 生态边界文档） | OSR-11 签名（D31 豁免至有 Developer 账号） |
| 每完成一个 Settings/凭证相关 task 时核对 OSR-03 | OSR-13 Keychain 迁移（等 Models UI 定稿） |
| 在 `memory/BACKLOG.md` 登记 OSR-xx 编号备查 | OSR-18～22 沙箱/Windows/审计 |
| T1 前安排 **OSR-00** 外部审计（1 人、无指导） | OSR-08～09 鉴权与 CLI 策略（等 Hybrid 体验拍板） |

**开 T1 的合适信号**（满足多数即可）：

- [ ] 主路径：选工作区 → 跑工作流 / 单 Agent 聊天 → 人工审批，可稳定复现
- [ ] 近 2 周无大规模 Settings / API 路由重构计划
- [ ] 愿意处理外部 Issue（即使暂不 merge PR）

**开 T2 的合适信号**（满足多数即可）：

- [ ] 已打至少一个 semver tag（如 `v1.0.0`）
- [ ] T1 项（OSR-06～10）已完成或明确豁免并写入文档
- [ ] 有真实用户（非你自己）愿意试装 DMG 并反馈

### 7.6 OSR-00：外部视角审计（公开前强烈推荐）

找 **完全未参与项目** 的开发者，在**零口头解释**前提下完成：

1. 克隆仓库（或安装 DMG）
2. 按 README 安装依赖
3. 运行 `./scripts/doctor.sh`
4. 授权工作区、配置 API Key
5. 跑一个内置 Workflow 或单 Agent 对话

**记录**：卡在哪一步、哪句文档过时、与实现不一致之处。结果写入 `runs/verification/` 或 Issue 里程碑。

这是发布前 **投入产出比最高** 的一步，与安全审计互补。

### 7.7 检查清单（权威勾选 · 镜像至 `memory/BACKLOG.md` §开源 / DMG 分发）

#### T0 — 现在起（功能开发并行）

- [x] OSR-01 `LICENSE`（MIT）
- [x] OSR-02 仓库卫生（`.gitignore`、`experiments/pty_poc/runs/`）
- [x] OSR-03 文档↔实现一致（API Key → `models.json` + T2 Keychain 路线图）
- [x] OSR-04 版本号 **1.0.0** + `CHANGELOG.md`
- [ ] OSR-05 新代码安全护栏（review 项，持续）
- [x] OSR-23 `PROJECT_SCOPE.md`
- [x] OSR-24 `STABILITY.md`
- [x] OSR-25 `EXTENSIBILITY.md`

#### T1 — 公开仓库前

- [x] **OSR-00 外部视角审计**（维护者自验 2026-06-29，D31）
- [x] OSR-06 社区与健康文件
- [x] OSR-07 Secret scanning CI
- [x] OSR-08 Sidecar 鉴权
- [x] OSR-09 CLI 权限策略
- [x] OSR-10 README / 构建文档 / 产品截图
- [x] OSR-26 `GOVERNANCE.md`（草案 v0.1）
- [x] OSR-27 兼容性矩阵 + `doctor.sh`
- [x] OSR-28 Issue / PR 模板

#### T2 — 首次 DMG 分发前

- [ ] OSR-11 Apple 签名 + 公证（⏭️ D31 豁免）
- [x] OSR-12 Release CI（v1.0.0 实跑 ✅ · [#28358384072](https://github.com/fancy1108/Clutch/actions/runs/28358384072)）
- [x] OSR-13 Keychain 迁移
- [ ] OSR-14 首次启动向导
- [x] OSR-15 安装与隐私文档
- [ ] OSR-16 Debug API + CSP
- [ ] OSR-17 Sidecar 无控制台窗

#### T3 — 生态成熟期（按需）

- [ ] OSR-18 OS 沙箱
- [ ] OSR-19 Windows
- [ ] OSR-20 自动更新
- [ ] OSR-21 工作流签名 / MCP 白名单
- [ ] OSR-22 外部安全审计
- [ ] OSR-29 `PERFORMANCE.md` 基线

---

## 8. 开源后运维建议

| 实践 | 说明 |
|------|------|
| GitHub Issues + `SECURITY.md` | 漏洞私密报告渠道 |
| 标签 `needs-triage` / `ready-for-agent` | 已有 [`docs/agents/triage-labels.md`](./agents/triage-labels.md) |
| 仅 merge 过 `verify.sh` 的 PR | 保持 ✅ |
| 安全公告 | CVE 或 GitHub Security Advisory，关联 semver tag |
| 复现包 | 每个 Release 附 DMG + 源码 tag + checksum |

---

## 9. 快速自检命令（维护者）

```bash
# 构建 DMG（本机 macOS）
cd apps/desktop && pnpm tauri build

# 安装后健康检查
curl -s http://127.0.0.1:8123/health

# 确认 sidecar 仅监听 loopback
lsof -iTCP:8123 -sTCP:LISTEN

# 确认 models.json 权限（迁移 Keychain 前）
ls -la ~/Library/Application\ Support/clutch/models.json

# 全量校验
./scripts/verify.sh
```

---

## 10. 参考

| 资源 | 路径 |
|------|------|
| **Goals / Non-Goals** | [`docs/PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) |
| **API 稳定性** | [`docs/STABILITY.md`](./STABILITY.md) |
| **扩展边界** | [`docs/EXTENSIBILITY.md`](./EXTENSIBILITY.md) |
| **维护者治理** | [`docs/GOVERNANCE.md`](./GOVERNANCE.md) |
| **性能基线** | [`docs/PERFORMANCE.md`](./PERFORMANCE.md) |
| 架构安全摘要 | [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md) §9 |
| 产品介绍（本地优先） | [`docs/PRODUCT_INTRO.md`](./PRODUCT_INTRO.md) |
| Tauri 打包说明 | [`apps/desktop/src-tauri/README.md`](../apps/desktop/src-tauri/README.md) |
| 存储目录决策 | [`memory/DECISIONS.md`](../memory/DECISIONS.md) D16 |
| Dev/Prod 端口决策 | D18 |
| OS 沙箱待办 | [`memory/BACKLOG.md`](../memory/BACKLOG.md) B-20 |

---

*本文档随实现演进更新；安全相关落地后应在 `memory/DECISIONS.md` 登记 ADR，并在 `docs/PRODUCT_INTRO.md` 保持用户可见描述一致。*
