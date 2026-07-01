# FILEMAP（文件路径速查）

> Agent Check-in 用：「改什么 → 去哪个文件」。  
> **完整架构设计、数据流与 ADR 叙事**见 [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)。  
> **开发任务**见 [`specs/core/tasks.md`](../specs/core/tasks.md)。

## 五层架构

| 层 | 目录 | 职责 |
|----|------|------|
| Layer 1 Governance | `CLAUDE.md`、`.cursor/rules/`、`.github/copilot-instructions.md` | 铁律、命令、Check-in — Agent 入口路由 |
| Layer 2 Product Truth | `specs/` | proposal、design、tasks — 产品需求快照（历史） |
| Layer 3 Runtime State | `memory/` | 进度、踩坑、决策 — 跨会话运行态 |
| Layer 4 Execution | `.claude/workflows/`、`.cursor/` | 操作剧本（须符合 `CLAUDE.md` §Layer 4 约束） |
| Layer 5 Evidence | `runs/` | `runs/<run_id>/` 工作流证据；`runs/verification/` 测试/覆盖率报告归档 |

## 权威优先级（冲突时）

`CLAUDE.md`（治理规则） > `memory/DECISIONS.md`（最新决策） > `specs/`（历史快照） > `runs/`（执行记录）

> `specs/core/proposal.md` 一旦与其他文档冲突，永远不是权威来源，只用于查证「最初的想法是什么」。

## 日志字段规范

所有自定义日志/事件输出遵循 `CLAUDE.md` §日志与事件字段规范（`run_id`、`node_id`、`source`、`level`、`message`、`timestamp`）。

## 文件定位

### 治理与规范

| 想改什么 | 去哪里 |
|---------|--------|
| 铁律、命令、Check-in | `CLAUDE.md` |
| 产品介绍文档 | `docs/PRODUCT_INTRO.md` |
| 文档总索引 | `docs/README.md` |
| 开源 / DMG 分发排期（OSR-xx） | `docs/OPEN_SOURCE_RELEASE.md` |
| 应用内更新（Prep / Go-live） | `docs/UPDATES.md` · `.github/workflows/release-updater.yml` |
| 开源协议 | `LICENSE` |
| 漏洞报告 | `SECURITY.md` |
| 社区行为准则 | `CODE_OF_CONDUCT.md` |
| 版本变更 | `CHANGELOG.md` · 版本快照 `docs/releases/` |
| Goals / Non-Goals | `docs/PROJECT_SCOPE.md` |
| API / Schema 稳定性 | `docs/STABILITY.md` |
| 扩展点边界 | `docs/EXTENSIBILITY.md` |
| 维护者治理 | `docs/GOVERNANCE.md` |
| 贡献指南（Phase 1 政策） | `CONTRIBUTING.md` |
| 性能基线 | `docs/PERFORMANCE.md` |
| 源码构建 | `docs/BUILD_FROM_SOURCE.md` |
| 环境自检 | `scripts/doctor.sh` |
| Tauri 桌面开发（Hybrid） | `scripts/tauri-dev.sh` · 根目录 `pnpm tauri:dev` |
| 产品需求历史 | `specs/core/proposal.md`（指针）· `specs/archive/proposal-v0.1.md` |
| 历史叙事归档 | `docs/archive/` · `specs/archive/` |
| 视觉设计快照 | `specs/core/design.md` → `docs/UI_UX_GUIDELINES.md` |
| 前端 UI 规范（权威） | `docs/UI_UX_GUIDELINES.md` |
| 开发任务清单（含 Verification） | `specs/core/tasks.md` |
| **D25 Hybrid Runtime Task（HRT）** | **`specs/core/hybrid-runtime-plan.md`** |
| Flow 多 Agent 接力 Task（D23） | `specs/core/tasks.md` §M3-F · Flow 多 Agent 接力 |
| Prototype → Task 全量映射 | `specs/core/tasks.md` §Prototype → Task 映射 |
| 待建 pytest 与 task 映射 | `specs/core/tasks.md` §待建 pytest 文件 |
| 里程碑级验收 T-01~04 | `specs/core/tasks.md` §测试与验收 |
| 进度 / 待办 | `memory/PROGRESS.md`（近期）· 归档 `memory/archive/PROGRESS-*.md` |
| **Git worktree · release slices** | v1.0.2 worktree 已清理（2026-07-01）；v1.0.3 开工时从 `dev` 新建：`git worktree add ../clutch-release-1.0.3-loop -b release/1.0.3-loop` |
| 候选优化需求池（未立项） | `memory/BACKLOG.md` · Active（含 **B-33** ← PR #22） |
| GitHub Issue 待修复 Bug | `memory/BACKLOG.md` §GitHub Issues · 待修复 Bug |
| **开源排期 OSR-xx 验收状态** | **`memory/ROADMAP.md` §开源分发** · Task 定义 `docs/OPEN_SOURCE_RELEASE.md` §7.2 |
| 文档生命周期 / 权威真相 | `docs/document-governance.md` |
| Orchestrator 主控能力调研（参考） | `docs/research/orchestrator-optimization-pool.md` |
| CLI PTY Session 改造方案（参考） | `docs/research/pty-session.md` |
| **D25 Hybrid 执行状态（权威）** | **`specs/core/hybrid-runtime-plan.md`** · D27 命名对齐 |
| PTY Session Step 0 实验 | `experiments/pty_poc/` |
| Task 交付索引（Commit / 证据） | `memory/DELIVERABLES.md` · 归档 `memory/archive/DELIVERABLES-*.md` |
| 决策与开放问题 | `memory/DECISIONS.md` |
| 功能验收状态 | `memory/ROADMAP.md` |
| 测试门禁状态 | `memory/TESTS.md` |
| Layer 4 边界与剧本约束 | `CLAUDE.md` §Layer 4 操作剧本 |
| 验收偏差 / 实现漂移物理诊断 | `.claude/workflows/truth-alignment.md` |

