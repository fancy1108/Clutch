# PROGRESS

> **生命周期：** 见 [`docs/document-governance.md`](../docs/document-governance.md) §文档生命周期。  
> 主文件仅保留当前状态 + 最近 10 次会话；更早记录见 [`archive/PROGRESS-2026-Q2.md`](./archive/PROGRESS-2026-Q2.md) · [`archive/PROGRESS-2026-Q3.md`](./archive/PROGRESS-2026-Q3.md)。

## Current Status

- **阶段：** **v1.3.0** 已发；主线 D8–D13 ✅；扩展/MCP **D14–D52 Agent 代 PM ✅**；Desktop E2E ✅；Design D36 仍 ❌
- **Git / PM 索引：** [`runs/verification/pm-acceptance/AGENT-PM-2026-07-25.md`](../runs/verification/pm-acceptance/AGENT-PM-2026-07-25.md)
- **下次优先：** D38 `builtin_tools.py`；P2 余下大文件

## Recent Sessions

## 2026-08-01 会话（D38 P2：App.tsx hooks 拆分）

- **落地：** `useAppSession.ts` / `useAppSettings.ts` / `useAppWorkspace.ts`；`App.tsx` ~2716→~1042 行壳
- **测：** `pnpm --filter @clutch/desktop build` + `test`（223 passed）
- **下次：** D38 `builtin_tools.py`

## 2026-08-01 会话（D38：ChatFeed hooks + bubble/dock）

- **落地：** `useChatFeedController.ts` / `ChatMessageBubble.tsx` / `ChatFeedDock.tsx`；`ChatFeed.tsx` ~2173→~490 行壳；re-export `configuredEngineToRuntimeLabel`
- **测：** `pnpm --filter @clutch/desktop build` + `test`（223 passed）
- **下次：** D38 `App.tsx` / `builtin_tools.py`

## 2026-08-01 会话（D38：design/generator Spec/UI/Iterate）

- **落地：** `gen_spec.py` / `gen_ui.py` / `gen_iterate.py`；`generator.py` 编排壳 + re-export
- **测：** `pytest tests/test_design_service.py tests/test_prototype_generator.py` 44 passed
- **下次：** ChatFeed hooks + bubble/dock

## 2026-08-01 会话（D38 Phase 2：chat_runner plain/workflow）

- **落地：** `chat_run_live.py` / `chat_plain.py` / `chat_workflow.py`；`chat_runner` ~4570→~1270 行；删 Phase1 影子 `_patch_question_card_status`；monkeypatch 指向定义模块
- **测：** pytest 942 passed / 8 skipped
- **下次：** generator + ChatFeed

## 2026-08-01 会话（D38 Phase 1：chat_runner 拆分）

- **落地：** `chat_messages.py` / `chat_ws_events.py` / `chat_mcp_gates.py`；`chat_runner` ~5347→~4570 行 + re-export；清理死 Request schema
- **测：** 计划内子集 + 全量 pytest / `./scripts/verify.sh`
- **下次：** Phase 2

## 2026-07-25 会话（Tool harness 全链路）

- **对照 Grok Build：** 采样→工具→回灌；Clutch 缺「空答不重试」
- **落地：** `tool_use_policy` + ReAct nudge/`tool_choice=required`；Allow network 默认 On；目录诚实隐藏死工具；web_fetch httpx
- **测：** `pytest tests/test_tool_use_policy.py …` 22 passed

## 2026-07-25 会话（补：Desktop E2E）

- **Desktop：** `./scripts/run-e2e.sh` → API 6 + Hybrid 1 + Desktop **5/5**（`wave-c-desktop-retry10.log`）
- **Real：** preflight 仍 Skip（缺 DeepSeek/Agnes；Ollama OK）— `wave-c-real-preflight.log`
- **下次：** 密钥齐后真连；commit 本轮 e2e 修复

## 2026-07-25 会话（Agent 代 PM 自验收）

- **Wave A/B：** D14–D52 用例内 pytest/vitest/doc-drift 全绿
- **Wave C：** API+Hybrid E2E ✅；修 sandbox `route_engine` FAKE_LLM（`0c3462d`/`61c22ec`）；Desktop/Real 当时 Skip（后已补 Desktop）
- **证据：** `runs/verification/pm-acceptance/AGENT-PM-2026-07-25.md`

