# Clutch Design 模式 — 产品功能介绍

> **面向读者**：产品经理、设计师、业务用户  
> **描述内容**：WHAT（能做什么）和 WHY（为什么有价值），不涉及 HOW（技术实现细节）  
> **状态标注**：✅ 已实现 · 🔧 进行中 · 📋 规划中

---

## 1. 产品定位与核心价值

**Design 模式**是 Clutch 双模架构（Coding | Design）中的设计侧工作区，定位为**基于画布的高保真 UI/UX 智能生成与交互验证工作台**。用户通过自然语言 + 参考物料（图片、网址、品牌文档），快速生成、修改和验证界面原型与视觉规范，并一键导出为生产级前端代码（React + Tailwind），无缝交接给 Coding 模式的开发 Agent。

| 核心能力 | 一句话说明 |
|---------|-----------|
| 🎨 **自然语言生成界面** | 打字描述需求，AI 自动生成设计规范 + 高保真 UI |
| 🔍 **精准点选修改** | 鼠标点击界面任意元素，就地修改，不破坏其他设计 |
| 🔗 **交互原型串联** | AI 自动识别可点击元素，生成页面跳转连线，支持可视化编辑 |
| 📱 **多设备适配** | Web 桌面端（1920×1080）和 App 移动端（390×844）一键切换 |
| 🧬 **品牌设计系统** | 内置 70+ 品牌预设（Apple、Stripe、Tesla 等），确保视觉一致性 |
| 🚀 **一键出码** | 原型批准后确定性导出 Vite + React 工程（非 AI 重绘），本地预览后交接 Coding 接 API |
| 🤝 **无感交接** | 设计产物 + 规范文档一键移交 Coding 模式，开发 Agent 继续实现 |

> **与 Coding 模式的关系**：Design 专注"界面与交互的视觉呈现"，调用 LLM 推理接口而非 CLI 工具链；用户满意后通过 Handoff 将 DESIGN.md + React 源码交接给 Coding 模式完成业务逻辑开发。

---

## 2. 已实现功能全景

### 2.1 双模切换与会话管理 ✅

- 顶部 Header 右侧 **Coding | Design** 切换按钮，一键进入设计工作区
- Design 会话与 Coding 会话**同一侧栏并存**，按 mode 过滤显示
- 每个会话自动生成**界面缩略图**（基于实际 HTML 动态渲染，非通用占位图）
- 会话数据落盘至 `.clutch/design/sessions/{标题}-{设备}__{run_id}/`，删除会话时同步清理产物

### 2.2 欢迎态与物料配置 ✅

进入 Design 模式后，用户看到极简的欢迎页面：

| 功能 | 说明 |
|------|------|
| **设备切换** | 🖥 Web 桌面端（1920×1080）/ 📱 App 移动端（390×844），引导 AI 采用不同布局策略 |
| **模型选择** | 右上角模型 pill，绑定全局 `active_model_id`，点击跳转 Models 设置 |
| **上传 Design.md** | 拖入或选择品牌规范 Markdown 文档，锁定设计基调 |
| **输入参考网址** | 粘贴 URL，后台自动抓取网页 CSS 变量、配色、排版并提取为设计参考 |
| **粘贴参考图** | 支持剪贴板粘贴或上传截图，Vision 模型自动分析视觉结构、配色与间距 |
| **风格预设** | 70+ 品牌设计系统预设（Apple、Stripe、Spotify、Notion 等），一键选定 |

### 2.3 无限画布（React Flow Canvas） ✅

提交需求后进入无限画布，设计流程以**可视化节点**从左到右排列：

| 节点类型 | 展示内容 |
|---------|---------|
| **Agent Log 卡** | LLM 思考步骤、模型名称、Token 用量的实时日志 |
| **参考物料卡** | 上传的参考图缩略图、网址快照、Design.md 原文 |
| **Spec 卡** | 设计规范可视化：调色板 HEX 色块、字体 Aa 字重示例、核心组件列表 |
| **UI Screen 卡** | 生成的 HTML 界面以 iframe 等比缩放预览，头部显示页面名称和状态标识 |