### 测试与 CI

| 想改什么 | 去哪里 |
|---------|--------|
| 测试策略与 E2E 范围 | `memory/DECISIONS.md`（D1） |
| E2E 落地前提勾选 | `memory/ROADMAP.md` §E2E 落地前提 |
| 后端单元测试（现有 + 随 task 新建） | `services/orchestrator/tests/`；清单见 `tasks.md` §待建 pytest |
| Video Core 测试 | `tests/test_video_core/` |
| CI 工作流 | `.github/workflows/ci.yml` |
| Secret scanning（gitleaks） | `.github/workflows/secret-scan.yml` |
| 本地一键校验 | `scripts/verify.sh` |
| Hybrid run 诊断导出（HRT-07） | `scripts/export-run-debug.sh` → `GET /api/runs/{id}/debug` |
| POC #6/#10 自动化验收（HRT-10） | `scripts/verify-hybrid-poc-06-10.sh` · `services/orchestrator/tests/test_hybrid_poc_acceptance.py` |
| D29 audit 回归（并发 rejection） | `services/orchestrator/tests/test_hybrid_audit_d29_regression.py` |
| 文档↔代码漂移机检 | `scripts/check-doc-drift.sh` |
| Git pre-commit（条件触发） | `.husky/pre-commit` |
| 验证报告归档 | `runs/verification/`（gitignore） |
| E2E 包（M2-10，D1 可执行后） | `e2e/`；见下表 |
| E2E 沙箱与门禁 | `scripts/e2e-sandbox-setup.sh`；`scripts/run-e2e.sh`；`runs/verification/.e2e-env` |
| E2E Node WS 助手 | `e2e/helpers/ws.ts` |
| E2E 桌面 Tauri 助手 | `e2e/helpers/tauri.ts`（`authorizeSandboxWorkspace`） |
| E2E 会话预置（Node） | `e2e/helpers/seed.ts` |
| E2E API：`session-history` | `e2e/tests/session-history.spec.ts` |
| E2E API：i18n 偏好 | `e2e/tests/i18n.spec.ts` |
| E2E API：workspace git | `e2e/tests/workspace-git.spec.ts` |
| E2E Desktop fixture | `e2e/fixtures/desktop.ts`（`@srsholmes/tauri-playwright`） |
| E2E Desktop 全 UI | `e2e/tests/desktop/all-ui.spec.ts` |
| E2E Desktop 历史续聊 | `e2e/tests/desktop/session-history.spec.ts` |
| E2E Tauri 沙箱 command | `apps/desktop/src-tauri/src/lib.rs` → `clutch_e2e_sandbox` |
| E2E 工作区注入（前端） | `apps/desktop/src/services/pickWorkspaceFolder.ts` |

