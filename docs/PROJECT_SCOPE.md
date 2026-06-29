# Clutch — 项目定位与边界（Goals / Non-Goals）

> **Normative policy only** — goals and boundaries, not implementation details. How it works: [`ARCHITECTURE.md`](./ARCHITECTURE.md). What users get: [`PRODUCT_INTRO.md`](./PRODUCT_INTRO.md).

---

## 1. 一句话定位

**Clutch** 是面向开发者与技术运营人员的 **本地 AI 多 Agent 编排与监督桌面应用**：用户在可视化画布上定义 SOP 工作流，系统在用户机器上调度 CLI / MCP / GUI 工具执行，并在 Chat、Terminal、Diff 等面板中提供可观测性与人工审批。

**增量价值**：不是替代 Claude Code / Cursor 的代码生成能力，而是在其之上加一层 **可持久化、可观测、可编辑的流程控制层**。

---

## 2. Goals（我们会做）

| 目标 | 说明 |
|------|------|
| **本地优先** | 编排、状态、日志、偏好默认落在本机；无自有云后端 |
| **零代码工作流** | 用户通过 UI / JSON 配置 SOP，不手写 LangGraph |
| **多 Agent 编排** | 可视化节点与连线；LangGraph 为唯一编排 SSOT |
| **Hybrid CLI 协同** | 桥接 Claude Code、agy、Aider、Ollama 等本地 CLI |
| **监督执行** | Terminal 真日志、文件变更、人工门控（Approve / Reject / Retry） |
| **工作区授权** | 用户显式授权项目根目录；工具访问受白名单约束 |
| **可扩展工具链** | MCP、自定义 Model Provider、Workflow 模板（见 [`EXTENSIBILITY.md`](./EXTENSIBILITY.md)） |
| **桌面分发** | macOS DMG 为首发路径；架构预留 Windows |

---

## 3. Non-Goals（我们不做）

以下请求 **不在项目范围内**。若强烈需要，请 fork 自建，而非期待上游合并。

| 不做 | 原因 / 替代方案 |
|------|----------------|
| **云托管 / SaaS 控制台** | 违背本地优先；用户自备 LLM Key 与 CLI |
| **浏览器版 / 纯 Web App** | 无法可靠调度本地 CLI、PTY、GUI 应用（Cursor） |
| **多租户团队协作** | 非实时协作 IDE；无共享工作区、无权限 RBAC 后台 |
| **云同步会话 / 跨设备状态** | 会话与 `ClutchState` 存本地；自行备份 `Application Support/clutch` |
| **替代 Claude Code / Cursor** | Clutch **调度与监督**它们，不重新实现底层模型与编辑能力 |
| **保证 100% 无人值守自动完成** | Agent 可能失败、需人工审批；产品目标是 **监督** 而非黑盒自治 |
| **内置遥测 / 产品分析** | 无自有上报；见 [`OPEN_SOURCE_RELEASE.md`](./OPEN_SOURCE_RELEASE.md) §6 |
| **官方插件市场 / 应用商店** | 扩展通过 Workflow、MCP、配置完成；无中心化市场 |
| **法律 / 合规托管** | 用户自行评估送入第三方 LLM 的数据；见隐私说明（T2 文档） |

---

## 4. 常见误解 → 标准答复

| Issue 类问题 | 答复要点 |
|--------------|----------|
| 为什么没有多人协作？ | Non-Goal：个人 / 小团队本地工具，见 §3 |
| 为什么没有云同步？ | 本地优先；可手动备份数据目录 |
| 为什么不支持浏览器版？ | 需深度本地进程与文件系统访问 |
| 为什么不内置 Cursor？ | 通过唤起 / CLI 桥接，不嵌入或替代 Cursor |
| 为什么 Workflow 跑不完？ | 不保证全自动；检查人工门控、CLI 安装与 Key 配置 |
| 能否做成 XX 云的 Agent 平台？ | 超出范围；欢迎 fork |

可将此类 Issue 打上 `wontfix` 并链接本文（见 [`docs/agents/triage-labels.md`](./agents/triage-labels.md)）。

---

## 5. 与相邻项目的关系

```
┌─────────────────────────────────────────────────────────┐
│  Clutch（编排 + 监督 + 工作流 UI）                        │
│       │ 调度                    │ 监督                    │
│       ▼                         ▼                         │
│  Claude Code / agy / Aider     Terminal / Diff / Chat    │
│  Ollama / MCP Servers          Human-in-the-Loop           │
│       │                                                   │
│       ▼                                                   │
│  Cursor 等 GUI（可选唤起）                                 │
└─────────────────────────────────────────────────────────┘
```

- **上游**：各 LLM Provider、本地 CLI 的许可与能力边界由各自产品决定。  
- **下游**：用户工作区内的代码与数据归用户所有。

---

## 6. 范围变更流程

若需将 Non-Goal 提升为 Goal（例如官方 Windows 支持、有限云备份）：

1. 在 [`memory/DECISIONS.md`](../memory/DECISIONS.md) 开 ADR 讨论  
2. 更新本文与 [`PRODUCT_INTRO.md`](./PRODUCT_INTRO.md)  
3. 在 [`ROADMAP.md`](../memory/ROADMAP.md) 设验收项  

未经上述流程的 **大范围方向 Issue** 可能直接关闭并指向本文。

---

## 7. 相关文档

| 文档 | 内容 |
|------|------|
| [`EXTENSIBILITY.md`](./EXTENSIBILITY.md) | 官方支持的扩展点 |
| [`STABILITY.md`](./STABILITY.md) | API / Schema 稳定性承诺 |
| [`GOVERNANCE.md`](./GOVERNANCE.md) | 维护者与 PR 决策 |
| [`OPEN_SOURCE_RELEASE.md`](./OPEN_SOURCE_RELEASE.md) | 开源、安全、分发排期 |
