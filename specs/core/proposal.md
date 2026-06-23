> **本文档为历史快照，不随项目演进更新。** 如与 `CLAUDE.md` / `memory/DECISIONS.md` 中记录的最新决策冲突，以后者为准。  
> 内部相对路径链接（如 `./ARCHITECTURE.md`）反映迁移前的目录结构，可能已失效，**不会被修复**——这是预期行为，不是遗漏。  
> 当前架构文档见 [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md)。

# Clutch — 产品需求提案

> **版本**: v0.1  
> **状态**: 提案已确认方向 [STALE：与 §16 技术负责人「待填写」并存]  
> **最后更新**: 2026-06-22  
> **关联文档**: [系统架构文档](./ARCHITECTURE.md)

---

## 1. 摘要

**Clutch** 是一款面向开发者与技术运营人员的桌面应用，用于 **可视化编排、运行和监督 AI 多 Agent 工作流**。用户无需编写代码，通过拖拽节点定义 SOP（标准作业程序），系统自动调度本地 AI 工具（CLI、MCP、Cursor 等），并在统一控制台中完成任务执行、质量校验与人工审批。

当前仓库为 **高保真 UI Prototype**（纯前端模拟）。本提案定义从 Prototype 到可交付 MVP 的产品目标、功能范围与验收标准。

---

## 2. 背景与问题

### 2.1 现状痛点

| 痛点 | 描述 |
|------|------|
| 工具碎片化 | Claude Code、Cursor、MCP 各自独立，缺乏统一编排视图 |
| 过程不可见 | CLI 在终端执行，难以追溯 Agent 决策与中间产物 |
| 质量难把关 | 生成代码缺少结构化 Evaluator 与人工 Gate |
| 重复劳动 | 常见 SOP（修 bug、写文档、视频流水线）无法复用 |
| 门槛高 | 现有 Agent 框架（LangGraph 等）需要写代码，非开发者难上手 |

### 2.2 机会

- LangGraph 提供了成熟的 **状态机 + 人机协同** 能力，适合作为后端引擎
- 现有 Prototype 已验证 **三栏监督式 UI** 与 **React Flow 工作流编辑器** 的交互可行性
- 桌面端可合法、深度地调度本地环境与 GUI 工具

---

## 3. 产品愿景与目标

### 3.1 愿景

> 让技术从业者像「导演」一样指挥 AI 团队：在一张画布上定义流程，在一个工作台里监督执行，在关键节点拍板决策。

### 3.2 产品目标（MVP）

1. **零代码编排**：用户通过界面拖拽完成工作流定义，无需了解 LangGraph
2. **真实可运行**：至少一条端到端流水线能调用真实本地工具并产生文件变更
3. **全程可监督**：Chat、Terminal、Diff、Flow 进度在同一界面实时更新
4. **人机协同**：校验失败时可 Approve / Reject / 带指令 Retry
5. **本地优先**：数据与 API Key 留在本机，Sidecar 不对外暴露

### 3.3 非目标（MVP 不做）

- 云端多租户 / 团队协作后台
- 移动端应用
- 替代 Cursor / Claude Code 成为 IDE
- 用户自定义 Python 节点代码
- 复杂计费与用量分析

---

## 4. 目标用户

### 4.1 主要用户画像

| 画像 | 描述 | 核心诉求 |
|------|------|----------|
| **独立开发者** | 使用 AI 工具提效，管理多个本地项目 | 可复用 SOP、看得见执行过程 |
| **技术运营** | 负责内容生产、发布流水线（如视频、文档） | 质量 Gate、人工审批 |
| **AI 工作流搭建者** | 为非技术人员配置 Agent 流程 | 界面化编排、少写代码 |

### 4.2 用户能力假设

- 熟悉基本开发概念（文件、终端、Git），但 **不需要** 会写 LangGraph 或 Python
- 已在本地安装或可安装 Claude Code CLI、Cursor 等工具
- macOS 为第一优先平台（后续扩展 Windows）

---

## 5. 核心用户旅程

### 5.1 旅程 A：使用模板运行任务

```
打开应用 → 选择「Video Production」模板 → 输入任务描述
→ 点击运行 → 观看 Chat / Terminal 实时输出
→ Evaluator 报错 → 点击「交给 Builder 修复」
→ 校验通过 → 完成
```

### 5.2 旅程 B：自定义工作流

```
设置 → Workflows → 新建工作流
→ 拖入「Agent 任务」「自动检查」「等我确认」节点并连线
→ 配置 Builder 使用 Claude CLI
→ 保存 → 回到主界面选择该工作流 → 运行
```

