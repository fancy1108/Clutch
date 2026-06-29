# Clutch — 数据与隐私说明

> **版本**：1.0.0 · **最后更新**：2026-06-29  
> **产品定位**：本地桌面工具，**无 Clutch 自有账号、无云同步、无遥测**（截至当前版本）。

---

## 1. 我们不收集什么

Clutch **不会**：

- 要求注册 Clutch 账号或登录 Clutch 云服务
- 将你的工作区内容、对话或 API Key 上传到 Clutch 运营方服务器
- 内置崩溃上报、使用分析或广告追踪 SDK
- 在后台扫描你磁盘上 Clutch 未授权目录以外的文件

所有编排、状态与配置默认保存在**你的 Mac 本地**。

---

## 2. 本地存储什么

根目录（DMG 安装版）：

```
~/Library/Application Support/clutch/
```

开发模式为 `clutch_dev/`。可通过环境变量 `CLUTCH_STORAGE_DIR` 指向其他绝对路径。

| 相对路径 | 内容 | 敏感程度 |
|----------|------|----------|
| `models.json` | 模型选择与自定义模型元数据（**不含 API Key**；Key 在 macOS Keychain） | 中 |
| `preferences/preferences.json` | 主题、语言、权限模式、昵称、头像（base64） | 中 |
| `workspaces.json` | 已授权工作区的绝对路径 | 中 |
| `states/{run_id}.json` | 对话、工具输出、终端日志、运行状态 | **高** |
| `history.json` | 运行历史元数据 | 低–中 |
| `logs/hybrid/*.jsonl` | Hybrid 轮次审计（命令摘要，部分脱敏） | 中 |
| `shell_snapshots/` | PTY 会话恢复数据 | **高** |
| `workflows/user/*.json` | 用户自定义工作流 | 中 |

文件权限：`models.json` 不再保存 API Key（macOS 上存入 **Keychain**）；非 macOS 开发环境仍可使用明文 `models.json`（`CLUTCH_USE_KEYCHAIN=0`）。

---

## 3. 哪些数据会离开本机

仅在你**主动配置并发起 AI 调用**时，数据会发往第三方：

| 目的地 | 触发条件 | 可能传输的内容 | 你的控制 |
|--------|----------|----------------|----------|
| Anthropic、OpenAI、DeepSeek、Google 等 | Settings 中配置 API Key 并聊天/跑工作流 | Prompt、工具结果、工作区相关片段 | 选择 Provider；可减少写入类操作 |
| 本地 Ollama | 选择 Ollama 模型 | 同上，**不出公网** | 完全本地 |
| 本地 CLI（Claude Code、Antigravity 等） | Hybrid / CLI 节点 | 由 CLI 自身策略决定 | 安装、登录与 CLI 权限由你管理 |
| 用户配置的 MCP Server | 启用 MCP 工具 | 取决于该 MCP 实现 | Settings → MCP 启用/禁用 |

各云厂商隐私政策请查阅其官网。Clutch 不代你接受其条款。

**Sidecar 网络**：打包版仅监听 `127.0.0.1:8123`；Tauri 启动时为 HTTP/WebSocket 附加本地 session token（OSR-08），不面向局域网或互联网暴露服务。

---

## 4. 你的权利（导出、删除、更正）

| 权利 | 操作 |
|------|------|
| **查看/更正** | Settings 内修改模型、工作区、偏好 |
| **导出** | 复制整个数据目录（勿分享含 Key 的归档）：`zip -r clutch-backup.zip ~/Library/Application\ Support/clutch/` |
| **删除** | 卸载应用并删除 `~/Library/Application Support/clutch/`（见 [`INSTALL.md`](./INSTALL.md) §卸载） |
| **诊断导出** | 运行中的 run 可使用 `scripts/export-run-debug.sh`（设计为不含密钥；发 Issue 前请自行检查） |

---

## 5. 日志与脱敏

- Hybrid 审计会对部分 shell 命令做摘要脱敏（如 `CLUTCH_P` 相关环境变量）
- Terminal 面板与 `terminal_logs` **可能**包含工具输出中的敏感字符串 — 分享截图或 Issue 前请自行打码
- 漏洞报告请勿附 `models.json` 或完整 session 状态（见 [`SECURITY.md`](../SECURITY.md)）

---

## 6. 合规说明（GDPR / CCPA）

Clutch 作为**纯本地工具**，通常不由 Clutch 项目方担任「数据控制者」处理你的对话内容；数据处理主要发生在你配置的**第三方 LLM / CLI** 与你本机磁盘之间。

若未来增加账号、云同步或遥测，将更新本文并可能在应用内增加 Privacy 设置页。

---

## 7. 适用人群与敏感数据

- 产品面向**开发者与技术运营人员**，不面向 13 岁以下儿童
- **请勿**在未获合规授权的情况下，将受监管数据（如 HIPAA、PCI-DSS 范围内的信息）送入第三方 LLM，除非你与该 Provider 有适当的法律协议（如 BAA）

---

## 8. 变更与联系

- 数据实践变更将记录在 [`CHANGELOG.md`](../CHANGELOG.md)
- 安全漏洞请使用 [`SECURITY.md`](../SECURITY.md) 中的私密报告渠道，勿公开贴 Key
