# Clutch — 视觉设计快照（Layer 2）

> **权威 UI 规范**见 [`UI_UX_GUIDELINES.md`](../../UI_UX_GUIDELINES.md)（随实现演进更新）。  
> 本文件为 Layer 2 占位快照：记录治理阶段已确认的方向，**不复制**完整规范条文。

## 已确认方向（2026-06-22）

| 主题 | 决策 |
|------|------|
| 主基调 | 浅色、高对比、开发者工具气质（监督台 / IDE 感） |
| 技术栈 | React 19 + Tailwind CSS 4 + Motion + lucide-react |
| 布局 | 三栏监督台：侧栏 · Chat · 右侧面板（Overview / Terminal / Changes / Flow） |
| 工作流编辑 | React Flow 画布；界面仅业务语言，不出现 LangGraph 术语 |
| 失败体验 | 醒目校验失败卡片 + 可操作下一步（Approve / Reject / Retry） |
| 参考原型 | 当前 `apps/desktop/src` Prototype 组件（去 mock 前的高保真 UI） |

## 关联文档

| 文档 | 用途 |
|------|------|
| [`UI_UX_GUIDELINES.md`](../../UI_UX_GUIDELINES.md) | 色彩、字体、组件、动效细则 |
| [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) §7 | Prototype 组件 → 目标职责映射 |
| [`specs/core/proposal.md`](./proposal.md) §8 | 界面与体验原则（历史快照） |
