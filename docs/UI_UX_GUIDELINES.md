# Clutch — UI / UX Guidelines

> **适用范围**：`apps/desktop/src` 内所有 React + Tailwind CSS 界面开发。  
> 架构与后端纪律见 [`CLAUDE.md`](../CLAUDE.md)。

---

## 1. 整体美学

- **主基调**：干净、高对比的浅色主题（Light Theme First）。
- **避免**：默认深色面板、通用高饱和渐变、未经请求的暗色模式。
- **气质**：精密、克制、偏开发者工具——监督台 / IDE 感，而非营销落地页。

---

## 2. 色彩与表面（Tailwind）

| 用途 | 取值 / Class |
|------|----------------|
| 主背景 | `#ffffff` 或 `bg-surface`（`#f9f9f9`） |
| 容器表面 | `bg-surface-container-low`（`#f7f7f7`）或 `bg-white` |
| 边框 | `border-outline-variant/30`、`border-neutral-200` |
| 阴影 | `shadow-sm`、`shadow-md` |

优先使用语义化 token，避免在组件内硬编码 hex。

---

## 3. 字体与排版

| 场景 | 字体 | Class |
|------|------|-------|
| 标题与正文 | Hanken Grotesk | `font-sans` |
| 命令、日志、数字 | JetBrains Mono | `font-mono` |

**习惯**：

- 区块标题：`uppercase tracking-wider font-bold`
- 正文：`text-[13px]` ~ `text-sm`，`leading-relaxed`
- 元信息 / 标签：`text-[10px]` ~ `text-xs`，`text-on-surface-variant`

---

## 4. React 组件规范

### 4.1 卡片与对话框

```tsx
// 标准卡片容器
<div className="p-4 bg-surface-container-low rounded-2xl border border-outline-variant/30 shadow-sm">
```

- 圆角：`rounded-xl` ~ `rounded-2xl`
- 内边距：`p-4` ~ `p-8`，保持呼吸感
- 悬停：轻微背景或边框变化，避免夸张 transform

### 4.2 行内操作按钮

| 语义 | Tailwind 组合 |
|------|----------------|
| 成功 / 批准 | `bg-emerald-50 hover:bg-emerald-600 border border-emerald-200 text-emerald-800 hover:text-white transition-all` |
| 危险 / 拒绝 / 停止 | `bg-rose-50 hover:bg-rose-600 border border-rose-200 text-rose-800 hover:text-white transition-all` |
| 主操作 / 命令 | `bg-neutral-900 hover:bg-black text-white` |

### 4.3 输入区域

- 中性填充底 + 淡边框
- 与周围排版对齐，占位符用 `text-on-surface-variant/60`

### 4.4 状态与反馈

| 状态 | 实现要点 |
|------|----------|
| 运行中 | `text-primary` 或中性高亮 |
| 失败 | `VALIDATION FAILED` 浅底卡片，避免大面积 `bg-red-*` |
| 完成 | `text-green-600` + 勾选图标 |
| Terminal | `bg-neutral-900 text-neutral-200 font-mono` 与主界面形成对比 |

---

## 5. 布局原则

| 区域 | 尺寸 / 行为 |
|------|-------------|
| 左栏 | 280px，可折叠 |
| 右栏 | 300px，可折叠 |
| Header | 固定 `h-[64px]` |
| Footer | 固定 `h-8`（32px） |
| 设置模态 | 约 `1040×640`，`rounded-[24px]` |

中间 Chat 区域使用 `max-w-2xl` 居中，保持阅读宽度。

---

## 6. 图标与动效

| 项 | 约定 |
|----|------|
| 图标 | **lucide-react**（新代码唯一来源） |
| 动效 | **Motion**；通用过渡 `transition-all duration-300` |
| 遗留 | Material Symbols 仅 Prototype 存量，新组件不得新增 |

---

## 7. 禁止事项

- MUI、Ant Design、Chakra 等重型 UI 库
- 未经请求的深色主题或大面积渐变
- 在 JSX 内写与规范冲突的任意色值
- 用内联 `style={{}}` 替代应由 Tailwind 表达的样式（动态计算除外）

---

## 8. 开发自检

修改 `apps/desktop/src` 后确认：

- [ ] 浅色主题、高对比可读
- [ ] 新图标来自 `lucide-react`
- [ ] 按钮语义色符合 §4.2
- [ ] `pnpm lint` 无报错
