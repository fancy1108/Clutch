# Changelog

All notable changes to Clutch are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

**Version policy:** See [`docs/STABILITY.md`](docs/STABILITY.md) for semver and module stability levels.

**Release gate:** A version must have a matching `## [x.y.z]` section here before tagging or publishing a GitHub Release (`scripts/release-preflight.sh` INV-R5). See [`docs/document-governance.md`](docs/document-governance.md) §Release 硬门禁.

**Version snapshots:** Per-release product summaries live in [`docs/releases/`](docs/releases/) (historical); current product truth is [`docs/PRODUCT_INTRO.md`](docs/PRODUCT_INTRO.md).

## [Unreleased]

### Added

- **Chat Clutch Agent capability roadmap (D44):** Authoritative delivery table D0–D53 in [`specs/core/clutch-agent-capability-plan.md`](specs/core/clutch-agent-capability-plan.md) (adds **D53** layered runtime prompt + progressive disclosure); ROADMAP section + FILEMAP/AGENTS index.
- **Clutch Agent builtin tools (capability D1):** Default `clutch-tools` for Clutch Agent with an authorized workspace — `read_file`, `list_dir`, `grep`, `search_replace`, `run_terminal_cmd`, plus existing `apply_patch`. No Hub bind required for builtins.
- **Agent Manager MCP Hub binding (capability D37):** Clutch Agent edit Module 4 restores Hub server checkboxes; save persists `mcpServerIds` (no longer wiped). Detail pane lists bound servers.
- **Chat live tool activity (capability D46):** Clutch Agent / MCP ReAct tool trail uses a Grok-style **verb_group** fold (`Read 2 files, Searched 1 pattern`); expand for step titles/detail. Steps stream via `pending_tool_steps`, then **seal** onto the assistant message as `toolSteps` (survive refresh). Log parsing remains fallback only.
- **Layered runtime prompt (capability D53):** System prompt assembled as layers (system / env / protocol / workspace rules / skills catalog / plan-mode reminder). Skills default to name+blurb (full SKILL.md on demand). **Agent Manager** shows a Runtime prompt layers panel (refreshable); `GET /api/agents/{id}/prompt-assembly` returns the same summary. Agent Manager `markdownDoc` is the editable protocol segment only.
- **Chat files-changed chips (capability D47):** Paths from this turn’s `files_changed` seal onto the assistant message as `filesChanged`; Chat renders clickable chips (optional image thumbs) that open the existing workspace file preview (DECISIONS D42). Changes panel `file_changed` events unchanged.
- **Plan-before-edit + in-chat plan card (capability D2 + D49):** Builtin `propose_plan` pauses the ReAct loop; Chat shows a **Plan card** with Approve / Revise / Cancel. Writes resume only after Approve; Revise asks the agent to call `propose_plan` again. Trivial turns may skip the tool.
- **Chat todos (capability D3 + D49):** Builtin `todo_write` updates `agent_todos` live and seals `todoList` on the assistant message; Chat renders a Todo card (pending / in_progress / completed). While any item is incomplete during a run, the Todo card **sticks to the top** of the chat scroll area; when all items are checked it **unpins** and scrolls with the sealed bubble. Sticky and sealed Todo cards support **chevron collapse/expand** via shared `chatAgentCard` chrome (default expanded; collapsed header keeps title + `done/total`). `todo_write` is **not** a human-approval gate (UI state only). Plan steps strip model-supplied `1.` prefixes so cards do not show `1. 1. …`; tool-trail header no longer appends a redundant total count next to “Awaiting approval”. Live Working UI uses `pending_tool_steps` only (does not replay the previous turn’s `terminal_logs` wave on a trivial follow-up). Supervisor approval bubbles dedupe by `approvalKey`; plan cards no longer seal a frozen tool trail; ReAct `max_steps` raised to 24 so plan+todo+edits do not falsely hit the iteration wall. Approval Args render as expandable/scrollable JSON (not a 120-char ellipsis); chat list scroll padding clears the fixed Allow/Reject dock.
- **Structured question card (capability D4 + D49):** Builtin `ask_user_question` pauses ReAct for a real fork (e.g. Redis vs Memcached). Chat shows a **Question card** with option buttons; picking an option (or typing a custom answer in the dock) resumes with the selection. Cancel ends the turn. Uses its own pause path (not the generic MCP risk Allow gate).
- **Self-check verification report (capability D5 + D50):** Builtin `submit_verification` seals a **Verification report** card in Chat (steps + passed/failed). Failed reports include next actions; claiming passed while session todos are incomplete is forced to failed. **View changes** opens sealed changed files (D47 / D42 preview).
- **Diff review in Chat (capability D6 + D50):** Each successful edit streams a **Cursor-style per-file Diff card** into the Chat timeline immediately (filename + `+/-` hunks). Optional `submit_diff_summary` still publishes a multi-file review card. Coexists with the Changes rail.
- **Project rules + Skills (capability D7, Grok-aligned):** Workspace rules load along **git root → authorized workspace** (`AGENTS.md` / `CLAUDE.md` + `.grok/.claude/.cursor/rules`; deeper wins). Skills use an **open catalog** (enabled global ∪ project ∪ custom Search Paths, plus optional Agent binds; same-name **project > custom > global**). Full `SKILL.md` via `read_skill`. User-home AGENTS rules deferred. Activating a workspace rotates project skill mounts only — manual Search Paths stay.
- **Long-chat task state (capability D8):** Context compaction keeps a deterministic Todo/Plan snapshot in the digest and re-injects a `task_state` prompt layer each turn so「还剩什么」survives fold; Chat still shows the compaction digest badge.
- **Run control in Chat (capability D9):** Stop leaves a resume hint + **Continue** control; consecutive tool failures trip a **loop fuse** (env `CLUTCH_LOOP_FUSE_FAILURES`); Chat composer shows live **Steps n/m · ~tok** (`run_stats`).
- **Subtask delegation (capability D10 + D48):** Builtin `delegate_subtask` (`explore` | `implement`) runs a capped nested ReAct loop; parent Chat shows nested **Subtasks** cards (live + sealed) with status/summary and expandable steps.
- **Background commands (capability D11):** `run_terminal_cmd` supports `background=true` plus `list_background_jobs` / `kill_background_job`; Chat shows a **Background jobs** bar (view output / kill) while the foreground turn stays free.
- **Git + web fetch (capability D12):** Builtin `git_status` / `git_diff` / `git_commit` (commit is risky/approval) and `web_fetch` for URL text summarization; steps appear in the D46 tool trail.
- **Permission rules (capability D13):** Persist allow/ask/deny command patterns; dangerous shell (`rm -rf`, `sudo`, …) force-ask even in Full; Chat permission menu **Clear remembered approvals**.
- **Chat ↔ Terminal sync (capability D51):** Shell / execute tool steps and subtask cards expose **View in Terminal** — opens the right-rail Terminal tab, highlights the matching `[CHAT] Step` log line, and (when a CLI Terminal session is available) switches to Terminal mode and focuses the active lane.
- **Capability ↔ Chat UI gate (capability D52):** `PRODUCT_INTRO` ships a **Capability → Chat UI** table (D1/D10/D37 spot-check rows required); `scripts/check-capability-ui-table.sh` is wired into `check-doc-drift.sh` (INV-D52).
- **MCP Hub trusted status (capability D38):** Remove misleading Hub “under development” banner; per-server **Test connection** (`POST /api/mcp/servers/test`) returns tool count on success or a readable error on failure.
- **MCP transport honesty (capability D39):** Hub registration is **stdio-only** (SSE option disabled; API rejects new SSE registers); optional Env `KEY=value` lines on register; legacy SSE rows stay visible as unavailable.
- **Chat MCP binding badge (capability D40):** Clutch Agent Chat shows `N MCP · ~M tools` (popover with server names) or a **Bind MCP** CTA when Hub bindings are empty.
- **MCP Hub real tool names + one-click FS (capability D42∥D44):** Agent Manager catalog/detail show real Hub tool names (not fake permission chips); Module 4 **Enable workspace file tools** binds `local-fs` in one click.
- **MCP resources pin-for-Chat (capability D43):** Hub can **Browse resources** on stdio servers; **Pin for Chat** stores a text snapshot injected into Clutch Agent prompt layers (`mcp_resources`).
- **Ignore rules + strict sandbox (capability D21):** Builtin `list_dir` / `grep` / `read_file` respect workspace `.gitignore` and `.clutchignore`; ignored paths are omitted from listings/search and rejected on direct read. **Settings → General → Strict sandbox** rejects shell commands and paths that escape the authorized workspace with readable errors.
- **Usage dashboard (capability D22):** Click the D9 **Steps n/m · ~tok** strip to open a history panel (current run + recent sessions); sidecar persists `session_tokens` / `tool_steps` on session records when runs end or are touched.
- **Chat mode presets (capability D27):** Composer permission menu switches **Explore / Plan / Edit automatically** (`explore` / `plan` / `auto_edit`); Explore hard-blocks write/exec MCP tools while allowing read/search.
- **Agent busy message queue (capability D20):** While Clutch Agent / MCP plain chat is **running**, new sends enqueue above the composer with **Queue #n** position badges and per-item cancel; messages drain in FIFO order when the turn returns to idle.
- **Thinking stream (capability D19):** Models that return `reasoning_content` stream into the D46 **Agent live activity** fold as **Thinking / 思考** (same strip as tool steps). Long `run_terminal_cmd` output attaches as expandable step detail snippets.
- **Background job monitor (capability D26):** When a D11 background job finishes, fails, or is killed, Chat gets a **[Monitor]** Supervisor line; failures also raise a short composer toast.
- **Compact tool approval bar:** `awaiting_human` uses a slim Allow / Reject strip above the composer (optional note + Retry), replacing the large Human-In-The-Loop card.
- **Sidebar session spinner:** MCP approve/complete now updates session history status; active Coding rows follow live `clutchStatus` so finished chats stop spinning.

