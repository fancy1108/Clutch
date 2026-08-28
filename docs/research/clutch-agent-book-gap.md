# Research Notice

Exploratory material only.

This document is **not** a source of truth.

Do **not** record implementation status or feature completion here.

Current implementation status:

- docs/PRODUCT_INTRO.md
- memory/ROADMAP.md
- docs/ARCHITECTURE.md

Candidates: [`memory/BACKLOG.md`](../../memory/BACKLOG.md) **B-36–B-50**。B-34 / B-35 定义见 [`specs/core/tasks.md`](../../specs/core/tasks.md) §Agent Harness · §Agent status。  
Open questions: [`memory/DECISIONS.md`](../../memory/DECISIONS.md) **Q-AGENT-1–4**.

---

## 1. 范围

对照 Obsidian《深入理解 AI Agent》01–10 与 Chat Clutch Agent（交付表 D0–D53 已自验）。结论只描述缺口与取舍，不勾选验收。

**一句话：** D0–D53 铺齐了「能做事」；下一阶段差在 Harness（约束/验证/纠正）、可复现评测、以及从经验外部化学习。不要再加一套与 D46–D52 平行的活动 UI，也不要用后训练当产品路线。

来源：`~/obsidian/PARA/2_Areas/AI_Agent_深入理解/深入理解AI Agent - 0{1–10}*.md`。

## 2. 公式

书：`Agent = LLM + 上下文 + 工具`；生产再加 Harness（约束 + 验证 + 纠正）。  
Clutch 已有 ReAct、builtins、Plan/Todo/验证卡、Skills 渐进披露、`/compact`、MCP Hub、Chat 步骤条。薄的是：自动纠正、状态栏/压缩的缓存布局、记忆整理、事件唤醒、任务级评测。

## 3. 按章缺口（候选 ID）

| 章 | 已覆盖 | 仍薄 | BACKLOG |
|----|--------|------|---------|
| 01 Harness | 审批、熔断、透明轨迹 | 独立审核、无进展循环、四层故障恢复 | B-37、B-38 |
| 02 上下文 | D53 分层、`/compact`、`task_state` | 时间/Todo 在 prefix 破坏缓存；无代码维护状态栏；压缩非五层 | B-35、B-36、B-44 |
| 03 记忆 | D16 扁平 JSON（≤64×400 字，塞最近 16 条） | 无冲突/睡眠整合/按需检索；写入无投毒审查 | B-39、B-45；检索见 B-10 |
| 04 工具 | 感知+执行+部分协作+Cron | 缺 Channel 推送唤醒、`notify_user`、ACI 反例 | B-41、B-42、B-46 |
| 05 Coding | 七件套、worktree API、严沙箱开关 | 验证自报；无强制测套；无独立 interpreter | B-37、B-47；PTY/策略见 B-18–B-21 |
| 06 评估 | pytest 契约；无任务级 eval | **最大结构缺口**：无评测集/提示词回归/消融 | B-34、B-48 |
| 07 后训练 | — | 不训权重；只吸收「会思考的模型 + 禁破坏性捷径」 | 不立项 |
| 08 进化 | 消费 Skills | 无成功摘要/失败反思/睡眠整合 | B-40、B-39 |
| 09 多模态 | 发图/OCR/出图 | Design 缺渲染截图 reviewer；不做 CU/机器人 | B-49；Design D36 |
| 10 多 Agent | Flow + 子任务卡 | 缺「新信息」门禁；并行未默认隔离 | B-43；并行见 B-08；分派见 B-01 |

## 4. 建议顺序（升格后，一次一个 task）

1. 评测骨架（B-34，先决 **Q-AGENT-1**）— 快照/契约/可选真模型；**不是**把时间从 system 前缀挪走
2. 上下文 Harness（B-35/B-36，先决 **Q-AGENT-2**）— 时钟/Todo 出前缀、进末尾状态条
3. 验证闭环（B-37/B-38，先决 **Q-AGENT-3**）
4. 记忆进化（B-39/B-40，先决 **Q-AGENT-4**）

原则：事实→知识库；稳且参数复杂→代码工具；常变策略→Skill。多 Agent 只为测试结果/截图/工具验证加角色，禁止同模型互评同一段文本。

## 5. 明确不立项

后训练当路线；为对齐书做 Computer Use / VLA / Agent 经济；再扩一套活动 UI；无评测地大改 system 或一次打进全部 MCP 工具；多个同模型 Agent 纯文本互辩当质量手段。

## 6. 与已有池的重叠（勿重复立项）

| 已有 | 书中对应 |
|------|----------|
| B-01 | 10 管理者分派 |
| B-02 / Q-USAGE-1 | 06 用量真值 |
| B-08 | 10 并行 + worktree |
| B-10 | 03 检索而非全塞 |
| B-12 | 05/08 文件系统记忆（本轮偏 `MEMORY.md`） |
| B-18–B-22 | 04/05 沙箱与 exec policy |
| B-26 | 04 协作 spawn/wait |
| B-27 / B-28 | 已指向交付表 D28 / D43 |