- 支持 React Flow 原生操作：**缩放、平移、拖拽节点**
- 支持 `⌘/Ctrl + C/V` **复制粘贴 UI 卡**，便于 A/B 对比
- 底部浮动输入栏：选中卡片后出现上下文 chip，输入自然语言就地修改

### 2.4 两阶段生成引擎 ✅

Design 模式采用"**先定规范，再出界面**"的两阶段流水线（D40：默认 Spec→UI 连跑）：

```
用户需求 + 参考物料
    ↓
Brief 结构化增强（platform / page structure）
    ↓
Phase 1: 生成设计规范（Spec）
  · 调色板 (Primary / Secondary / Accent / Background / Text)
  · 字体系统 (Heading / Body / Mono)
  · 组件风格 (Button / Input / Card / Modal 等)
    ↓
（可选）Spec 软确认 — 仅当 CLUTCH_DESIGN_SPEC_CONFIRM=1；默认同一次生成继续出 UI
    ↓
Phase 2: 生成 UI 界面
  · 严格遵守 Spec 中的颜色和字体约束
  · 多页面时保持统一的侧栏导航和视觉风格
  · 语义 button + data-clutch-id 供 IUE 识别；无真实跳转/表单提交
```

### 2.5 Pick Mode 元素精准修改 ✅

开启 **Pick Mode**（铅笔图标）后，用户可在 UI 预览画面上：

1. **悬停**：鼠标划过元素时显示虚线框
2. **点选**：单击锁定蓝色实线框，浮现组件标签（如 `button: 立即注册`、`input: 手机号`）
3. **修改**：底栏自动带上选中元素信息，输入"把这个按钮改成橙色圆角"→ AI 仅修改该元素

这一机制实现了**"精准手术刀式"调整**，保护已有设计不被全量重写破坏。

### 2.6 多页面并行生成 ✅

- 输入"做一个 Dashboard、一个列表页、一个详情页"→ AI 自动解析为多个页面
- 多页面在画布上**横向并排**展示
- 生成过程支持**渐进式加载**：占位卡片先显示 shimmer 扫光动画，逐个完成后显示内容
- 后续迭代中可继续"新增一个设置页面"，AI 追加新节点到画布最右侧

### 2.7 可点击交互原型（PreviewDemo） ✅

每个 UI Screen 卡可打开**交互原型弹窗**，提供完整的高保真预览与编辑体验：

**三种视图模式**：

| Tab | 功能 |
|-----|------|
| **Simulator 模拟器** | 带设备外壳（显示器底座 / iPad / iPhone 边框）的交互式 iframe。点击页面元素可真实跳转，支持前进/后退导航 |
| **Matrix 矩阵** | Desktop / Tablet / Mobile 三端并排展示，一键验证多设备适配效果 |
| **Flows 连线图** | SVG 可视化交互关系：热区元素 → 目标页面缩略图连线，出入连接数量清晰标注 |

**编辑模式**（铅笔图标切换）：

- **拖拽重连**：拖动连线端点修改跳转目标
- **拖拽创建**：从一个元素拖出线条到目标缩略图，创建新交互
- **右键菜单**：修改触发条件、删除连线、查看详情
- **自动保存**：所有连线修改自动存入 localStorage

**核心交互能力**：

- iframe 内真实点击跳转，不污染宿主浏览器历史
- 导航栈支持前进/后退
- 页面缩略图侧栏列表（标记入/出连接数）

### 2.8 交互理解引擎（IUE） ✅

后台的 **Interaction Understanding Engine (IUE)** 自动分析静态 HTML，识别交互元素并推断跳转关系：

| 阶段 | 能力 |
|------|------|
| **Stage 1** | 从 DOM 树提取所有可交互候选元素 |
| **Stage 2** | 分类元素角色（17 种：SubmitButton、NavLink、TableRowLink 等） |
| **Stage 3** | 匹配潜在跳转目标 |
| **Stage 4** | 按置信度打分排序 |
| **Stage 5** | 输出可读的推理理由 |
| **Stage 6** | 等待人工确认/编辑 |