### Changed

- Removed redundant Explore / Plan / Implement pills above the Chat composer; the same modes remain in the permission menu.
- Clutch Agent system prompt documents clutch-tools usage.

Feature/patch release — **Coding image paste & click-to-preview**, Design handoff/Spec flow polish, workspace history stability.

### Added

- **Coding image paste (Chat + Terminal OrchestratorBar):** Clipboard/attach images from Clutch composers (not xterm). Chat always sends multimodal first; on vision soft-refuse / API reject, retries with local OCR/palette analysis. Local CLI agents (Mimo / Claude Code, …) get workspace file refs (`@path` / `[file:]`) instead of base64 on argv. Terminal uploads to `.clutch/attachments/` with `*` gitignore + size-triggered GC; send button Loading during upload.
- **Click-to-preview artifacts:** Chat paths / `[file:]` / `@path` / fenced code blocks open the App preview overlay (large content uses plain `<pre>`; **images open as media**). Terminal xterm + dispatch history linkify paths/filenames with workspace resolve (exact → unique basename fuzzy); missing/ambiguous shows toast. **Terminal Overview** shows attachment image thumbnails on dispatch records (click to enlarge).
- **Pillow + pytesseract:** Declared orchestrator dependencies for local image analysis / OCR fallback (system `tesseract` binary still required for OCR text).

### Changed

- **Design Spec→UI continuous by default (D40):** Prompt generates Spec then screens in one run — no confirm CTA. Opt-in pause with `CLUTCH_DESIGN_SPEC_CONFIRM=1` (`awaiting_spec_confirm` + Confirm Spec & Generate UI).
- **Design handoff SSOT (D39/D41):** Preview Demo → Coding stepped flow. **Generate** is a deterministic HTML→React export (no LLM redraw): real per-screen `.tsx`, prototype Tailwind CDN theme, contract Links in source. Preview scaled-to-fit + open full size → Approve → Send to Coding (wire APIs next).
- **Design Spec soft-confirm + flow discipline (D40):** Soft-confirm is opt-in (`CLUTCH_DESIGN_SPEC_CONFIRM=1`); brief enhance before Spec; declared iterate modes (Edit / Add / Variant / Revise Spec); async iterate + confirm-spec; HTML prompts allow semantic buttons/`data-clutch-id` for IUE.

### Fixed

- **Chat Thinking bubble height:** Typing indicator no longer mirrors the last user bubble (image messages made a huge empty box). Uses normal agent-bubble width + `min-h-9` (single-line reply height), not a `w-fit` pill.
- **Design “New Design” not at top of sidebar:** Clicking New Design reused an old empty draft (kept its `started_at` / history position). Always create a fresh session at the top and delete prior empty New Design drafts.
- **Design iterate stuck “Generating…” overlay:** Async Edit/Pick iterate left `drawing` true and round pin on after poll reached `ready`, so the artboard kept the spinner and could show stale HTML. Clear overlay + unpin to latest round when the session finishes.
- **Workspace list / session history desync (D43):** Project ids are now path-stable (`sha256` of resolved path); legacy random ids migrate on load and remap `history.json`. `workspaces.json` uses atomic replace. Default store refuses ephemeral `/tmp`-style authorize (tests must set `CLUTCH_STORAGE_DIR` / `CLUTCH_E2E_SANDBOX`). Desktop E2E passes `CLUTCH_STORAGE_DIR` into `tauri:e2e` so sandboxes cannot wipe `clutch_dev`.
- **Coding/Design image try-first:** Attached images are always sent to the LLM as multimodal first. Only when the model soft-refuses vision or the API rejects image input do we retry with local OCR/palette analysis (Coding uses a chat-specific fragment without Design hex mandates).
- **Agnes 2.0 Flash chat vision:** Agnes **chat** models are treated as vision-capable; clipboard pastes are attempted multimodally (no preemptive `data:` downgrade).
- **Chat vision history:** `_history_for_llm` no longer flattens multimodal user turns to `[image omitted]` when vision is enabled for the turn.
- **Sidebar session history for all workspaces:** Hydrate/load history for every project in the sidebar, not only the active one.

## [1.2.8] - 2026-07-16

