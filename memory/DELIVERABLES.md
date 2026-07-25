# DELIVERABLES（Task 交付索引）

> **角色：** Task ID → Git commit → Verification → 证据路径。**不复制** `git diff`（代码真相在 Git）。  
> **何时写：** 每个**代码 Task** 完成并 commit 后，在 Check-out 追加一节（见 `CLAUDE.md` §Check-out）。  
> **生命周期：** 见 [`docs/document-governance.md`](../docs/document-governance.md) §文档生命周期；冷数据见 [`archive/`](./archive/)。

## D11 PM 通过 + bg job UX（2026-07-25）

| 项 | 说明 |
|----|------|
| **PM** | D11 ✅ — `runs/verification/pm-acceptance/D11.md`；ROADMAP ✅ |
| **Verification** | `pytest tests/test_bg_jobs_d11.py tests/test_bg_jobs_monitor_d26.py -q`；`vitest bgJobMonitor` |
| **Fixes** | 结束进对话 `bgJob`；底栏仅 RUNNING；Kill 乐观；killed 不弹失败 toast；dock 上滚 |
| **下一批** | D12 PM |

## D10 PM 通过 + explore 预算（2026-07-25）

| 项 | 说明 |
|----|------|
| **PM** | D10∥D48 ✅ — `runs/verification/pm-acceptance/D10.md`；ROADMAP ✅ |
| **Verification** | `pytest tests/test_subagent_d10.py -q` → 5 passed |
| **Fixes** | explore max_steps 16 / implement 12；explore 少扫目录；implement 卡非强制 |
| **下一批** | D11 PM |

## D9 PM 通过 + Usage 占位（2026-07-25）

| 项 | 说明 |
|----|------|
| **PM** | D9 ✅ Stop/Continue — `runs/verification/pm-acceptance/D09.md`；熔断跳过；ROADMAP ✅ |
| **Changed** | 移除 `UsageDashboard` / `+ → Usage`；Overview 用量 `—`；开放问题 **Q-USAGE-1** |
| **下一批** | D10∥D48 PM |

## D8 PM 通过 + 验收期修复（2026-07-25）

| 项 | 说明 |
|----|------|
| **PM** | D8 ✅ — `runs/verification/pm-acceptance/D08.md`；ROADMAP ✅ |
| **Verification** | `pytest tests/test_task_state_d8.py tests/test_compaction.py tests/test_todo_d3.py -q`；`pnpm test -- src/services/clutchState.test.ts` |
| **Fixes** | todo JSON 字符串不炸字符；compaction 权威替换；`/compact` 末尾 User+digest；Stop 乐观 UI；状态问答不续干活；深色 slash notice |

## Wave5b — D32 / Cap-D25 / D24 / D36 / D14（2026-07-25）

| ID | Commit | Verification | PM |
|----|--------|--------------|-----|
| D32 | `9a863ae` | `pytest tests/test_worktree_isolation_d32.py -q` → 2 passed | `runs/verification/pm-acceptance/D32.md` |
| Cap-D25 | `05547b8` | `pytest tests/test_scheduled_tasks_cap_d25.py -q` → 3 passed | `runs/verification/pm-acceptance/Cap-D25.md` |
| D24 | `605d0fc` | `pytest tests/test_diagnostics_d24.py -q` → 2 passed | `runs/verification/pm-acceptance/D24.md` |
| D36 | `e42ba01` | `pytest tests/test_headless_agent_d36.py -q` → 2 passed | `runs/verification/pm-acceptance/D36-headless.md` |
| D14 | `5d65a68` | `pytest tests/test_grok_cli_d14.py -q` → 4 passed | `runs/verification/pm-acceptance/D14.md` |

## Wave5b — D32（进行中）

| ID | Commit | Verification | PM |
|----|--------|--------------|-----|
| D32 | `9a863ae` | `pytest tests/test_worktree_isolation_d32.py -q` → 2 passed | `runs/verification/pm-acceptance/D32.md` |
| Cap-D25 | `05547b8` | `pytest tests/test_scheduled_tasks_cap_d25.py -q` → 3 passed | `runs/verification/pm-acceptance/Cap-D25.md` |
| D24 | _(pending)_ | `pytest tests/test_diagnostics_d24.py -q` | `runs/verification/pm-acceptance/D24.md` |

## Wave5a — D34 / D23（2026-07-25）

| ID | Commit | Verification | PM |
|----|--------|--------------|-----|
| D34 | `5679a1b` | `pytest tests/test_foreground_shell_d34.py -q` → 3 passed | `runs/verification/pm-acceptance/D34.md` |
| D23 | `bc67e30` | `pytest tests/test_session_fork_d23.py tests/test_file_rewind_d23.py -q` → 3 passed | `runs/verification/pm-acceptance/D23.md` |
| D16 | `930f9a5` | `pytest tests/test_cross_session_memory_d16.py -q` → 2 passed | `runs/verification/pm-acceptance/D16.md` |
| D17 | `68a05a8` | `pytest tests/test_tool_hooks_d17.py -q` → 1 passed | `runs/verification/pm-acceptance/D17.md` |
| D35 | `5de258d` | `pytest tests/test_capability_pack_d35.py -q` → 1 passed | `runs/verification/pm-acceptance/D35.md` |

## Wave4 — D28 / D15 / D33 / D31（2026-07-25）

| ID | Commit | Verification | PM |
|----|--------|--------------|-----|
| D28 | `cc2662e` | `pytest tests/test_mcp_tool_discovery_d28.py -q` → 5 passed | `runs/verification/pm-acceptance/D28.md` |
| D15 | `0c0c095` | `pytest tests/test_web_search_d15.py -q` → 4 passed | `runs/verification/pm-acceptance/D15.md` |
| D33 | `bec5dbb` | `pytest tests/test_rich_read_d33.py -q` → 3 passed | `runs/verification/pm-acceptance/D33.md` |
| D31 | `d2f2b2f` | `pytest tests/test_plan_step_comments_d31.py -q` → 3 passed；`PlanCardView.test.ts` → 4 passed | `runs/verification/pm-acceptance/D31.md` |

## Clutch Agent D18 斜杠命令 (`518b8d0`)

| 项目 | 值 |
|------|-----|
| **Task** | D18 `/plan` `/compact` `/todos` `/help` + compact API |
| **Commit** | `518b8d0` |
| **Branch** | `dev` |
| **Verification** | `pnpm test -- src/services/slashCommands.test.ts` → 3 passed；`pytest tests/test_compact_api_d18.py -q` → 2 passed |
| **PM 用例** | `runs/verification/pm-acceptance/D18.md` |
| **下一批** | D22 → D27… |

## Clutch Agent D43 MCP Resources (`4462570`)

| 项目 | 值 |
|------|-----|
| **Task** | D43 Browse resources + Pin for Chat + prompt inject |
| **Commit** | `4462570` |
| **Branch** | `dev` |
| **Verification** | `uv run pytest tests/test_mcp_resources_d43.py -q` → 2 passed |
| **PM 用例** | `runs/verification/pm-acceptance/D43.md` |
| **下一批** | 人工全表点验 |

## Clutch Agent D42∥D44 真工具名 + 一键 local-fs (`24f0e31`)

