# ROADMAP

> **Default FAIL：** 所有功能项默认 ❌，必须实际验证通过后才能标记 ✅。  
> 验证证据记入 `TESTS.md` 或 `runs/verification/`。  
> 任务拆解见 [`specs/core/tasks.md`](../specs/core/tasks.md)。

## 功能清单

| 模块 | 优先级 | 里程碑 | 状态 | 任务 ID |
|------|--------|--------|------|---------|
| 工作流画布 | P0 | M1 | ❌ | M1-06, M1-07 |
| 运行监督台 | P0 | M2 | ❌ | M2-01–03, M2-07 |
| 编排引擎 | P0 | M1 | ❌ | M1-02–05（D4 Provider 抽象） |
| 人工干预 | P0 | M2 | ❌ | M2-04, M2-05 |
| 桌面基座（Tauri + Sidecar + WS） | P0 | M0 | ❌ | M0-01–06 |
| CLI 工具接入 | P1 | M3 | ❌ | M3-01 |
| 文件变更与 Diff | P1 | M3 | ❌ | M3-02 |
| Cursor 唤起 + 自动检查 | P1 | M3 | ❌ | M3-03, M3-04 |
| Agent 配置 | P1 | M4 | ❌ | M4-02 |
| MCP 管理 | P2 | M4 | ❌ | M4-03 |
| Skills 注册（后端同步） | P2 | 延后 | ❌ | tasks §P2 |
| 单 Agent 模式 | P2 | 延后 | ❌ | tasks §P2 |
| 内置模板 | P1 | M4 | ❌ | M4-01 |
| 运行历史 | P0 | M2 | ❌ | M2-07（D3） |
| macOS 打包 | P1 | M4 | ❌ | M4-06 |
| **MVP 闭环** | — | M3 | ❌ | proposal §10.1 |

## E2E 落地前提（关联 DECISIONS D1）

> D1 决策状态为 `已记录` 时，**禁止**建 `e2e/` 或安装 Playwright，即使范围已定。

| 前提 | 关联里程碑 | 状态 | 验证证据 |
|------|------------|------|----------|
| 前端收到真实 `state_patch` | M0 | ❌ | TESTS.md / `runs/verification/` |
| Terminal / Chat 无 mock，为真数据 | M2 | ❌ | ROADMAP 功能项 + TESTS.md |
| CLI 真实执行跑通 | M3 | ❌ | ROADMAP 功能项 + TESTS.md |

## 待办（开发里程碑）

- [ ] **M0**：见 `tasks.md` §M0 → 验收后更新 E2E 前提第一行
- [ ] **M1**：见 `tasks.md` §M1（D4、D5 已决）
- [ ] **M2**：见 `tasks.md` §M2 → D1 可改为 `可执行`
- [ ] **M3**：见 `tasks.md` §M3 → MVP 闭环 ❌ 改 ✅
- [ ] **M4**：见 `tasks.md` §M4

## 待验证前提（来自 proposal §13 依赖与前提）

| 假设 | 待验证内容 |
|------|-----------|
| Python 3.11+ 可运行 | 开发期用户环境；发布期内嵌 runtime 可行性 |
| Claude API Key / Claude Code 已登录 | 用户自行配置路径与 UX |
| 目标项目已 clone 并授权为工作区 | 工作区路径白名单机制 |
| macOS 12+ 为第一平台 | Tauri 打包与 Sidecar 生命周期 |
