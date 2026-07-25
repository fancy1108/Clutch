# Cap-D25 — 扩展 D25（scheduler）定时/循环任务 · PM 验收

## 目标
可创建间隔任务（默认关/需确认）；列表/删除；触发时通知或跑一轮 Chat Agent。

## 步骤
1. Chat 输入栏上方点 **Scheduled tasks** 展开面板。
2. 输入 prompt + 间隔（≥30s），点 **Add**（默认 **off**）。
3. `GET /api/scheduled-tasks` 或 UI 列表可见新任务。
4. 启用需 `POST .../enable` 或创建时 `confirm=true`。
5. 到点后 sidecar 日志/通知；若 `run_agent_turn` 则触发 headless 一轮。
6. **Delete** 移除任务。

## 自动化
```bash
cd services/orchestrator && uv run pytest tests/test_scheduled_tasks_cap_d25.py -q
```