### 前端（`apps/desktop/src`）

| 想改什么 | 去哪里 |
|---------|--------|
| 应用根布局、ClutchState 投影 | `App.tsx` |
| WebSocket store、`useClutchState` | `services/clutchState.ts` |
| 会话 / 运行 API | `services/runApi.ts` |
| Skills Registry API（P2-01） | `services/skillsApi.ts` |
| Theme 偏好 API（P2-03） | `services/themeApi.ts`（含 language） |
| API 抽象（mock 待 M2 替换） | `services/api.ts` |
| 侧栏（工作区 / 历史，M2-07/09） | `sidebar.tsx` |
| 底部状态栏（Branch / Model / Agent） | `App.tsx` footer |
| 工作区 Git 分支 API | `services/workspaceApi.ts` → `GET /api/workspace/git` |
| Chat 流与人工干预 UI | `components/ChatFeed.tsx` |
| 工作流 Chat 步骤 / Agent 类型解析 | `services/workflowAgentSteps.ts` |
| Agent / 工具品牌 Logo | `services/brandLogos.ts` · `components/BrandLogo.tsx` |
| 右侧面板（Overview/Files/Flow/Changes/Terminal） | `components/RightPanel.tsx` |
| Terminal 日志子面板 | `components/TerminalPanel.tsx` |
| 文件预览浮层 | `App.tsx`（`previewFile`） |
| 模型配置 UI（M4-09） | `components/ModelsManager.tsx` |
| 主题 Appearance（P2） | `components/ThemeManager.tsx` |
| 设置模态壳 | `components/SystemPreferencesModal.tsx` |
| i18n（P2） | `components/LanguageContext.tsx` |
| 工作流画布编辑 | `components/WorkflowOrchestration.tsx` |
| 工作流 JSON 面板（D9） | `components/WorkflowJsonPanel.tsx` |
| 画布 ↔ compiler 转换（D9） | `services/workflowFormat.ts` |
| 工作流 Sidecar API 客户端 | `services/workflowApi.ts` |
| Agent 角色配置 | `components/AgentManager.tsx` |
| 内置 Clutch Agent 定义与合并 | `services/builtinAgent.ts` |
| Agent Registry API | `services/agentApi.ts` |
| AI 工具连接状态 | `components/AiToolsManager.tsx` |
| Skills 注册 | `components/SkillsRegistry.tsx` |
| MCP 配置 | `components/McpServerHub.tsx` |
| MCP Registry API（P2-02） | `services/mcpApi.ts` |
| 顶栏 | `components/Header.tsx` |
| 全局样式 | `index.css` |
| 类型定义 | `types.ts` |
| **待废弃** mock 数据 | `mockData.ts` |
| Vite 配置与代理 | `vite.config.ts` |
| Tauri 壳与 Sidecar 拉起 | `src-tauri/` |

### 后端（`services/orchestrator`）

