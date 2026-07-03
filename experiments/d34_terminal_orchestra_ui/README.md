# D34 Terminal Orchestra UI Mock

> Layer 4 实验 · 非产品代码。决策见 `memory/DECISIONS.md` D34。

## 打开方式

```bash
open experiments/d34_terminal_orchestra_ui/mock.html
```

## 场景切换（页面顶部）

| 场景 | 说明 |
|------|------|
| **A∥B 冷启动** | 两 Lane 并行 |
| **聚焦 A → 派 B** | 自然语言 + `@文件` 推断 from |
| **A,B → C 整合** | 多 `@文件` 合并 sources；图语法仍可用 |
| **完成 · 草稿队列** | Toast + 预填草稿 |

## 交互

| 操作 | 行为 |
|------|------|
| Lane 标签 | 切换聚焦 |
| 终端 **折叠** | 右侧独立栏 `float-rail`（不遮挡 xterm）；紧凑胶囊 LOGO + 摘要 |
| 底部 **↑** | 派发确认 (Bar 上方) → 确认后写入 Overview **派发历史** |
| 输入 | **自然语言**（`@目标 + 口语 + @文件`，后台编译图）或 **图语法**（`from @A @B`） |
| 右侧 **Overview** | 本 Session **派发记录** + handoff 预览 / 发送到 Bar |
| Lane **箭头连线** | from→to 可视化；线中 📎 悬浮预览 / →Bar |
| 右侧其他 Tab | Files / Flow / Changes / Terminal（占位，与现网一致） |

## 实现映射

| Mock | 拟议落地 |
|------|----------|
| 折叠悬浮卡 | `TerminalLaneFloatRail`（终端右侧栏，与 xterm 不重叠） |
| Overview 区 | 扩展 `RightPanel` `overview` Tab |
| Handoff 预览 | 读 `.clutch/handoffs/*.md` + 轻量 Markdown 渲染 |
| Orchestrator Bar | `ChatInputBar` 扩展或 `OrchestratorBar` |
| 自然语言解析 | `parse_dispatch_mentions`：@Agent + @file → graph |
| Handoff 发送到 Bar | Overview action → 预填 Bar + `file_refs[]` |
