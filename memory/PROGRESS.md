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

## 2026-07-13 会话（支持在设计会话迭代中新增多个页面）

- **迭代多画板生成与渐进式加载支持**：
  - **迭代入口多页面规划**：重构了 `generator.py` 中的 `iterate_session` 新增分支（`action == "add"`），引入 `_parse_multi_screens` 用于识别迭代输入（如底部输入框中输入 `生成一个Dashboard页面，一个列表页面`）中包含的多个期望新增页面。
  - **相对横向并排定位**：通过 `_screen_layout_x` 获取当前画布最右侧坐标，作为新增多画板的起始位置，横向顺次排布。
  - **渐进式注册与扫光加载动画**：在循环开始前将新增页面全部写入 `manifest["screens"]` 占位，在开始生成时注册 `round_history` 中的 placeholder 记录，使迭代中新增的多页面拥有和首次生成完全一致的扫光加载动画骨架和顺畅的轮次跳转。
- **校验与测试**：
  - 通过了全量 `./scripts/verify.sh` 一键校验。

## 2026-07-13 会话（优化多页面渐进式加载动画与 Round 轮次跳转）

- **加载动画与多画板占位优化**：
  - **后端顺序化注册与预占位**：重构了 `generator.py` 中的多页面生成逻辑，在循环开始前将所有规划的页面预先写入 `manifest["screens"]`，在开始生成每一个特定页面前提前在 `round_history` 中注册该页面的 placeholder 轮次。使得前端轮询时能立刻感知新轮次，并显示占位加载卡片。
  - **前端占位符与就绪隔离**：修改了 `designWorkspaceUtils.ts` 中的 `buildCanvasNodes`，支持对无 HTML 内容的规划中画板渲染为 `placeholder` 状态，触发与首屏完全一致的全卡片 Shimmer sweep 扫光加载动画。
  - **消除闪屏与重复加载**：完成了已生成好 HTML 页面与全局 `"generating_ui"` 加载状态的隔离，防止正在生成后续页面时前面的页面被重复遮罩和闪屏，提供了完美的步进式、骨架图扫光加载交互体验。
- **校验与测试**：
  - 通过了全量 `./scripts/verify.sh`（723 个单元测试全数通过，无文档漂移问题）。

## 2026-07-13 会话（实现设计画布多页面自动生成）

- **设计画布多页面自动生成实现**：
  - 引入了 `_extract_json_data` 辅助函数，支持解析大模型返回的 JSON list 结构。
  - 新增 `_parse_multi_screens` 架构规划步骤，通过大模型提取用户简述（brief）中期望生成的多页面列表。
  - 重构了 `generate_session` 生成逻辑，将原有的单页面硬编码逻辑重构为基于规划的多页面迭代生成循环；在画布上以 X 轴位置偏置 `ui_layout_step` 的方式，将多页面横向并排呈现。
  - 在前端反馈中增加步骤状态动态更新（如 `Generating screen 1/3...`），并支持最终呈现所有已生成页面名称及文件路径。
- **单元测试与校验**：
  - 新增 `test_generate_session_with_multiple_screens` 与 `test_parse_multi_screens_fallback` 测试，验证多页面并排定位布局及备用计划兜底。
  - 通过了 `./scripts/verify.sh` 一键全量校验，723 个测试用例和文档漂移检查均顺利通过。

## 2026-07-13 会话（修复参考设计 Spec 提取颜色与暗黑模式判定错误）

- **设计 Spec 提取逻辑优化**：
  - 修复了 legacy HTML 爬虫 `_extract_css_tokens` 的暗黑模式判定，移除了过于泛化的 `'"dark"' in html[:2000]` 对 inline theme 脚本配置的误判，引入了对 style 标签及外链样式表中 `@media (prefers-color-scheme: dark)` 的精准检测。
  - 在 spec 生成 (`generate_session`) 和 HTML 生成 (`_build_ui_generation_prompt`) 中引入了提示词防冲突策略：当 Playwright 浏览器精准提取的计算样式 (`browser_prompt_fragment`) 可用时，自动屏蔽容易产生干扰的 legacy `token_desc`，避免大模型因双重矛盾指令产生混淆。
- **校验**：执行了 `./scripts/verify.sh` 一键校验，前后端 716 个测试全部通过。

## 2026-07-13 会话（修复设计画布状态同步、下拉菜单转换、就绪/选取模式以及爬虫 CSS 变量提取）

- **设计画布状态同步优化**：合并了 `DesignWorkspace.tsx` 中两个冲突的 React Flow 节点同步 `useEffect`，规避了切换设计轮次（Round）时的组件重复渲染与排版竞争问题。
- **自定义下拉框组件转换**：将设计轮次水平滚动选择栏改写为自定义绝对定位下拉菜单（DesignRoundSelector），符合 Clutch 状态栏/页脚菜单的 UI/UX 指引规范，支持 Click-Outside 与 Escape 退出。
- **就绪交互模式（Prototype）解锁**：在 Ready 模式下解除了 preview iframe 的 `pointer-events-none` 限制，用户可在原型画布上正常触发 hover、输入、点击等页面交互。
- **组件拾取选取修复（Safari/WebKit 兼容性）**：为 `UiCardNode` 的 iframe 节点引入了基于 Picking 状态的动态 `key` 绑定以强制销毁重构，规避 WebKit 底层缓存 `srcDoc` 导致拾取脚本不执行的缺陷；同时添加了 `nodrag nopan` 以隔离 React Flow 的鼠标手势劫持。
- **Agent Log 缺失日志修复**：在 `designApi.ts` 历史轮次解析中，针对后端未返回内嵌日志的情况，引入了 session 全局 process_log 轮次索引 Fallback 机制，恢复了步骤执行细节显示。
- **网页爬虫 CSS 变量提取与跨域绕过**：重构了 `browser_extract.py` 浏览器提取爬虫，针对 CDN/跨域样式表不可读 `sheet.cssRules` 报错的问题，增加了对 root, body 以及直接子容器（`body > *, body > * > *`）计算样式变量（`getComputedStyle`）的自动扫描；增加了对 Tailwind 杂音变量（`--tw-*` 等）的过滤并扩容至 35 个，确保模型能 100% 提取到正确的品牌颜色设计 spec。
- **校验**：执行了 `./scripts/verify.sh` 一键校验，前后端测试全部正常通过。

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