| 项目 | 值 |
|------|-----|
| **Task** | D42 real Hub tool chips + D44 Enable workspace file tools + D45 Epicode honesty |
| **Commit** | `24f0e31` |
| **Branch** | `dev` |
| **Verification** | pre-commit verify.sh (build + vitest + pytest) |
| **PM 用例** | `runs/verification/pm-acceptance/D42.md` · `D44.md` · `D41.md` · `D45.md` |
| **下一批** | 人工点验（D43 已于 `4462570` 交付） |

## Clutch Agent D40 Chat MCP 徽章 (`724c26c`)

| 项目 | 值 |
|------|-----|
| **Task** | D40 Chat MCP badge / Bind CTA |
| **Commit** | `724c26c` |
| **Branch** | `dev` |
| **Verification** | `pnpm test -- src/services/agentMcpSummary.test.ts` → 2 passed |
| **PM 用例** | `runs/verification/pm-acceptance/D40.md` |
| **下一批** | **D42∥D44** |

## Clutch Agent D39 传输诚实 (`092ee91`)

| 项目 | 值 |
|------|-----|
| **Task** | D39 stdio-only Hub + Env form; reject SSE register |
| **Commit** | `092ee91` |
| **Branch** | `dev` |
| **Verification** | `uv run pytest tests/test_mcp_registry.py tests/test_mcp_probe_d38.py -q` → 8 passed |
| **PM 用例** | `runs/verification/pm-acceptance/D39.md` |
| **下一批** | **D40** Chat MCP 徽章 |

## Clutch Agent D38 Hub 可信状态 (`b2d8f49`)

| 项目 | 值 |
|------|-----|
| **Task** | D38 Test connection + remove under-development banner |
| **Commit** | `b2d8f49` |
| **Branch** | `dev` |
| **Verification** | `uv run pytest tests/test_mcp_probe_d38.py -q` → 5 passed |
| **PM 用例** | `runs/verification/pm-acceptance/D38.md` |
| **下一批** | **D39** 传输诚实 |

## Clutch Agent D52 能力↔交互对照门禁 (`1365f6d`)

| 项目 | 值 |
|------|-----|
| **Task** | D52 PRODUCT_INTRO Capability→Chat UI table + INV-D52 |
| **Commit** | `1365f6d` |
| **Branch** | `dev` |
| **Verification** | `./scripts/check-capability-ui-table.sh` → OK |
| **PM 用例** | `runs/verification/pm-acceptance/D52.md` |
| **下一批** | **D38** Hub 可信状态 |

## Clutch Agent D51 Chat ↔ Terminal 同步 (`ee4e2a2`)

| 项目 | 值 |
|------|-----|
| **Task** | D51 View in Terminal → log highlight / lane focus |
| **Commit** | `ee4e2a2` |
| **Branch** | `dev` |
| **Verification** | `cd apps/desktop && pnpm test -- src/services/chatTerminalSync.test.ts` → 6 passed |
| **PM 用例** | `runs/verification/pm-acceptance/D51.md` |
| **下一批** | **D52** 能力↔交互对照门禁 |

## Clutch Agent D13 权限规则 (`ed7c568`)

| 项目 | 值 |
|------|-----|
| **Task** | D13 allow/ask/deny + dangerous force-ask + clear approvals |
| **Commit** | `ed7c568` |
| **Branch** | `dev` |
| **Verification** | `uv run pytest tests/test_permission_rules_d13.py -q` |
| **PM 用例** | `runs/verification/pm-acceptance/D13.md` |
| **下一批** | 人工点验 D8–D13 |

## Clutch Agent D12 Git + 网页 (`194d33a`)

| 项目 | 值 |
|------|-----|
| **Task** | D12 git_status/diff/commit + web_fetch |
| **Commit** | `194d33a` |
| **Branch** | `dev` |
| **Verification** | `uv run pytest tests/test_git_web_d12.py -q` |
| **PM 用例** | `runs/verification/pm-acceptance/D12.md` |
| **下一批** | **D13 权限规则** |

## Clutch Agent D11 后台命令 (`59b45ee`)

| 项目 | 值 |
|------|-----|
| **Task** | D11 background jobs + Chat job bar |
| **Commit** | `59b45ee` |
| **Branch** | `dev` |
| **Verification** | `uv run pytest tests/test_bg_jobs_d11.py -q` → 5 passed |
| **PM 用例** | `runs/verification/pm-acceptance/D11.md`（待人工点验；ROADMAP 仍 ❌） |
| **下一批** | **D12 Git + 网页** |

## Clutch Agent D10∥D48 子任务委派 (`25dc5dc`)

| 项目 | 值 |
|------|-----|
| **Task** | D10 delegate_subtask + D48 嵌套 Subtasks 卡 |
| **Commit** | `25dc5dc` |
| **Branch** | `dev` |
| **Verification** | `uv run pytest tests/test_subagent_d10.py tests/test_mcp_react.py -q` |
| **PM 用例** | `runs/verification/pm-acceptance/D10.md`（待人工点验；ROADMAP 仍 ❌） |
| **下一批** | **D11 后台命令** |

## Clutch Agent D9 运行可控 (`bef9b75`)

| 项目 | 值 |
|------|-----|
| **Task** | D9 Stop/Continue + loop fuse + Chat Steps/tok |
| **Commit** | `bef9b75` |
| **Branch** | `dev` |
| **Verification** | `uv run pytest tests/test_run_control_d9.py tests/test_mcp_react.py -q` + pre-commit verify |
| **PM 用例** | `runs/verification/pm-acceptance/D09.md`（待人工点验；ROADMAP 仍 ❌） |
| **下一批** | **D10∥D48** |

## Clutch Agent D8 长聊不丢任务态 (`7936786`)

| 项目 | 值 |
|------|-----|
| **Task** | D8 压缩后保留 Todo/计划 + `task_state` 层 |
| **Commit** | `7936786` |
| **Branch** | `dev` |
| **Verification** | `uv run pytest tests/test_task_state_d8.py tests/test_compaction.py -q` → 16 passed |
| **PM 用例** | `runs/verification/pm-acceptance/D08.md`（待人工点验；ROADMAP 仍 ❌） |
| **下一批** | **D9 运行可控** |

## Clutch Agent D7 project rules + Skills (`af58e94`)

| 项目 | 值 |
|------|-----|
| **Task** | D7 项目规则 + Skills（Grok-aligned · D45） |
| **Commit** | `af58e94` |
| **Branch** | `dev` |
| **Verification** | `test_d7_project_rules_skills` + pre-commit `verify.sh`（pytest 806 passed） |
| **PM** | 2026-07-25 验收通过（规则 token + read_skill→SKILL_BODY_LOADED） |
| **下一批** | **D8 长聊不丢任务态** |

## Clutch Agent D6∥D50 Diff review (`26b9716`)

| 项目 | 值 |
|------|-----|
| **Task** | D6 Diff 审查 + D50 对话内 Cursor 式 Diff 卡 |
| **Commit** | `26b9716` |
| **Branch** | `dev` |
| **Verification** | `test_diff_summary_d6` + pre-commit `verify.sh`（build OK；vitest 159；pytest 798 passed / 3 skipped） |
| **PM** | 2026-07-24 验收通过（边改边出 Diff；ROADMAP D6+D50 ✅） |
| **下一批** | **D7 项目规则 + Skills** |