## 2026-07-25 会话（D13 A + Ask=只读）

- **PM：** D13 ✅ 用例 A；B/C 跳过
- **产品：** Explore 并入 Ask；Ask=对话只读（D54）；pill = Agent/Plan/Full/Ask；onboarding 已对齐
- **下次：** 扩展表或 D27 点验

## 2026-07-25 会话（D12 PM）

- **PM：** D12 ✅；`my-video` 真 commit `bcfc099` / `d12-pm-test`；web_fetch 总结 OK
- **下次：** **D13**

## 2026-07-25 会话（D11 PM + bg job UX）

- **PM：** D11 ✅；RUNNING 底栏 / 结束进对话；Kill 乐观无红 toast
- **修复：** dock 上滚；`msg.bgJob`；Kill 离线回收
- **下次：** **D12**

## 2026-07-25 会话（D10 PM + explore 预算）

- **PM：** D10∥D48 ✅；explore→done；implement 卡非强制
- **修复：** explore max_steps 16 / implement 12；高效 explore 提示
- **下次：** **D11**

## 2026-07-25 会话（D9 PM + Usage 占位）

- **PM：** D9 ✅ Stop/Continue；熔断不点验；用量 Overview 占位 `—`（Q-USAGE-1）
- **产品：** 移除 `+ → Usage`；用量入口仅右侧 Overview
- **下次：** **D10∥D48**

## 2026-07-25 会话（D8 PM 通过 + 验收期修复）

- **PM：** D8 ✅（`/compact` 末尾摘要；「还剩哪些 todo」答对）
- **修复（同批）：** todo JSON 字符串不炸字符；压缩 patch 整表替换；`/compact` 用户气泡+摘要在末尾；Stop 乐观 UI；状态问答不继续改文件
- **下次：** **D9** PM 验收

## 2026-07-25 会话（扩展 D14–D36 全表交付）

- **实现：** Wave1–5 完成旁路 D14 + 扩展 D15–D36（含 Cap-D25 / headless D36）
- **下次：** **你验收** PM README 扩展表

## 2026-07-25 会话（扩展 D14–D36：D19）

- **Commit：** `3f3e66e`（D19）
- **实现：** `live_reasoning` WS 流 + AgentLiveActivity「思考」折叠；shell 输出 snippet
- **下次：** D26

## 2026-07-25 会话（扩展 D14–D36：D20）

- **Commit：** `94fdc8f`（D20）
- **实现：** Clutch Agent running 时消息入队 + Queue #n + 取消；idle 后 FIFO 发送
- **下次：** D19 → D26

## 2026-07-25 会话（扩展 D14–D36：D22+D27）

- **Commit：** `c68301b`（D22）、`a269764`（D27）
- **实现：** Usage dashboard + session 用量持久化；Explore 权限模式 + Chat 三键切换
- **下次：** D20+ 按 capability 表顺序（用户指定停于此）

## 2026-07-25 会话（扩展 D14–D36：D18 起）

- **Commit：** `518b8d0`（D18 斜杠命令）
- **下次：** D22 → D27 → … 按计划顺序

## 2026-07-25 会话（续：D43 Resources → 交验收）

- **实现：** resources/list+read；Hub Browse/Pin；prompt `mcp_resources` 层
- **下次：** 扩展表 D14–D36（用户要求都做）

## 2026-07-25 会话（续：D42∥D44 + D45）

- **Commit：** `24f0e31`
- **实现：** Agent 列表真工具名；Module 4 一键 local-fs；Epicode 文档标明 HTTP 未通
- **下次：** D43 → 交验收

## 2026-07-25 会话（续：D40 Chat MCP 徽章）

- **Commit：** D40 `724c26c`
- **实现：** `McpBindingBadge` + `agentMcpSummary`；未绑 CTA → Agent Manager
- **下次：** D42∥D44…

## 2026-07-25 会话（续：D39 传输诚实）

- **Commit：** D39 `092ee91`
- **实现：** SSE 禁用/API 拒注册；Env KEY=value；legacy SSE 标 unavailable
- **下次：** D40…

## 2026-07-25 会话（续：D38 Hub 探测）

