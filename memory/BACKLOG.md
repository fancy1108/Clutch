# BACKLOG（候选优化需求池）

> **未立项**的 Orchestrator / 主控 Agent 增强项。不是开发承诺，Agent 不得当作必做任务执行。  
> 调研全文（分派流程图、`dispatch` 字段）见 [`docs/research/orchestrator-optimization-pool.md`](../docs/research/orchestrator-optimization-pool.md) §7。  
> **升格路径：** 候选 → `DECISIONS.md` §开放问题（待拍板）→ Dxx 决策 → `specs/core/tasks.md` + `ROADMAP.md`。

---

## 开源 / DMG 分发（OSR-xx · 已立项）

> **权威 Task 表：** [`docs/OPEN_SOURCE_RELEASE.md`](../docs/OPEN_SOURCE_RELEASE.md) §7.2（编号、触发线、估时、依赖）  
> **验收勾选：** 同文件 §7.7（与下表同步维护）  
> **进度接力：** `memory/PROGRESS.md` · **功能验收镜像：** `memory/ROADMAP.md` §开源分发  
> **交付索引：** 每 Task commit 后写入 `memory/DELIVERABLES.md`（同 HRT / M4 纪律）  
> **状态图例：** ❌ 未通过 · ⚠️ 部分 / 草案待验收 · 🔄 持续 · ✅ 已验收

### T0 — 持续护栏

| ID | 任务 | 状态 | 证据 / 备注 |
|----|------|------|-------------|
| OSR-01 | `LICENSE`（MIT） | ✅ | 根目录 `LICENSE` |
| OSR-02 | 仓库卫生 | ✅ | `.gitignore`、`experiments/pty_poc/runs/` |
| OSR-03 | 文档↔实现一致 | ✅ | Key → `models.json`；**已知漂移：** `permission_mode` UI 未接到 CLI `skip-permissions`（OSR-09） |
| OSR-04 | semver + `CHANGELOG.md` | ✅ | **0.1.0** |
| OSR-05 | 新代码安全护栏 | 🔄 | Review 项，持续 |
| OSR-23 | `PROJECT_SCOPE.md` | ✅ | 草案 v0.1 |
| OSR-24 | `STABILITY.md` | ✅ | 草案 v0.1 |
| OSR-25 | `EXTENSIBILITY.md` | ✅ | 草案 v0.1 |

### T1 — 公开仓库前

| ID | 任务 | 状态 | 证据 / 备注 |
|----|------|------|-------------|
| **OSR-00** | **外部视角审计** | ❌ | 证据应写入 `runs/verification/`；**T1 前优先** |
| OSR-06 | `SECURITY.md` + `CONTRIBUTING.md` + `CODE_OF_CONDUCT.md` | ✅ | `SECURITY.md` · `CODE_OF_CONDUCT.md` · `CONTRIBUTING.md` 已链 |
| OSR-07 | Secret scanning CI（gitleaks） | ✅ | `.github/workflows/secret-scan.yml` · `.gitleaks.toml` |
| OSR-08 | Sidecar session token 鉴权 | ❌ | HTTP/WS 仍无 token |
| OSR-09 | CLI `--dangerously-skip-permissions` 门控 | ❌ | 依赖产品决策；见 `OPEN_SOURCE_RELEASE.md` §5.2.3 |
| OSR-10 | README + 源码构建说明 | ⚠️ | README 有兼容性 + `doctor.sh`；**缺** `docs/BUILD_FROM_SOURCE.md`、DMG 分叉、截图 |
| OSR-26 | `GOVERNANCE.md` | ✅ | 草案 v0.1 |
| OSR-27 | 兼容性矩阵 + `doctor.sh` | ✅ | `README.md` §兼容性 · `scripts/doctor.sh` |
| OSR-28 | Issue / PR 模板 | ✅ | `.github/ISSUE_TEMPLATE/` · `pull_request_template.md` |

**T1 开闸信号**（`OPEN_SOURCE_RELEASE.md` §7.5）：主路径稳定 · 近 2 周无大规模 Settings 重构 · 愿意处理外部 Issue — 见 `ROADMAP.md` §开源分发。

### T2 — 首次 DMG 分发前