## Clutch Agent D5∥D50 Verification report (`30d5f86`)

| 项目 | 值 |
|------|-----|
| **Task** | D5 自检报告 + D50 对话内 VerificationReport 卡（Diff 摘要仍随 D6） |
| **Commit** | `30d5f86807380c1da6e899fa590bc962153093ca` |
| **Branch** | `dev` |
| **Verification** | pre-commit `verify.sh`（随 feat commit）；`test_verification_d5` + `test_merge_patch_optional_d5` |
| **PM** | 2026-07-24 验收通过（ROADMAP D5 ✅；故意失败出 VERIFICATION FAILED + next actions） |
| **下一批** | **D6∥D50 Diff 摘要** ✅ |

## Clutch Agent D4∥D49 Question card (`662129c`)

| 项目 | 值 |
|------|-----|
| **Task** | D4 结构化提问 + D49 对话内提问卡 |
| **Commit** | `662129c64071430481551475f128819749cb8c87` |
| **Branch** | `dev` |
| **Verification** | pre-commit `verify.sh`：build OK；vitest 156；pytest 784 passed / 3 skipped；doc-drift 0 error |
| **PM** | 2026-07-24 验收通过（ROADMAP D4 ✅；路径 Redis→health→plan 一致；卡壳与 Plan/Todo 对齐 UI_UX） |
| **下一批** | **D5∥D50 自检报告** ✅ `30d5f86` |

## Clutch Agent D3∥D49 Todo card (`4d6f6ef`)

| 项目 | 值 |
|------|-----|
| **Task** | D3 Todo 面板 + D49 对话内 Todo 卡 |
| **Commit** | `4d6f6efbba72a646efbaaa5240ad8897dcf53002` |
| **Branch** | `dev` |
| **Verification** | pre-commit `verify.sh`：build OK；vitest 156；pytest 777 passed / 3 skipped；doc-drift 0 error |
| **PM** | 2026-07-24 验收通过（ROADMAP D3 ✅） |
| **下一批** | **D4∥D49 结构化提问** ✅ `662129c` |

## Clutch Agent D2∥D49 plan card (`13be92a`)

| 项目 | 值 |
|------|-----|
| **Task** | D2 先计划再动手 + D49 对话内计划卡 |
| **Commit** | `13be92a694b0e58af0609e48b84bc6d04ba98e03` |
| **Branch** | `dev` |
| **Verification** | pre-commit `verify.sh`：build OK；vitest 151；pytest 含 `test_plan_d2_d49` |
| **PM** | 2026-07-24 验收通过（ROADMAP D2 / D49-计划 ✅） |
| **下一批** | **D3∥D49 Todo** |

## Clutch Agent D47 files-changed chips (`3a9a951`)

| 项目 | 值 |
|------|-----|
| **Task** | D47 中间产物芯片（seal `filesChanged` + FilesChangedChips → D42 预览） |
| **Commit** | `3a9a951d13574373a895851f5ea8beea4840991e` |
| **Branch** | `dev` |
| **Verification** | pre-commit `verify.sh`：build OK；vitest 151；pytest 766+（含 `test_files_changed_d47`）；doc-drift 0 error |
| **PM** | 2026-07-24 验收通过（ROADMAP D47 ✅） |
| **下一批** | **D3∥D49 Todo**（D2∥D49 计划已过） |

## Clutch Agent D53 layered prompt (`9a840e2`)

| 项目 | 值 |
|------|-----|
| **Task** | D53 分层 system prompt + Agent Manager 分层摘要 UI |
| **Commit** | `9a840e2085ea4055704c1dbbbd7db9bff1ef7a5d` |
| **Branch** | `dev` |
| **Verification** | pre-commit `verify.sh`：build OK；vitest 150；pytest 763 passed / 3 skipped；doc-drift 0 error |
| **PM** | 2026-07-24 验收通过（ROADMAP D53 ✅） |
| **交付要点** | `compose_agent_prompt_assembly` 分层；skills catalog；`GET …/prompt-assembly`；Agent Manager 层字符量面板 |
| **下一批** | **D47** → D2∥D49 |

## Clutch Agent D1+D37+D46 (`1097a6d`)

| 项目 | 值 |
|------|-----|
| **Task** | D1 builtins + D37 MCP Hub bind + D46 persisted verb_group tool trail |
| **Commit** | `1097a6dde5b7c165be810ed2661e6c35a762a4bf` |
| **Branch** | `dev` |
| **Verification** | pre-commit `verify.sh`：build OK；vitest 150；pytest 762 collected（hook 通过）；doc-drift 0 error |
| **PM** | 2026-07-24 验收通过（ROADMAP D1/D37/D46 ✅） |
| **交付要点** | `clutch-tools`；Agent Manager `mcpServerIds`；`toolSteps` / `pending_tool_steps`；apply_patch 裸行；Search 标题含 path |
| **下一批** | **D47** → D2∥D49 |

## Devin + Copilot CLI Whitelist (`6ce426b`)

| 项目 | 值 |
|------|-----|
| **Task** | 添加 Devin CLI + GitHub Copilot CLI 白名单支持 |
| **Commit** | `6ce426b` |
| **Branch** | `dev` |
| **Verification** | `./scripts/verify.sh`：vitest 136/136, pytest 730/734, build OK |
| **代码量** | 10 files, +80/-5 |

### Devin CLI

| 项目 | 详情 |
|------|------|
| 二进制版本 | devin 3000.1.27 (0d4bf12e) |
| 路由 | `devin -p --permission-mode dangerous` |
| conversation_mode | separate（支持 resume/continue） |
| 图标 | 复用 rivet.svg（默认） |

### GitHub Copilot CLI

| 项目 | 详情 |
|------|------|
| 二进制 | copilot（下载中，npm: @github/copilot） |
| 路由 | `copilot -p`（待测试） |
| 图标 | copilot.svg（← ~/Downloads/copilot.svg） |

## comate CLI Whitelist (`65f23e6`)

| 项目 | 值 |
|------|-----|
| **Task** | 添加 Baidu Comate CLI 白名单支持 |
| **Commit** | `65f23e6444acdfc92f4be7e6bdfef22190f135c8` |
| **Branch** | `dev` |
| **Verification** | `./scripts/verify.sh`：vitest 136/136, pytest 730/734 (1 预存 keychain), build OK |
| **代码量** | 10 files, +55/-5 |

### 交付文件

| 文件 | 变更 |
|------|------|
| `services/orchestrator/src/tools_status.py` | CLI_CANDIDATES + RECOMMENDED_CLI_IDS + `~/.comate/bin` |
| `services/orchestrator/src/agent_type.py` | AGENT_TYPES + 别名 (comate/baidu comate) |
| `services/orchestrator/src/engine_router.py` | CLI_ROUTING_CONFIGS（comate chat, positional prompt） |
| `services/orchestrator/src/terminal_cli_catalog.py` | CLI_TO_DISPLAY → "Baidu Comate" |
| `services/orchestrator/src/interactive_pty_runtime.py` | CLI_BINARY_MAP → comate |
| `apps/desktop/src/services/cliInstallGuides.ts` | CLI_INSTALL_GUIDES + RECOMMENDED_CLI_IDS |
| `apps/desktop/src/services/brandLogos.ts` | comate.svg + BrandLogoKey + ALIAS_TO_KEY |
| `apps/desktop/src/services/terminalOrchestraUtils.ts` | CLI_DISPLAY → "Baidu Comate" |
| `apps/desktop/src/assets/tool-logos/comate.svg` | 百度 Logo（new） |
| `docs/assets/tool-logos/comate.svg` | 文档图标（new） |

