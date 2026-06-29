# Archive Notice

This file is archived and read-only.

Do not append new records here.

For current project state, see:

- memory/PROGRESS.md
- memory/DELIVERABLES.md
- memory/ROADMAP.md

Archived on: 2026-06-29
Reason: D25 Hybrid Runtime (HRT) milestone completed

---

# DELIVERABLES Archive — HRT

## 已交付（文档 / 计划 · 无代码 commit）

### HRT-00 ✅ 计划与文档对齐
- **日期：** 2026-06-27
- **Commit：** `7221641` — docs(hybrid): add HRT execution plan and sync memory/specs (HRT-00)
- **Verification：** `./scripts/check-doc-drift.sh` → 0 errors
- **证据：** —
- **交付文件：**
  - `specs/core/hybrid-runtime-plan.md` — D25 权威 HRT Task 表 + 验收 + 文档矩阵
  - `specs/core/tasks.md` — §D25 HRT 索引
  - `memory/ROADMAP.md` — §D25 Hybrid + 人工验收勾选
  - `memory/DECISIONS.md` — D27 命名拆分 · D28 审计 · Q-HRT-1/2
  - `memory/PROGRESS.md` — HRT 进度快照 + 下次优先
  - `memory/FILEMAP.md` · `memory/BACKLOG.md` · `docs/document-governance.md` · `AGENTS.md` · `docs/research/pty-session.md` — 交叉引用

### HRT-01~03 ✅ 气泡过滤 · marker · snapshot 注入范围
- **日期：** 2026-06-27
- **Commit：** `1d281f6` — fix(hybrid): tighten marker detection and snapshot handoff scope (HRT-01~03)
- **Verification：** `uv run pytest tests/test_claude_hybrid_output_parser.py tests/test_engine_router.py -q` → 27 passed
- **证据：** —
- **交付文件：**
  - `services/orchestrator/src/claude_hybrid_output_parser.py` — 过滤 snapshot 行；marker+clutch$ 完成检测
  - `services/orchestrator/src/engine_router.py` — context_prefix 仅 shell_recovered 时注入
  - `services/orchestrator/tests/test_claude_hybrid_output_parser.py` — snapshot / marker 单测

### HRT-04 ✅ 单 session Plain Chat 产品验收
- **日期：** 2026-06-27
- **Commit：** `53c4829` — docs(hybrid): record HRT-04 single-session acceptance pass (A–E)
- **Verification：** 用户人工验收 A–E 全部通过
- **证据：** `runs/verification/2026-06-27-hrt-04-acceptance.md`
- **交付文件：** —
- **依赖 commit：** `1d281f6` · `848ed7f`

### HRT-10 ✅ POC 验收 #6 / #10 自动化
- **日期：** 2026-06-27
- **Commit：** `5e1491d` — test(hybrid): automate POC acceptance #6 and #10 (HRT-10)
- **Verification：** `./scripts/verify-hybrid-poc-06-10.sh` → 8 passed；`./scripts/verify.sh` → 378 pytest + 14 vitest + build（`test_mcp_client_lifecycle` 偶发 flake，单跑通过）
- **证据：** —
- **交付文件：**
  - `services/orchestrator/tests/test_hybrid_poc_acceptance.py` — BUSY 拒绝、池满、hybrid 无 legacy fallback、双 run_id PTY/cwd 隔离
  - `scripts/verify-hybrid-poc-06-10.sh` — 一键跑 HRT-10 验收用例

---

