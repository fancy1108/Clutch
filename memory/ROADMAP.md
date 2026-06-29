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
| Skills 注册（后端同步） | P2 | P2 | ✅ | P2-01 |
| 全量 MCP 配置 | P2 | P2 | ✅ | P2-02 |
| Theme 持久化 | P2 | P2 | ✅ | P2-03 |
| i18n 双语 | P2 | P2 | ✅ | P2-04 |
| 侧栏 REPOSITORIES CRUD | P2 | P2 | ✅ | P2-05 |
| General Settings | P2 | P2 | ✅ 部分落地 | P2-06（D14；支持用户头像定制） |
| 内置模板 | P1 | M4 | ✅ | M4-01 |
| 运行历史 | P0 | M2 | ✅ | M2-07（D3）+ D11 对话持久化 |
| 文件浏览（Files 面板） | P0 | M2 | ✅ | M2-11 |
| Token / 校验结果展示 | P0 | M2 | ✅ | M2-13, M2-14 |
| 工作区授权 | P0 | M2 | ✅ | M2-09；M4-05 |
| E2E / 前端单测 | P0 | M2 | ✅ | M2-10, T-01–03（D1）；D12 桌面 E2E 7/7 |
| macOS 打包 | P1 | M4 | ✅ | M4-06 |
| **MVP 闭环** | — | M3 | ✅ | proposal §10.1；T-03 |

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
- [x] **M4**：M4-01–09（含 M4-06 DMG）
- [x] **T-03**：MVP 闭环 E2E（proposal §10.1）
- [x] **D12**：桌面全 UI E2E（`tauri-playwright`）

## 待验证前提（来自 proposal §13 依赖与前提）

| 假设 | 待验证内容 | 关联 task |
|------|-----------|-----------|
| Python 3.11+ 可运行 | 开发期用户环境；发布期内嵌 runtime 可行性 | M4-06 ✅ |
| Claude API Key / Claude Code 已登录 | 自动读取 `~/.claude/settings.json` | M4-04 ✅ |
| 目标项目已 clone 并授权为工作区 | 工作区路径白名单机制 | M2-09, M4-05 ✅ |
| macOS 12+ 为第一平台 | Tauri 打包与 Sidecar 生命周期 | M0-05 ✅, M4-06 ✅ |

---

## D25 · Hybrid Runtime（`CLUTCH_RUNTIME_MODE=hybrid`）

> **Task 权威表**：[`specs/core/hybrid-runtime-plan.md`](../specs/core/hybrid-runtime-plan.md)（HRT-xx）  
> **设计参考**：[`docs/research/pty-session.md`](../docs/research/pty-session.md)

| 模块 | 优先级 | 里程碑 | 状态 | Task ID |
|------|--------|--------|------|---------|
| ShellSession + SHELL_EXEC 核心 | P0 | D25-S1 | ✅ 代码 | HRT-S1 |
| agy Hybrid + baseline | P1 | D25-S2 | ✅ 代码 | HRT-S2 |
| Snapshot + 侧栏 ↻ + PTY 恢复 | P1 | D25-S3 | ✅ 代码 | HRT-S3 |
| runtime_registry 分发 | P1 | D25-S4 | ✅ 代码 | HRT-S4 |
| 池上限 + Snapshot 保留 | P2 | D25-S5-partial | ✅ 代码 | HRT-S5-partial |
| **基础 Plain Chat 产品验收** | **P0** | **D25** | **✅** | **HRT-04**（2026-06-27 用户 A–E） |
| Hybrid 审计 JSONL + debug API | P1 | D25 | ✅ | HRT-05~07 · `446b7a0` |
| 诊断导出 | P2 | D25 | ✅ | HRT-07 · `export-run-debug.sh` |
| 多 session 并发治理 | P1 | D25 | ⚠️ | HRT-08~10 ✅ · §F 人工多 session 待验 |
| POC #6/#10 自动化 | P1 | D25 | ✅ | HRT-10 · `test_hybrid_poc_acceptance.py` |

### D25 人工验收（HRT-04 门禁 · 默认 FAIL）

- [x] **A** 首轮气泡仅 assistant 文本（无 shell / snapshot 泄漏）
- [x] **B** 第二轮续聊正常 + 发送键恢复
- [x] **C** 旧 session 侧栏 ↻
- [x] **D** 回复后 idle；可切 session；无永久 Thinking
- [x] **E** Terminal 有 `[HYBRID]` + `[CHAT] ... chars`
- [ ] **F** 多 session 并发（见 `hybrid-runtime-plan.md` §3.2 F1–F5；HRT-08~10 代码 ✅，**人工待验**）
- [x] **G** 后台 hydrate（HRT-09；F 表内 F5 与 export 脚本覆盖排查）

证据：`runs/verification/2026-06-27-hrt-04-acceptance.md`

---

## 开源 / DMG 分发（OSR-xx）

> **Task 权威表：** [`docs/OPEN_SOURCE_RELEASE.md`](../docs/OPEN_SOURCE_RELEASE.md) §7.2、§7.7  
> **状态镜像：** [`memory/BACKLOG.md`](./BACKLOG.md) §开源 / DMG 分发  
> **Default FAIL：** 未实际验收不得标 ✅

| 阶段 | 触发线 | 目标 | 状态 | 备注 |
|------|--------|------|------|------|
| T0 护栏 | 持续 | 许可证、文档边界、semver | ⚠️ | OSR-01～04、23～25 ✅；OSR-05 🔄 |
| **T1 可公开仓库** | **公开 repo 前** | 社区文件、Sidecar 鉴权、CLI 策略 | ✅ | OSR-00/06～10、26～28 已验收（D31） |
| T2 可放心装 DMG | 陌生人分发前 | 未签名 DMG、Keychain、安装向导 | ⚠️ | OSR-13 Keychain ✅；OSR-14～17 待做 |
| T3 生态成熟 | 按需 | 沙箱、Windows、自动更新 | ❌ | OSR-18～22、29 |

### T1 检查清单（公开仓库前 · 默认 FAIL）

- [x] **OSR-00** 外部视角审计（维护者自验通过 2026-06-29，D31）
- [x] **OSR-06** `SECURITY.md` + `CODE_OF_CONDUCT.md` + `CONTRIBUTING.md`
- [x] **OSR-07** Secret scanning CI
- [x] **OSR-08** Sidecar session token 鉴权
- [x] **OSR-09** CLI 权限策略（D30：维持 skip + README 披露）
- [x] **OSR-10** README + `BUILD_FROM_SOURCE.md` + 产品截图（`docs/images/`）
- [x] **OSR-26** `GOVERNANCE.md`（草案 v0.1）
- [x] **OSR-27** 兼容性矩阵 + `doctor.sh`
- [x] **OSR-28** Issue / PR 模板

### T1 开闸信号（§7.5）

- [ ] 主路径：工作区 → 聊天/工作流 → 审批 可稳定复现
- [ ] 近 2 周无大规模 Settings / API 路由重构
- [ ] 愿意处理外部 Issue