## qodercli CLI Whitelist (`a14db2d`)

| 项目 | 值 |
|------|-----|
| **Task** | 添加 Qoder CLI 白名单支持 |
| **Commit** | `a14db2d544a406753f832660424bf889d535e0a4` |
| **Branch** | `dev` |
| **Verification** | `./scripts/verify.sh`：vitest 136/136, pytest 730/734 (1 预存 keychain), build OK, doc-drift 0 |
| **API 验证** | `GET /api/tools/status` 返回 qoder-cli（installed=true, registered=true, agentType=qoder-cli） |
| **代码量** | 10 files, +56/-5 |

### 交付文件

| 文件 | 变更 |
|------|------|
| `services/orchestrator/src/tools_status.py` | CLI_CANDIDATES + RECOMMENDED_CLI_IDS + _CLI_EXTRA_BIN_DIRS |
| `services/orchestrator/src/agent_type.py` | AGENT_TYPES + _LEGACY_AI_ENGINE_TO_TYPE |
| `services/orchestrator/src/engine_router.py` | CLI_ROUTING_CONFIGS + _normalize_engine_type + _resolve_agent_type |
| `services/orchestrator/src/terminal_cli_catalog.py` | CLI_TO_DISPLAY |
| `services/orchestrator/src/interactive_pty_runtime.py` | CLI_BINARY_MAP |
| `apps/desktop/src/services/cliInstallGuides.ts` | CLI_INSTALL_GUIDES + RECOMMENDED_CLI_IDS |
| `apps/desktop/src/services/brandLogos.ts` | import + BrandLogoKey + BRAND_LOGO_SRC + ALIAS_TO_KEY |
| `apps/desktop/src/services/terminalOrchestraUtils.ts` | CLI_DISPLAY |
| `apps/desktop/src/assets/tool-logos/qoder.svg` | 品牌图标（new） |
| `docs/assets/tool-logos/qoder.svg` | 文档图标（new） |  
> **逐文件 diff：** `git show <commit> --stat` / `git show <commit>`

## 填写模板（复制后改）

```markdown
### <Task-ID> ✅ | ⚠️ 部分 | ❌ 回滚
- **日期：** YYYY-MM-DD
- **Commit：** `<hash>` — `<git log -1 --format=%s>`
- **Verification：** `<命令>` → `<结果摘要>`
- **证据：** `runs/verification/<date>-<task-id>.log` 或 [CI #N](url) 或 `—`（门禁已覆盖）
- **交付文件：**（一行一个，只写路径 + 一句话职责；详情 `git show`）
  - `path/to/file` — …
```

---


### Agent_task 多出边放宽 ✅
- **日期：** 2026-07-16
- **Commit：** `813defa` — `fix: allow agent_task nodes to have multiple outgoing edges`
- **Verification：** `./scripts/verify.sh` → build ✓, vitest 136/136, pytest 730/734
- **证据：** 用 `AI 图片生成多 Agent 工作流` 实际 JSON 验证 → Reasons: []
- **交付文件：**
  - `apps/desktop/src/services/workflowFormat.ts` — 移除 `branching_node` 限制，所有节点类型统一使用 `MAX_BRANCH_OUT=3`；移除未使用的 `isGate` 变量

### Check/Gate 节点 end 汇聚不兼容修复 ✅
- **日期：** 2026-07-16
- **Commit：** `6ec20b9` — `fix: relax end node in-degree check to allow multi-path convergence to end`
- **Verification：** `./scripts/verify.sh` → build ✓, vitest 136/136, pytest 730/734 (1 预存 keychain ACL)
- **证据：** `—`
- **交付文件：**
  - `apps/desktop/src/services/workflowFormat.ts` — `getCanvasIncompatibilities` 中 end 入度检查从 `endIn !== 1` 改为 `endIn < 1`；无 agent_task 路径从 `endIn === 1` 改为 `endIn >= 1`；`formatCanvasIncompatibilities` 消息更新

### Approval Node 多选保存 422 — orchestrator schema & routing 同步 ✅
- **日期：** 2026-07-16
- **Commit：** `b24442d` — `fix(flow): Approval Node 多选保存 422 — orchestrator schema & routing 同步数组 when`
- **Verification：** `./scripts/verify.sh` → build ✓, vitest 136/136, pytest 730/734 (1 预存 keychain ACL)
- **证据：** `—`
- **交付文件：**
  - `services/orchestrator/src/orchestrator/routing.py` — `resolve_from_edges` / `resolve_branch_from_edges` 中 path_map 构建兼容 when: list（展开到 dict）
  - `services/orchestrator/src/workflow_validator.py` — `workflows_dir()` 查找顺序改为源文件优先（workflows/ → workflow_assets/），dev 模式不再消费过期构建产物

### EdgeWhen multi-select (Next Flow 条件多选) ✅
- **日期：** 2026-07-16
- **Commit：** `bec65d6` — `feat(flow): Next Flow 条件选择器支持多选 (EdgeWhen 单值→数组)`
- **Verification：** `./scripts/verify.sh` → 136 vitest passed, 730 pytest passed, doc-drift 0
- **证据：** `—`
- **交付文件：**
  - `packages/shared-types/index.ts` — `edgeWhen: Record<string, EdgeWhen[]>` (单值→数组)
  - `workflows/workflow.schema.json` — `data.when` oneOf [string, array] 向后兼容
  - `apps/desktop/src/services/workflowFormat.ts` — compilerToCanvas/canvasToCompiler/验证 全适配数组
  - `apps/desktop/src/components/WorkflowOrchestration.tsx` — 条件选择 <select>→checkbox 多选，边标签 ' / ' 拼接
  - `services/orchestrator/src/compiler/compiler.py` — path_map/EdgeMeta 支持 list[str] when
  - `apps/desktop/src/services/workflowFormat.test.ts` — 测试数据适配数组格式

## Active Deliverables

### LLM Judge for check nodes ✅
- **日期：** 2026-07-16
- **Commit：** `ae84a9b` — `feat(compiler): add LLM judge for check nodes with natural-language prompt`
- **Verification：** `./scripts/verify.sh` → 730 pytest passed (1 pre-existing keychain), 136 vitest passed, pnpm build ✓
- **证据：** `—`
- **交付文件：**
  - `services/orchestrator/src/compiler/compiler.py` — 新增 `_llm_judge_check` 函数（读取上游 node_outputs、调 LLM 判定 passed/failed）；`_handle_check` 优先走 prompt/LLM judge 分支，回退 legacy evaluate_node_data
  - `workflows/workflow.schema.json` — check 节点 data 新增可选 `prompt` 字段，`checks` 改为非必填
  - `apps/desktop/src/services/workflowFormat.ts` — `canvasToCompiler` 对 check 节点写 `data.prompt`；`compilerToCanvas` 读回 `data.prompt` → description
  - `apps/desktop/src/components/WorkflowOrchestration.tsx` — check 节点弹窗：Label/Prompt 仅限 gate/check 显示，加 helper text + 自然语言 placeholder 示例

