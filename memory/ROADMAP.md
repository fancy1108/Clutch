# ROADMAP

> **Default FAIL：** 所有功能项默认 ❌，必须实际验证通过后才能标记 ✅。  
> 验证证据记入 `TESTS.md` 或 `runs/verification/`。

## 功能清单

（第 6 步拆解 `tasks.md` 后填实）

## E2E 落地前提（关联 DECISIONS D1）

> D1 决策状态为 `已记录` 时，**禁止**建 `e2e/` 或安装 Playwright，即使范围已定。

| 前提 | 关联里程碑 | 状态 | 验证证据 |
|------|------------|------|----------|
| 前端收到真实 `state_patch` | M0 | ❌ | TESTS.md / `runs/verification/` |
| Terminal / Chat 无 mock，为真数据 | M2 | ❌ | ROADMAP 功能项 + TESTS.md |
| CLI 真实执行跑通 | M3 | ❌ | ROADMAP 功能项 + TESTS.md |

## 待办（开发里程碑）

- [ ] **M0**：Tauri + Sidecar 骨架 + WebSocket；验收：前端收到真实 `state_patch` → 更新上表第一行
- [ ] **M1**：WorkflowCompiler + 最小 LangGraph；M1 前决策 Q2、Q3（见 `DECISIONS.md`）
- [ ] **M2**：去除 mock，Terminal / Chat 真数据 → 更新上表第二行；D1 可改为 `可执行`
- [ ] **M3**：CLI Adapter 跑通 → 更新上表第三行；E2E 闭环用例可对齐
- [ ] 第 6 步：拆解 `specs/core/tasks.md`，填实 §功能清单

## 待验证前提（来自 proposal §13 依赖与前提）

| 假设 | 待验证内容 |
|------|-----------|
| Python 3.11+ 可运行 | 开发期用户环境；发布期内嵌 runtime 可行性 |
| Claude API Key / Claude Code 已登录 | 用户自行配置路径与 UX |
| 目标项目已 clone 并授权为工作区 | 工作区路径白名单机制 |
| macOS 12+ 为第一平台 | Tauri 打包与 Sidecar 生命周期 |
