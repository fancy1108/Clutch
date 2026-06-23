# ROADMAP

> **Default FAIL：** 所有功能项默认 ❌，必须实际验证通过后才能标记 ✅。  
> 验证证据记入 `TESTS.md` 或 `runs/verification/`。  
> 任务拆解见 [`specs/core/tasks.md`](../specs/core/tasks.md)。

## 功能清单

| 模块 | 优先级 | 里程碑 | 状态 | 任务 ID |
|------|--------|--------|------|---------|
| 工作流画布 | P0 | M1 | ✅ | M1-01/06/07/09 |
| 运行监督台 | P0 | M2 | ✅ | M2-01–14 |
| 编排引擎 | P0 | M1 | ✅ | M1-02~05、M1-08/09 |
| 人工干预 | P0 | M2 | ✅ | M2-04, M2-05, M2-12 |
| 桌面基座（Tauri + Sidecar + WS） | P0 | M0 | ✅ | M0-01–06 |
| LLM Provider | P1 | M1 | ✅ | M1-08（D4）；M4-09 |
| CLI 工具接入 | P1 | M3 | ✅ | M3-01, M3-07 |
| 文件变更与 Diff | P1 | M3 | ✅ | M3-02（`file_changed` 投影） |
| Cursor 唤起 + 自动检查 | P1 | M3 | ✅ | M3-03, M3-04, M3-05 |
| Agent 配置 | P1 | M4 | ✅ | M4-02 |
| MCP 管理 | P2 | M4 | ✅ | M4-03（filesystem 状态） |
| Skills 注册（后端同步） | P2 | 延后 | ❌ | tasks §P2 |
| 单 Agent 模式 | P2 | 延后 | ❌ | tasks §P2 |
| 内置模板 | P1 | M4 | ✅ | M4-01 |
| 运行历史 | P0 | M2 | ✅ | M2-07（D3） |
| 文件浏览（Files 面板） | P0 | M2 | ✅ | M2-11 |
| Token / 校验结果展示 | P0 | M2 | ✅ | M2-13, M2-14 |
| 工作区授权 | P0 | M2 | ✅ | M2-09；M4-05 |
| E2E / 前端单测 | P0 | M2 | ✅ | M2-10, T-01–02（D1） |
| macOS 打包 | P1 | M4 | 🟡 | M4-06（`pnpm tauri build` 待本机验证） |
| **MVP 闭环** | — | M3 | 🟡 | proposal §10.1；T-03 待 Playwright 闭环用例 |

## E2E 落地前提（关联 DECISIONS D1）

| 前提 | 关联里程碑 | 状态 | 验证证据 |
|------|------------|------|----------|
| 前端收到真实 `state_patch` | M0 | ✅ | `test_ws_state_patch.py` |
| Terminal / Chat 无 mock，为真数据 | M2 | ✅ | M2-01/02/06 + `verify.sh` |
| CLI 真实执行跑通 | M3 | ✅ | `test_cli_adapter.py` |

## 待办（开发里程碑）

- [x] **M0**：M0-01–06
- [x] **M1**：M1-01–09
- [x] **M2**：M2-01–14
- [x] **M3**：M3-01–07（pytest）
- [x] **M4**：M4-01–05、07–09
- [ ] **M4-06**：本机 `pnpm tauri build` 产出 DMG 证据
- [ ] **T-03**：MVP 闭环 E2E（proposal §10.1）

## 待验证前提（来自 proposal §13 依赖与前提）

| 假设 | 待验证内容 | 关联 task |
|------|-----------|-----------|
| Python 3.11+ 可运行 | 开发期用户环境；发布期内嵌 runtime 可行性 | M4-06 |
| Claude API Key / Claude Code 已登录 | 用户自行配置路径与 UX | M4-04, M3-01 |
| 目标项目已 clone 并授权为工作区 | 工作区路径白名单机制 | M2-09, M4-05 ✅ |
| macOS 12+ 为第一平台 | Tauri 打包与 Sidecar 生命周期 | M0-05 ✅, M4-06 🟡 |
