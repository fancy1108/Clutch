# Workflow Templates

内置 SOP 工作流（JSON）。字段定义以 **`workflow.schema.json`** 为权威；`docs/ARCHITECTURE.md` §6.2 为说明性文档。

| 文件 | 说明 |
|------|------|
| `workflow.schema.json` | JSON Schema（校验模板与编辑器导出） |
| `video-production.json` | 示例：视频生产流水线 |
| `weather-to-vision.json` | 示例：天气调研与插画生成双 Agent 接力流水线 |

编译引擎：由 `services/orchestrator` 中的 `WorkflowCompiler` 进行解析并编译为 LangGraph 可执行图。
