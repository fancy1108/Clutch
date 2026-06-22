# Workflow Templates

内置 SOP 工作流（JSON）。字段定义以 **`workflow.schema.json`** 为权威；`docs/ARCHITECTURE.md` §6.2 为说明性文档。

| 文件 | 说明 |
|------|------|
| `workflow.schema.json` | JSON Schema（校验模板与编辑器导出） |
| `video-production.json` | 示例：视频生产流水线 |

编译目标：`services/orchestrator` 中的 `WorkflowCompiler`（待实现）。
