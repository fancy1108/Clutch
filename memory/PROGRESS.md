# PROGRESS

> **生命周期：** 见 [`docs/document-governance.md`](../docs/document-governance.md) §文档生命周期。  
> 主文件仅保留当前状态 + 最近 10 次会话；更早记录见 [`archive/PROGRESS-2026-Q2.md`](./archive/PROGRESS-2026-Q2.md) · [`archive/PROGRESS-2026-Q3.md`](./archive/PROGRESS-2026-Q3.md)。

## Current Status

- **阶段：** **v1.2.2 已发布（macOS）**（2026-07-11）— Windows MSI/NSIS 已在 CI 构建成功，待挂到 Release（本机下载超时）
- **Release：** [v1.2.2](https://github.com/fancy1108/Clutch/releases/tag/v1.2.2) · tag on `main` @ `7fa6901`
- **Git：** `main` / `dev` @ `7fa6901`
- **macOS：** DMG + SHA256SUMS 已上传；Homebrew tap 已 bump
- **Windows：** Actions artifact `clutch-windows-x64` @ run [29158434326](https://github.com/actions/runs/29158434326) — 需 `gh release upload`

## Next Actions

- 挂 Windows MSI/NSIS 到 Release（网络恢复后）
- 等 updater assets workflow 完成
- Windows 实体机 smoke（可选）

## Recent Sessions

## 2026-07-13 会话（D38 Stable Context Boundary 代码模块化重构完成）

- **后端大文件拆分（Phase 1 & Phase 2）**：
  - 将 `design/service.py` 拆分为 `session_store.py`、`preview_manager.py`、`generator.py`、`thumbnail.py`、`layout.py` 和 `token_usage.py`，保持 `service.py` 作为外观模式（Facade）暴露原 API。
  - 将 FastAPI 路由大文件 `main.py` 按业务领域拆入 `routes/` 包下独立的路由子模块：`chat.py`、`design.py`、`models.py`、`pty.py`、`settings.py`、`workspace.py`。
- **前端大文件拆分（Phase 3, Phase 4 & Phase 5）**：
  - 将 `services/clutchState.ts` 纯辅助函数（合并消息、更新 Optimistic run 判定等）抽取至 `services/clutchStateUtils.ts` 并重新导出。
  - 将 `DesignWorkspace.tsx` 中的 React Flow 状态节点渲染拆入 `nodes/` 目录下（`AgentLogCardNode.tsx`、`SpecCardNode.tsx`、`UiCardNode.tsx`、`RefCardNode.tsx`、`MdDocCardNode.tsx`、`UrlCardNode.tsx`），提取画布生成及定位计算等纯函数到 `designWorkspaceUtils.ts`。
  - 将 `App.tsx` 中的 `PromptModal` 和 `AppErrorBoundary` 组件抽取至 `components/` 下的独立文件中。
- **文档更新**：更新了 `memory/FILEMAP.md` 对齐全新模块化结构，更新 `memory/DECISIONS.md` 将 D38 状态修改为 `已完成`。
- **验证**：执行了 `./scripts/verify.sh` 一键验证，前后端所有静态类型检查、测试（含后端 713 个单元测试、前端测试）全部通过。

## 2026-07-12 会话（交接 Handoff 派发流程耗时优化与界面交互体验改进）

- **性能优化**：将 Handoff 派发时 LLM 生成 Smart Summary 的耗时从同步改成了非阻塞后台任务异步生成，结合最新 12,000 字符的智能输入截断策略，彻底解决了界面可能因云端模型慢响应而卡死的问题。
- **Handoff 质量提升与动态注入轮询（智能体原生 Handoff 触发）**：针对大部分用户可能未安装特定 `/handoff` 命令行技能的情况，我们设计了更具普适性的智能提示词注入方案。当触发交接时，如果源端是 CLI 智能体，后台会自动向其终端 PTY 注入包含详细指示的系统级 Prompt（要求其总结对话，写入 OS 临时目录并以 `handoff-` 开头命名，并输出路径）。后台随后以 1.0s 为步长、最高 30.0s 动态轮询检索临时目录（以兼容慢速 LLM 思维耗时），并允许最长 45s 的文件修改寿命检查；一旦检测到生成的文件，立即读取、清洗 YAML 头，并作为 `SOURCE OUTPUT` 装载，从而无需任何预装 Skill 即可 100% 捕获终端内交互式聊天细节。如果超时未生成，则平滑降级至外部 LLM 总结。
- **PTY 模拟回车执行确认**：在注入提示词到终端 PTY 时，将换行符 `\n` 改为真正模拟回车提交的 `\r`（Carriage Return），并配合 150ms 缓冲延时，解决了提示词仅被打入输入框而未回车提交导致任务卡在输入区的问题。
- **跨会话终端数据隔离修复**：修复了前端 `clutchState.ts` 内存 `Map` (`this._laneTranscripts`) 在切换/新建会话（`runId` 变化）时未进行清空的 Bug，彻底杜绝了上一个会话中其他智能体的终端报错历史泄露合并到新会话中全新智能体手交摘要中的数据污染问题。
- **手交期间源终端展开与延时折叠**：重构了 Handoff 派发时的界面布局流。在 `generating_handoff` 期间，源端智能体终端保持展开（不折叠）状态以便用户能直观看到或执行命令行内的敏感写盘许可确认（如输入 `y` 确认）；一旦 Handoff 文件生成完毕、进入 `opening_terminal` 阶段后，才自动触发源端折叠并放大目标端终端。
- **设计画布画布跨会话污染修复**：为 `<DesignWorkspace>` 组件引入了 `key={sessionRunId}`，强制 React 在切换左侧会话历史时完全销毁并重新初始化该组件，彻底解决了旧会话节点和缓存污染新会话画布的界面“串行”Bug。
- **TUI 精细清洗**：重构了 `clean_pty_transcript` 方法，精细清洗过滤了 horizontal 边框线（如 `━━━━`）、填充块（`████`）、键盘操作指南（`tab 切换模式`/`ctrl+p` 等）、无用 headers 等 TUI 画布冗余元数据，让交接生成的 Handoff 文本内容整洁易读。
- **状态机步骤渲染**：前端及后端增加了 `generating_handoff` -> `opening_terminal` -> `injecting_goal` -> `done` 的步骤流渲染，支持在卡片最底下一行完美呈现 Spinner 和国际化提示语，防止了头部 Badge 排版重叠。
- **面板秒折叠**：发送交接时，立即在前端触发 `from @agent1` 来源面板的折叠，使用户获得极速交互响应。
- **后台终端数修正与系统守护进程过滤**：在 `main.py` 中为 `list_alive_for_run` 传递了 `include_system=True` 以启用系统级 PTY/CLI 进程扫描；同时在 `interactive_pty_runtime.py` 的 `scan_system_cli_processes` 中增加了路径前缀过滤，排除了位于 `/usr/sbin/`、`/usr/libexec/`、`/System/` 和 `/sbin/` 的系统守护进程（如 `distnoted agent` 或 `cfprefsd agent`），确保后台终端统计仅精确匹配用户配置并运行的实际 CLI 智能体进程。
- **校验**：本地 `./scripts/verify.sh` 通过，所有单元测试通过。

## 2026-07-12 会话（修复 Codex 路径及多 CLI 终端消息注入时机问题）

- **修复**：更新了 `~/.local/bin/codex` 软链接至最新的 `/Applications/ChatGPT.app/Contents/Resources/codex`（最新版的 dmg 将 `Codex.app` 更名为 `ChatGPT.app`）。
- **优化**：在 `services/orchestrator/src/tools_status.py` 的 `_CLI_EXTRA_BIN_DIRS` 中增加了 `/Applications/ChatGPT.app/Contents/Resources` 和 `/Applications/Codex.app/Contents/Resources` 作为 fallback 路径。
- **修复**：在 `apps/desktop/src/services/terminalOrchestraUtils.ts` 中，为 `mimo-cli`、`codex-cli`、`claude-cli` 和 `codebuddy-cli` 等所有重型交互式终端补全了 PTY 启动就绪检测（精确匹配各种语言提示语如 `输入消息`/`ctrl+p`/`write tests for`/`ask a question`/`for shortcuts`）与 warmup 时间策略，解决了终端未完全就绪就注入消息导致消息丢失的问题。
- **验证**：本地运行 `./scripts/verify.sh` 校验成功。

## 2026-07-11 会话（v1.2.2 发版）

- PR [#60](https://github.com/fancy1108/Clutch/pull/60) merge → `main`；tag `v1.2.2`；`main`→`dev` 同步
- macOS `release.yml` ✅（含 Homebrew tap sync）
- Windows Build ✅；artifact 上传 Release 因本机下载超时未完成

### v1.2.1 发版清单

| 项 | 状态 |
|----|------|
| CHANGELOG + README + `docs/releases/v1.2.1.md` | ✅ |
| 版本号 bump | ✅ |
| PR merge `dev` → `main` (#48) | ✅ |
| `git tag v1.2.1` on `main` + push | ✅ |
| macOS DMG CI (`release.yml`) | ✅ [run](https://github.com/actions/runs/29136178177) |
| Homebrew tap sync | ✅（CI 缺 `HOMEBREW_TAP_GITHUB_TOKEN`，已手动 `sync-homebrew-tap.sh`） |
| macOS updater (`latest.json`) | ✅ [run](https://github.com/fancy1108/Clutch/actions/runs/29136334316) |

## Next Actions

- **v1.2.2 发版中** — `release/v1.2.2` → merge `main` → tag `v1.2.2` → macOS DMG CI + Windows Build 挂 Release → Homebrew tap + updater
- （可选）配置 `HOMEBREW_TAP_GITHUB_TOKEN`

## Recent Sessions

## 2026-07-11 会话（v1.2.2 发版准备）

- 版本 bump 1.2.1 → 1.2.2；CHANGELOG / README / releases 快照；**macOS + Windows**（patch 例外，对齐 Design Preview）
- 分支：`release/v1.2.2`

## 2026-07-11 会话（开放 PR 合入 + issues #55/#53/#52）

- 合入 #56/#58 → `main`，#57 → `dev`，并 sync `main`→`dev`
- **#55：** `getCanvasIncompatibilities` + JSON banner 点名节点/边
- **#53：** `file_exists` FORBIDDEN/resolved path 日志；schema + PRODUCT_INTRO
- **#52：** human_decision 锁、清 check_result、resume 时 `running`、HITL 按钮防抖
- **校验：** `./scripts/verify.sh` → 711 passed；vitest workflowFormat 4 passed
- **分支：** `fix/issues-55-53-52`

## 2026-07-11 会话（v1.2.x Windows parity · PR 准备）

- **同步** `win` fast-forward 到 upstream `dev` `3db7e03`，后续 merge 作者 v1.2.1 `e03aa64` 以解除 PR conflict；保留主工作区 `clutch_win_wuxian` 不变。
- **修复** Windows Design Preview：`.cmd` 命令解析、pnpm ignored-build policy、UTF-8 install output、preview process tree stop、重新生成前停止 preview、manifest replace 重试。
- **修复** Windows Tauri build/dev：desktop `tauri:dev` 走 Node wrapper；`beforeBuildCommand` 走 `scripts/run-build-sidecar.mjs`，不再依赖裸 `uv` 在 PATH。
- **验证** `pytest tests/test_design_service.py` 28 passed；真实 Design Preview smoke 通过；`pnpm build`、`pnpm test`、orchestrator 全量 pytest、`cargo check`、`pnpm tauri:build` 通过。

## 2026-07-11 会话（v1.2.1 发版完成）

- Merge #48 · tag `v1.2.1` · DMG + SHA256SUMS · Homebrew tap 手动 sync · updater workflow 已触发
- 用户从 1.2.0 经应用内全量更新拿修复；热更通道供后续后端热修

## 2026-07-11 会话（热更 D37 + v1.2.1 打包准备）

- D37 Sidecar 热更客户端 + Chat/Design/Models hotfix · verify ✅

## 2026-07-11 会话（v1.2.0 Chat 回归诊断 + 修复）

- Chat dict 崩溃根因与修复路径

## 2026-07-10 会话（v1.2.0 updater / 发版 / D36）

- 见 archive / 上文历史