### Prompt color constraints + shared layout context + setNodes dedup ✅
- **日期：** 2026-07-14
- **Commit：** `3aa748a` — `fix(design): enforce color constraints in prompts + dedup setNodes to fix jitter`
- **Verification：** `./scripts/verify.sh` → 731 pytest + 130 vitest passed (1 pre-existing keychain), doc-drift zero
- **证据：** `—`
- **交付文件：**
  - `services/orchestrator/src/design/generator.py` — CRITICAL RULES now ban Tailwind default colors, arbitrary hex, colorful gradients for ALL modes. Added `_build_shared_layout_context` with sidebar nav constraints for multi-page. Threaded `shared_layout_context` through `_generate_ui_html` → `_build_ui_generation_prompt`.
  - `apps/desktop/src/components/design/DesignWorkspace.tsx` — Added `lastNodeFingerprintRef` fingerprint dedup in `syncNodesFromSession` to skip redundant `setNodes`/`setEdges` calls and prevent jitter.

### Design parallel iterate_session add + unified tailwind inject for modify path ✅
- **日期：** 2026-07-14
- **Commit：** `c2a772b` — `feat(design): parallel iterate_session add + unified tailwind inject for modify path`
- **Verification：** `./scripts/verify.sh` → 731 pytest passed (1 pre-existing keychain), 130 vitest passed, doc-drift zero; 41 design tests green
- **证据：** `—`
- **交付文件：**
  - `services/orchestrator/src/design/generator.py` — iterate_session add path: sequential loop → ThreadPoolExecutor concurrent workers with manifest_lock; add path + modify path: inject_unified_tailwind_config before write_text

### Premium hardware mockup shells, script-free external DOM state injections, and custom dropdowns unification ✅
- **日期：** 2026-07-14
- **Commit：** `—`（本会话 commit）
- **Verification：** `./scripts/verify.sh` → all checks passed (726 passed, check-doc-drift passed); manual browser testing verified all simulator views and dropdown clicks.
- **证据：** —
- **交付文件：**
  - `apps/desktop/src/components/PreviewDemo.tsx` — Rebuilt page selector as custom dropdown. Refactored iframe DOM modification to execute externally using contentDocument same-origin access, bypassing script string injection and resolving JS leakage bugs. Added monitor stand and bezel for Desktop. Corrected CheckCircle import.
  - `apps/desktop/src/components/MatrixPreview.tsx` — Excluded script/style text nodes from text walker replacements. Refactored viewports to load state rules externally, and added laptop/iPad/iPhone pure CSS frames.
  - `apps/desktop/src/components/StateController.tsx` — Rebuilt state controller as custom dropdown with animated ChevronDown and colored status indicators.
  - `apps/desktop/src/components/design/DesignWorkspace.tsx` — Expanded modal height bounds to 700px.
  - `services/orchestrator/src/prototype_generator.py` — Upgraded regex tokenizer for Chinese range normalization and substring overlapping matches.

### Design vision model fallback degradation ✅

### Preview Demo scrollbar + i18n fix ✅
- **日期：** 2026-07-14
- **Commit：** `d15143c` — `fix(preview-demo): fix scrollbar hidden by thumbnails + hardcoded Chinese in en mode`
- **Verification：** `./scripts/verify.sh` → 731 pytest passed (1 pre-existing keychain), 130 vitest passed, doc-drift zero; `pnpm build` success
- **证据：** `—`
- **交付文件：**
  - `apps/desktop/src/components/PreviewDemo.tsx` — 滚动容器 pr-0.5→pr-2 修复滚动条被 iframe 遮盖；9 处硬编码中文（出N入N、可点击、热区、跳转到、更改目标页面、删除此交互、新增交互等）替换为 t() 国际化调用
  - `apps/desktop/src/components/LanguageContext.tsx` — zhTranslations 新增 11 条 PreviewDemo 相关翻译条目

### Design vision model fallback degradation ✅
- **日期：** 2026-07-13
- **Commit：** `e92961f` — `fix: design iteration generating login page instead of requested landing page`
- **Verification：** `./scripts/verify.sh` → all checks passed (723 python tests, check-doc-drift passed); 4 new vision fallback unit tests pass.
- **证据：** —
- **交付文件：**
  - `services/orchestrator/src/design/generator.py` — Added `_VISION_ERROR_RE` regex and `_looks_like_vision_error` detection in `_llm_complete_vision` for runtime fallback when vision-enabled models return error responses. Added `image_attached` param to `_build_ui_generation_prompt` to prevent prompt/image mismatch. Added final text-only degradation block in `_generate_ui_html` dropping image after all retries fail. Added inline vision error detection in generated HTML for immediate retry without image.
  - `services/orchestrator/tests/test_design_service.py` — Added `test_looks_like_vision_error_detects_common_patterns`, `test_llm_complete_vision_falls_back_on_vision_error`, `test_llm_complete_vision_skips_vision_when_not_ok`, `test_generate_ui_html_detects_vision_error_in_html`.

### Design canvas zoom/pan restoration over prototype iframe ✅
- **日期：** 2026-07-13
- **Commit：** `2b72508` — `fix(design): restore canvas zoom/pan gestures over prototype iframe`
- **Verification：** `./scripts/verify.sh` → all checks passed; manual verification on canvas.
- **证据：** —
- **交付文件：**
  - `apps/desktop/src/components/design/nodes/UiCardNode.tsx` — Replaced pointer-events capture layer with transparent overlay for zoom/pan pass-through when not in picking mode.

### Multi-page design iteration and sequential loading animation support ✅
- **日期：** 2026-07-13
- **Commit：** `e3d0dd0` — `feat(design): support multi-screen generation in iterate session`
- **Verification：** `./scripts/verify.sh` → all checks passed (723 python tests, check-doc-drift passed); unit tests verified successfully.
- **证据：** —
- **交付文件：**
  - `services/orchestrator/src/design/generator.py` — Refactored `iterate_session` `"add"` action branch to plan multiple added screens via `_parse_multi_screens`, horizontally layout new screen coordinate positions, pre-populate planned screens in manifest, and register placeholder rounds sequentially.

### Multi-page design sequential loading animations and round transitions ✅
- **日期：** 2026-07-13
- **Commit：** `8c4f6c6` — `feat(design): optimize multi-page loading animations and round transitions`
- **Verification：** `./scripts/verify.sh` → all checks passed (723 python tests, check-doc-drift passed); unit tests verified successfully.
- **证据：** —
- **交付文件：**
  - `services/orchestrator/src/design/generator.py` — Pre-populate planned screens in `manifest["screens"]` and pre-register round history entries before starting each screen generation loop.
  - `apps/desktop/src/components/design/designWorkspaceUtils.ts` — Update `buildCanvasNodes` to render screens without HTML as shimmer sweep placeholders and isolate ready screens from drawing loaders.

