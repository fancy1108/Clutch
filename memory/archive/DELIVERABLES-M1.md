# Archive Notice

This file is archived and read-only.

Do not append new records here.

For current project state, see:

- memory/PROGRESS.md
- memory/DELIVERABLES.md
- memory/ROADMAP.md

Archived on: 2026-06-29
Reason: milestone M1 completed

---

# DELIVERABLES Archive — M1

- **日期：** 2026-06-22
- **Commit：** `f45172c` — feat(m1): add minimal LangGraph runtime and start_run API
- **Verification：** `uv run pytest tests/test_start_run.py tests/test_graph.py -v` — **仅**断言 `run_id` / 桩图 `n1`，未接 Compiler
- **证据：** `memory/TESTS.md` 7 passed → 15 passed（M1-01 后）
- **交付文件：**
  - `services/orchestrator/src/graph.py` — 最小 LangGraph（START→orchestrator→END）
  - `services/orchestrator/src/main.py` — `POST /api/runs/start`、`/stop`
  - `services/orchestrator/tests/test_start_run.py` — API smoke
  - `services/orchestrator/tests/test_graph.py` — 桩图节点断言

### M1-01 ✅
- **日期：** 2026-06-22
- **Commit：** `5367020` — feat(m1): add workflow JSON schema validation (M1-01)
- **Verification：** `uv run pytest tests/test_workflow_validator.py tests/test_validate_api.py -v` → 15 passed 总计
- **证据：** `memory/TESTS.md`；[CI #2](https://github.com/fancy1108/Clutch/actions)（`11e6d77` 前后）
- **交付文件：**
  - `services/orchestrator/src/workflow_validator.py` — 加载与校验 `workflows/*.json`
  - `services/orchestrator/src/main.py` — `POST /api/workflows/validate`；`start_run` 前置校验
  - `services/orchestrator/tests/test_workflow_validator.py` — Schema / video-production 用例
  - `services/orchestrator/tests/test_validate_api.py` — HTTP API 用例
  - `workflows/workflow.schema.json` — schema 小改

### M1-02 ✅
- **日期：** 2026-06-23
- **Commit：** `ea5e648` — feat(m1): add WorkflowCompiler for video-production JSON (M1-02)
- **Verification：** `uv run pytest tests/test_compiler.py -v` → 6 passed；`./scripts/verify.sh` → 21 passed
- **证据：** `runs/verification/2026-06-23-m1-02-compiler-pytest.log`
- **交付文件：**
  - `services/orchestrator/src/compiler/__init__.py` — 导出 WorkflowCompiler API
  - `services/orchestrator/src/compiler/compiler.py` — JSON → LangGraph 编译、五类 handler、条件边
  - `services/orchestrator/tests/test_compiler.py` — 节点/边/类型与 video-production.json 一致

---

### M1-03 ✅
- **Commit：** `3c45ad0` — feat(m1): wire start_run to WorkflowCompiler (M1-03)
### M1-04 ✅
- **Commit：** `dc904dc` — feat(m1): add orchestrator edge-first routing with LLM fallback (M1-04)
### M1-05 ✅
- **Commit：** `1dadde3` — feat(m1): push run_completed over WebSocket on terminal status (M1-05)
### M1-08 ✅
- **Commit：** `63e1bde` — feat(m1): add LLM Provider Router with DeepSeek default (M1-08)
### M1-09 ✅
- **Commit：** `7048999` — feat(m1): add user workflow persistence API (M1-09)
### M1-07 ✅
- **Commit：** `b6584ef` — feat(m1): add workflow graph structure validation (M1-07)