- **Commit：** D38 `b2d8f49`
- **实现：** 去 UnderDevelopment 横幅；`POST /api/mcp/servers/test` + Hub「Test connection」
- **自测：** `pytest tests/test_mcp_probe_d38.py` → 5 passed
- **下次：** D39 → D40…

## 2026-07-25 会话（续：D52 门禁）

- **Commit：** D52 `1365f6d`
- **实现：** PRODUCT_INTRO Capability→Chat UI 表 + `check-capability-ui-table.sh` / INV-D52
- **下次：** MCP D38…

## 2026-07-25 会话（续：D51 Chat↔Terminal）

- **Commit：** D51 `ee4e2a2`
- **实现：** `chatTerminalSync` + 步骤/子任务「在 Terminal 查看」→ 右栏日志高亮 +（有 CLI 时）Terminal mode / lane focus
- **自测：** `pnpm test -- src/services/chatTerminalSync.test.ts` → 6 passed
- **下次：** D52 → MCP D38…

## 2026-07-25 会话（过夜：D8→D13 全交付）

- **用户授权：** 按序实现、自测、逐项 commit；明早人工点验
- **Commits：** D8 `7936786` · D9 `bef9b75` · D10 `25dc5dc` · D11 `59b45ee` · D12 `194d33a` · D13 _(本批)_
- **下次（人工）：** 打开 `runs/verification/pm-acceptance/README.md` 按 D08→D13 逐项点验；通过后再把 ROADMAP 标 ✅

## 2026-07-25 会话（D7 commit + D8 实现）

- **Commit：** D7 `af58e94`
- **D8：** `task_state` 层 + 压缩 digest 钉 Todo/Plan；Chat 仍有压缩摘要徽章
- **下次：** overnight commit 批次

- **实现：** Grok 对齐规则链 + 开放 Skills catalog + read_skill；Custom Mount 保留（D45）
- **PM：** 2026-07-25 通过（RULE_TOKEN_ORANGE；read_skill→SKILL_BODY_LOADED）
- **下次：** **D8 长聊不丢任务态**

## 2026-07-24 会话（D7 对齐 Grok Build 实现）

- **拍板（D45）**：Skills 开放 catalog；同名 project>custom>global；规则 git root→workspace 链；User 规则不做
- **实现：** `resolve_effective_skill_keys`；扩自动 Skills 路径；嵌套 AGENTS/rules；Custom Mount 永不卸
- **下次：** PM ✅

## 2026-07-24 会话（D6 Diff 审查 PM 通过）

- **实现：** Cursor 式 `fileDiff` 挂工具步骤 + `InlineFileDiffCard`；行级 append hunk；Changes 与 Diff 同源；`raw_path` 回归修复
- **PM：** 2026-07-24 通过（边改边出 alpha/beta Diff 卡）
- **Commit：** `26b9716`
- **下次：** D7 ✅

## 2026-07-24 会话（D5 自检报告 PM 通过）

- **实现：** `submit_verification` + seal `verificationReport` + `VerificationReportCardView`；todos 未完强制 failed；`_merge_patch` 放行 optional keys
- **PM：** 2026-07-24 通过（故意失败出 VERIFICATION FAILED 卡 + next actions）
- **Commit：** `30d5f86`
- **下次：** D6∥D50 ✅

## 2026-07-24 会话（D4 结构化提问 PM 通过）

- **实现：** `ask_user_question` + QuestionCard + 共享 `chatAgentCard`（Plan/Todo 对齐 UI_UX）；选项可点；路径 Redis→health→plan 一致
- **PM：** 2026-07-24 通过
- **Commit：** `662129c`
- **下次：** D5∥D50 自检报告 ✅ `30d5f86`

## 2026-07-24 会话（D4 结构化提问实现）

- **实现：** `ask_user_question` + pause `kind:question` + seal `questionCard` + `QuestionCardView`（选项点击）+ dock Cancel/自定义；非 risky 门
- **下次：** PM 验收（加缓存 → 选 Redis）→ commit → D5∥D50

## 2026-07-24 会话（D3 Todo PM 通过）