| 想改什么 | 去哪里 |
|---------|--------|
| FastAPI 入口、HTTP/WS 路由 | `src/main.py` |
| ClutchState 初始值 | `src/state.py` |
| 会话元数据持久化（M2-07） | `src/run_history.py` |
| 会话 messages 持久化（D11） | `src/run_state_store.py` |
| LangGraph 最小运行时 | `src/graph.py` |
| Workflow JSON Schema 校验 | `src/workflow_validator.py` |
| WorkflowCompiler（M1-02） | `src/compiler/` |
| Orchestrator 路由（M1-04） | `src/orchestrator/routing.py` |
| Engine Router（aiEngine / Connect 分流） | `src/engine_router.py` |
| ShellSession Hybrid Runtime（D25 Step 1） | `src/shell_session.py`、`src/shell_exec_runtime.py`、`src/hybrid_audit_log.py`（HRT-05 JSONL）、`src/hybrid_concurrency.py`（HRT-08 拒绝+提示）、`src/run_debug.py`（HRT-06 debug API）、`src/claude_hybrid_output_parser.py`（含 `OutputEvent`）、`src/runtime_config.py` |
| RuntimeStrategy / Provider 注册表 | `src/runtime_strategy.py`、`src/provider_registry.py`、`src/runtime_registry.py` |
| Context Continuity 快照 | `src/session_snapshot.py`；`GET/PUT /api/shell-snapshots/{run_id}` · `GET /api/shell-snapshots` |
| HumanInputKind 载荷 | `src/human_input.py` |
| agent_task 节点执行 | `src/agent_executor.py` |
| Agent 持久化与内置 Agent | `src/agent_storage.py` |
| 运行日志 WS 转发 | `src/run_log_forwarder.py` |
| 工作流状态投影 | `src/workflow_projection.py` |
| 工作流运行中取消 | `src/workflow_cancel.py` |
| Terminal 日志格式化与时间戳 | `src/terminal_logs.py` |
| MCP 工具风险判定 | `src/mcp_risk.py` |
| MCP ReAct 执行 | `src/mcp_react.py` |
| Codex 兼容 apply_patch（增删改移） | `src/apply_patch.py` |
| 内置虚拟工具服务器 clutch-tools | `src/builtin_tools.py` |
| 凭证来源（CC Switch / 环境变量） | `src/credentials/sources.py` |
| 工作区 Git 分支探测 | `src/workspace.py` → `get_git_info()` |
| LLM Provider Router（M1-08，D4） | `src/llm/router.py` |
| LLM HTTP 补全 | `src/llm/http_complete.py` |
| 模型配置序列化 | `src/models_config.py` |
| 用户工作流存储 API（M1-09，D5） | `src/workflow_storage.py` |
| Skills Registry 持久化（P2-01） | `src/skills_storage.py`、`src/skills_scanner.py` |
| MCP Registry 持久化（P2-02） | `src/mcp_storage.py` |
| 用户偏好 / Theme（P2-03） | `src/preferences_storage.py` |
| CLI Adapter（M3） | `src/adapters/` — `cli_adapter.py`、`claude_cli_adapter.py`、`agy_cli_adapter.py`、`ollama_adapter.py` |
| CLI PTY Session 调研（参考） | `docs/research/pty-session.md` |
| PTY Session Step 0 实验 | `experiments/pty_poc/` |
| Video Core（M5） | `src/video_core/` — `config.py`、`env.py`、`pipeline.py`、`renderer.py` |
| 依赖与 pytest 配置 | `pyproject.toml` |

### 共享与 Workflow

| 想改什么 | 去哪里 |
|---------|--------|
| 前后端共享 TS 类型 | `packages/shared-types/index.ts` |
| Workflow JSON Schema | `workflows/workflow.schema.json` |
| 内置模板（只读） | `workflows/*.json` |
| 用户工作流（读写，D5） | Tauri 应用数据目录 `workflows/` |
| 可选导出到项目 | `.clutch/workflows/`（导入/导出，非默认） |
| Agent / Evaluator 配置 UI | `components/AgentManager.tsx` |