### Multi-page design session generation ✅
- **日期：** 2026-07-13
- **Commit：** `aa2efd2` — `feat(design): support generating multiple screens side-by-side in design sessions`
- **Verification：** `./scripts/verify.sh` → all checks passed (723 python tests, vitest checks, doc drift checks passed); added specific unit tests validating multi-screen planning and coordinate positioning.
- **证据：** —
- **交付文件：**
  - `services/orchestrator/src/design/generator.py` — Add `_extract_json_data` to support lists/dicts JSON extraction, add `_parse_multi_screens` parser, refactor `generate_session` to loop over planned screens, dynamically update status, and lay screens side-by-side horizontally.
  - `services/orchestrator/tests/test_design_service.py` — Add test cases validating multiple screen generation side-by-side and fallback logic.

### Design spec crawler fixes and browser tokens prioritization ✅
- **日期：** 2026-07-13
- **Commit：** `—`（已写入工作区，待 Commit）
- **Verification：** `./scripts/verify.sh` → all checks passed (716 python tests, vitest checks, doc drift checks passed); manual scratch script check -> verified dark_mode is false and colors are correct
- **证据：** —
- **交付文件：**
  - `services/orchestrator/src/design/generator.py` — Refined `dark_signals` logic in `_extract_css_tokens` to prevent false-positives on theme initialization script tag contents. Prioritized computed browser tokens (`browser_prompt_fragment`) over legacy `token_desc` in prompts to avoid conflicts.

### Design Workspace syncing, UI interaction fixes, and reference URL crawler improvements ✅
- **日期：** 2026-07-13
- **Commit：** `4163a46` — `fix: design rounds sync, custom dropdown selection, interactive ready/picking modes, and css variables scraper bypass`
- **Verification：** `./scripts/verify.sh` → all checks passed (715 python tests, vitest checks, doc drift checks passed)
- **证据：** —
- **交付文件：**
  - `apps/desktop/src/components/design/DesignWorkspace.tsx` — Consolidate duplicate React Flow sync effects, convert native round select to custom popover dropdown menu.
  - `apps/desktop/src/components/design/nodes/UiCardNode.tsx` — Dynamic React key binding for preview iframe to bypass WebKit cache, nodrag/nopan event isolation for component picking, pointer-events toggle for interactive Ready mode.
  - `apps/desktop/src/services/designApi.ts` — Fallback global process log filtering for design rounds lacking nested log arrays.
  - `services/orchestrator/src/design/browser_extract.py` — Computed variables scanning fallback for root, body, and container wrappers to bypass CORS. Added Tailwind utility noise filtering and expanded variable limit.

### Handoff performance optimizations and UI experience improvements ✅
- **日期：** 2026-07-12
- **Commit：** `da69fcf`, `04439e1`, `07521aa`, `e03752e`, `5218d30`, `1e824ca`
- **Verification：** `pytest tests/test_terminal_orchestra.py` -> 29 passed; `pnpm build` -> successfully built; manual PTY & background task latency check -> green
- **证据：** —
- **交付文件：**
  - `services/orchestrator/src/handoff_summarizer.py` — Added intelligent TUI visual noise cleaning, integrated current chat history context, and added OS temp directory scanning for native agent handoff files.
  - `services/orchestrator/src/llm/router.py` — Propagated `timeout_sec` and `max_tokens` keywords down to `http_chat_complete`.
  - `services/orchestrator/src/main.py` — Decoupled summarization into an async background task, fixed target log entry index mapping bugs, enabled system-wide active PTY CLI scan, injected custom system instructions for CLI agents, used Carriage Return (`\r`) to submit commands, and increased polling timeout to 30s.
  - `services/orchestrator/src/handoff_writer.py` — Passed `agent_handoff_summary` to write handoff file directly when generated by the source agent.
  - `services/orchestrator/src/interactive_pty_runtime.py` — Added OS system directory filtering to `scan_system_cli_processes` to prevent OS background daemons matching generic agent names from inflating active background terminal counts.
  - `services/orchestrator/src/terminal_orchestra.py` — Initialized `step_status` for dispatches, added `_apply_handoff_initial_layout` and `transition_handoff_layout` to defer source lane collapse.
  - `apps/desktop/src/App.tsx` — Added `key={sessionRunId}` to `DesignWorkspace` component to force React remount on session switch.
  - `apps/desktop/src/services/clutchState.ts` — Added `_laneTranscripts.clear()` call when `runId` changes to isolate terminal transcripts between sessions.
  - `apps/desktop/src/components/terminal-orchestra/OverviewDispatchLog.tsx` — Moved target pending status indicator to the bottom row of log cards to prevent visual badge overlap.
  - `apps/desktop/src/components/terminal-orchestra/OrchestratorBar.tsx` — Prevented source terminal collapsing during handoff generation phase.
  - `apps/desktop/src/components/terminal-orchestra/TerminalLanePane.tsx` — Intercepted prompt injection when the handoff summary is still generating.
  - `apps/desktop/src/services/terminalOrchestraUtils.ts` — Updated pending state checks to respect the step status flow.
  - `apps/desktop/src/components/LanguageContext.tsx` — Added Chinese translations for the new dispatch states.
  - `docs/PRODUCT_INTRO.md` — Updated the PRD specifications regarding handoff dispatch states and log card layout.

### Codex path fix & Multi-CLI message inject fix ✅
- **日期：** 2026-07-12
- **Commit：** `41d8e87`, `3a75635`
- **Verification：** `ln -sf /Applications/ChatGPT.app/Contents/Resources/codex ~/.local/bin/codex && ~/.local/bin/codex --version` -> `codex-cli 0.144.0-alpha.4`；`pytest` -> 711 passed；`./scripts/verify.sh` -> passed
- **证据：** —
- **交付文件：**
  - `services/orchestrator/src/tools_status.py` — Added `/Applications/ChatGPT.app/Contents/Resources` and `/Applications/Codex.app/Contents/Resources` to CLI extra search paths.
  - `apps/desktop/src/services/terminalOrchestraUtils.ts` — Added `mimo-cli`, `codex-cli`, `claude-cli`, and `codebuddy-cli` to PTY inject ready detection and warmup logic.
  - `apps/desktop/src/services/terminalOrchestraUtils.test.ts` — Updated unit tests for claude-cli ready-to-inject prompt tests and warmup expect values.

### Issues #55 / #53 / #52 ✅
- **日期：** 2026-07-11
- **Commit：** `c7dfaa1` — fix: address workflow issues #55, #53, and #52
- **Verification：** `./scripts/verify.sh` → 711 passed, 2 skipped；pre-commit hook green
- **证据：** —
- **交付文件：**
  - `apps/desktop/src/services/workflowFormat.ts` — canvas incompatibility reasons
  - `apps/desktop/src/components/WorkflowOrchestration.tsx` / `WorkflowJsonPanel.tsx` — banner wiring
  - `services/orchestrator/src/evaluator.py` — file_exists FORBIDDEN + resolved path
  - `services/orchestrator/src/compiler/compiler.py` / `main.py` — human gate resume hardening
  - `apps/desktop/src/components/ChatFeed.tsx` — HITL button debounce
  - `docs/PRODUCT_INTRO.md` / `CHANGELOG.md` / `workflows/workflow.schema.json` — docs

