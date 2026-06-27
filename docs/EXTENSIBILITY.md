# Clutch — 扩展性边界

> **读者**：希望集成、插件化或 fork 扩展的开发者  
> **问题**：「我应该改哪里？」「PR 改整个 Runtime 会被接受吗？」  
> **状态**：草案 v0.1（2026-06-27）

---

## 1. 设计原则

1. **扩展优先走数据与协议**，而非 fork 核心运行时。  
2. **官方扩展点** 有文档、有测试、有稳定性标签（见 [`STABILITY.md`](./STABILITY.md)）。  
3. **内部实现** 欢迎阅读学习，但不接受「替换整套状态机」类上游 PR。

---

## 2. 官方支持的扩展点

| 扩展点 | 方式 | 稳定性 | 入口 / 参考 |
|--------|------|--------|-------------|
| **Workflow 模板** | JSON 文件 | Beta → Stable | `workflows/*.json`、`workflow.schema.json` |
| **用户工作流** | UI 导出 / `POST /api/workflows/user` | Beta | Settings → Workflows |
| **MCP Server** | 用户配置 stdio/SSE 服务 | Beta | Settings → MCP；`mcp_storage.py` |
| **内置虚拟工具** | `clutch-tools__*`（如 `apply_patch`） | Beta | `builtin_tools.py` |
| **Model Provider** | Settings 配置 + `models.json` | Beta | `llm/router.py`、`ModelsManager` |
| **自定义模型** | Custom model API | Beta | `custom_models.py` |
| **Agent 定义** | Agent JSON（角色、工具绑定、引擎） | Beta | Settings → Agents |
| **CLI 引擎** | 注册 CLI Adapter（claude、agy、ollama…） | Internal→Beta | `adapters/*`、`engine_router.py`（**贡献需与维护者对齐**） |
| **Skills 挂载** | 路径注册 | Beta | Settings → Skills |
| **主题 / 语言** | Preferences API | Experimental | `preferences_storage.py` |

### 推荐扩展路径（由易到难）

```
1. 新建 Workflow JSON（复制模板改节点）
2. 接入 MCP Server（零 Clutch 代码）
3. 配置 Agent + 选择引擎/模型
4. 贡献新的 CLI Adapter（需 pytest + 文档，见 CONTRIBUTING）
5. Fork 并替换 Engine Router（上游不接受，见 §3）
```

---

## 3. 内部实现（请勿依赖 / 勿直接 PR 替换）

| 区域 | 路径 | 为何 Internal |
|------|------|----------------|
| **Workflow Compiler** | `compiler/compiler.py` | LangGraph 图构建细节频繁变 |
| **LangGraph 运行时** | `workflow_runtime.py`、`agent_executor.py` | 编排 SSOT |
| **Engine Router** | `engine_router.py` | Hybrid / legacy 路由策略 |
| **Shell / PTY 会话** | `shell_session.py`、`shell_exec_runtime.py` | 安全与并发敏感 |
| **前端状态投影** | `clutchState.ts`、`App.tsx` WS 处理 | 非公共 SDK |
| **React Flow 编辑器内部** | `WorkflowOrchestration.tsx` 等 | UI 实验性强 |

### 通常 **不会合并** 的 PR 类型

- 用另一套编排引擎替换 LangGraph  
- 重写全局状态管理（Redux / 自研 store 替代 WS 投影）  
- 在 core 中硬编码特定公司/项目的 Workflow  
- 未经讨论的 **云服务**、**遥测**、**账号体系**  
- 绕过工作区白名单的「全局文件访问」  

详见 [`GOVERNANCE.md`](./GOVERNANCE.md) §4。

---

## 4. 扩展点详解

### 4.1 Workflow JSON

- **Schema**：`workflows/workflow.schema.json`  
- **校验**：`POST /api/workflows/validate`  
- **编译**：Sidecar 启动时加载；用户工作流存 `Application Support/clutch/workflows/user/`  

扩展节点类型前，请先开 Issue 讨论 Schema 变更（属公共契约）。

### 4.2 MCP

- Clutch 作为 MCP **客户端** 连接用户声明的服务器。  
- 工作区文件系统 MCP 需先 **授权工作区**。  
- 风险工具受 `permission_mode` 与 `human_required` 门控（`mcp_react.py`）。

### 4.3 Model Provider

- 通过 `LLMProviderRouter` 注册 Provider。  
- 新 Provider 贡献需：环境变量或 Settings 文档、`http_complete` 路径、pytest。

### 4.4 CLI Adapter

- 统一由 `engine_router.route_engine()` 分发。  
- 新 CLI 需：adapter 模块、Hybrid 策略说明、可选 PTY 支持评估。  
- **不是**「任意 shell 字符串」插件系统；受 Workspace 与权限模式约束。

---

## 5. Fork 指南

若官方扩展点不够用，**fork 是正当路径**：

| 目标 | 建议 |
|------|------|
| 私有 SOP 平台 | Fork + 自定义 Workflow 模板 |
| 企业内网 CLI | Fork + 内部 Adapter |
| 完全自定义 UI | 保留 Sidecar，重写 `apps/desktop`（注意 API Experimental） |
| 云托管版 | 超出 [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md)；独立产品 |

---

## 6. 相关文档

| 文档 | 内容 |
|------|------|
| [`STABILITY.md`](./STABILITY.md) | 各接口稳定性等级 |
| [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) | 产品边界 |
| [`GOVERNANCE.md`](./GOVERNANCE.md) | PR 评审与合并 |