- **实现：** `todo_write`（免人工审批）+ live `agent_todos` + seal `todoList` + `TodoCardView`；计划步骤去重编号；审批气泡去重；Args 可展开；聊天滚过 dock；`max_steps` 24
- **PM：** 2026-07-24 通过
- **下次：** D4∥D49 结构化提问卡

## 2026-07-24 会话（D3 Todo 实现）

- **实现：** `todo_write` + live `agent_todos` + seal `todoList` + `TodoCardView`
- **下次：** PM 验收（多步 ≥3 todos 状态跟随）→ commit

## 2026-07-24 会话（D47 files_changed 芯片）

- **实现：** seal `filesChanged`；`FilesChangedChips` → D42 预览；Commit `3a9a951`
- **PM：** 2026-07-24 通过

- **验收：** Agent Manager「运行时提示词分层」可见；Plan/Ask 切换 mode 层；rules 跟工作区
- **ROADMAP：** D53 → ✅
- **Commit：** `9a840e2`

## 2026-07-24 会话（Workspace 历史消失 bug / D43）

- **现象：** 开发版一打开侧栏项目/历史空了（用户未删）
- **根因：** 随机 `workspace_id` + `workspaces.json` 被临时沙箱/非原子写污染 → 会话孤儿
- **修复：** 路径稳定 id + 加载迁移 remap history + 原子写 + 拒 ephemeral 授权 + `run-e2e.sh` 传 `CLUTCH_STORAGE_DIR`（D43）
- **数据：** 已手工恢复 ECC/test/clutch 旧 id；sidecar 启动会迁到稳定 id 并自动 remap
- **验证：** `pytest tests/test_workspaces_api.py` → 10 passed

## 2026-07-20 会话（Coding 发图 + 中间产物预览）

- **A1–D 已实现（D42）**
  - Chat：vision multimodal history 保留；非视觉 / Agnes `data:` 注入 Coding 专用 `image_analysis`（禁 Design 调色板硬约束）
  - Terminal OrchestratorBar：粘贴图片 chip + Loading；`POST /api/workspace/attachments`（`.gitignore *` + GC）
  - Chat/Terminal：路径/`[file:]`/fence/xterm 可点预览；`GET /api/workspace/file/resolve` 精确→basename 唯一
  - 文档：PRODUCT_INTRO / CHANGELOG Unreleased / FILEMAP / DECISIONS D42
- **验证：** `./scripts/verify.sh` → build OK，vitest 139，pytest 741 passed / 3 skipped，doc-drift 0 error

## 2026-07-17 会话（Trae CLI 白名单）

- **Trae CLI 白名单**：完整添加 trae-cli（binary: traecli v0.120.42）
- **路由配置**：`traecli -p --yolo`（--yolo = bypass permission checks，对标 Claude Code）
- **品牌 Logo**：Trae.svg（来自下载文件夹）
- **Commit**：`a595904`
- **验证**：vitest 136/136, pytest 730/734, build OK

## 2026-07-17 会话（Devin + Copilot 白名单）

- **Devin CLI 白名单**：完整添加 devin-cli（binary: devin v3000.1.27）
- **路由配置**：`devin -p --permission-mode dangerous`（对标 Claude Code）
- **GitHub Copilot CLI**：已有 CLI_CANDIDATES 条目，新增品牌图标、路由配置、推荐列表
- **品牌 Logo**：copilot.svg（来自下载），devin 复用 rivet.svg 作为默认图标
- **Commit**：`6ce426b`
- **验证**：vitest 136/136, pytest 730/734 (1 预存 keychain), build OK

## 2026-07-17 会话（comate 白名单）

- **Baidu Comate 白名单**：在所有注册表中添加 comate-cli 支持
- **路由配置**：binary=comate, extra_args=["chat"], prompt_flag=""（位置参数）
- **品牌 Logo**：百度.svg → tool-logos/comate.svg
- **推荐安装**：`curl -fsSL https://comate.baidu.com/install | bash`
- **Commit**：`65f23e6`
- **验证**：vitest 136/136, pytest 730/734 (1 预存 keychain), build OK

## 2026-07-17 会话（qodercli 白名单）