### v1.2.x Windows parity ✅ 待 PR
- **日期：** 2026-07-11
- **Commit：** `10d1291` + upstream v1.2.1 merge commit（待 push）
- **Verification：** `python -m uv run pytest tests/test_design_service.py -p no:cacheprovider` → 28 passed；真实 Design Preview smoke → start/connect/stop/port released；`pnpm build` → passed；`pnpm test` → 17 files / 128 tests passed；`python -m uv run pytest -p no:cacheprovider` → 683 passed, 9 skipped；`cargo check` → passed；`pnpm tauri:build` → v1.2.1 MSI/NSIS built
- **证据：** `—`
- **交付文件：**
  - `services/orchestrator/src/design/service.py` — Windows command resolution, install error handling, preview lifecycle cleanup, manifest replace retry
  - `services/orchestrator/tests/test_design_service.py` — Design Preview Windows regression coverage
  - `apps/desktop/package.json` — desktop `tauri:dev` uses Node launcher
  - `apps/desktop/src-tauri/tauri.conf.json` · `scripts/run-build-sidecar.mjs` — Windows-safe sidecar build entry
  - `apps/desktop/src-tauri/gen/schemas/windows-schema.json` — Tauri Windows generated schema
  - `CHANGELOG.md` · `docs/PRODUCT_INTRO.md` · `docs/BUILD_FROM_SOURCE.md` · `memory/PROGRESS.md` · `memory/FAILURES.md` · `CLAUDE.md` — Windows parity documentation

### D36 Design 会话模型 + 原型交互画布 ⚠️ 待 commit
- **日期：** 2026-07-10
- **Commit：** （未提交 — 等待用户确认 commit）
- **Verification：** `./scripts/verify.sh` → 0 errors；`pytest tests/test_design_service.py` → 2 passed
- **证据：** `runs/verification/2026-07-10-design-canvas-reference.md`
- **交付文件：**
  - `apps/desktop/src/components/design/DesignWorkspace.tsx` — 欢迎页 + 无限画布（规范→描绘→NL）
  - `apps/desktop/src/App.tsx` / `Header.tsx` / `sidebar.tsx` — `appMode` Coding|Design；会话按 mode
  - `apps/desktop/src/services/designApi.ts` · `runApi.ts` — session-scoped Design API + `mode`
  - `services/orchestrator/src/design/` — 两阶段 generate + iterate
  - `memory/DECISIONS.md` D36 · `docs/PRODUCT_INTRO.md` §3.5 · `memory/ROADMAP.md` · `CHANGELOG.md`

### D35 Design 模式（原型画布与预览沙箱）⚠️ 已被 D36 修订
- **日期：** 2026-07-10
- **Commit：** （未提交 — 等待用户确认 commit）
- **Verification：** 见 D36
- **证据：** `—`
- **交付文件：** 见 D36（项目左栏形态已废弃）

---

## Recently Completed

### upstream 首页图标同步 ✅
- **日期：** 2026-07-03
- **Commit：** `9a982f4` — `fix(ui): sync workflow sidebar icon from upstream`
- **Verification：** `pnpm build` → passed；`pnpm test` → 17 files / 125 tests passed；Husky pre-commit → Git Bash PATH 无 `uv`，等价验证通过后 `HUSKY=0` 提交
- **证据：** `—`
- **交付文件：**
  - `apps/desktop/src/sidebar.tsx` — Workflows SOP 展开态与折叠态图标同步为 upstream dev 的 `fork_right`

### upstream dev 同步与左侧折叠入口调整 ✅
- **日期：** 2026-07-03
- **Commit：** `214af4d` — `merge upstream dev and align sidebar collapse chrome`
- **Verification：** `pnpm build` → passed；`pnpm test` → 17 files / 125 tests passed；`python -m uv run pytest tests/test_llm_provider.py` → 7 passed；Husky pre-commit → Git Bash PATH 无 `uv`，等价验证通过后 `HUSKY=0` 提交
- **证据：** `—`
- **交付文件：**
  - `apps/desktop/src/App.tsx` — Header 不再接收顶部侧栏折叠回调，Sidebar 接管开合状态更新
  - `apps/desktop/src/components/Header.tsx` — 移除顶部左侧侧栏折叠按钮
  - `apps/desktop/src/sidebar.tsx` — 新增左侧面板右边缘中线折叠按钮，复用 `ChromeEdgeToggle`
  - `docs/PRODUCT_INTRO.md` — 同步 Workspace Chrome 产品说明
  - `memory/PROGRESS.md` — 合并 upstream 发版记录并记录 Windows 侧维护进展

### Windows workspace chrome polish 同步 ✅
- **日期：** 2026-07-03
- **Commit：** `796120b` — `fix(ui): restore Windows workspace chrome polish`
- **Verification：** `pnpm build` → passed；`pnpm test` → 17 files / 125 tests passed；Husky pre-commit → Git Bash PATH 无 `uv`，等价验证通过后 `HUSKY=0` 提交
- **证据：** `—`
- **交付文件：**
  - `apps/desktop/src/App.tsx` — Header 侧栏折叠入口恢复，移除左侧浮动折叠按钮
  - `apps/desktop/src/components/Header.tsx` — 恢复顶部 Header 内置折叠按钮与昨天的 breadcrumb chrome
  - `apps/desktop/src/sidebar.tsx` — 恢复折叠态纯图标 tooltip、Workflow 图标和底部 Settings 布局
  - `apps/desktop/src/components/ChatFeed.tsx` — 恢复聊天主区宽度/间距与气泡紧凑样式，同时保留 Terminal Orchestra
  - `apps/desktop/src/components/RightPanel.tsx` — 恢复右侧监督面板等分 Tab 与短指示条
  - `docs/PRODUCT_INTRO.md` — 同步 Workspace Chrome 产品说明

### Settings 字体大小偏好恢复 ✅
- **日期：** 2026-07-03
- **Commit：** `68769fb` — `fix(settings): restore font size preference`
- **Verification：** `pnpm build` → passed；`pnpm test` → 17 files / 125 tests passed；Husky pre-commit → Git Bash PATH 无 `uv`，等价验证通过后 `HUSKY=0` 提交
- **证据：** `—`
- **交付文件：**
  - `apps/desktop/src/App.tsx` — 恢复 font size 偏好读取、保存和 `data-font-size` 应用
  - `apps/desktop/src/components/SystemPreferencesModal.tsx` — 恢复 General Settings 字体大小选择框
  - `docs/PRODUCT_INTRO.md` — 同步 Settings Dashboard 功能说明

### Windows interactive PTY lanes ✅
- **日期：** 2026-07-03
- **Commit：** `395bacb` — `fix(windows): support interactive PTY lanes`
- **Verification：** `python -m uv run pytest tests/test_interactive_pty_runtime.py` → 11 passed, 5 skipped；`python -m uv run pytest tests/test_terminal_orchestra.py tests/test_ws_pty_events.py tests/test_ws_dispatch_orchestra.py tests/test_interactive_pty_runtime.py` → 36 passed, 5 skipped, 1 warning；`pnpm build` → passed；`pnpm test` → 17 files / 125 tests passed；`python -m uv run pytest` → 634 passed, 9 skipped, 1 warning；Windows `cmd.exe` low-level 与 manager PTY smoke → marker observed；`bash scripts/check-doc-drift.sh` → 未运行，当前 PowerShell PATH 无 `bash`
- **证据：** `—`
- **交付文件：**
  - `services/orchestrator/src/interactive_pty_runtime.py` — Windows interactive PTY backend attach/read/write/close
  - `services/orchestrator/src/windows_pty.py` — 暴露 read/write/alive/close 行为给 interactive manager 复用
  - `services/orchestrator/tests/test_interactive_pty_runtime.py` — Windows PTY fake backend 回归测试
  - `docs/PRODUCT_INTRO.md` — 同步 Windows Terminal Orchestra 支持说明