### 5.3 旅程 C：Cursor 协同写码

```
工作流进入「Write Code」步骤
→ 系统提示「在 Cursor 中打开项目」→ 用户点击按钮
→ 用户在 Cursor 编辑并保存
→ 系统自动触发 Evaluator 检查
→ 结果推送到 Chat 与 Changes 面板
```

---

## 6. 功能需求

### 6.1 功能总览

| 模块 | 优先级 | 说明 |
|------|--------|------|
| 工作流画布 | P0 | 拖拽编排、保存、加载、模板 |
| 运行监督台 | P0 | Chat + Terminal + 状态展示 |
| 编排引擎 | P0 | LangGraph 执行 Workflow JSON |
| 人工干预 | P0 | Approve / Reject / Retry |
| CLI 工具接入 | P1 | Claude Code 等 |
| 文件变更与 Diff | P1 | Changes 面板真实数据 |
| Cursor 唤起 + 自动检查 | P1 | GUI 工具协同 |
| Agent 配置 | P1 | 角色、说明、工具、Skills |
| MCP 管理 | P2 | 连接、状态、工具数 |
| Skills 注册 | P2 | 目录扫描与挂载 |

---

### 6.2 FR-01 工作流编辑器（Workflow Editor）

**描述**：用户在可视化画布上创建和编辑 SOP 工作流。

| ID | 需求 | 验收标准 |
|----|------|----------|
| FR-01-01 | 提供有限节点类型：开始、Agent 任务、自动检查、等我确认、完成 | 侧边栏可拖入五种节点 |
| FR-01-02 | 支持节点连线表示执行顺序 | 连线可保存并在重新打开时还原 |
| FR-01-03 | Agent 任务节点可配置：角色、任务说明、可选工具 | 表单保存至 Workflow JSON |
| FR-01-04 | 自动检查节点可配置检查项（如文件存在、lint 命令） | 至少支持 `file_exists` 与 `shell` 两种 |
| FR-01-05 | 检查节点支持「通过 / 不通过」分支连线 | 不通过可连至「等我确认」或回退 Agent |
| FR-01-06 | 保存前校验图结构合法性 | 缺少开始/结束、孤立节点时给出中文提示 |
| FR-01-07 | 提供内置模板（如 Video Production、Bug Fix） | 一键导入后可修改另存 |
| FR-01-08 | 用户无需看到任何代码或 LangGraph 概念 | 界面仅出现业务语言 |

---

### 6.3 FR-02 运行监督台（Supervision Console）

**描述**：主界面三栏布局，实时展示运行状态。

| ID | 需求 | 验收标准 |
|----|------|----------|
| FR-02-01 | 左侧栏展示工作区 / 项目 / 历史运行入口 | 可切换不同工作流上下文 |
| FR-02-02 | 中间 Chat 流按 Agent 角色展示消息 | Orchestrator / Builder / Evaluator 有区分样式 |
| FR-02-03 | 失败消息以醒目卡片展示 | 与 Prototype VALIDATION FAILED 体验一致 |
| FR-02-04 | 右侧 Overview 展示当前状态、进度、Token 等摘要 | 随 WebSocket 实时更新 |
| FR-02-05 | 右侧 Terminal 展示真实子进程日志 | 非 mock 字符串 |
| FR-02-06 | 右侧 Changes 展示真实 git diff 或文件 diff | 文件可点击预览 |
| FR-02-07 | 右侧 Flow 展示当前工作流及活跃节点高亮 | 运行中节点视觉区分 |
| FR-02-08 | 底部状态栏展示 Branch、Mode、当前 Flow | 与 Prototype 一致 |
| ~~FR-02-09~~ | ~~支持 Single / Multi Agent 模式切换~~ | **废止（D10）** — 仅 Multi Agent |

---

### 6.4 FR-03 编排与执行引擎（Orchestration Engine）

**描述**：后端将 Workflow JSON 编译为 LangGraph 并执行。

| ID | 需求 | 验收标准 |
|----|------|----------|
| FR-03-01 | 接收 `start_run(workflow_id, instruction)` 启动运行 | 返回 `run_id` |
| FR-03-02 | 维护 `ClutchState` 全局状态 | 状态可序列化、可推送 |
| FR-03-03 | Orchestrator 节点负责路由下一跳 | 依据工作流边与 LLM 分析 |
| FR-03-04 | 支持 `stop_run` 终止执行 | 子进程被清理 |
| FR-03-05 | 每次状态跳跃推送 WebSocket 事件 | 前端 500ms 内感知 |
| FR-03-06 | 运行结束推送 `run_completed` | 含 passed / failed 最终态 |