> **感谢 [@MyloveAless](https://github.com/MyloveAless) 设计了完整的「AI 图片生成多 Agent 工作流」（7 节点：Aesthetic Architect → Prompt Stylist → Human Gate → Parameter Engineer → Check → Safety Specialist → Visual Generator），并在端到端测试中发现了多项流程阻断问题，推动了本轮全部修复。**

### Added

- **Check passed 消息可见化：** Check 节点通过时现在会显示 "Checks passed." 消息（status=COMPLETED, badge=PASSED），不再静默跳过，用户可明确感知校验环节已执行。
- **Agent_task 无条件并行扇出：** 编译器和前端统一支持 agent_task 节点最多 3 条无条件出边（之前编译器硬拒绝 >1 条，前端 canvas 兼容性检查也不允许），支持一个节点同时驱动多个下游并行执行。

### Changed

- **Human Gate 提示文案修正：** 从 "Validation checks did not pass" (FAILED / VALIDATION FAILED) 改为 "Awaiting human approval. Please review…" (PENDING / AWAITING APPROVAL)，不再让用户误以为是 Check 节点报错。
- **Evaluator / Supervisor / Builder 头像统一：** 工作流元 Agent 不再随机匹配 Cursor 或默认图标，统一使用 Rivet logo 作为头像标识。

### Fixed

- **Check/Gate 节点 end 汇聚不兼容修复：** `getCanvasIncompatibilities` 中 `end` 节点入度检查从 `endIn !== 1` 放宽到 `endIn < 1`，允许多路径汇聚到 end。
- **Agent_task 多出边放宽：** 移除 `agent_task` 节点 `branching_node`（out>1）限制，所有节点类型统一使用 `MAX_BRANCH_OUT=3` 出度上限。
- **Gate/Check 数据透明穿透：** 下游 agent_task 节点的直接上游如果是 human_gate 或 check，现在会递归向上查找真正的数据源（agent_task），而非把审批信号 "approve" 当作数据传入。修复了 3-Parameter Engineer 收到 "approve" 而非画面描述的问题。
- **Workflow step 状态防污染：** `buildWorkflowReplyStepIndex` 不再将 Evaluator / Supervisor 等元消息错误映射到 agent_task 步骤，修复了 1-Aesthetic Architect 被标记为 FAILED 的问题。
- **新建会话消息泄露：** 修复 WebSocket 竞态条件——旧 socket 关闭时先清除 onmessage 回调，并增加 runId 守卫，避免旧工作流的 state_patch 注入空白新会话。
- **brandLogos 别名过宽：** 移除 `agent: 'cursor-cli'` 通配别名，防止 Evaluator 等消息意外匹配到 Cursor logo。

## [1.2.7] - 2026-07-14

Feature release — **interactive prototype engine with visual connection editing and React code generation**.

> **Key features:** One-click interactive prototype, dual-mode preview/editor, SVG connection lines, drag-to-connect, thumbnails sidebar, interaction contract persistence, React code generation from contract.

### Added

- **IUE (Interaction Understanding Engine):** 6-stage pluggable pipeline that automatically infers navigation flows between design screens (candidate identification → intent classification → target matching → confidence scoring → Chinese reasoning → approval gate). 17 element roles, 5 matching methods, deduplication and noise filtering.
- **Clickable Interactive Prototype:** Preview mode where clicking buttons/links in the simulator iframe navigates directly to target screens, with browser-style back/forward history.
- **Dual-Mode Editor:** Pencil toggle switches between preview mode (click→navigate) and edit mode (click→context menu). Visual SVG connection lines drawn from hot zones in the simulator to target thumbnails in the sidebar.
- **Drag-to-Connect:** In edit mode, drag the target circle on a connection line to a different thumbnail to change the flow target. Click an unconnected element to start a new line and drop it on a thumbnail.
- **Thumbnail Sidebar:** Replaced the dropdown screen selector with scrollable thumbnail cards showing mini iframe previews and incoming/outgoing flow counts. Connection line endpoints follow sidebar scrolling with off-screen clamping.
- **Interaction Contract Persistence:** Auto-save user-edited flows to `.clutch/design/sessions/<id>/interaction_contract.json`. Loads on reopen, survives app restart.
- **React Code Generation:** One-click generation of a complete Vite + React 19 + Tailwind 4 project from the interaction contract. HTML→JSX conversion, onClick injection from contract flows, full project scaffold (App.tsx, screens/, package.json, vite.config.ts).
- **AI Prompt Copy:** Generated modal includes a pre-written prompt with contract path and code path, ready to paste to any AI coding agent.
- **Role-based Flow Inference:** IUE now infers flows for buttons without explicit target text (e.g., "Sign In" on a login page → Dashboard) via role-intent heuristics.
- **Extended Interactive Selector:** Edit mode detects nav items, menu items, and list elements in addition to buttons and links, enabling interaction editing on all UI elements.

### Changed

- PRD updated with §8 implementation reality section documenting design deviations and adjusted priorities.
- Code generation button moved to icon-only next to the pencil toggle in the simulator header.
- Connection line accuracy improved: keyword overlap threshold raised to ≥2 words, deduplication per (source, target) pair, low-confidence filtering.

### Fixed

- Preview API now uses authenticated `sidecarFetch` instead of bare `fetch`, fixing zero-flow results in Tauri desktop mode.
- Delete flow now properly removes click handlers and blue outlines via `onclick` replacement and `data-clutch-clickable` tracking.
- Add flow requires explicit source element text input, preventing empty matches.
- `generatingCode` `useState` moved before conditional returns, fixing "Rendered more hooks" React error.
- Copy Path and Copy Prompt buttons use separate state variables, preventing cross-interference.
- **Pick-mode element selection restored:** iframe sandbox reset to `allow-scripts allow-same-origin` after an earlier change dropped `allow-same-origin`, leaving the inline picker script in an opaque origin so `postMessage` never reached the parent — the hover outline still painted but clicks fell through to React Flow and could only select the whole board.
- **Design Modify iteration page type locked:** prompt and parser now refuse to change a screen's page type (e.g. login → dashboard) mid-iteration; the LLM is constrained to the original page identity.
- **Session history records preserved on load failure:** state-load errors no longer silently delete `sessions.json` records; failed loads return the prior state untouched.
- **Empty draft dedup is view-only:** deduplication of empty draft sessions no longer persists deletions back to disk — history deletion only happens via the explicit delete action.
- **Prototype toolbar polish:** an arrow separator was added between the Connections and Code buttons and the toolbar was right-aligned to match the simulator header layout.

## [1.2.6] - 2026-07-13

Patch release — **macOS + Windows**. Fixes CSP inline script restriction, Design mode canvas zoom over prototypes, vision model fallback for image-unaware LLMs, and ships multi-screen generation with loading animations and round transitions.

> **Release assets (v1.2.6):** Tag `v1.2.6` — **macOS:** `Clutch_1.2.6_aarch64.dmg` + `SHA256SUMS.txt` (CI `release.yml`). **Windows:** `Clutch_1.2.6_x64-setup.exe` + `Clutch_1.2.6_x64_en-US.msi` + `SHA256SUMS_WIN.txt` (CI `windows-build.yml`). Sidecar hotpatch asset (`sidecar-patch.json` + binary) published separately. Optional macOS updater via `Release (updater assets)` workflow (requires minisign key). Product snapshot: [`docs/releases/v1.2.6.md`](docs/releases/v1.2.6.md).

### Added

- **Design Round History Entry:** Added `model_usage` field to round_history entries.
- **Multi-Screen Iteration:** Design iterations (`"add"` mode) now parse multi-screen shorthand (e.g., "生成 Dashboard + 设置页面") via `_parse_multi_screens`, planning and registering all screens upfront with sequential round entries.
- **Multi-Screen Progressive Loading:** Multi-screen generate/iterate cycle now pre-populates placeholder screens in the manifest for smooth shimmer-animation loading sequences.
- **Screen Round Versions:** Each screen now carries its own `screenVersions` map and per-screen `roundIndex` tracking for correct versioned file paths across multiple screens.
- **Design Loading Optimizations:** Refined round history sync, shimmer animation stagger, and canvas layout positioning for smoother multi-screen UX.

### Changed

- **Design Round History Schema:** `round_history` entries now include `screen_id`, `html_path`, `prompt`, and `process_log` fields for richer round-level metadata.
- **Canvas Layout:** Multi-screen reference cards and new screen nodes are arranged horizontally in sequence from the rightmost position.

### Fixed

- **CSP Inline Script Block:** Added `'unsafe-inline'` to `"script-src"` inside `tauri.conf.json`'s CSP policies to permit component picking script execution inside `srcDoc` iframes.
- **Iframe body close tag check:** Made `</body>` tag detection case-insensitive inside `withPickerScript` to ensure the picker script is correctly appended.
- **querySelector ID safety:** Wrapped label querySelector in a `try/catch` block to prevent invalid CSS identifier syntax errors in element IDs from halting script execution.
- **Canvas Zoom/Pan Over Prototype:** Restored React Flow zoom/pan gestures when hovering over prototype iframe cards in the Design canvas.
- **Vision Model Fallback Degradation:** Design generation now gracefully degrades when the active LLM returns vision errors (e.g. "Cannot read image" — model lacks image input). Three independent fallback paths ensure results are produced instead of errors: (1) `_llm_complete_vision` detects error-like LLM responses and retries text-only with local image analysis; (2) `_generate_ui_html` detects vision errors inside generated HTML and drops the image on retry; (3) prompt construction only references attached images when they are actually sent (`image_attached` flag).

## [1.2.5] - 2026-07-13

Patch release — **macOS + Windows**. Fixes PyInstaller packaging config in `clutch.spec` to correctly bundle the `presets/` directory containing design system presets (like the Claude style spec cache) so they are available in production app builds.

> **Release assets (v1.2.5):** Tag `v1.2.5` — **macOS:** `Clutch_1.2.5_aarch64.dmg` + `SHA256SUMS.txt` (CI `release.yml`). **Windows:** `Clutch_1.2.5_x64-setup.exe` + `Clutch_1.2.5_x64_en-US.msi` + `SHA256SUMS_WIN.txt` (CI `windows-build.yml`). Sidecar hotpatch asset (`sidecar-patch.json` + binary) published separately. Optional macOS updater via `Release (updater assets)` workflow (requires minisign key). Product snapshot: [`docs/releases/v1.2.5.md`](docs/releases/v1.2.5.md).

### Fixed

- **Design Preset Packaging:** Updated `clutch.spec` PyInstaller packaging configuration to bundle the `src/design/presets` directory containing all design style specs and markdowns.
- **Preset loading validation test:** Added `test_builtin_presets_loading` to design service tests to ensure Claude, linear.app, and framer presets are successfully loaded.

## [1.2.4] - 2026-07-13

Patch release — **macOS + Windows**. Ships prototype Ready mode interactions, design round custom dropdown menu, Safari/WebKit picking remount fix, execution log fallback mapping, and Playwright computed CSS variable scraper bypass for CORS-restricted domains.

> **Release assets (v1.2.4):** Tag `v1.2.4` — **macOS:** `Clutch_1.2.4_aarch64.dmg` + `SHA256SUMS.txt` (CI `release.yml`). **Windows:** `Clutch_1.2.4_x64-setup.exe` + `Clutch_1.2.4_x64_en-US.msi` + `SHA256SUMS_WIN.txt` (CI `windows-build.yml`). Sidecar hotpatch asset (`sidecar-patch.json` + binary) published separately. Optional macOS updater via `Release (updater assets)` workflow (requires minisign key). Product snapshot: [`docs/releases/v1.2.4.md`](docs/releases/v1.2.4.md).

### Added

- **Ready mode interaction (Prototype):** Interactive events (hovers, typing, clicks) unlocked inside design preview iframes when not in picking mode.
- **Computed CSS Scraper fallback:** Scraper dynamically queries computed variables from container classes (e.g., `.sustainability-platform`) to bypass CORS restrictions on external stylesheets.
- **Tailwind Utility Filtering:** Scraper filters out framework utility variables (`--tw-*`, etc.) to prioritize true brand/theme tokens in LLM prompts.

### Changed

- **Design Round Dropdown menu:** Horizontal scrollable round selector bar converted to custom popover dropdown select menu matching Clutch's standard popup UI menus (supports Escape key and click-outside close).

### Fixed

- **Canvas Node sync glitch:** Consolidated React Flow sync hooks to eliminate layout race conditions and disappearing cards on round switch.
- **Safari/WebKit component picker:** Dynamic React key binding triggers clean iframe remounts on picking toggle, bypassing WebKit `srcDoc` caching bugs. Event hijacking blocked using `nodrag nopan` class overrides.
- **Agent Log execution fallback:** Restored execution steps in left-hand Agent Log cards when the backend updates histories without nested log arrays by scanning the global process log.

## [1.2.3] - 2026-07-12

Patch release — **macOS + Windows**. macOS: Apple Silicon DMG + in-app updater. Windows: MSI/NSIS. Ships native **handoff flow (D34)**, Design session isolation and layout fixes, and TUI injection reliability for Mimo/Claude/Codex CLI agents.

> **Release assets (v1.2.3):** Tag `v1.2.3` — **macOS:** `Clutch_1.2.3_aarch64.dmg` + `SHA256SUMS.txt` (CI `release.yml`). **Windows:** `Clutch_1.2.3_x64-setup.exe` + `Clutch_1.2.3_x64_en-US.msi` + `SHA256SUMS_WIN.txt` (CI `windows-build.yml`). Sidecar hotpatch asset (`sidecar-patch.json` + binary) published separately. Optional macOS updater via `Release (updater assets)` workflow (requires minisign key).

### Added

- **Handoff flow (D34):** Native `/handoff` PTY command injection — the source agent's PTY receives a `/handoff` command, generates a structured handoff file on disk, which the target agent's PTY picks up via general prompt injection and polling. Guarded by `is_handoff_skill_installed`. Multi-turn chat history context included in handoff summarization prompt. Steps refined: `generating_handoff` → `opening_terminal` → `injecting_goal` with per-step status in the Dispatch Log.
- **Sidecar hotpatch notes:** Version-range check in manifest (`min_app_version` / `max_app_version`); Notes and severity fields.

### Changed

- **Handoff summarization:** LLM timeout increased; summarization prompt includes full conversation history for richer context; TUI artifacts cleaned from summaries.
- **TUI warmup timing:** All heavy CLIs (opencode, mimo, codex, codebuddy, claude) use higher base warmup values; handoff warmup increased from 3200→3400ms for opencode, 4500→4700ms for ollama.
- **Design reference layout:** Reference cards moved from row 2 to row 1 (same row as Agent Log), sized to 300px.

### Fixed

- **Design session leakage (v1.2.2 regression):** `DesignWorkspace` keyed with `sessionRunId`; `applySession` guarded by runId filter; lane transcripts cleared on runId change; canvas state fully reset on switch — prevents stale UI cards and cross-session state corruption.
- **Design Chinese text garbled:** `ensureCharset` injects `<meta charset="utf-8">` into iframe `srcDoc` to fix garbled CJK characters in generated UI previews.
- **Handoff PTY race:** Polling timeout increased to 30s for slow LLM tool writes; `\r` used instead of `\n` for PTY command submission; `agent_display_name` import and `clean_type` resolution fixed.
- **Handoff source lanes:** Source lanes stay open during handoff generation and only collapse after the handoff dispatch completes.
- **CLI detection:** System daemon directories filtered out during active CLI scanning; system-wide running CLI processes counted correctly; ChatGPT.app fallback paths added for Codex CLI on macOS.
- **Claude CLI inject timing:** `isPtyOutputReadyForInject` now waits for prompt text (`> Ask a question`) instead of 24-char threshold — prevents premature injection before Claude CLI is ready.
- **Bottom padding:** Minimum 120px padding in ChatFeed for terminal layout to prevent input bar occlusion.

## [1.2.2] - 2026-07-11

Patch release — **macOS + Windows**. Ships Windows Design Preview / build parity (users can leave [v1.1.1](https://github.com/fancy1108/Clutch/releases/tag/v1.1.1)), plus workflow reliability fixes from community reports (#50–#55). Exception to the usual “patch = macOS-only” rule so Windows gets Design Preview in the same train as macOS.

> **Release assets (v1.2.2):** Tag `v1.2.2` — macOS `Clutch_1.2.2_aarch64.dmg` + `SHA256SUMS.txt` (CI `release.yml`); Windows MSI/NSIS via `Windows Build` workflow attached to the Release; optional macOS updater via `Release (updater assets)`. Product snapshot: [`docs/releases/v1.2.2.md`](docs/releases/v1.2.2.md).

### Fixed

- **ZCode CLI (#50 / #51):** Stop emitting unsupported `--session-id` / `--append-system-prompt`; use `history_only` and prepend system prompt into `-p` body (avoids exit-1 misclassified as “sign-in required”).
- **Agent config (#54):** Reject unknown `agentType` on save; warn when workflow `tool` disagrees with agent `agentType` (silent mis-routing).
- **Workflow JSON banner (#55):** When a flow is forced into JSON mode, the hint lists the offending node/edge ids (e.g. `human_gate`, conditional `when:`) instead of only a generic “complex workflow” message.
- **`check(file_exists)` (#53):** Outside-workspace absolute paths fail cleanly with a `FORBIDDEN` log (no crash); failed checks log the resolved workspace path so `/tmp/...` vs workspace-relative mismatches are obvious.
- **Human gate approve spam (#52):** Serialize `human_decision` per run, ignore duplicate clicks after the gate advances, clear stale `check_result` on approve, patch `status: running` during resume, and disable HITL buttons until status leaves `awaiting_human`.
- **Windows Design Preview:** Resolve `pnpm` / `npm` / `npx` through full executable paths, handle pnpm ignored-build policy for generated Vite previews, normalize install/start failures into `DesignError`, and kill the preview process tree on stop/timeout.
- **Windows Design sessions:** Retry atomic manifest replacement when Windows briefly locks `manifest.json` during async polling.
- **Windows Tauri build/dev:** `tauri:dev` uses the cross-platform Node launcher; Tauri `beforeBuildCommand` uses a Node sidecar-build wrapper that falls back to `python -m uv` or the orchestrator `.venv` instead of requiring bare `uv` on `PATH`.

## [1.2.1] - 2026-07-11

Patch release — **macOS only** (Apple Silicon DMG + in-app updater). Fixes Chat crash / Design footer & palette / Models connection false failures from v1.2.0, and ships **sidecar hotpatch** client (D37) for future backend-only patches. Windows users remain on [v1.1.1](https://github.com/fancy1108/Clutch/releases/tag/v1.1.1).

> **Release assets (v1.2.1):** Tag `v1.2.1` — **macOS only:** `Clutch_1.2.1_aarch64.dmg` + `SHA256SUMS.txt`; optional `latest.json` updater bundle. **This hotfix ships via full app update** (1.2.0 clients lack the hotpatch client). Product snapshot: [`docs/releases/v1.2.1.md`](docs/releases/v1.2.1.md).

### Added

- **Sidecar hotpatch (D37):** Silent download of a verified `orchestrator` binary into Application Support; Settings-adjacent **Update ready** chip; confirm → restart sidecar only. Manifest: `sidecar-patch.json`. See [`docs/UPDATES.md`](docs/UPDATES.md) §5.

### Changed

- **Updater download UI:** Progress pill shows MB downloaded (and total when known).
- **CSP:** Allow `release-assets.githubusercontent.com` for GitHub Release asset downloads.

### Fixed

- **Chat mode (v1.2.0 regression):** Clutch Agent plain chat crashed with `expected string or bytes-like object, got 'dict'` after Design mode changed `http_chat_complete` to return `{content, reasoning_content}`. Engine router and MCP/chat callers now unwrap via `LLMProviderRouter.extract_content` before sanitizing/displaying.
- **Design footer:** Switching into Design after Coding Terminal Orchestra no longer hides Model / Active Agent / Workflow (stuck `workspaceViewMode=terminal`).
- **Design welcome palette:** Restore design-system preset picker (was shipped as a disabled placeholder in v1.2.0; local WIP had the working control).
- **Models connection test:** Prefer fast OpenAI-compatible `GET /models` probe before a chat completion — Agnes 2.0 Flash can exceed 60s TTFT under load and was falsely marked CONNECTION FAILED in Settings.

## [1.2.0] - 2026-07-10

Minor release — **macOS only** (Apple Silicon DMG + in-app updater). **Design mode (D36)**, **ZCode CLI**, and Design Agent Log / generate reliability fixes. Windows users remain on [v1.1.1](https://github.com/fancy1108/Clutch/releases/tag/v1.1.1); next Windows installers target a later release.

> **Release assets (v1.2.0):** Tag `v1.2.0` — **macOS only:** `Clutch_1.2.0_aarch64.dmg` + `SHA256SUMS.txt` via CI; optional `latest.json` updater bundle. **No Windows installers** for this release. Product snapshot: [`docs/releases/v1.2.0.md`](docs/releases/v1.2.0.md).

### Added

- **Design mode (D36):** Header `Coding | Design` toggle; language moved to Settings → General. Design is a workspace session (`mode: design`), not a separate project rail. Two-phase generative flow: welcome prompt → infinite canvas → design-spec card first → UI card with draw animation → bottom NL iterate. **References:** paste/drop/attach image; upload **Design.md**; attach **website URL**. **Sidebar history** shows UI thumbnails + title + relative time. **Right rail** available in Design (default collapsed); artifacts under `.clutch/design/sessions/`. **Canvas selection** + element pick; iterate modify vs add; ⌘/Ctrl+C/V copy-paste UI. Session-scoped API; Approve → Vite/React/Tailwind → preview → Send to Coding. Built-in Clutch design-system preset; `design-to-code` workflow template.
- **Design Agent Log:** Canvas Agent Log card shows Thinking + Execution; each step carries **status**, **model**, and **token** tags (per-step history when the user switches models mid-session).
- **ZCode CLI (`zcode-cli`):** First-class routing for Z.AI ZCode headless agent (`zcode -p` + `--mode yolo` + `--json`), Terminal Orchestra `@ZCode` dispatch, session resume (`zcode --resume sess_...` / `zcode -c`), recommended Tools card with brand logo — contributed via [#43](https://github.com/fancy1108/Clutch/pull/43) by [@polaris-smart](https://github.com/polaris-smart).
- **Epicode memory workflow template** (`workflows/epicode-memory-pipeline.json`) and community MCP guide (`docs/mcp-servers/epicode.md`) — via [#22](https://github.com/fancy1108/Clutch/pull/22) by [@sunormesky-max](https://github.com/sunormesky-max).

### Changed

- **Dependencies:** lucide-react 1.23.0, @xyflow/react 12.11.2, motion 12.42.2, @xterm/addon-fit 0.11.0, tauri 2.11.5; Windows CI workflow aligned to `pnpm/action-setup@v6`.

### Fixed

- **Design UI code entry:** Bottom-bar **UI code** opens the Approve → Generate → Send to Coding tray on demand (no auto-open, no sky banner).
- **Design generate stuck Sketching:** Poll continues until screen HTML is present; busy tracks real UI hydrate; Design progress mirrors into the Terminal panel.
- **Design canvas blank artboard:** Empty/blank LLM HTML falls back to a prompt-aware draft; Tauri CSP allows `https://cdn.tailwindcss.com` for Design iframe Tailwind.
- **Design history:** Relative timestamps; gray placeholder until real UI exists; live HTML preview thumbnails; device badge updates immediately on Web/Mobile choice.
- **Design session folders:** Artifacts under `.clutch/design/sessions/{title}-{web|mobile}__{run_id}/`; deleting a session deletes the folder.
- **Design iterate:** Selecting a UI artboard defaults to modify in place; failed/identical LLM output falls back to an intent-aware draft.
- **macOS Dock:** PyInstaller sidecar no longer registers as a GUI app (single Dock icon).
- **Windows CI:** `test_scan_mimo_models_reads_cli_catalog` no longer depends on POSIX shell scripts on `PATH`.

## [1.1.2] - 2026-07-06

Patch release — **macOS only** (Apple Silicon DMG + in-app updater). **MiMo Code CLI** first-class integration, **Cursor Agent CLI** as a recommended tool, Terminal Orchestra dispatch fixes, and Claude Code CC Switch config repair in Settings. Windows users remain on [v1.1.1](https://github.com/fancy1108/Clutch/releases/tag/v1.1.1) until the next **minor** release (e.g. v1.2.0).

> **Release assets (v1.1.2):** Tag `v1.1.2` — **macOS only:** `Clutch_1.1.2_aarch64.dmg` + `SHA256SUMS.txt` via CI; optional `latest.json` updater bundle. **No Windows installers** for patch releases — Windows ships on minor bumps (1.2.0, 1.3.0, …). Product snapshot: [`docs/releases/v1.1.2.md`](docs/releases/v1.1.2.md).

### Added

- **MiMo Code CLI (`mimo-cli`)**: Whitelist detection (prefers `~/.mimocode/bin/mimo` over broken npm shims), headless routing (`mimo run --dangerously-skip-permissions`), Terminal Orchestra PTY + `@Mimo` dispatch, Settings → Models/MCP/Skills read-only scan tab, Xiaomi brand logo, and D19 doc sync.
- **Cursor Agent CLI recommended:** Added to default Tools/onboarding recommendations (`cursor-agent` / `agent`); brand logo and install guide.
- **Claude Code CC Switch repair:** Settings → Models (Claude Code tab) can detect and repair broken CC Switch config paths via sidecar API.

### Changed

- **Cursor CLI detection:** Tools scan now targets **Cursor Agent CLI** (`cursor-agent` / `agent` from `curl cursor.com/install`) instead of the IDE shell launcher (`cursor`).

### Fixed

- **Terminal session stats:** Background terminal count now reflects Clutch-managed PTY sessions only (no longer inflates with every system-wide CLI process).
- **Cursor Terminal Orchestra:** `@Cursor` dispatch is recognized in Orchestrator Bar (matches Cursor Agent CLI).
- **Chat thinking row:** Loading bubble matches the height of the preceding user message bubble (not the full row).
- **Homebrew cask:** `depends_on macos` uses symbol form (`:sonoma`) for current Homebrew.

## [1.1.1] - 2026-07-04

Patch release — **Windows interactive PTY** ([#30](https://github.com/fancy1108/Clutch/pull/30)), **platform chrome split**, and shared workspace UI polish. Thanks [@996wuxian](https://github.com/996wuxian).

> **Release assets (v1.1.1):** Tag `v1.1.1` — macOS DMG + `SHA256SUMS.txt` via CI; Windows MSI/NSIS via **Windows Build** workflow (manual attach to Release). Product snapshot: [`docs/releases/v1.1.1.md`](docs/releases/v1.1.1.md).

### Added

- **Windows Terminal Orchestra PTY:** Interactive lanes on Windows via WinPTY backend ([#30](https://github.com/fancy1108/Clutch/pull/30)).
- **Platform maintenance guide:** [`docs/PLATFORM_MAINTENANCE.md`](docs/PLATFORM_MAINTENANCE.md) — macOS / Windows file boundaries and shared `navConfig`.

### Fixed

- **General Settings font size:** Restored preference UI, persistence, root `data-font-size`, and custom `SettingsSelect` dropdown ([#30](https://github.com/fancy1108/Clutch/pull/30)).
- **Windows `tauri:dev`:** Cross-platform dev launcher via `node scripts/run-tauri-dev.mjs` ([#30](https://github.com/fancy1108/Clutch/pull/30)).
- **Chat workspace chrome:** Unified compact chat layout and 30px right supervision panel gutter on macOS and Windows.

### Changed

- **Workspace chrome (Windows):** Sidebar collapse on panel edge, icon-only collapsed rail ([#30](https://github.com/fancy1108/Clutch/pull/30)).
- **Platform chrome split:** `platform/chrome/*.{macos,windows}.tsx`, shared `navConfig.ts`, `data-platform` shell attribute; macOS keeps floating sidebar toggle and icon+label collapsed rail.

## [1.1.0] - 2026-07-03

Minor release — **Terminal Orchestra (D34)**, **Windows desktop polish**, **CodeBuddy CLI**, **OpenCode Zen**, **Agnes Video**, and agent-scoped Settings.

> **Release assets (v1.1.0):** Tag `v1.1.0` — macOS DMG, Windows MSI/NSIS, `latest.json` + signed updater bundle (macOS), `SHA256SUMS.txt`. Product snapshot: [`docs/releases/v1.1.0.md`](docs/releases/v1.1.0.md).

> **macOS 更新：** v1.0.2+ 用户可通过应用内横幅更新；v1.0.0 / v1.0.1 仍须先手动安装 v1.0.2+ 一次。详见 [`docs/UPDATES.md`](docs/UPDATES.md).

> **Windows：** 安装包由 CI 构建；维护者尚未在实体 Win10/11 上完成完整人工验收 ([#23](https://github.com/fancy1108/Clutch/issues/23))。

### Added

- **Terminal Orchestra (D34):** Terminal mode multi-lane PTY, OrchestratorBar dispatch (`@Agent` natural language + graph syntax), handoff files, Overview dispatch log, lane handoff overlay, float-rail collapse, completion draft queue, dispatch history on leave, and CLI session resume copy-paste commands.
- **Terminal mode CLI coverage:** Chat/Terminal toggle and embedded `INTERACTIVE_PTY` lanes support all connected CLI agent types (`*-cli`); Orchestrator `@` mentions align with routed tools (Codex, Aider, CodeBuddy, Rivet, Ollama, Antigravity, custom CLIs).
- **Orchestrator → PTY inject:** Dispatched tasks echo into the target lane xterm and auto-submit Enter.
- **Windows desktop polish:** Sidebar collapse, chat spacing, tab styling, global font-size preference, cached session snapshots, background WebSocket on session switch, and Windows Tauri dev/sidecar fixes ([#28](https://github.com/fancy1108/Clutch/pull/28)).
- **Agent-scoped capability tabs:** Settings → **Models**, **MCP Hub**, and **Skills Registry** use top tabs (**Clutch Agent** · **Claude Code** · **OpenCode**); CLI tabs scan native config read-only; CC Switch provider switch when `cc-switch` is on PATH.
- **Agent Manager clarity:** Skills/MCP modules branch by agent type; non-Clutch agents clear misleading Clutch bind fields on save.
- **CLI config API:** `GET /api/cli-config/{agent_type}/models|skills|mcp` and `POST .../activate-provider` for `claude-cli` and `opencode-cli`.
- **Agnes Video V2.0 (chat):** Built-in `agnes-video-v2.0` model; inline player + download; Chinese prompts auto-translated to English; authenticated media URLs for `<video>` playback.
- **Product website (GitHub Pages):** **https://fancy1108.github.io/Clutch/** — bilingual overview, install commands, contact.
- **README:** Terminal Session screenshot in bilingual README.
- **OpenCode Zen text models:** Built-in `opencode` provider in Settings → Models; five curated free chat models; optional catalog refresh; save-time connectivity checks.
- **CodeBuddy CLI:** First-class `codebuddy-cli` routing (`codebuddy -p` headless, `--resume` / `--session-id` session recovery).
- **Terminal lane grid pagination:** More than four expanded lanes show a dot carousel (4 lanes per 2×2 page).
- **Overview dispatch UX:** Loading badge (`Opening terminal…`) while target PTY boots or pending inject; dispatch timestamps in local timezone (backend stores ISO UTC).

### Changed

- **Terminal input dock:** OrchestratorBar uses the same fixed `bottom-8` layout as Chat, with measured gap equal to input bar height.
- **Terminal lane lifecycle:** Collapsed or paginated lanes stay mounted off-screen (xterm keepalive); PTY stays attached; xterm hydrates from transcript and force-repaints on show (no black screen on expand/collapse).

### Fixed

- **Dispatch labels:** Natural `@Agent` switch shows **User → Agent**; graph / file-ref dispatches show handoff.
- **Agnes Video playback:** `/api/workspace/media` accepts `?token=` when Bearer header is missing.
- **CLI session resume cards:** Copy-paste commands per agent type (`codex resume --last`, `opencode -c`, hide invalid Clutch UUID on unsupported CLIs).
- **Terminal inject dedupe:** Race no longer triple-echoes prompts into a lane.
- **Rivet branding:** Only Rivet uses the gray robot fallback icon in `@` picker.
- **Terminal lane black screen:** Collapse, pagination, or grid hide/show no longer disconnects PTY or wipes xterm canvas.
- **Overview dispatch pending:** `Opening terminal…` clears when PTY is `ready`, not stuck on lane `booting` label.
- **Ollama interactive PTY:** Spawn `ollama run <model>`; pass configured agent model on preview attach; surface spawn errors instead of stuck `detached`.
- **PTY prompt inject:** Antigravity/Ollama/OpenCode wait for TUI-ready output before typing; inject works on background lanes.
- **Handoff / Overview polish:** Preview modal empty section below title removed; optimistic dispatch in Overview; handoff Send-to-Bar graph syntax.
- **Chat/Terminal switch:** xterm stays mounted; right panel tabs Overview/Files/Changes/Terminal; terminal session command Copy restored.
- **Persisted run state:** Tolerate empty or corrupt run state files on hydrate.

## [1.0.3] - 2026-07-01

Minor release — **Hybrid shell pool queue**, **OpenCode CLI**, **Ollama settings fix**, **brand refresh**, and **maintainer real-connection E2E**.

> **Release assets (v1.0.3):** [GitHub Release](https://github.com/fancy1108/Clutch/releases/tag/v1.0.3) — macOS DMG, Windows MSI/NSIS, `latest.json` + signed updater bundle (macOS), `SHA256SUMS.txt`. Product snapshot: [`docs/releases/v1.0.3.md`](docs/releases/v1.0.3.md).

> **macOS 更新：** v1.0.2+ 用户可通过应用内横幅更新至 v1.0.3；v1.0.0 / v1.0.1 仍须先手动安装 v1.0.2+ 一次。详见 [`docs/UPDATES.md`](docs/UPDATES.md).

> **Windows：** 安装包由 CI 构建；维护者尚未在实体 Win10/11 上完成完整人工验收 ([#23](https://github.com/fancy1108/Clutch/issues/23))。

### Added

- **Hybrid shell pool queue (plain chat):** When all Hybrid shell slots are busy, new sessions **queue globally (FIFO)** with input-bar blocker UI (agent avatars + queue position); auto-resume when a slot frees — replaces Supervisor `pool_full` reject for plain chat.
- **Same-session pending message queue:** Send while a Hybrid turn runs; messages appear as **待发送消息** and drain in order after the current turn.
- **OpenCode CLI:** First-class `opencode-cli` routing (Hybrid shell when `CLUTCH_RUNTIME_MODE=hybrid`).
- **Built-in Agnes 2.0 Flash** chat model preset.
- **Real-connection E2E acceptance** (`./scripts/verify.sh --e2e-real`): 13 desktop cases including same-session queue (Q1) and cross-session pool queue (P1).
- **Install scripts:** `scripts/install.sh` (macOS curl DMG) and `scripts/install.ps1` (Windows NSIS); Homebrew tap [fancy1108/homebrew-clutch](https://github.com/fancy1108/homebrew-clutch).
- **Docs:** Bilingual README, [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md), [`docs/RELEASE_MAINTAINER.md`](docs/RELEASE_MAINTAINER.md).

### Changed

- **Brand / app icons:** Refreshed Clutch mark SVGs and regenerated Tauri desktop icon set (full-bleed black, no Dock white edges); `BrandLogo` shows mark on black background.
- **In-app update UI (macOS):** Compact **Update / Later / Restart** pill on the sidebar footer row beside Settings (`BTN_PRIMARY`); download shows spinner + percent.
- **Settings → Models Config (Ollama):** Model list reflects **local `ollama list`** tags; persisted `active_model_id` from another machine falls back to first installed tag (`models_config.py`).
- **CLI error copy (#19):** Hybrid → legacy fallback no longer double-prefixes failure text; 529 / 5xx gateway errors show clearer busy/unavailable message (`engine_router.py`).
- **README & onboarding:** Latest release v1.0.3; install pin examples updated.

### Fixed

- **Hybrid pool queue stuck:** Drain retry on slot release, WS refresh of blocker metadata, re-enqueue on handler failure (`plain_chat_pool_queue.py`).
- **E2E dev deps:** Playwright kept available for acceptance runs without bloating normal dev builds.

## [1.0.2] - 2026-07-01

Minor release — **Windows installers**, **in-app updates (macOS)**, **macOS sidecar lifecycle fix (#18)**, and **expanded CLI tool discovery (incl. Rivet)**.

> **Release assets (v1.0.2):** [GitHub Release](https://github.com/fancy1108/Clutch/releases/tag/v1.0.2) — macOS DMG, Windows MSI/NSIS, `latest.json` + signed updater bundle (macOS), `SHA256SUMS.txt`. Product snapshot: [`docs/releases/v1.0.2.md`](docs/releases/v1.0.2.md).

> **Windows 说明（v1.0.2）：** MSI / NSIS 安装包由 GitHub Actions CI 构建并通过自动化测试；**维护者尚未在实体 Windows 10/11 机器上完成完整人工验收**。若 Release 页附 Windows 资产，请优先核对 SHA-256 与来源；遇到问题欢迎 [开 Issue](https://github.com/fancy1108/Clutch/issues/new/choose)。macOS DMG 仍为本次主要发布与 smoke 路径。

> **macOS 更新说明：** v1.0.0 / v1.0.1 用户须**手动安装 v1.0.2 一次**；之后可通过应用内横幅自动更新。详见 [`docs/UPDATES.md`](docs/UPDATES.md) · [`docs/INSTALL.md`](docs/INSTALL.md) §3。

### Added

- **Windows desktop distribution:** Windows 10/11 x64 MSI and NSIS installers, ConPTY-backed Hybrid sessions, cross-platform MCP/file-lock handling, and Windows Credential Manager storage for provider API keys.
- **Windows build automation:** Manual/PR workflow builds and uploads Windows installer artifacts.
- **In-app updates (OSR-20):** Tauri `plugin-updater` + update banner; `release-updater.yml` for signed update assets; **go-live on v1.0.2** — see [`docs/UPDATES.md`](docs/UPDATES.md).
- **CLI tools (Rivet + whitelist):** Expanded Agent CLI discovery — installed tools always shown; curated install guides for uninstalled CLIs; **Rivet** headless routing via `rivet-cli` with `RIVET_FORCE_RECOVERY_CLI=1`.

### Changed

- **Tool Settings:** 20+ CLI whitelist scan; uninstalled tools default to Clutch-verified recommendations (`claude`, `ollama`, `codex`, `agy`) with install hints.

### Fixed

- **macOS restart / Dock (#18):** Tauri shell kills sidecar on exit, clears stale `orchestrator` on launch, and restores the main window on Dock reopen after closing the window (red button).
- **Rivet CLI (nvm/npm):** Sidecar prepends Rivet’s `bin` directory to `PATH` so `#!/usr/bin/env node` works when the packaged app lacks nvm in its environment (exit 127).

### Changed (packaging)

- **Release hardening (OSR-16):** Packaged sidecar disables `GET /api/runs/{run_id}/debug` and OpenAPI docs unless `CLUTCH_DEBUG_API=1`; WebView Content-Security-Policy in `tauri.conf.json` (production + `devCsp` for Vite HMR).
- **Sidecar distribution (OSR-17):** PyInstaller bundle ships with `console=False` (no terminal window on macOS).

### Added (docs)

- Document lifecycle governance: Source of Truth table, event-driven update matrix, and `memory/archive/` rotation with read-only Archive Notice on all archived files.

## [1.0.1] - 2026-06-30

Patch release — fixes packaged-app **Models Config** connectivity and macOS Keychain prompt spam. **Upgrade recommended** for all v1.0.0 DMG users.

### Fixed

- **Generated images blank in chat (packaged app):** Agnes returns CDN URLs (`*.agnes-ai.space`), not base64; WebView CSP blocked those hosts. Sidecar now downloads the image and embeds a `data:` URI in chat replies.
- **Release CI sidecar HTTPS broken:** GitHub Actions bundled python.org CPython 3.11.9 (old OpenSSL); outbound model API calls failed in the DMG. Release workflow now uses uv-managed Python 3.11 only.
- **Models Config red error (packaged app):** PyInstaller sidecar crashed on `GET /api/models/config` when Keychain read failed — logging used reserved LogRecord field `message` → HTTP 500; UI misreported as “Cannot reach Clutch sidecar”.
- **Sidecar session token (OSR-08):** Tauri ACL now exposes `clutch_sidecar_token` to the main webview; authenticated fetch retries once on 401.
- **Keychain prompt spam:** Read keys via `security find` with `-A` ACL migration (one-time per machine); avoids repeated prompts on adhoc-signed sidecar rebuilds.
- **Error copy:** Models UI distinguishes unreachable sidecar vs unauthorized session vs server error; `CLUTCH_DEBUG=1` surfaces raw connection errors.

### Changed

- PyInstaller sidecar bundles `keyring` for macOS Keychain on packaged builds; `upx=False` in `clutch.spec`.
- Right-panel **Flow** tab stays visible in multi-agent mode (empty state when no workflow selected).
- WebView CSP allows Agnes image CDN hosts as fallback.

### Known limitations (v1.0.1)

- macOS DMG remains **unsigned** (same as v1.0.0); Gatekeeper workaround unchanged.
- First Models load after install may still take ~10–15s while macOS Keychain grants access — click **Always Allow** when prompted.

## [1.0.0] - 2026-06-29

First public release — unsigned macOS DMG via [GitHub Releases](https://github.com/fancy1108/Clutch/releases/tag/v1.0.0). Snapshot: [`docs/releases/v1.0.md`](docs/releases/v1.0.md).

### Added

- **Desktop app (Tauri 2 + React 19):** Multi-agent workflow supervision — visual Flow editor, real-time Chat/Terminal, human approval gates, Files/Changes/Diff panels, session history, and workspace authorization.
- **Hybrid Runtime (D25):** Plain-chat CLI execution via persistent shell sessions (Claude Code and compatible CLIs), session snapshots, and hybrid audit logs.
- **Flow refine:** After a workflow completes or stops, `@Agent` feedback and `/continue` to revise outputs without restarting the full graph.
- **Models & tools:** Provider configuration UI, CC Switch import, Ollama local routing, MCP hub, Skills registry, theme and i18n (EN/ZH) preferences.
- **First-run onboarding wizard (OSR-14):** Seven-step setup — health check, workspace, models, tools, Flow intro, permissions summary, ready.
- **macOS Keychain for API keys (OSR-13):** Provider keys stored in Keychain (`com.clutch.app`); legacy plaintext keys in `models.json` migrated on load (`CLUTCH_USE_KEYCHAIN=0` to opt out).
- **Sidecar session token (OSR-08):** HTTP and WebSocket require a per-launch token from Tauri; `/health` remains public; E2E sandbox bypass documented.
- **Release CI (OSR-12):** Tag-triggered DMG build, gitleaks preflight, `SHA256SUMS.txt`, and `scripts/release-preflight.sh` sensitive-path gates.
- **User & contributor docs:** [`docs/INSTALL.md`](docs/INSTALL.md), [`docs/DATA_AND_PRIVACY.md`](docs/DATA_AND_PRIVACY.md), [`docs/BUILD_FROM_SOURCE.md`](docs/BUILD_FROM_SOURCE.md), [`docs/PRODUCT_INTRO.md`](docs/PRODUCT_INTRO.md), README product screenshots.
- **Community & governance:** MIT [`LICENSE`](LICENSE), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md), GitHub Issue/PR templates, `scripts/doctor.sh`, and open-source boundary docs (`PROJECT_SCOPE`, `STABILITY`, `EXTENSIBILITY`, `GOVERNANCE`, `PERFORMANCE`).
- **Secret scanning (OSR-07):** gitleaks workflow on push/PR.
- **Message compaction (B-03):** Long-session token folding with original messages archived to `runs/archive/{run_id}.jsonl`.

### Changed

- **Semver starting point `1.0.0`** for open source and DMG distribution (D31: unsigned DMG acceptable without Apple Developer account).
- **Default multi-agent mode:** Single/Multi toggle removed from UI; sessions default to multi-agent supervision.
- **CLI permission policy (OSR-09 / D30):** Claude CLI continues to use `--dangerously-skip-permissions` by default; documented in README and SECURITY (disclosure, not runtime gate).
- `experiments/pty_poc/runs/` is local-only (gitignored).

### Security

- Sidecar binds to localhost; session token required for API/WS after app launch.
- API keys prefer macOS Keychain over plaintext `models.json`.
- Release preflight blocks tracked `models.json`, `.env`, and Application Support paths from git.
- High-risk MCP tools require supervisor approval before execution.

### Known limitations (v1.0.0)

- macOS DMG is **not** Apple-notarized (OSR-11 deferred).
