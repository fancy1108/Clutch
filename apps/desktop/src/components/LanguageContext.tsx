import React, { createContext, useContext, useState, useEffect } from 'react';

export type Language = 'en' | 'zh';

interface LanguageContextProps {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextProps | undefined>(undefined);

// Dictionary for translations. Keeps AI professional terms as requested: "AI 专业名词得显示成英文+中文，如Agent / 智能体"
const zhTranslations: Record<string, string> = {
  // Navigation & Sidebar
  "New Chat": "New Chat / 新建会话",
  "New Chat / Reset": "New Chat / 重置",
  "AI Agents": "AI Agents / AI 智能体",
  "Branch": "Branch / 分支",
  "Model": "Model / 模型",
  "Workflow": "Workflow / 工作流",
  "System Preferences": "System Preferences / 系统设置",
  "Status Overview": "Status Overview / 状态概览",
  "Active Preset Themes": "Active Themes / 活跃 Theme / 主题",
  "Available Preset Themes": "Available Preset Themes / 可用 Theme / 主题预设",
  "Workspace:": "Workspace / 工作空间:",
  "Session:": "Session / 会话:",
  "ACTIVE": "ACTIVE / 活跃",
  "STYLING ENGINE OK": "STYLING ENGINE OK / 样式引擎正常",
  "REPOSITORIES": "REPOSITORIES / 源码仓库",
  "General": "General / 通用",
  "AI Tools": "AI Tools / AI 工具",
  "Models Config": "Models Config / 模型配置",
  "Skills Registry": "Skills Registry / 技能注册表",
  "MCP Server Hub": "MCP Server Hub / MCP 服务网关",
  "Appearance": "Appearance / 外观配置",
  "Feature under active development": "Feature under active development / 功能正在积极开发中",
  "Active Palette Scheme:": "Active Palette Scheme / 活跃配色方案:",
  "Active Theme": "Active Theme / 活跃 Theme / 主题",
  "Updates all buttons, panels, background layout variables, and typography states.": "刷新工作空间界面各布局组件、按钮面板及排版颜色状态。",
  "Customize the developer workspace environment with cohesive colors, borders, shadows, and eye-friendly presets.": "定制开发工作空间环境，包含协调的色彩、边框、阴影和对眼部友好的预设。",
  "Workspace Theme Configurator": "Workspace Theme Configurator / 工作空间 Theme / 主题配置器",

  // Model Config page
  "AI Workspace Models": "AI Workspace Models / AI 模型中心",
  "Monitor, connect, and configure Large Language Models for active agent execution, reasoning logic, and prompt engineering.": "监视、连接和配置 Large Language Models / 大语言模型，用于活跃 Agent / 智能体执行、推理逻辑和 Prompt Engineering / 提示词工程。",
  "Add External Model Provider": "Add External Model Provider / 添加外部 Model / 模型提供商",
  "Integration Hub": "Integration Hub / 集成中心",
  "Connect External Model Provider": "Connect External Model Provider / 连接外部 Model / 模型提供商",
  "Model Name / Identifier": "Model Name / Identifier / Model / 模型标识符",
  "Provider Platform": "Provider Platform / 提供商平台",
  "Local Ollama Integration Guide": "Local Ollama Integration Guide / 本地 Ollama 集成指南",
  "Then run your model, for example:": "然后运行您的 Model / 模型，例如：",
  "Custom Provider Name": "Custom Provider Name / 自定义提供商名称",
  "API Endpoint URL (Optional)": "API Endpoint URL (Optional) / API 端点 URL (可选)",
  "API Key / Credentials (Optional)": "API Key / Credentials (Optional) / API Key / 凭据 (可选)",
  "Context Window Spec": "Context Window Spec / 上下文窗口规格",
  "Default Temperature": "Default Temperature / 默认 Temperature / 温度",
  "Model Notes / Purpose": "Model Notes / Purpose / Model / 模型备注与用途",
  "Save & Connect Model": "Save & Connect Model / 保存并连接 Model / 模型",
  "Cancel": "Cancel / 取消",
  "Configured & Connected Models": "Configured & Connected Models / 已配置与已连接的 Models / 模型",
  "Installed": "已安装",
  "Active LLM Orchestrator:": "Active LLM Orchestrator / 活跃 LLM Orchestrator / 大模型编排器:",
  "PROVIDER SYNCED": "PROVIDER SYNCED / 提供方已同步",
  "Activate Mode": "Activate Mode / 激活 Model / 模型",

  // Chat placeholders / messages
  "Ask @Builder, @Orchestrator or trigger @Workflow...": "咨询 @Builder / 构建器, @Orchestrator / 编排器 或触发 @Workflow / 工作流...",
  "Ask your AI Agent anything...": "咨询您的 AI Agent / 智能体 任何问题...",
  "Run Workflow": "Run Workflow / 运行工作流",
  "Run SOP": "Run SOP / 运行 SOP",
  "Start a supervised session": "开始新的监督会话",
  "Select a workspace and start a workflow, or type an instruction below. Clutch will orchestrate Builder / Evaluator and ask for your approval when needed.": "选择工作区并启动工作流，或直接在下方输入指令。Clutch 会编排 Builder / Evaluator 并在需要时请你审批。",
  "Authorize workspace": "授权工作区",
  "Choose workflow template": "选择工作流模板",
  "Workflow running": "工作流运行中",
  "Receiving sidecar events": "监督台正在接收 Sidecar 事件…",
  "Human gate hint": "检查未通过或需要人工确认，请选择下一步操作。",
  "Retry instructions placeholder": "附加指令，例如 \"跳过语法检查直接打包\"",
  "No active workflow overview": "暂无运行中的工作流。启动模板或发送指令后，这里会显示 Token 统计与 Flow 进度。",
  "Authorize workspace files hint": "请先在侧栏添加项目文件夹，或点击 Authorize workspace。",
  "Workspace folder empty": "工作区为空。",
  "No terminal logs yet": "暂无日志。启动工作流后 Sidecar 输出会显示在这里。",
  "Session tokens accumulated": "本轮累计",
  "Select project folder": "选择项目根目录",
  "Add project folder": "添加项目文件夹",
  "No repositories yet. Use Add project folder or Authorize workspace to begin.": "尚无项目。请通过侧栏添加文件夹，或点击 Authorize workspace。",
  "New session": "新建会话",
  "Projects": "Projects / 项目",
  "No sessions in this project yet": "此项目下暂无会话",
  "Select a project before starting a conversation.": "请先选择项目，再开始对话。",
  "Settings": "Settings / 设置",

  // General Settings Panel
  "Developer Profiles": "Developer Profiles / 开发者角色配置",
  "Active Workspace Developer Profiles": "Active Workspace Developer Profiles / 活跃工作空间开发者配置",
  "Create, switch, or customize roles with tailored system prompt instructions, memory logs, and API allowances.": "创建、切换或定制具有量身定制的 System Prompt / 系统提示词指令、Memory / 内存日志和 API 配额的角色。",
  "Switch Profile": "Switch Profile / 切换 Profile / 角色",
  "ACTIVE PROFILE": "ACTIVE PROFILE / 活跃 Profile / 角色",
  "System Prompt / Directive": "System Prompt Directive / 系统 Prompt / 提示词指令",
  "Active Memory context": "Active Memory / 活跃 Memory / 内存上下文",
  "API Calls Allowance Limit": "API Calls Limit / API 调用次数限额",
  "Customize Active Instructions": "Customize System Prompts / 定制 System Prompt / 系统提示词指令",
  "Update Developer Settings": "Update Developer Settings / 更新开发者设置",
  "Save Custom Settings": "Save Custom Profiles / 保存自定义 Profile / 角色",

  // Agent Manager
  "AI Agents Registry": "AI Agents Registry / AI 智能体注册表",
  "Orchestrate, edit, and launch autonomous specialized agent personas with custom tool allocations and constraints.": "编排、编辑和启动具有自定义 Tool / 工具分配和约束的自治专业 Agent / 智能体角色。",
  "Create Custom Agent": "Create Custom Agent / 创建自定义 Agent / 智能体",
  "System Orchestrator Status: Active": "System Orchestrator / 系统编排器状态: ACTIVE / 活跃",
  "Active Agent Roles": "Active Agent Roles / 活跃 Agent / 智能体角色",
  "Define and manage agents and system roles.": "定义与管理 Agents / 智能体 及系统角色。",
  "Core Role Directive": "Core Directive / 核心 Directive / 指令/提示词",
  "Equipped Tools": "Equipped Tools / 装备 Tools / 工具",
  "Active Tasks Log": "Active Tasks Log / 活跃任务日志",
  "System Instruction Prompt": "System Custom Prompt / 系统指令 Prompt / 提示词",
  "Edit Agent Details": "Edit Agent Details / 编辑 Agent / 智能体详情",
  "Add Custom Agent Profile": "Add Agent Profile / 添加 Agent / 智能体属性",
  "Agent Name / Brand": "Agent Name / Agent / 智能体名称",
  "Primary Purpose": "Primary Purpose / 主要用途",
  "System Instructions prompt": "System Prompt Instructions / 系统指令 Prompt / 提示词",
  "Associated LLM Model": "Associated LLM Model / 关联 LLM Model / 大模型",
  "Add Agent Persona": "Add Agent Persona / 新增 Agent / 智能体",
  "Save Persona Settings": "Save Persona / 保存 Agent / 智能体设置",
  "Active Agent": "Active Agent / 活跃 Agent / 智能体",
  "Edit Persona": "Edit Persona / 编辑 Agent / 智能体角色",
  "Delete Persona": "Delete Persona / 删除 Agent / 智能体角色",

  // Workflow panel
  "Workflows Standard Operating Procedures": "Workflows SOP / 工作流 SOP / 标准作业程序",
  "Define, monitor, and execute step-by-step pipeline runs using automated agent interactions, validations, and artifact commits.": "通过自动化的 Agent / 智能体交互、验证和 Artifact / 交付物提交，定义、监控并执行分步 Pipeline / 管道流工作流。",
  "Create Custom SOP": "Create Custom SOP / 创建自定义 Workflows SOP / 工作流标准作业程序",
  "Total Flows Loaded": "Total Flows Loaded / 已加载 Workflows / 工作流总数",
  "Flow status:": "Flow status / Workflows / 工作流状态:",
  "Flow Tasks SOP Progress": "Flow Tasks Progress / Workflows SOP / 任务进度",
  "Run Active SOP": "Run Active SOP / 执行活跃 SOP / 工作流",
  "Running Flow SOP Execution...": "Running SOP Execution / 正在执行 SOP / 工作流中...",
  "Workflow execution successfully finished!": "Workflow / 工作流 SOP 执行成功完毕！",
  "Select a flow sequence to inspect execution.": "选择一个 Flow / 工作流序列来检查执行状态。",
  "Step Details": "Step Details / 步骤详情",
  "Target Persona / Agent": "Target Persona / Agent / 目标智能体",
  "Mock Output Artifact": "Mock Output Artifact / 交付成果物 / Artifact",
  "View Generated Flow Output": "View SOP Output / 查看生成的 SOP / 工作流结果",

  // AI Tools page
  "AI Tools Registry & Sandbox": "AI Tools Registry / AI 工具注册中心与沙箱",
  "Integrate, configure, and sand-box server-side functions and client APIs usable by connected agents for live task completion.": "集成、配置和沙盒化服务端 Function / 函数和客户端 API，供已连接的 Agents / 智能体用于实时任务完成。",
  "Add Custom Tool Plugin": "Add Custom Tool Plugin / 添加自定义 Tool / 工具插件",
  "Register New Tool Extension": "Register New Tool / 注册新 Tool / 工具",
  "Tool Label": "Tool Label / 工具标签",
  "Execution Hook": "Execution Hook / 执行 Hook / 钩子",
  "Plugin Source Script": "Plugin Source Script / 插件 Source / 源码脚本",
  "Register Tool Plugin": "Register Tool Plugin / 注册 Tool / 工具",
  "Connected Tool Providers": "Connected Tool Providers / 已连接的 Tool / 工具提供方",
  "Developer sandbox execution test:": "Developer sandbox execution / 开发者沙盒执行测试:",
  "Test Tool Execution": "Test Tool / 测试 Tool / 工具",
  "ACTIVE / ONLINE": "ACTIVE / ONLINE / 活跃上线",
  "SIMULATION OK": "SIMULATION OK / 模拟状态正常",
  "Active Sandbox Logs:": "Active Sandbox Logs / 活跃沙盒日志",

  // Skills registry page
  "Skills Library Index": "Skills Library Index / 技能库索引",
  "Provision pre-defined behavior trees, domain patterns, and schema blueprints directly into agent contextual memory.": "直接将预定义的行为树、领域模式和 Schema / 架构蓝图注入 Agent / 智能体上下文 Memory / 内存空间中。",
  "Add Domain Skill Capability": "Add Domain Skill / 添加领域 Skill / 技能",
  "System Skills Loaded": "System Skills Loaded / 已加载系统 Skills / 技能",
  "Register Skill Tree Extension": "Register Skill / 注册 Skill / 技能",
  "Skill Label / Name": "Skill Label / 技能名称",
  "System Prompt Capability Overlay": "Prompt Overlay / 提示词叠加 / Prompt Overlay",
  "Inject Skill Override": "Inject Skill Override / 注入 Skill / 技能",
  "Active Domain Skills": "Active Domain Skills / 活跃领域 Skills / 技能",
  "Status": "Status / 状态",
  "LOADED / ONLINE": "LOADED / ONLINE / 已加载上线",

  // MCP Servers
  "Model Context Protocol Gateways": "Model Context Protocol Gateways / Model Context Protocol (MCP) 服务网关",
  "Connect and manage secure remote contextual backends, SQL servers, filesystem sockets, and public API registries supporting the MCP protocol.": "连接并管理支持 MCP 协议的远程 contextual / 上下文后端、SQL 数据库、文件系统套接字和公共 API 注册表。",
  "Add Remote MCP Hub Connecting Sockets": "Add Remote MCP Hub / 连接远程 MCP 服务组",
  "Connected MCP Sockets": "Connected MCP Sockets / 已连接的 MCP 节点",
  "Open Connection Sockets": "Open Connection Sockets / 打开连接节点",
  "Configure Remote MCP Server Node": "Configure MCP Node / 配置 MCP 节点",
  "Socket Hook Name": "Socket Hook Name / 节点钩子名称",
  "Transport Layer Mode": "Transport Layer Mode / 传输层模式",
  "Endpoint Transport URL": "Transport URL / 传输层 URL",
  "Register Node": "Register MCP Node / 注册 MCP 节点",
  "ONLINE / ACTIVE": "ONLINE / ACTIVE / 在线活跃",
  "ACTIVE CONNECTION OK": "ACTIVE CONNECTION OK / 活跃连接正常",

  // Base Header
  "Single Agent": "Single Agent / 单智能体",
  "Multi-Agent": "Multi-Agent / 多智能体",
  "Workspace theme updated to:": "Workspace Theme / 配色主题更新为:",
  "Active LLM Orchestrator": "Active LLM Orchestrator / 活跃 LLM 编排器",

  // Theme presets
  "Pristine Light": "Pristine Light / 极简白",
  "Clean Hanken aesthetic with spacious negative spaces and absolute neutral shades.": "极简 Hanken 设计风格，配有宽敞的负空间和绝对纯净的自然色彩预设。",
  "Cyberpunk Neon": "Cyberpunk Neon / 赛博霓虹",
  "Vibrant high-contrast dark theme with fluorescent purple, cyan, pink accents, and absolute neon shadows.": "高饱和度对比的暗黑主题，配有荧光紫、青色、粉色点缀与霓虹灯阴影效果。",
  "Nordic Frost": "Nordic Frost / 北欧冰霜",
  "Serene soft-blue cool theme inspired by cold scandinavian winter, slate cliffs, and pine forests.": "受北欧严冬、石板悬崖和松林启发的松绿与淡蓝色冰霜极简格调方案。",
  "Slate Charcoal": "Slate Charcoal / 石板深灰",
  "Ultra-professional eye-saving dark theme focused on graphite shades, subtle borders, and steel tones.": "超干练眼部友好的深灰墨黑方案，聚焦于石墨黑、细腻纤薄边框和冷钢色调设计。",
  "Terminal Green": "Terminal Green / 终端绿",
  "Vintage matrix-style monochrome retro aesthetic showcasing glowing emerald typography and pure terminal layouts.": "复古 Matrix 终端单色美学，展现发光祖母绿字符与纯粹极客命令行布局样式。",

  // Theme UI components
  "Active": "Active / 活跃启用",
  "Palette:": "Palette / 配色:",
  "Background": "Background / 背景色",
  "Surface": "Surface / 界面色",
  "Text color": "Text / 文字色",
  "Accent primary": "Primary / 核心主调",
  "Select": "Select / 选择应用"
};

// Simple auto-translator to handle terms containing professional words
const translateText = (text: string, language: Language): string => {
  if (language === 'en') return text;
  
  // Clean whitespace for matching
  const trimmed = text.trim();
  if (zhTranslations[trimmed]) {
    return zhTranslations[trimmed];
  }

  // Handle substring replacements for AI professional words
  let result = trimmed;
  
  // Define custom regex maps for professional terms
  const termsMap = [
    { regex: /\bMulti-Agent\b/gi, replacement: "Multi-Agent / 多智能体" },
    { regex: /\bSingle-Agent\b/gi, replacement: "Single-Agent / 单智能体" },
    { regex: /\b(AI\s+)?Agent(s)?\b/gi, replacement: "Agent / 智能体" },
    { regex: /\b(LLM\s+)?Model(s)?\b/gi, replacement: "Model / 模型" },
    { regex: /\bWorkflow(s)?\b/gi, replacement: "Workflow / 工作流" },
    { regex: /\bPrompt(s)?\b/gi, replacement: "Prompt / 提示词" },
    { regex: /\bSkill(s)?\b/gi, replacement: "Skill / 技能" },
    { regex: /\b(AI\s+)?Tool(s)?\b/gi, replacement: "Tool / 工具" }
  ];

  for (const item of termsMap) {
    if (item.regex.test(result)) {
      result = result.replace(item.regex, item.replacement);
      // Once translated key structural words, we can also perform generic translations 
      // of layout actions to make it beautiful
    }
  }

  // Match other common dynamic structures:
  if (result === "New Chat / Reset") return "New Chat / 重置";
  if (result === "Close Panel") return "Close Panel / 关闭面板";
  if (result === "Collapse Sidebar") return "Collapse Sidebar / 折叠侧边栏";
  if (result === "Expand Sidebar") return "Expand Sidebar / 展开侧边栏";
  if (result === "Status Overview") return "Status Overview / 状态概览";

  return result;
};

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    const saved = localStorage.getItem('workspace_lang');
    return (saved === 'zh' || saved === 'en') ? saved : 'en';
  });

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem('workspace_lang', lang);
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