---

### 6.5 FR-04 人工干预（Human-in-the-Loop）

**描述**：校验失败或 Gate 触发时，用户可手动决策。

| ID | 需求 | 验收标准 |
|----|------|----------|
| FR-04-01 | 进入人工闸门时 UI 展示 Approve / Reject / Retry | 与 Prototype 按钮一致 |
| FR-04-02 | Approve 可强制通过当前 Gate | 状态变为 passed，有审计日志 |
| FR-04-03 | Reject 将任务打回并记录原因 | Chat 出现 Supervisor 消息 |
| FR-04-04 | Retry 支持附加文字指令 | 指令传入下一轮 Builder |
| FR-04-05 | 人工操作写入 Terminal 审计日志 | 含 `[SUPERVISOR]` 前缀 |

---

### 6.6 FR-05 工具接入（Tool Integration）

| ID | 需求 | 验收标准 |
|----|------|----------|
| FR-05-01 | CLI Adapter 可执行配置命令并捕获输出 | Claude Code CLI 可完成一次真实调用 |
| FR-05-02 | 退出码非 0 时标记步骤失败 | 触发后续失败分支 |
| FR-05-03 | GUI Adapter 可唤起 Cursor 打开工作区 | macOS `open -a Cursor` 生效 |
| FR-05-04 | FS Watcher 检测保存事件并 debounce | 触发 Evaluator 不超过 3s 延迟 |
| FR-05-05 | MCP Server 可配置连接信息与状态展示 | 至少 filesystem MCP 可连通 |
| FR-05-06 | AI Tools 面板展示工具连接状态 | connected / available |

---

### 6.7 FR-06 Agent 与 Skills 配置

| ID | 需求 | 验收标准 |
|----|------|----------|
| FR-06-01 | 可编辑 Orchestrator / Builder / Evaluator 说明文档 | Markdown 预览 |
| FR-06-02 | 可配置 Agent 绑定的 MCP 工具与 Skills | 保存后下次运行生效 |
| FR-06-03 | 可定义 Deliverables（期望产出文件） | 缺失时 Evaluator 可报错 |
| FR-06-04 | Skills Registry 支持挂载目录与启用/禁用 | 与 Agent 配置联动 |

---

### 6.8 FR-07 桌面应用与本地服务

| ID | 需求 | 验收标准 |
|----|------|----------|
| FR-07-01 | 以 Tauri 桌面应用形式启动 | 无需用户手动开两个终端 |
| FR-07-02 | 自动启动 Python Sidecar 并健康检查 | 失败时有明确错误提示 |
| FR-07-03 | API Key 通过本地安全存储配置 | 不出现在日志中 |
| FR-07-04 | Sidecar 仅监听 localhost | 外部网络无法访问 |

---

## 7. 非功能需求

| 类别 | 要求 |
|------|------|
| **性能** | UI 操作响应 < 100ms；日志流延迟 < 500ms |
| **稳定性** | 单个子进程崩溃不导致整个 Sidecar 崩溃 |
| **可用性** | 核心流程无需阅读文档即可完成（模板运行） |
| **可维护性** | Workflow JSON Schema 版本化；Compiler 与 UI 解耦 |
| **安全** | 工作区路径白名单；高危工具需确认 |
| **美学** | 遵循 `UI_UX_GUIDELINES.md` |
| **平台** | MVP 支持 macOS；架构预留 Windows |

---

## 8. 界面与体验原则

1. **业务语言优先**：界面不出现 LangGraph、node、edge 等术语
2. **监督而非黑盒**：任何自动动作都可在 Terminal / Chat 追溯
3. **失败是可操作的**：错误卡片旁必有下一步（修复、审批、重试）
4. **渐进复杂度**：模板 → 改参数 → 拖节点，三级上手路径
5. **多 Agent 编排**：统一 Multi Agent 工作流体验（单 Agent 模式不开发，D10）

---

## 9. 数据与配置

| 数据 | 存储位置 | 说明 |
|------|----------|------|
| Workflow 定义 | 本地 JSON 文件 | 用户工作流 / 模板 |
| Agent 配置 | 本地 JSON / SQLite | 角色 prompt、工具绑定 |
| API Keys | Tauri secure store | 加密 |
| Skills 挂载路径 | 本地配置 | 可沿用 Registry 逻辑 |
| 运行历史 | 本地 SQLite（P2） | MVP 可仅内存 |