| ID | 任务 | 状态 | 依赖 / 备注 |
|----|------|------|-------------|
| OSR-11 | Apple 签名 + 公证 | ❌ | 需 Developer 账号 |
| OSR-12 | Release CI 打 DMG | ❌ | 依赖 OSR-11 |
| OSR-13 | API Key → Keychain + 迁移 | ❌ | Models UI 稳定后 |
| OSR-14 | 首次启动向导 | ❌ | 依赖 OSR-09、OSR-13 |
| OSR-15 | `INSTALL.md` + `DATA_AND_PRIVACY.md` | ❌ | |
| OSR-16 | Debug API 收敛 + WebView CSP | ❌ | `csp: null` |
| OSR-17 | PyInstaller `console=False` | ❌ | `clutch.spec` 仍 `console=True` |

### T3 — 生态成熟期（按需）

| ID | 任务 | 状态 | 备注 |
|----|------|------|------|
| OSR-18 | OS 级沙箱 PoC | ❌ | 对齐 BACKLOG B-20 |
| OSR-19 | Windows MSI | ❌ | |
| OSR-20 | Tauri 自动更新 | ❌ | |
| OSR-21 | 工作流签名 / MCP 白名单 | ❌ | |
| OSR-22 | 外部安全审计 | ❌ | |
| OSR-29 | `PERFORMANCE.md` 基线 | ⚠️ | 草案 v0.1；无 benchmark 实测 |

---

## 已升格 → D25 HRT（勿重复立项）

| 原候选方向 | HRT ID | 决策 |
|------------|--------|------|
| Hybrid 操作审计 / 按 run 排查 | HRT-05 ~ HRT-07 | D28 |
| 多 session 并发 / 池满提示 | HRT-08 ~ HRT-10 | D27 · Q-HRT-1 |

权威 Task 表：[`specs/core/hybrid-runtime-plan.md`](../specs/core/hybrid-runtime-plan.md)

---

主控 **只调度、不干活**；**不让人选 Flow / Agent**。分派终态三种：

| 场景 | 条件 | 终态 | BACKLOG |
|------|------|------|---------|
| **A** | 能理解需求 + 匹配到 Flow | 专用 Flow | B-01 |
| **B** | 能理解需求 + 无 Flow + 匹配到单 Agent | 指定 Agent + 迷你流 | B-16 |
| **C** | 不能理解需求；或能理解但 Flow、单 Agent 均无匹配 | 内置通用 Agent | B-15 |

与 **D10**（不做 Single Agent **模式切换** UI）不冲突：B/C 为系统自动 fallback，非用户可选产品模式。

## 状态说明

| 状态 | 含义 |
|------|------|
| **候选** | 调研认可，尚未讨论是否做 |
| **待决策** | 已写入 `DECISIONS.md` §开放问题，等人类拍板 |
| **已升格** | 已拆入 `tasks.md`；本行保留作索引，勿删 ID |

## 候选池

### 主控分派（P0 · 优先）

| ID | 候选能力 | 优先级 | 参考 | 状态 | 升格条件 |
|----|----------|--------|------|------|----------|
| B-01 | 主控分派：理解需求 + 匹配 Flow + 精炼 `current_instruction` | P0 | Goose Recipe、LangGraph Supervisor | 候选 | 人类确认 + D14 决策；P2-07 |
| B-16 | 无 Flow 时匹配单个 Agent（Agent Manager 池 + `single-agent-run` 迷你流） | P0 | Agent Manager、Goose Recipe | 已否决 | 2026-06-27 彻底废除，已有明确的 Single/Multi Agent 模式分类 |
| B-15 | 内置通用 Agent + `general-fallback.json` 只读工作流 | P0 | D10 边界、内置模板模式 | 已否决 | 2026-06-27 彻底废除，已有明确的 Single/Multi Agent 模式分类 |
| B-04 | `agent_task` 按 tool 真执行（CLI / Cursor / MCP），非统一 `router.chat` | P0 | M3 CLI Adapter、ARCHITECTURE §6.4 | 候选（部分落地 `eaf2ea0`） | 人类确认 + 决策；P2-10 |

### 监督与成本（P1）

