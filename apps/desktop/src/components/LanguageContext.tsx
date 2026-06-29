import React, { createContext, useContext, useState, useEffect } from 'react';
import { fetchLanguagePreference, saveLanguagePreference } from '../services/themeApi';

export type Language = 'en' | 'zh';

interface LanguageContextProps {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextProps | undefined>(undefined);

// Chinese UI copy — zh mode shows pure Chinese; en mode shows English keys unchanged.
const zhTranslations: Record<string, string> = {
  // Navigation & Sidebar
  "New Chat": "新建会话",
  "New Chat / Reset": "重置",
  "AI Agents": "AI 智能体",
  "Branch": "分支",
  "Not a git repository": "非 Git 仓库",
  "Model": "模型",
  "Engine": "驱动引擎",
  "Model is provided by the selected agent tool": "模型由所选 Agent 工具自带",
  "Workflow": "工作流",
  "System Preferences": "系统设置",
  "Status Overview": "状态概览",
  "Active Preset Themes": "活跃 主题",
  "Available Preset Themes": "可用 主题预设",
  "Workspace:": "工作空间:",
  "Session:": "会话:",
  "ACTIVE": "活跃",
  "STYLING ENGINE OK": "样式引擎正常",
  "REPOSITORIES": "源码仓库",
  "General": "通用",
  "General Settings": "通用设置",
  "Customize your application profile, account settings and default preferences.": "自定义您的应用个人资料、帐户设置和默认偏好。",
  "Profile Avatar": "个人头像",
  "Profile Name": "个人名称",
  "Enter your name": "输入您的名称",
  "Choose Photo": "选择照片",
  "Reset to Default": "重置为默认",
  "Supported formats: PNG, JPG, GIF. Max file size: 5MB.": "支持格式：PNG、JPG、GIF。文件大小限制：5MB。",
  "AI Tools": "AI 工具",
  "Models Config": "模型配置",
  "Skills Registry": "技能注册表",
  "MCP Server Hub": "MCP 服务网关",
  "Appearance": "外观配置",
  "Feature under active development": "功能正在积极开发中",
  "Active Palette Scheme:": "活跃配色方案:",
  "Active Theme": "活跃 主题",
  "Updates all buttons, panels, background layout variables, and typography states.": "刷新工作空间界面各布局组件、按钮面板及排版颜色状态。",
  "Customize the developer workspace environment with cohesive colors, borders, shadows, and eye-friendly presets.": "定制开发工作空间环境，包含协调的色彩、边框、阴影和对眼部友好的预设。",
  "Workspace Theme Configurator": "工作空间 主题配置器",

  // Model Config page
  "AI Workspace Models": "AI 模型中心",
  "Monitor, connect, and configure Large Language Models for active agent execution, reasoning logic, and prompt engineering.": "监视、连接和配置大语言模型，用于智能体执行、推理逻辑和提示词工程。",
  "Add External Model Provider": "添加外部 模型提供商",
  "Integration Hub": "集成中心",
  "Connect External Model Provider": "连接外部 模型提供商",
  "Model Name / Identifier": "模型标识符",
  "Provider Platform": "提供商平台",
  "Local Ollama Integration Guide": "本地 Ollama 集成指南",
  "Then run your model, for example:": "然后运行您的模型，例如：",
  "Custom Provider Name": "自定义提供商名称",
  "API Endpoint URL (Optional)": "API 端点 URL (可选)",
  "API Key / Credentials (Optional)": "凭据 (可选)",
  "Context Window Spec": "上下文窗口规格",
  "Default Temperature": "默认 Temperature温度",
  "Model Notes / Purpose": "模型备注与用途",
  "Save & Connect Model": "保存并连接 模型",
  "Cancel": "取消",
  "Configured & Connected Models": "已配置与已连接的 模型",
  "Installed": "已安装",
  "Active LLM Orchestrator:": "活跃 LLM Orchestrator大模型编排器:",
  "PROVIDER SYNCED": "提供方已同步",
  "Activate Mode": "激活 模型",

  // Chat placeholders / messages
  "Note: These settings only apply to the built-in Clutch Agent and MCP tools, and do not affect CLI Agents (such as Claude Code).": "提示：此权限模式仅适用于内置 Clutch 智能体与 MCP 工具，不影响 CLI 智能体（如 Claude Code）。",
  "@Agent your feedback (Hybrid) — auto-continues downstream; Stop to pause": "@Agent 反馈修改意见（Hybrid）— 精修后自动继续；可先停止再改",
  "Ask @Builder, @Orchestrator or trigger @Workflow...": "咨询 @Builder、@Orchestrator 或触发 @Workflow…",
  "Ask your AI Agent anything...": "向 AI 智能体提问…",
  "View execution details": "查看底层执行细节",
  "Shell command": "Shell 命令",
  "System prompt": "系统提示词",
  "Boundary marker": "边界标记",
  "Raw shell output": "原始 Shell 输出",
  "No structured execution details were captured for this turn.": "本轮未捕获结构化执行细节",
  "sections": "项",
  "Expand": "展开",
  "Collapse": "收起",
  "Run Workflow": "运行工作流",
  "Run SOP": "运行 SOP",
  "Start a supervised session": "开始新的监督会话",
  "Select a workspace and start a workflow, or type an instruction below. Clutch will orchestrate Builder / Evaluator and ask for your approval when needed.": "选择工作区并启动工作流，或直接在下方输入指令。Clutch 会编排 Builder/Evaluator，并在需要时请你审批。",
  "Start a single agent session": "开始单智能体会话",
  "Select a workspace and type an instruction below to chat with the agent directly.": "选择工作区并在下方输入指令，直接与智能体进行对话。",
  "Authorize workspace": "授权工作区",
  "Choose workflow template": "选择工作流模板",
  "Create Flow": "创建工作流",
  "Add Node": "添加节点",
  "Save Flow": "保存工作流",
  "Saving...": "保存中…",
  "Save Node": "保存节点",
  "Selected for chat": "已选中 · 用于 Chat",
  "No workflows yet": "暂无工作流",
  "Manage workflows...": "管理工作流...",
  "Manage models...": "管理模型...",
  "Manage agents...": "管理 Agent...",
  "No models configured": "暂无已配置模型",
  "View workflow": "查看工作流",
  "Edit workflow": "编辑工作流",
  "Edit Workflow": "编辑工作流",
  "Create New Workflow": "创建新工作流",
  "Delete workflow": "删除工作流",
  "Empty workflow — click Add Node to begin": "空工作流 — 点击 Add Node 开始编排",
  "Describe what you want this workflow to do...": "描述你希望此工作流完成的任务…",
  "Clear": "清除",
  "Workflow running": "工作流运行中",
  "Receiving sidecar events": "监督台正在接收 Sidecar 事件…",
  "Human gate hint": "检查未通过或需要人工确认，请选择下一步操作。",
  "Retry instructions placeholder": "附加指令，例如 \"跳过语法检查直接打包\"",
  "No active workflow overview": "暂无运行中的工作流。启动模板或发送指令后，这里会显示 Token 统计与 Flow 进度。",
  "No session activity yet": "开始与 Agent 对话后，这里会显示会话状态与 Token 统计。",
  "Workflow step execution": "工作流步骤执行",
  "Workflow steps unavailable": "无法加载工作流步骤定义。",
  "Workflow selected — send a message to start": "已选择工作流 — 发送消息即可启动",
  "Uncommitted changes": "未提交变更",
  "No uncommitted changes": "暂无未提交变更。",
  "Terminal logs": "终端日志",
  "Authorize workspace files hint": "请先在侧栏添加项目文件夹，或点击 Authorize workspace。",
  "Workspace folder empty": "工作区为空。",
  "No terminal logs yet": "暂无日志。启动工作流后 Sidecar 输出会显示在这里。",
  "Session tokens accumulated": "本轮累计",
  "Select project folder": "选择项目根目录",
  "Add project folder": "添加项目文件夹",
  "New project group": "新建项目分组",
  "Filter projects": "筛选项目",
  "No projects in this group yet": "此分组下暂无项目",
  "No projects match your filter": "没有匹配筛选条件的项目",
  "No repositories yet. Use Add project folder or Authorize workspace to begin.": "尚无项目。请通过侧栏添加文件夹，或点击 Authorize workspace。",
  "New session": "新建会话",
  "Projects": "项目",
  "No sessions in this project yet": "此项目下暂无会话",
  "Saved workspace snapshot": "已保存工作环境快照",
  "Continue previous work": "可继续上次工作",
  "Select a project before starting a conversation.": "请先选择项目，再开始对话。",
  "Are you sure you want to remove this project from the list?": "确定要从列表中移除该项目吗？",
  "Are you sure you want to permanently delete this session?": "确定要永久删除该会话吗？",
  "Delete": "删除",
  "Delete project": "删除项目",
  "Delete session": "删除会话",
  "Enter group name...": "请输入分组名称...",
  "Confirm": "确认",
  "Reload": "重新加载",
  "Thinking...": "思考中...",
  "Clutch Agent": "Clutch 智能体",
  "Settings": "设置",
  "Default Group": "默认分组",
  "Move to Group": "移动至分组",
  "Rename Group": "重命名分组",
  "Delete Group": "删除分组",
  "Rename": "重命名",
  "Are you sure you want to delete this group?": "确定要删除该分组吗？",
  "Enter new group name...": "请输入新的分组名称...",

  // Header
  "Select workspace": "选择工作区",
  "Go Back": "返回",
  "Workspace": "工作空间",

  // General Settings Panel
  "Developer Profiles": "开发者角色配置",
  "Active Workspace Developer Profiles": "活跃工作空间开发者配置",
  "Create, switch, or customize roles with tailored system prompt instructions, memory logs, and API allowances.": "创建、切换或定制具有系统提示词、内存日志和 API 配额的角色。",
  "Switch Profile": "切换 角色",
  "ACTIVE PROFILE": "活跃 角色",
  "System Prompt / Directive": "系统 提示词指令",
  "Active Memory context": "活跃 内存上下文",
  "API Calls Allowance Limit": "API 调用次数限额",
  "Customize Active Instructions": "定制 System Prompt系统提示词指令",
  "Update Developer Settings": "更新开发者设置",
  "Save Custom Settings": "保存自定义 角色",

  // Agent Manager
  "AI Agents Registry": "AI 智能体注册表",
  "Orchestrate, edit, and launch autonomous specialized agent personas with custom tool allocations and constraints.": "编排、编辑和启动具有自定义 工具分配和约束的自治专业 智能体角色。",
  "Create Custom Agent": "创建自定义 智能体",
  "System Orchestrator Status: Active": "系统编排器状态: 活跃",
  "Active Agent Roles": "活跃 智能体角色",
  "Define and manage agents and system roles.": "定义与管理 智能体 及系统角色。",
  "Core Role Directive": "核心 指令/提示词",
  "Equipped Tools": "装备 工具",
  "Active Tasks Log": "活跃任务日志",
  "System Instruction Prompt": "系统指令 提示词",
  "Edit Agent Details": "编辑 智能体详情",
  "Add Custom Agent Profile": "添加 智能体属性",
  "Agent Name / Brand": "智能体名称",
  "Primary Purpose": "主要用途",
  "System Instructions prompt": "系统指令 提示词",
  "Associated LLM Model": "关联 LLM Model大模型",
  "Add Agent Persona": "新增 智能体",
  "Save Persona Settings": "保存 智能体设置",
  "Active Agent": "当前智能体",
  "Select an AI Agent before sending.": "发送前请先选择智能体。",
  "Select an AI Agent or a Workflow before sending.": "发送前请选择智能体或工作流。",
  "builtin": "系统内置",
  "Edit Persona": "编辑 智能体角色",
  "Delete Persona": "删除 智能体角色",

  // Workflow panel
  "Workflows Standard Operating Procedures": "工作流 SOP标准作业程序",
  "Define, monitor, and execute step-by-step pipeline runs using automated agent interactions, validations, and artifact commits.": "通过自动化的 智能体交互、验证和 交付物提交，定义、监控并执行分步 管道流工作流。",
  "Create Custom SOP": "创建自定义 Workflows SOP标准作业程序",
  "Total Flows Loaded": "已加载 工作流总数",
  "Flow status:": "工作流状态:",
  "Flow Tasks SOP Progress": "任务进度",
  "Run Active SOP": "执行活跃 SOP",
  "Running Flow SOP Execution...": "正在执行 SOP中...",
  "Workflow execution successfully finished!": "工作流 SOP 执行成功完毕！",
  "Select a flow sequence to inspect execution.": "选择一个 工作流序列来检查执行状态。",
  "Step Details": "步骤详情",
  "Target Persona / Agent": "目标智能体",
  "Mock Output Artifact": "交付成果物",
  "View Generated Flow Output": "查看生成的 SOP结果",
  "Execution JSON Format": "执行格式 JSON",
  "Edit complex flows (checks, approvals, branches, loops) here; schema will be verified by Sidecar before saving.": "复杂流程（检查节点、人工审批、条件分支、循环）请在此编辑；保存前会经 Sidecar 校验。",
  "Failed to load": "加载失败",
  "Cannot connect to Sidecar": "无法连接 Sidecar",
  "Copy": "副本",
  "Saved to local workflow directory": "已保存到本机工作流目录",
  "Failed to save": "保存失败",
  "Step 1": "第一步",
  "Fill task instructions here": "在此填写任务说明",
  "Finish": "完成",
  "Failed to create workflow": "创建工作流失败",
  "Are you sure you want to delete this workflow?": "确定删除此工作流？",
  "Failed to delete": "删除失败",
  "Save as copy": "另存为副本",
  "Loading...": "加载中…",
  "Built-in template (Read-only)": "内置模板 · 只读",
  "User Workflow": "用户工作流",
  "Canvas editable (Simple linear workflow)": "支持画布编辑（简单线性流程）",
  "JSON mode only (Includes check/approval/branch)": "仅 JSON 模式（含检查/审批/分支）",
  "Canvas": "画布",
  "Complex workflow: please edit in JSON mode": "复杂流程：请用 JSON 编辑",
  "Built-in template: please save as copy after editing": "内置模板：编辑后请「另存为副本」",
  "Request failed": "请求失败",
  "JSON must contain id, nodes, and edges fields": "JSON 必须包含 id、nodes、edges 字段",
  "Confirm stopping the current run? This will interrupt Builder/Evaluator execution.": "确认停止当前运行？此操作将中断 Builder执行。",
  "Next steps: select \"Bypass & Approve\", \"Reject & Redo\" below, or type instructions and click \"Retry\".": "下一步：在下方选择「Bypass & Approve」、「Reject & Redo」，或填写指令后 Retry。",


  // AI Tools page
  "AI Tools Registry & Sandbox": "AI 工具注册中心与沙箱",
  "Integrate, configure, and sand-box server-side functions and client APIs usable by connected agents for live task completion.": "集成、配置和沙盒化服务端 函数和客户端 API，供已连接的 智能体用于实时任务完成。",
  "Add Custom Tool Plugin": "添加自定义 工具插件",
  "Register New Tool Extension": "注册新 工具",
  "Tool Label": "工具标签",
  "Execution Hook": "执行 钩子",
  "Plugin Source Script": "插件 源码脚本",
  "Register Tool Plugin": "注册 工具",
  "Connected Tool Providers": "已连接的 工具提供方",
  "Developer sandbox execution test:": "开发者沙盒执行测试:",
  "Test Tool Execution": "测试 工具",
  "ACTIVE / ONLINE": "活跃上线",
  "SIMULATION OK": "模拟状态正常",
  "Active Sandbox Logs:": "活跃沙盒日志",

  // Skills registry page
  "Skills Library Index": "技能库索引",
  "Provision pre-defined behavior trees, domain patterns, and schema blueprints directly into agent contextual memory.": "直接将预定义的行为树、领域模式和 架构蓝图注入 智能体上下文 内存空间中。",
  "Add Domain Skill Capability": "添加领域 技能",
  "System Skills Loaded": "已加载系统 技能",
  "Register Skill Tree Extension": "注册 技能",
  "Skill Label / Name": "技能名称",
  "System Prompt Capability Overlay": "提示词叠加",
  "Inject Skill Override": "注入 技能",
  "Active Domain Skills": "活跃领域 技能",
  "Status": "状态",
  "LOADED / ONLINE": "已加载上线",

  // MCP Servers
  "Model Context Protocol Gateways": "Model Context Protocol (MCP) 服务网关",
  "Connect and manage secure remote contextual backends, SQL servers, filesystem sockets, and public API registries supporting the MCP protocol.": "连接并管理支持 MCP 协议的远程 上下文后端、SQL 数据库、文件系统套接字和公共 API 注册表。",
  "Add Remote MCP Hub Connecting Sockets": "连接远程 MCP 服务组",
  "Connected MCP Sockets": "已连接的 MCP 节点",
  "Open Connection Sockets": "打开连接节点",
  "Configure Remote MCP Server Node": "配置 MCP 节点",
  "Socket Hook Name": "节点钩子名称",
  "Transport Layer Mode": "传输层模式",
  "Endpoint Transport URL": "传输层 URL",
  "Register Node": "注册 MCP 节点",
  "ONLINE / ACTIVE": "在线活跃",
  "ACTIVE CONNECTION OK": "活跃连接正常",

  // Base Header
  "Single Agent": "单智能体",
  "Multi-Agent": "多智能体",
  "Workspace theme updated to:": "配色主题更新为:",
  "Active LLM Orchestrator": "活跃 LLM 编排器",

  // Theme presets
  "Pristine Light": "极简白",
  "Clean Hanken aesthetic with spacious negative spaces and absolute neutral shades.": "极简 Hanken 设计风格，配有宽敞的负空间和绝对纯净的自然色彩预设。",
  "Cyberpunk Neon": "赛博霓虹",
  "Vibrant high-contrast dark theme with fluorescent purple, cyan, pink accents, and absolute neon shadows.": "高饱和度对比的暗黑主题，配有荧光紫、青色、粉色点缀与霓虹灯阴影效果。",
  "Nordic Frost": "北欧冰霜",
  "Serene soft-blue cool theme inspired by cold scandinavian winter, slate cliffs, and pine forests.": "受北欧严冬、石板悬崖和松林启发的松绿与淡蓝色冰霜极简格调方案。",
  "Slate Charcoal": "石板深灰",
  "Ultra-professional eye-saving dark theme focused on graphite shades, subtle borders, and steel tones.": "超干练眼部友好的深灰墨黑方案，聚焦于石墨黑、细腻纤薄边框和冷钢色调设计。",
  "Terminal Green": "终端绿",
  "Vintage matrix-style monochrome retro aesthetic showcasing glowing emerald typography and pure terminal layouts.": "复古 Matrix 终端单色美学，展现发光祖母绿字符与纯粹极客命令行布局样式。",

  // Theme UI components
  "Active": "活跃启用",
  "Palette:": "配色:",
  "Background": "背景色",
  "Surface": "界面色",
  "Text color": "文字色",
  "Accent primary": "核心主调",
  "Select": "选择应用",
  "System": "系统",

  // Right panel & misc UI
  "Overview": "概览",
  "Files": "文件",
  "Flow": "流程",
  "Changes": "变更",
  "Terminal": "终端",
  "Choose workflow": "选择工作流",
  "Workflows SOP": "工作流 SOP",
  "workflow": "工作流",
  "workflow_id": "工作流 ID",
  "active_node": "当前节点",
  "active_agent": "当前智能体",
  "status": "状态",
  "instruction": "指令",
  "Collapse Panel": "收起面板",
  "Expand Panel": "展开面板",
  "Close Panel": "关闭面板",
  "Collapse Sidebar": "折叠侧栏",
  "Expand Sidebar": "展开侧栏",
  "Session Token Analytics": "会话 Token 统计",
  "Total Tokens": "Token 总计",
  "Estimated Cost": "预估费用",
  "Token Distribution": "Token 分布",
  "Input vs Output": "输入 vs 输出",
  "Input": "输入",
  "Output": "输出",
  "Workspace Folder Structure": "工作区文件夹结构",
  "Preview file": "预览文件",
  "Preview Full": "完整预览",
  "Project Files": "项目文件",
  "Workflow agents": "工作流智能体",
  "Skills / Commands": "技能 / 命令",
  "Remove workflow": "移除工作流",
  "Model is determined by the selected workflow": "模型由所选工作流决定",
  "Model is bound on this agent": "模型绑定于当前智能体",
  "Failed to switch model.": "切换模型失败。",
  "Failed to save workflow": "保存工作流失败",
  "Save": "保存",
  "Drag to chat": "拖到聊天框",
  "idle": "空闲",
  "running": "运行中",
  "refining": "精修中",
  "awaiting_human": "待审批",
  "passed": "通过",
  "failed": "失败",
};


export const translateRunStatus = (status: string, language: Language): string => {
  if (language === 'en') return status;
  const key = status.trim().toLowerCase();
  return zhTranslations[key] ?? status;
};

// Fallback translator for keys not in the dictionary.
export const translateText = (text: string, language: Language): string => {
  if (language === 'en') return text;

  const trimmed = text.trim();
  if (zhTranslations[trimmed]) {
    return zhTranslations[trimmed];
  }

  const termsMap: Array<{ regex: RegExp; replacement: string }> = [
    { regex: /\bMulti-Agent\b/gi, replacement: '多智能体' },
    { regex: /\bSingle-Agent\b/gi, replacement: '单智能体' },
    { regex: /\bWorkflows?\b/gi, replacement: '工作流' },
    { regex: /\bAgents?\b/gi, replacement: '智能体' },
    { regex: /\bModels?\b/gi, replacement: '模型' },
    { regex: /\bPrompts?\b/gi, replacement: '提示词' },
    { regex: /\bSkills?\b/gi, replacement: '技能' },
    { regex: /\bTools?\b/gi, replacement: '工具' },
  ];

  let result = trimmed;
  for (const { regex, replacement } of termsMap) {
    result = result.replace(regex, replacement);
  }
  return result;
};

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    const saved = localStorage.getItem('workspace_lang');
    return (saved === 'zh' || saved === 'en') ? saved : 'en';
  });

  useEffect(() => {
    void fetchLanguagePreference()
      .then((lang) => {
        setLanguageState(lang);
        localStorage.setItem('workspace_lang', lang);
      })
      .catch(() => {});
  }, []);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem('workspace_lang', lang);
    void saveLanguagePreference(lang).catch(() => {});
  };

  const t = (key: string): string => {
    return translateText(key, language);
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};