---

## 10. MVP 范围与里程碑

### 10.1 MVP 定义

**MVP = 用户能完成一次「从模板运行 → CLI 真实执行 → 检查失败 → 人工审批 → 通过」的完整闭环。**

### 10.2 里程碑

| 阶段 | 周期（建议） | 交付物 | 验收 |
|------|--------------|--------|------|
| **M0: 基座** | 1–2 周 | Tauri + Sidecar 骨架 + WebSocket | 前端收到真实 `state_patch` |
| **M1: 引擎** | 2 周 | WorkflowCompiler + 最小 LangGraph | JSON 工作流可执行 |
| **M2: 监督台** | 1–2 周 | 去除 mock，接入真实事件 | Terminal / Chat 为真数据 |
| **M3: 工具** | 2 周 | CLI Adapter + Diff + Cursor 唤起 | Claude CLI 跑通 |
| **M4: 打磨** | 1 周 | 模板、错误提示、打包 | 可安装 DMG 演示 |

### 10.3 MVP 功能裁剪

| 包含 | 不包含 |
|------|--------|
| 5 种基础节点类型 | 自定义脚本节点 |
| 1–2 个内置模板 | 模板市场 |
| Claude CLI | 全部 AI 工具 |
| filesystem MCP | 全部 MCP 类型 |
| macOS 打包 | Windows 签名发布 |
| 本地单用户 | 账号体系 |

---

## 11. 成功指标

| 指标 | MVP 目标 |
|------|----------|
| 首次运行成功率 | ≥ 90%（在预装依赖环境下） |
| 模板到完成时间 | < 10 分钟（含一次人工干预） |
| 工作流创建时间 | 新用户 < 15 分钟可自建三节点流程 |
| 日志可追溯性 | 100% 运行步骤在 Terminal 有记录 |
| 崩溃率 | Sidecar 连续 1 小时运行无未捕获崩溃 |

---

## 12. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| Python 打包复杂 | 发布延期 | 早期用 dev 模式；M4 再内嵌 runtime |
| CLI 输出不可解析 | 体验差 | 先原样流式展示，再逐步结构化 |
| Cursor 无 API | 无法自动写码 | 文件监听 + 提示式协同，不承诺全自动 |
| 用户拖出非法图 | 编译失败 | 保存前 UI 校验 + 中文错误 |
| LLM 路由不稳定 | 跳错节点 | 工作流边优先于 LLM 决策（规则兜底） |
| API 成本 | 费用超支 | 可配置模型；Token 统计展示 |

---

## 13. 依赖与前提

- 用户本机可运行 Python 3.11+（开发期）或安装包内嵌 runtime（发布期）
- 用户自行配置 Claude API Key 或 Claude Code 已登录
- 目标项目已 clone 到本地并授权为工作区
- macOS 12+（MVP）

---

## 14. 开放问题

| # | 问题 | 建议决策时间 |
|---|------|--------------|
| Q1 | 运行历史是否纳入 MVP | M2 结束前 |
| Q2 | 默认 LLM 用 Claude 还是可切换 | M1 开始前 |
| Q3 | Workflow 文件存放于项目内还是应用数据目录 | M1 开始前 |
| Q4 | Evaluator 默认检查规则库如何维护 | M3 开始前 |

---

## 15. 附录：与 Prototype 的对照

当前 Prototype 已具备 **视觉与交互验证**，以下能力需在 MVP 中「去 mock 化」：

| Prototype 现状 | MVP 目标 |
|------------------|----------|
| `setTimeout` 模拟修复 | LangGraph 真实状态跳转 |
| `mockData.ts` 硬编码消息 | WebSocket `message` 事件 |
| `getFullFileContent` 假文件 | 真实工作区读盘 |
| `alert()` 占位设置项 | 接后端 API |
| Skills `localStorage` | 后端配置同步 |
| AI Studio / Gemini 占位 | Claude API + 本地 Sidecar |

---

## 16. 审批记录

| 角色 | 姓名 | 日期 | 结论 |
|------|------|------|------|
| 产品负责人 | — | 2026-06-22 | 方向确认：Tauri + Python LangGraph + 界面化 Workflow |
| 技术负责人 | — | 待填写 [STALE：与文首「已确认方向」并存] | — |

---

*[STALE] 本提案为活文档，随 MVP 迭代更新。技术细节见 [架构文档](./ARCHITECTURE.md)。—— 与文首「历史快照」声明冲突，以 CLAUDE.md / memory/DECISIONS.md 为准。*