- 采用**可插拔管道架构**，默认使用规则启发式，可按需替换为 LLM/向量/视觉模型
- 当前主要服务于 Flows 连线图的初始化建议

### 2.9 业务状态模拟 ✅

在原型弹窗中可通过 **State Controller** 下拉切换业务状态，实时验证界面在异常态下的表现：

| 状态 | 效果 |
|------|------|
| ✅ **Normal** | 正常状态 |
| ⚠️ **Warning** | 警告横幅（页面顶部注入黄色提示） |
| 🔴 **Critical** | 严重错误态（红色错误提示 + 表单输入框标红） |
| 📊 **DataOverflow** | 数据溢出态（长文本/大数字极限值替换） |
| 💥 **Extreme** | 极端组合态（警告 + 错误 + 溢出同时生效） |

状态模拟通过外部 DOM 注入实现，不修改源码，安全可靠。

### 2.10 代码生成与预览沙箱 ✅

设计定稿后，打开 **Preview Demo → Coding** 进入唯一出码路径（产物目录 `react/`，D39/D41）。面板分步引导：

```
Approve Prototype（批准原型）
    ↓
Generate UI Code（确定性出码，非 AI 重绘）
  · 批准 HTML 机械转为每屏 .tsx → `.clutch/design/sessions/.../react/`
  · 同源 Tailwind CDN + prototype tailwind.config
  · interaction_contract.json → React Router <Link>
  · App.tsx 路由已配置；前端 UI + 客户端导航就绪
    ↓
Start Preview（启动预览）
  · 后台拉起 Vite 开发服务器
  · 验收代码跑起来 = 定稿样子 + 连线可用
  · 动态端口分配，多会话不冲突
```

PreviewDemo 旁路 Generate Code 同样写入 `react/`（不再以 `generated/` 作为交接目录）。

### 2.11 开发交接（Handoff） ✅

- 在 **Preview Demo → Coding** 中依次：Approve Prototype → Generate → Preview → **Approve UI code** → **Send to Coding**
- 打包内容：
  - `DESIGN.md`（设计规范文档，作为开发 Agent 的指令）
  - `react/` 源码路径 + 项目结构说明
  - Prompt 简报（用户原始需求和迭代历史摘要）
- 自动切换回 Coding 模式，Payload 注入 Chat 输入框
- 内置 `design-to-code` 工作流模板可一键启动 Builder Agent

### 2.12 品牌预设系统 ✅

- 内置 **70+ 品牌设计系统预设**，覆盖科技、金融、社交、工具等主流产品风格
- 每个预设包含：颜色方案（`.spec.json`）+ 设计规范描述（`.md`）
- 在欢迎态通过 Style Select 下拉框一键选择
- 生成 Spec 卡时自动应用选定的品牌规范

---

## 3. 用户使用流程

### 典型完整流程

```
1️⃣ 切换模式
   顶部 Header 点击 "Design"

2️⃣ 设定目标（欢迎态）
   选择设备 → 可选上传参考图/网址/Design.md → 选择风格预设
   输入："做一个 SaaS 后台的数据大盘和用户管理页"

3️⃣ 画布审查
   画布依次生成：Agent Log → Spec 卡（色板/字体） → UI Screen 卡
   浏览所有页面，检查视觉风格

4️⃣ 局部微调（可选）
   方式 A：底栏打字"把侧栏从深色改成浅灰色"
   方式 B：开启 Pick Mode，点击侧栏 → 输入"浅灰色背景"
   方式 C：输入"新增一个设置页面"追加新节点

5️⃣ 交互验证（可选）
   打开 UI 卡的 PreviewDemo
   在 Simulator 中点击页面元素，验证跳转逻辑
   切换到 Flows Tab，检查/修正 AI 生成的连线
   切换 State Controller，验证异常态表现

6️⃣ 代码化
   Approve Prototype → Generate UI Code → Start Preview
   在 Vite 预览中操作真实 React 界面，确认无误

7️⃣ 交接编码
   Send to Coding → 自动切换到 Coding 模式
   开发 Agent 接收设计产物，继续实现后端 API / 业务逻辑
```

