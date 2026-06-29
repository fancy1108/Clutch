# Clutch — 架构稳定性承诺

> **Normative policy only** — stability commitments, not implementation. Details: [`ARCHITECTURE.md`](./ARCHITECTURE.md).

---

## 1. 稳定性等级

| 等级 | 含义 |
|------|------|
| **Stable** | 语义化版本内保持向后兼容；破坏性变更仅在 major 升级并写迁移说明 |
| **Beta** | 功能可用，字段可能增删；minor 版本可能调整 |
| **Experimental** | 可能随时重构；勿在生产集成中硬依赖 |
| **Internal** | 仅仓库内部使用；**不通知即可变更** |

---

## 2. 模块与接口对照表

| 模块 / 接口 | 稳定性 | 说明 |
|-------------|--------|------|
| **Workflow JSON Schema** (`workflows/workflow.schema.json`) | **Stable**（1.0 前为 Beta） | 用户工作流与模板；Compiler 输入契约 |
| **WebSocket 信封** (`event` + `data`，如 `state_patch`) | **Beta** | 事件名稳定倾向高；`data.patch` 字段随 `ClutchState` 演进 |
| **HTTP REST `/api/*`** | **Experimental** | 路由与 payload 随功能迭代；**1.0 前不保证兼容** |
| **`ClutchState` 字段** | **Experimental** | 前端仅投影 WS；字段可增删 |
| **LangGraph 内部图 / Compiler 实现** | **Internal** | `services/orchestrator/src/compiler/`、`workflow_runtime.py` |
| **Engine Router / Hybrid 运行时** | **Internal** | `engine_router.py`、`shell_exec_runtime.py` |
| **Frontend UI 组件与路由** | **Experimental** | `apps/desktop/src/**` 大规模重构预期中 |
| **MCP 工具调用约定** | **Beta** | 工具名、`clutch-tools__*` 内置工具；第三方 MCP 遵循 MCP 规范 |
| **Model Provider 配置** (`models.json` 结构) | **Beta** | Provider 列表扩展中；Key 存储方式可能迁移 Keychain |
| **Agent 配置 JSON** | **Beta** | Settings 持久化格式可能调整 |
| **Tauri Commands** | **Experimental** | `src-tauri/src/lib.rs` 命令面小但可能扩展 |
| **PyInstaller Sidecar 打包布局** | **Internal** | 仅发布工程关心 |

### Internal 路径（可随时变更，勿扩展依赖）

以下目录/概念 **不对外承诺**：

```
services/orchestrator/src/compiler/
services/orchestrator/src/workflow_runtime.py
services/orchestrator/src/engine_router.py
services/orchestrator/src/run_state_store.py
apps/desktop/src/services/clutchState.ts   # 投影层，非公共 SDK
memory/                                    # 维护者运行态，非 API
```

**规则**：`anything documented as Internal may change without notice.`

---

## 3. 版本与 Release 生命周期

当前版本：**1.0.0**（首个公开发布；各模块稳定性见 §2）。

| 阶段 | 版本号 | 含义 |
|------|--------|------|
| **Alpha** | `0.0.x` | 功能快速迭代；API / Schema 均可破 |
| **Beta** | `0.1.x` – `0.9.x` | 主路径可用；**仍可能 breaking**；Workflow Schema 趋向稳定 |
| **Stable** | `1.0.0+` | HTTP/WS 公共面、Workflow Schema 遵循 semver |
| **LTS** | `1.x` 长期分支（未来） | 仅安全修复；**尚未承诺** |
| **Deprecated** | 文档标注 + 至少一 minor 过渡期 | 移除前在 `CHANGELOG.md` 说明 |

### 0.x 政策（重要）

> **Until 1.0, breaking changes are expected.**  
> 升级 minor（如 `0.2` → `0.3`）后若 Workflow 无法加载或 API 报错，请先查 `CHANGELOG.md`，而非假定兼容。

| 变更类型 | 0.x 处理方式 |
|----------|----------------|
| Workflow Schema 字段新增 | 通常向后兼容 |
| Workflow Schema 字段删除/改名 | 可能无迁移脚本 |
| `/api` 路由重命名 | 允许 |
| `ClutchState` 字段重命名 | 允许（前端同步改） |
| 用户数据目录结构 | 尽量迁移；不保证跨 0.x 所有版本 |

---

## 4. 依赖方的建议

| 你想做… | 应依赖… | 应避免依赖… |
|---------|---------|-------------|
| 自定义 SOP | `workflow.schema.json` + 模板 JSON | Compiler 内部节点类型实现 |
| MCP 工具 | 标准 MCP + Clutch 工作区授权 | Engine Router 私有钩子 |
| 外部仪表盘 | WS `state_patch`（接受字段变化） | 未文档化的 REST 端点 |
| 第三方「插件」 | 见 [`EXTENSIBILITY.md`](./EXTENSIBILITY.md) | 替换 LangGraph / 重写 `clutchState.ts` |

---

## 5. 破坏性变更流程（1.0 前后通用）

1. 在 `CHANGELOG.md` 的 **Breaking** 小节记录  
2. 若影响 Workflow Schema：递增 schema `version` 或文档化迁移  
3. 若影响 HTTP：保留旧路由至少一个 minor（1.0 后）或明确 0.x 无此义务  
4. 重大决策写入 [`memory/DECISIONS.md`](../memory/DECISIONS.md)

---

## 6. 相关文档

| 文档 | 内容 |
|------|------|
| [`EXTENSIBILITY.md`](./EXTENSIBILITY.md) | 支持的扩展点 |
| [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) | 做 / 不做 |
| [`GOVERNANCE.md`](./GOVERNANCE.md) | 谁决定合并与发版 |
| [`PERFORMANCE.md`](./PERFORMANCE.md) | 性能基线（非 API 契约） |
