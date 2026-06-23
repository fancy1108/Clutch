# FAILURES（防坑手册）

> 任何导致回滚或浪费超过 10 分钟的问题必须记录。  
> 新会话启动时，在读 `PROGRESS.md` 之后立即读本文件。

## 格式说明

- `[OPEN]` — 尚未解决，会话中须避开或标注风险
- `[RESOLVED]` — 已解决；**必须**同步补一行到 `CLAUDE.md` §已知陷阱

## 活跃问题（尚未解决）

（暂无）

## [OPEN] M1-06 阻塞：`WorkflowDef/steps` 与编译器 `nodes/edges` JSON 无映射规范

- **现象：** `WorkflowOrchestration.tsx` 使用 Prototype 的 `WorkflowDef` + `WorkflowStep`（含 `nextSteps`）；Sidecar / Compiler 使用 `workflows/*.json` 的 `nodes` + `edges`（含 `agent_task` / `check` / `human_gate` / `end` 类型）
- **影响：** M1-06「编辑器读写真实 JSON」无法在不猜测转换规则的情况下实现
- **规避：** M1-09 后端 CRUD API 已就绪；模板可通过 API 读写 compiler JSON
- **解除条件：** 在 `specs/` 或 `DECISIONS.md` 明确 UI 模型 ↔ compiler JSON 的转换规则，或重构编辑器直接编辑 compiler JSON

## [OPEN] M0-05 阻塞：本机无 Rust 工具链

- **现象：** `cargo` / `rustc` 未安装；无法运行 `pnpm tauri dev` 验收 M0-05
- **影响：** Tauri Sidecar 生命周期 task 无法在本环境完成 Verification
- **规避：** Sidecar 仍可通过 `cd services/orchestrator && uv run uvicorn src.main:app --reload --port 8123` 手动启动；`pnpm dev` 前端开发不受影响
- **解除条件：** 安装 Rust（https://rustup.rs）后执行 `pnpm tauri init` / 补全 `src-tauri/` Rust 工程并实现 Sidecar spawn

## 已解决问题（经验库）

（暂无）