### 迭代修改流程

```
选中 UI 卡 → 底栏出现上下文 chip → 输入修改需求 → AI 就地修改该页面
（明确说"新增页面"才会追加新节点；否则默认在选中页面上修改）
```

---

## 4. 规划中功能

以下功能已进入路线图，按优先级排序：

### 4.1 近期优先（连线精度与 Spec 确认） 🔧

| 功能 | 说明 | 价值 |
|------|------|------|
| **连线精度修复** | 优化 IUE Stage 2 分类和 Stage 3 匹配的去噪能力，减少错误连线 | 减少用户手动修线工作量 |
| **Spec 软确认（opt-in）** | 默认 Spec→UI 连跑；设 `CLUTCH_DESIGN_SPEC_CONFIRM=1` 可暂停审 Spec（D40） | 需要时避免坏规范污染全部屏幕 |
| **交互契约落盘** | ✅ 已实现：PreviewDemo 编辑写入 `interaction_contract.json`，Path A 出码读取 | 为代码生成提供可靠数据源 |

### 4.2 中期规划（状态与交互增强） 📋

| 功能 | 说明 | 价值 |
|------|------|------|
| **业务状态补齐** | 新增 Empty（空数据）、Loading（骨架屏）、Error（网络异常）、PermissionDenied（无权限）等状态模拟 | 覆盖更多真实业务场景 |
| **弹窗/抽屉交互** | 支持 Modal、Drawer、Popover 等浮层类型交互的原型模拟 | 更逼真的交互演示 |
| **交互契约 → 代码生成** | React Compiler 读取 Interaction Contract，自动生成 `<Sheet>`、`<Dialog>` 等组件包装代码 | 真正的"所见即所得"代码交付 |

### 4.3 远期愿景（智能进化） 📋

| 功能 | 说明 |
|------|------|
| **交互记忆体** | 用户编辑连线行为反馈到 IUE，越用越准——"越懂你的产品" |
| **场景组播放器** | 将多步操作封装为连续剧情（如"订单退款全流程"），步进式演示 |
| **完整原型运行时** | 全局状态机 + Overlay Context + Mock API 拦截，支持复杂仪表盘原型仿真 |

---

## 5. 常见问题（FAQ）

**Q: Design 模式和 Figma 有什么区别？**  
A: Design 模式不做矢量设计工具，不替代 Figma。它的核心是"用自然语言生成高保真 UI + 直接出生产代码"。适合快速验证想法、生成可用的前端起点代码，而非精细像素级设计。

**Q: 生成的代码质量如何？可以直接上线吗？**  
A: 生成的 React + Tailwind 代码是规范的组件化结构，适合作为前端起点。业务逻辑（API 对接、状态管理、权限控制等）需在 Coding 模式下由开发 Agent 继续实现。

**Q: Design 模式需要配置 API Key 吗？**  
A: 需要。Design 模式通过 LLM 推理生成界面，依赖 Settings → Models 中配置的云端模型 API Key。

**Q: 支持哪些模型？**  
A: 支持 Settings → Models 中配置的所有 Chat 模型（DeepSeek、Anthropic、OpenAI、Google、Agnes 等）。建议使用有 Vision 能力的模型以支持参考图分析。

**Q: 生成的产物保存在哪里？**  
A: `.clutch/design/sessions/{标题}-{设备}__{run_id}/` 目录下，包含 HTML 文件、DESIGN.md、React 源码等。所有数据本地存储，不上传云端。

---

> **文档维护**：本文基于 v1.2.7 版本功能编写。技术实现细节见 [`DESIGN_WORKSPACE_GUIDE.md`](./DESIGN_WORKSPACE_GUIDE.md)，交互原型规格见 [`specs/core/prd-one-click-interactive-prototype.md`](../specs/core/prd-one-click-interactive-prototype.md)，实施进度见 [`memory/ROADMAP.md`](../memory/ROADMAP.md)。
