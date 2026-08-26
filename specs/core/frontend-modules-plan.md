# Frontend modules（FM-xx）

> **Task 定义 + Verification。** 验收状态仅 [`memory/ROADMAP.md`](../../memory/ROADMAP.md) §Frontend modules — **本文件不勾选 ✅/❌。**  
> **决策：** D56 — [`memory/DECISIONS.md`](../../memory/DECISIONS.md)  
> 每条须用户能在桌面 UI 点验；新控件带 `data-testid`；勾 ROADMAP 前更新 `docs/PRODUCT_INTRO.md`。  
> 一次一个模块。不进本轨道：价表、Windows 实体机（D55）、已否决 B-15/B-16。D32 worktree 开关已有；FM-11 只做并行子树 + 合并/丢弃。

## 门禁

1. 桌面可点击路径（不只 pytest）。
2. `./scripts/verify.sh`；触及 Settings/Chat 时补 E2E testid。
3. 单次 ≤3 新文件、≤200 行。

## Wave 1 · Settings / Trust

| ID | 主题 | 用户点验 | Verification |
|----|------|----------|--------------|
| **FM-01** | General 收尾（P2-06） | 默认工作区重启仍激活；高危确认 On 时 Stop 先确认；General 显示版本 | pytest 偏好 API + E2E General |
| **FM-02** | MCP / 工作流本机信任（OSR-21） | Hub 白名单；未信任工作流运行前确认卡 | pytest + 手动跑 SOP |
| **FM-03** | Exec policy UI（B-18/21/22；OSR-18 界面） | Settings allow/ask/deny；危险命令 `human_required` | pytest + Chat 审批 |

## Wave 2 · CLI 只读扫描

模式：`readOnlyScan`（Claude/OpenCode/MiMo）。Coming soon 七个升格为页签。

| ID | CLI |
|----|-----|
| **FM-04** | Codex |
| **FM-05a–f** | Aider · CodeBuddy · Antigravity · Rivet · Ollama · ZCode |

点验：Settings Models/Skills/MCP 有该 CLI 页签，能扫到配置或明确空态。其它 whitelist（cursor/grok/…）不在首期。

## Wave 3 · Orchestra 收口（D34-ε）

| ID | 主题 | 用户点验 |
|----|------|----------|
| **FM-06** | 超 N 排队 + 草稿生命周期 | 第 5 路可见排队；Complete → 可编辑/关闭草稿；确认卡可改 sources |
| **FM-07** | 保存为工作流 | Overview → SOP，Workflows 节点顺序对齐派发 |
| **FM-08** | 对话模式 handoff | Chat 可见草稿 / Send to Bar；切 Terminal 时 handoff 含近期对话 |

## Wave 4 · 编排

| ID | 主题 | 用户点验 |
|----|------|----------|
| **FM-09** | 主控分派（B-01） | 空态直接发送；横幅「已匹配 SOP」或「用当前 Agent」；不强制先选工作流 |
| **FM-10** | 画布 tool（B-04） | 节点可选 CLI/MCP/llm；Overview 显示该节点引擎 |

## Wave 5 · 协作 / 记忆 / 事件 / Design

| ID | 来源 | 用户点验 |
|----|------|----------|
| **FM-11** | B-08 | 并行子任务各 worktree 路径；合并/丢弃 |
| **FM-12** | B-10 | Settings/Files 搜 `.clutch/memory`，结果可打开 |
| **FM-13** | B-42 | Settings 配 Webhook；事件到时 Chat 横幅「继续」 |
| **FM-14** | B-46 | `notify_user` 卡；子 Agent 发送/取消 |
| **FM-15** | B-43 | 并行前「新信息」确认卡 |
| **FM-16** | B-49 | Design 渲染截图 + 审查卡可驳回 |
| **FM-17** | B-47 | 解释器超时/断网结构化错误卡 |
| **FM-18** | B-05 | 校验失败进 Chat/Overview 可读条 |
| **FM-19** | B-06 | Planner/Executor 分模型；Overview 显示本轮模型 |

## Wave 6 · 非界面（全部 FM 勾完之后）

| ID | 主题 | 完成标准 |
|----|------|----------|
| **FM-20** | OSR-29 | `docs/PERFORMANCE.md` 补本机测量数 |
| **FM-21** | OSR-11 | Apple 签名+公证流程文档；无账号则记录阻塞 |
| **FM-22** | OSR-22 | 外部审计委托说明 + 报告存放路径 |

## 顺序

`FM-01 → 02 → 03 → 04 → 05a–f → 06 → 07 → 08 → 09 → 10 → 11–19 → 20–22`

## 文件落点（首模块）

| 模块 | 主要路径 |
|------|----------|
| FM-01 | `SystemPreferencesModal.tsx` · `preferences_storage.py` · `routes/settings.py` · `App.tsx` Stop |
| FM-02 | `McpServerHub.tsx` · 工作流信任偏好 |
| FM-04+ | `agentCapabilityTiers.ts` · `cli_agent_config.py` |
| FM-06–08 | `terminal_orchestra.py` · `TerminalLaneGrid.tsx` · `OrchestratorBar.tsx` · `ChatFeed.tsx` |
| FM-09 | `ChatFeed.tsx` 空态 · sidecar 匹配 API |
| FM-10 | `WorkflowOrchestration.tsx` · `agent_executor.py` |
