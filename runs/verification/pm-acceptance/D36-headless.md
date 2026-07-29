# D36 — Headless / CI Clutch Agent · PM 验收

> **注意：** 本 D36 = Chat Agent 无 UI/CI 调用（≠ Design 模式 D36）。

## 目标
`POST /api/agent/run` 或 `python -m src.headless_cli` 跑同一 Clutch Agent 核心。

## 步骤
1. 授权工作区并配置模型。
2. API：`curl -X POST http://127.0.0.1:8124/api/agent/run -H 'Content-Type: application/json' -d '{"prompt":"say hi","workspace_path":"/path"}'`
3. 返回 `exit_code` + `output` + `run_id`。
4. CLI：`cd services/orchestrator && uv run python -m src.headless_cli -p "say hi" --workspace /path --json`

## 自动化
```bash
cd services/orchestrator && uv run pytest tests/test_headless_agent_d36.py -q
```

## 结果

- [x] Agent 代 PM ✅ 2026-07-25 — 自动化见 `AGENT-PM-2026-07-25.md`