| ID | 候选能力 | 优先级 | 参考 | 状态 | 升格条件 |
|----|----------|--------|------|------|----------|
| B-02 | API 真实 token usage + cache hit/miss 进 `state_patch` | P1 | Reasonix、DeepSeek TUI、M2-13 升级 | 候选 | P2-08 立项 |
| B-03 | Messages compaction + 原文归档 `runs/archive/{run_id}.jsonl` | P1 | Reasonix SPEC §3.6、OpenCode auto-compact | 候选 | 人类确认 + 决策 |
| B-05 | 图内路由 LLM 读 `validation_errors` + 最近日志（非 start 分派） | P1 | LangGraph Supervisor、M1-04 升级 | 候选 | 人类确认 + 决策；P2-11 |
| B-06 | 双模型 Planner / Executor 独立 session（cache 友好） | P1 | Reasonix Coordinator §3.5 | 候选 | 人类确认 + D4 扩展 |

### 增强（P2–P3）

| ID | 候选能力 | 优先级 | 参考 | 状态 | 升格条件 |
|----|----------|--------|------|------|----------|
| B-07 | Auto 模型路由（flash vs pro + thinking 档位） | P2 | DeepSeek TUI `--model auto` | 候选 | 人类确认 + 决策 |
| B-08 | 子 Agent 并行 + git worktree 隔离（企业项目防改坏代码关键能力） | P2 | Stoneforge、DeepSeek TUI RLM | 候选 | 人类确认 + 决策 |
| B-09 | Skills 按任务语义动态注入（非全量塞 prompt） | P2 | DeepSeek TUI `load_skill` | 候选 | P2-01 ✅ 后立项 |
| B-12 | 工作区 `.clutch/AGENTS.md` 项目记忆 + Sidecar 扫描 | P2 | Reasonix `/init`、Goose Goosehints | 候选 | 人类确认 + 决策 |
| B-13 | 编辑后 LSP diagnostics 回灌 Builder 下一轮 | P2 | DeepSeek TUI、OpenCode LSP | 候选 | 人类确认 + 决策 |
| B-14 | Cache-safe 子 Agent fork（prefix 对齐 fan-out） | P2 | [agentcache](https://github.com/masteragentcoder/agentcache) | 候选 | B-08 立项后评估 |
| B-10 | 跨 run 记忆检索（BM25 history / terminal_logs） | P3 | Reasonix `history` / `memory` 工具 | 候选 | 人类确认 + 决策 |
| B-11 | Workspace checkpoint / Human Gate reject 回滚 | P3 | DeepSeek TUI side-git `/restore` | 候选 | 人类确认 + 决策 |

### Agent 执行与 Codex / Claude Code 对标（2026-06-25 调研）

> **已落地（勿重复立项）：** D21 `clutch-tools__apply_patch`（增/删/改/移 + Supervisor 审批 + `file_changed`）。  
> **调研来源：** [openai/codex](https://github.com/openai/codex) `codex-rs/apply-patch`、`core/tools`；Claude Code Tools / Permissions 文档。

#### 执行与引擎（P0）

| ID | 候选能力 | 优先级 | 参考 | 状态 | 升格条件 |
|----|----------|--------|------|------|----------|
| B-17 | **Codex CLI 引擎接入**：`engine_router` 路由 `codex-cli`（`tools_status` 已探测，未执行） | P0 | openai/codex CLI、`claude_cli_adapter` 模式 | **部分落地 2026-06-28** | plain chat + hybrid `codex exec --json`；flow 节点待验收 |
| B-18 | **受控 Shell 执行**：`exec_command` / `shell_command`（PTY、工作区内、Supervisor 审批） | P0 | Codex `unified_exec`、`shell_spec` | 候选 | B-21 或沙箱方案拍板后立项 |
| B-19 | **长驻 Shell 会话**：`write_stdin` + session id 续跑（dev server / 交互命令） | P1 | Codex `exec_command` + `write_stdin` | 候选 | B-18 立项后评估 |

#### 安全与监督（P1）

| ID | 候选能力 | 优先级 | 参考 | 状态 | 升格条件 |
|----|----------|--------|------|------|----------|
| B-20 | **OS 级沙箱**（需要深入调研的待定需求）：工作区外路径 / 网络边界（Linux bubblewrap、Windows sandbox） | P1 | Codex `linux-sandbox`、`windows-sandbox-rs` | 候选 | 人类确认 + 安全评审与详细技术调研 |
| B-21 | **Exec policy**：命令模式 allow/deny/ask（`Bash(rm:*)`、`Edit(/src/**)` 等） | P1 | Codex `docs/execpolicy.md` | 候选 | 人类确认 + D22 决策 |
| B-22 | **路径级工具权限**：按 glob 限制 read/write/edit/delete 目标路径 | P1 | Claude Code permissions、Codex FileSystemPermissions | 候选 | B-21 立项后拆分 |
| B-23 | **apply_patch UI diff**：删除/更新前内容快照 + Terminal/Chat 红绿 diff 展示 | P1 | Codex `FileChange::Delete`、TUI `diff_render` | 候选 | D21 验收反馈后立项 |
| B-24 | **PreToolUse hooks**：确定性脚本拦截危险命令（rm、python `os.remove` 等绕过） | P2 | Claude Code hooks、Codex 社区安全实践 | 候选 | B-21 立项后评估 |

#### Agent 工具生态（P2）

| ID | 候选能力 | 优先级 | 参考 | 状态 | 升格条件 |
|----|----------|--------|------|------|----------|
| B-25 | **计划工具**：`update_plan` / plain chat 任务清单与进度投影 | P2 | Codex `plan` handler | 候选 | 人类确认 + 决策 |
| B-26 | **Multi-agents**：`spawn_agent` / `wait_agent` / `send_message` 子 Agent 编排 | P2 | Codex `multi_agents_v2`、LangGraph 子图 | 候选 | B-08 或主控分派拍板后评估 |
| B-27 | **tool_search**：MCP 工具延迟发现与按需加载（大工具集场景） | P2 | Codex `tool_search` | 候选 | MCP 工具数 >N 时立项 |
| B-28 | **MCP resources**：`list_mcp_resources` / `read_mcp_resource` | P2 | Codex `mcp_resource` handlers | 候选 | 人类确认 + 决策 |
| B-29 | **view_image**：工作区内图片读入多模态上下文 | P2 | Codex `view_image` | 候选 | 模型多模态能力就绪后立项 |
| B-30 | **内置 web_search**：域名 allowlist + Supervisor 门控 | P2 | Codex `WebSearch` / `WebFetch` | 候选 | 人类确认 + 决策 |
| B-31 | **request_permissions**：运行时申请额外目录/命令权限（会话级扩权） | P2 | Codex `request_permissions` | 候选 | B-21/B-22 立项后评估 |
| B-32 | **apply_patch 流式事件**：patch 生成过程中增量 diff 推送 WS | P3 | Codex `PatchApplyUpdatedEvent` | 候选 | B-23 立项后评估 |

#### 已有部分能力 · 待补齐（索引）

| 能力 | Clutch 现状 | 对标 BACKLOG |
|------|-------------|--------------|
| 文件真删除 | ✅ D21 `*** Delete File` | — |
| 高风险工具审批 | ✅ Supervisor + `mcp_risk` | B-21/B-24 细粒度补强 |
| 用户确认输入 | ⚠️ 仅审批卡片 | B-31 |
| CLI Agent 路由 | ✅ Claude CLI；✅ Codex CLI（plain chat hybrid）；Agy/Ollama 动态下拉 | B-17 部分落地 |
| Skills / MCP Hub | ✅ 已落地 | B-09 动态注入、B-27/B-28 扩展 |

## 与已立项任务的关系

- **P2-01…P2-06**（`tasks.md` §P2）为已承诺交付，**不**在本池重复登记。
- **P2-07～P2-13** 为分派相关预留 ID，升格时再写入 `tasks.md`。
- **B-04 部分落地（2026-06-25，`eaf2ea0` + `6cc6c6b`）**：`engine_router` 已按 Agent `aiEngine` 与 Tools Connect 分流 Claude CLI / Cursor / 全局 LLM；`execute_agent_task` 与 plain chat 已接入。MCP ReAct 路径在 `agent_executor` 内独立实现。主控自动分派（B-01/B-15/B-16）仍属候选。升格待人类确认。
- **D21 部分落地（2026-06-25，`5e34f7c`）**：`clutch-tools__apply_patch` 补齐 Configured LLM 路径增删改移；Shell、沙箱、Codex CLI、multi-agents 等待办见上表 B-17～B-32。

## 维护纪律

- 新增候选：补一行，状态默认 **候选**。
- 进入讨论：改 **待决策**，并在 `DECISIONS.md` §开放问题 增一条（禁止在其他文档另开开放问题列表）。
- 确定开发：改 **已升格**，链到 `tasks.md` 任务 ID 与 `DECISIONS.md` Dxx。
- 明确不做：删行或标 `已否决`（附一行否决理由与日期）。