- **Qoder CLI 白名单**：在所有白名单注册表中添加 qoder-cli 支持
- **路由配置**：binary=qodercli, conversation_mode=separate, extra_args=['--dangerously-skip-permissions'], prompt_flag=-p
- **推荐安装**：`curl -fsSL https://qoder.com/install | bash`
- **品牌 Logo**：qoder.svg 已添加到前后端 assets
- **Commit**：`a14db2d`
- **验证**：vitest 136/136, pytest 730/734 (1 预存 keychain), build OK, doc-drift 0
- **API 测试**：tools/status 返回 qoder-cli (installed=true, registered=true, agentType=qoder-cli)
- **Terminal 模式**：CLI_BINARY_MAP、KNOWN_DISPATCH_AGENTS 均已注册，支持消息注入和 handoff

## 2026-07-16 会话（Approval Node 多选 422 修复）

- **诊断**：bec65d6 多选改造遗漏 — `workflows_dir()` 优先查找 gitignored `workflow_assets/` 旧副本，orchestrator 仍用旧 schema 拒绝数组 when
- **修复**：`routing.py` path_map 构建兼容 list when（展开）；`workflow_validator.py` 查找顺序调为源文件优先
- **Commit**：`b24442d`
- **验证**：vitest 136/136, pytest 730/734 (1 预存 keychain ACL), build ✓

## 2026-07-16 会话（Flow Next Flow 条件选择器多选支持）

- **EdgeWhen 多选化**：`edgeWhen` 从 `Record<string, EdgeWhen>` 改为 `Record<string, EdgeWhen[]>`，支持 `reject` + `retry` 同时指向同一节点
- **改动范围**：6 文件 — 类型定义、JSON Schema、编译工具、UI（多选 checkbox）、运行时编译器、测试
- **校验**：vitest 136/136，pytest 730/734（1 预存 keychain），doc-drift 0
- **Commit**：`bec65d6`

## 2026-07-16 会话（LLM Judge for check nodes）

- **LLM Judge 实现**：后端 `_llm_judge_check` 读取上游 `node_outputs`、调 LLM 判定 passed/failed；`_handle_check` 优先走 prompt 分支
- **Schema 更新**：check 节点 data 新增可选 `prompt` 字段，`checks` 改为非必填
- **前端适配**：`canvasToCompiler` / `compilerToCanvas` 双向映射 `prompt` ↔ `description`；弹窗 helper text + 自然语言 placeholder
- **校验**：vitest 136/136，pytest 730/731（1 预存 keychain），build ✓
- **Commit**：`ae84a9b`

## 2026-07-14 会话（强制颜色约束 + 多页面共享布局 + 前端节点抖动修复）

- **Prompt 颜色约束提权**：将「严禁随意用色」从仅 `md_text` 分支提升为全场景生效 — 禁止 Tailwind 默认颜色名（`bg-blue-*` 等）、禁止任意 hex 值、禁止无 spec 的渐变背景
- **多页面共享布局**：新增 `_build_shared_layout_context`，当 `screens_to_gen > 1` 时向 LLM 注入侧栏导航结构、颜色一致性、菜单项顺序约束
- **前端节点抖动修复**：`syncNodesFromSession` 新增 fingerprint 去重（id+position+phase+html），消除 poll 周期内 `applySession` + useEffect 双重 `setNodes` 导致的重复渲染
- **校验**：vitest 130/130，pytest 731/732（1 预存 keychain），doc-drift 零漂移
- **Commit**：`3aa748a`

## 2026-07-14 会话（Design 并行多页面生成 + 统一主题风格注入 — iterate_session 补齐）

- **iterate_session `action=="add"` 并发化**：将顺序 `for` 循环替换为 `ThreadPoolExecutor` 并发 worker（max 8 threads），与 `generate_session` 的 `_gen_screen_worker` 模式完全对齐
- **Tailwind 统一注入补齐**：
  - `iterate_session` add 路径：worker 内调用 `inject_unified_tailwind_config` 后再写盘
  - `iterate_session` modify 路径：`write_text` 前调用 `inject_unified_tailwind_config`，确保单页修改后风格一致
- **校验**：41 design tests 全绿，pytest 731/732（1 预存 keychain），doc-drift 零漂移，vitest 130/130
- **Commit**：`c2a772b`

## 2026-07-14 会话（一键原型 PRD — Phase 1 IUE 交互理解引擎）【本次会话】