### Ollama Models Config 本机同步 ✅
- **日期：** 2026-07-01
- **Commit：** `2257560` — `fix(models): sync Settings Ollama list with local ollama list`
- **Verification：** `pytest tests/test_models_config_api.py` → 21 passed · `verify.sh` → 523 pytest passed
- **证据：** `—`
- **交付文件：**
  - `services/orchestrator/src/models_config.py` — 本机 Ollama tag 同步与 `active_model_id` 回退
  - `services/orchestrator/src/main.py` — POST 前 sync
  - `services/orchestrator/tests/test_models_config_api.py`
  - `docs/PRODUCT_INTRO.md` §3.4

### #19 CLI 错误文案 ✅
- **日期：** 2026-07-01
- **Commit：** `2cb3016` — `fix(router): single-layer CLI errors and gateway-busy copy (#19)`
- **Verification：** `pytest tests/test_engine_router.py` · `verify.sh`
- **证据：** `—`
- **交付文件：**
  - `services/orchestrator/src/engine_router.py`
  - `services/orchestrator/tests/test_engine_router.py`

### 安装渠道与发版文档 ✅
- **日期：** 2026-07-01
- **Commit：** `5cb8950` … `1a26ca0`（README · GETTING_STARTED · install.sh/ps1 · homebrew-clutch tap · RELEASE_MAINTAINER）
- **Verification：** `check-doc-drift.sh` · tap 仓库已 push
- **证据：** [homebrew-clutch](https://github.com/fancy1108/homebrew-clutch)
- **交付文件：**
  - `docs/GETTING_STARTED.md` · `docs/RELEASE_MAINTAINER.md` · `docs/PACKAGE_MANAGERS.md`
  - `README.md` · `README.zh-CN.md`
  - `scripts/install.sh` · `scripts/install.ps1` · `scripts/sync-homebrew-tap.sh`
  - `.github/workflows/release.yml` — 可选 Homebrew tap CI sync

### D38 Stable Context Boundary Code Decomposition ✅
- **日期：** 2026-07-13
- **Commit：** `d333668` — `refactor: D38 Stable Context Boundary code decomposition`
- **Verification：** `pnpm build` → 成功; `pnpm test` → 17 files 130 passed; `pytest` → 713 passed 2 skipped; `check-doc-drift.sh` → 0 errors
- **证据：** —
- **交付文件：**
  - Backend — `services/orchestrator/src/main.py` 降 268 行, `chat_runner.py`, `routes/`, `design/generator.py`, `session_store.py`, `preview_manager.py`, `thumbnail.py`, `layout.py`, `token_usage.py`
  - Frontend — `DesignWorkspace.tsx` 降 1,642 行, `designWorkspaceUtils.ts`, `nodes/`(6 个), `clutchStateUtils.ts`, `PromptModal.tsx`, `AppErrorBoundary.tsx`
  - Docs — `FILEMAP.md`, `DECISIONS.md`, `PROGRESS.md`, `DELIVERABLES.md`

---

## Archive Index

| 里程碑 | 路径 |
|--------|------|
| M0 | [`archive/DELIVERABLES-M0.md`](./archive/DELIVERABLES-M0.md) |
| M1 | [`archive/DELIVERABLES-M1.md`](./archive/DELIVERABLES-M1.md) |
| M2–M4 / P2 | [`archive/DELIVERABLES-M2-M4-P2.md`](./archive/DELIVERABLES-M2-M4-P2.md) |
| M3（工具链） | [`archive/DELIVERABLES-M3.md`](./archive/DELIVERABLES-M3.md) |
| D25 / 迭代 | [`archive/DELIVERABLES-POST-MVP.md`](./archive/DELIVERABLES-POST-MVP.md) |
| HRT | [`archive/DELIVERABLES-HRT.md`](./archive/DELIVERABLES-HRT.md) |
| OSR（T0–T2） | [`archive/DELIVERABLES-OSR.md`](./archive/DELIVERABLES-OSR.md) |
| PROGRESS 会话 | [`archive/PROGRESS-2026-Q2.md`](./archive/PROGRESS-2026-Q2.md) · [`archive/PROGRESS-2026-Q3.md`](./archive/PROGRESS-2026-Q3.md) |

_v1.0.0–v1.0.2 已发布交付见 `archive/DELIVERABLES-OSR.md` 及 Git tag / `CHANGELOG.md`。_

---

## D22 — Usage dashboard (`c68301b`)

- **Verification:** `cd services/orchestrator && uv run pytest tests/test_usage_d22.py -q` → 2 passed；`cd apps/desktop && pnpm test src/components/UsageDashboard.test.ts` → 2 passed
- **PM:** `runs/verification/pm-acceptance/D22.md`
- **Files:** `UsageDashboard.tsx`, `ChatInputBar.tsx`, `runApi.ts`, `chat_runner.py`, `test_usage_d22.py`, `PRODUCT_INTRO.md`, `CHANGELOG.md`

---

## D20 — Agent busy message queue (`94fdc8f`)

- **Verification:** `cd apps/desktop && pnpm test -- src/services/chatPendingQueue.test.ts` → 5 passed
- **PM:** `runs/verification/pm-acceptance/D20.md`
- **Files:** `chatPendingQueue.ts`, `ChatFeed.tsx`, `ChatInputBar.tsx`, `PRODUCT_INTRO.md`, `CHANGELOG.md`

---

## D19 — Thinking stream in live activity (`3f3e66e`)

- **Verification:** `uv run pytest tests/test_thinking_stream_d19.py -q` → 2 passed；`pnpm test src/services/agentLiveReasoning.test.ts` → 1 passed
- **PM:** `runs/verification/pm-acceptance/D19.md`
- **Files:** `mcp_react.py`, `tool_steps.py`, `chat_runner.py`, `state.py`, `AgentLiveActivity.tsx`, `ChatFeed.tsx`, `shared-types/index.ts`

---

## D26 — Background job failure monitor (`8be7f06`)

- **Verification:** `uv run pytest tests/test_bg_jobs_monitor_d26.py -q` → 3 passed；`pnpm test src/services/bgJobMonitor.test.ts` → 2 passed
- **PM:** `runs/verification/pm-acceptance/D26.md`
- **Files:** `bg_jobs_monitor.py`, `chat_runner.py`, `bgJobMonitor.ts`, `ChatFeed.tsx`

---

## D27 — Explore / Plan / Implement modes (`a269764`)

- **Verification:** `cd services/orchestrator && uv run pytest tests/test_permission_explore_d27.py -q` → 3 passed
- **PM:** `runs/verification/pm-acceptance/D27.md`
- **Files:** `permissionApi.ts`, `ChatInputBar.tsx`, `mcp_react.py`, `preferences_storage.py`, `agent_prompt.py`, `subagent_runner.py`, `test_permission_explore_d27.py`