- **IUE 模块创建**：`services/orchestrator/src/iue/` — 3 文件
  - `models.py`：ElementCandidate、ElementRole（17 roles）、TargetMatch、FlowSuggestion、ApprovalStatus
  - `engine.py`：`InteractionUnderstandingEngine` 6 阶段可插拔管道（候选识别→意图分类→目标匹配→置信打分→推理输出→审批门）
  - `__init__.py`：公共 API 导出
- **路由接入**：`routes/preview.py` — `/api/preview` 使用 IUE `analyze_to_dicts()` 返回结构化 flows（含 confidence/reason/role/status）；`/api/suggest_flows` 以 IUE 为主、LLM 为辅
- **测试**：5 个测试全绿（全管道、dict 兼容、Stage 2 分类、Stage 4 打分、空 board）
- **校验**：vitest 130/130，pytest 730/731（1 预存 keychain），doc-drift 零漂移
- **Commit**：`cc17c65`

## 2026-07-14 会话（一键原型设备外壳与外部 DOM 业务状态模拟器优化）

- **外部安全 DOM 业务状态操纵（无损修复文字溢出）**：
  - 彻底移除了 Iframe 源码中注入的 script 标签字串，消除任何因未闭合 HTML 标签或模板解析将代码解释为可见字符外露的隐患。
  - 改用外部 React 端在 iframe 的 `onLoad` 以及状态变化时直接操纵 `contentDocument` DOM 对象添加警告横幅、置红出错输入框、TextWalker 替换数据溢出等。
  - 为 `<iframe>` 沙箱配置了 `allow-same-origin` 以许可同源 DOM 访问，彻底解决了 state/extreme 变动不生效的同源阻断问题。
- **精确容器与变量极值匹配**：
  - 重构了 extreme mode 的变量匹配过滤规则，在文本遍历中直接过滤 `script` 与 `style` 节点，并且仅对数字和长字符变量追加测试，保留按钮标签等静态模板文字不变。
  - 智能检索画板中的表单或 main 卡片，将警告/错误横幅准确置于卡片顶部最内部，使布局完全符合项目视觉美感。
- **自定义下拉框与设备外壳拟真**：
  - 重构了左侧的“选择画板页面”下拉菜单为一致的 Clutch 高保真自定义 Dropdown，支持外圈 Hover、点击外部自动收起以及 ChevronDown 旋转微交互。
  - 为 Desktop 模拟器套上了带底座与立柱的电脑显示器外框，Tablet 套上了 iPad 外框，Mobile 套上了 iPhone 外框。
  - 扩容弹窗总体高度至 `700px`，并将模拟器内容高度增至 `510px`，并在 useMemo 中减去了硬件外壳的厚度冗余，防止任何溢出截断。
- **逻辑连线图 crash 修复**：
  - 引入了 `CheckCircle` 缺失 import，修复了逻辑连线图 Tab 白屏崩溃报错。
- **校验**：
  - 全量 `./scripts/verify.sh` 一键校验通过（726 个单元测试通过，零文档漂移）。

## 2026-07-13 会话（v1.2.6 发版准备）

- **版本号：** 已是 `1.2.6`（package.json / tauri.conf.json）。
- **CHANGELOG 更新：** 补充了 v1.2.6 遗漏的改动（Canvas zoom/pan fix, Vision model fallback degradation, Multi-screen generation, Progressive loading, Round history schema）。
- **Release doc 更新：** 重写 `docs/releases/v1.2.6.md` 覆盖全部 Shipped capabilities。
- **DELIVERABLES 补充：** 记录了 vision fallback (`e92961f`) 和 canvas zoom (`2b72508`) 两个 commit 的交付信息。
- **校验：** `verify.sh` 723 通过，`release-preflight.sh` INV-R1~R5 全部通过。

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

## 2026-08-01 会话（D38：design/generator Spec/UI/Iterate）

- **落地：** `gen_spec.py` / `gen_ui.py` / `gen_iterate.py`；`generator.py` 编排壳 + re-export
- **测：** `pytest tests/test_design_service.py tests/test_prototype_generator.py` 44 passed
- **下次：** ChatFeed hooks + bubble/dock

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
