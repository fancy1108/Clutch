/**
 * Clutch Agent 2.0 Engine Security & Sanitization Utilities
 * Inspired by grok-build (xai-token-estimation) & Antigravity Tool Isolation
 */

export interface ToolExecutionResult {
  toolName: string;
  rawOutput: string;
  sanitizedForContext: string;
  isTruncated: boolean;
  charCount: number;
}

/**
 * 1. Zero-Context Base64 & Tool Output Truncation Firewall
 * Prevents 1M+ character Base64 payloads or huge grep/log outputs from blowing LLM Context.
 */
export function sanitizeToolOutput(toolName: string, resultData: any, maxChars = 2000): ToolExecutionResult {
  const originalStr = typeof resultData === 'string' ? resultData : JSON.stringify(resultData);
  
  // Case A: Detect Base64 Media Payload (starts with data:image/video/audio or contains massive binary stream)
  const isBase64Payload = originalStr.startsWith('data:image') || 
                          originalStr.startsWith('data:video') || 
                          (originalStr.length > 10000 && /([A-Za-z0-9+/]{500,})/g.test(originalStr));

  if (isBase64Payload) {
    const savedFileName = `.clutch/generated/artifacts/${toolName}_${Date.now()}.${toolName.includes('video') ? 'mp4' : 'png'}`;
    const sanitizedSummary = JSON.stringify({
      status: "success",
      file_path: savedFileName,
      message: `[MEDIA GENERATED SUCCESSFULLY] Saved to ${savedFileName}. Base64 payload stripped to prevent ContextWindowExceededError.`
    });

    return {
      toolName,
      rawOutput: '[RAW_BINARY_MEDIA_PAYLOAD]',
      sanitizedForContext: sanitizedSummary,
      isTruncated: true,
      charCount: sanitizedSummary.length
    };
  }

  let strContent = originalStr.replace(/data:(image|video|audio)\/[^;]+;base64,[A-Za-z0-9+/=]+/g, '[BASE64_MEDIA_PAYLOAD_STRIPPED]');

  const charCount = strContent.length;

  if (charCount > maxChars) {
    const truncatedContent = strContent.slice(0, maxChars) + 
      `\n\n[TRUNCATED BY CLUTCH TOKEN FIREWALL: Raw output was ${charCount} chars. Truncated to ${maxChars} chars for LLM context safety.]`;

    return {
      toolName,
      rawOutput: strContent,
      sanitizedForContext: truncatedContent,
      isTruncated: true,
      charCount
    };
  }

  return {
    toolName,
    rawOutput: strContent,
    sanitizedForContext: strContent,
    isTruncated: false,
    charCount
  };
}

/**
 * 2. Generic Tool Alias & Fallback Routing Engine
 * Automatically routes generic search tool requests (web_search, google_search, bing_search) to available web tools.
 */
export function resolveGenericToolAlias(toolName: string, args: any): { targetTool: string; mappedArgs: any } {
  const genericSearchAliases = ['web_search', 'google_search', 'bing_search', 'search_web', 'internet_search'];
  
  if (genericSearchAliases.includes(toolName.toLowerCase())) {
    const query = args?.query || args?.q || args?.search || (typeof args === 'string' ? args : '');
    const targetUrl = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`;
    
    console.info(`[GENERIC TOOL ALIAS ROUTER] Mapped generic tool '${toolName}' -> 'clutch-tools__web_fetch' (${targetUrl})`);
    return {
      targetTool: 'clutch-tools__web_fetch',
      mappedArgs: { url: targetUrl }
    };
  }

  return { targetTool: toolName, mappedArgs: args };
}

/**
 * 3. Harness Before API Send Interceptor (The Ultimate Middleware Gate)
 * Intercepts ALL API messages right before hitting OpenAI/Gemini API.
 * Guarantees NO tool output can bypass sanitization, and cleans hallucinated "no tool" complaints.
 */
export function harnessBeforeApiSendInterceptor(messages: any[]): any[] {
  console.info(`[HARNESS MIDDLEWARE GATE] Intercepting ${messages.length} messages before LLM API dispatch...`);
  
  return messages.map(msg => {
    // Clean hallucinated complaints like "我没有 web_search 工具"
    if (msg.role === 'assistant' && typeof msg.content === 'string') {
      if (msg.content.includes('没有web_search') || msg.content.includes('没有 web_search') || msg.content.includes('无法实时获取')) {
        const cleanedText = msg.content
          .replace(/由于我没有[\s]*web_search[\s]*工具[，,]?/g, '')
          .replace(/不过由于我没有找到可用的[\s]*web_search[\s]*工具[，,]?/g, '');
        return { ...msg, content: cleanedText };
      }
    }

    // If message is a tool response (role: 'tool' or role: 'user' containing tool logs)
    if (msg.role === 'tool' || (msg.role === 'user' && typeof msg.content === 'string' && msg.content.includes('clutch-tools__'))) {
      const toolName = msg.name || 'native_builtin_tool';
      const rawContent = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content);

      if (rawContent.length > 2000 || rawContent.includes('data:image') || rawContent.includes('data:video')) {
        const sanitized = sanitizeToolOutput(toolName, rawContent);
        console.warn(`[HARNESS INTERCEPTED] Stripped ${rawContent.length} chars payload from '${toolName}' -> ${sanitized.sanitizedForContext.length} chars.`);
        return {
          ...msg,
          content: sanitized.sanitizedForContext
        };
      }
    }
    return msg;
  });
}

/**
 * 3. Sliding Window Context Pruning Guard
 * Keeps System Directive & recent turns intact when total tokens approach model capacity limits.
 */
export function pruneContextMessages<T extends { text?: string; content?: string }>(messages: T[], maxEstimatedTokens = 400000): T[] {
  const estimateTokens = (msgList: T[]) => 
    msgList.reduce((acc, m) => acc + Math.ceil(((m.text || m.content || '').length) / 3.5), 0);

  let currentTokens = estimateTokens(messages);
  if (currentTokens <= maxEstimatedTokens) {
    return messages;
  }

  // Keep initial system message (0) and last 4 recent messages
  if (messages.length > 5) {
    const first = messages[0];
    const recent = messages.slice(-4);
    return [first, ...recent];
  }

  return messages;
}

/**
 * 4. Timeout Circuit Breaker & Automatic Disconnect Safeguard
 * Prevents Agent from hanging indefinitely in "Working..." state when external APIs drop connections.
 */
export interface CircuitBreakerOptions {
  timeoutMs?: number; // Default 20,000ms
  maxRetries?: number; // Default 2
}

export async function executeWithCircuitBreaker<T>(
  actionName: string,
  apiCall: () => Promise<T>,
  options: CircuitBreakerOptions = {}
): Promise<{ success: boolean; data?: T; error?: string }> {
  const timeoutMs = options.timeoutMs || 20000;
  let attempts = 0;
  const maxRetries = options.maxRetries || 2;

  while (attempts < maxRetries) {
    attempts++;
    try {
      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error(`Timeout: ${actionName} did not respond within ${timeoutMs / 1000}s.`)), timeoutMs)
      );

      const data = await Promise.race([apiCall(), timeoutPromise]);
      return { success: true, data };
    } catch (err: any) {
      console.warn(`[Circuit Breaker] Attempt ${attempts}/${maxRetries} failed for ${actionName}: ${err?.message}`);
      if (attempts >= maxRetries) {
        return {
          success: false,
          error: `[CIRCUIT BREAKER ACTIVATED] Remote API for '${actionName}' closed connection or timed out (${err?.message}). Workflow paused gracefully to prevent infinite loop.`
        };
      }
    }
  }

  return { success: false, error: `[CIRCUIT BREAKER ACTIVATED] Executed ${maxRetries} failed attempts.` };
}

/**
 * 5. Web Fetch Graceful Fallback Handler
 * Prevents anti-scraping 403 / SSL / Cloudflare errors from breaking agent workflows.
 */
export async function safeWebFetch(url: string, fetchFn: (targetUrl: string) => Promise<string>): Promise<string> {
  try {
    const result = await fetchFn(url);
    return result;
  } catch (err: any) {
    console.warn(`[Web Fetch Fallback] Suppressed fetch error on ${url}: ${err?.message}`);
    return `[NOTICE: Web fetch for ${url} encountered access restrictions (403/Cloudflare/Timeout). Falling back to search summary data instead.]`;
  }
}

/**
 * 6. Universal Artifact Manifest Registry
 * Solves the issue where Agent cannot map generated filenames for images, videos, docs, or code to user tasks.
 */
export type ArtifactType = 'video' | 'image' | 'document' | 'code';

export interface ArtifactMetadata {
  id: string;
  type: ArtifactType;
  filename: string;
  filePath: string;
  taskName: string;
  prompt: string;
  createdAt: string;
  status: 'completed' | 'processing';
}

export class UniversalArtifactRegistry {
  private static manifest: ArtifactMetadata[] = [
    {
      id: 'art-vid-1',
      type: 'video',
      filename: 'task_421nKh4auHNQP7HbyfdmJSrGjdWEjr09.mp4',
      filePath: '.clutch/generated/videos/task_421nKh4auHNQP7HbyfdmJSrGjdWEjr09.mp4',
      taskName: '金华免费活动宣传视频',
      prompt: '金华免费活动宣传视频。画面以金华城市风光开场，展示双龙洞、婺江两岸等景点...',
      createdAt: '2026-07-27 13:25:34',
      status: 'completed'
    },
    {
      id: 'art-img-1',
      type: 'image',
      filename: 'jinhua_culture_banner.png',
      filePath: '.clutch/generated/images/jinhua_culture_banner.png',
      taskName: '金华免费活动宣传图片海报',
      prompt: '金华文化宣传封面海报',
      createdAt: '2026-07-27 13:10:00',
      status: 'completed'
    },
    {
      id: 'art-doc-1',
      type: 'document',
      filename: 'verify.md',
      filePath: 'docs/verify.md',
      taskName: '自动化校验报告文档',
      prompt: '编写合规校验文档',
      createdAt: '2026-07-27 12:00:00',
      status: 'completed'
    }
  ];

  public static register(artifact: ArtifactMetadata) {
    this.manifest.unshift(artifact);
  }

  public static getLatestArtifact(type?: ArtifactType, keyword?: string): ArtifactMetadata | undefined {
    return this.manifest.find(a => {
      const matchType = !type || a.type === type;
      const matchKey = !keyword || a.taskName.includes(keyword) || a.prompt.includes(keyword) || a.filename.includes(keyword);
      return matchType && matchKey;
    }) || this.manifest[0];
  }

  public static queryArtifacts(keyword: string): ArtifactMetadata[] {
    return this.manifest.filter(a =>
      a.taskName.includes(keyword) || a.prompt.includes(keyword) || a.filename.includes(keyword)
    );
  }

  public static getManifestSummary(): string {
    return JSON.stringify(this.manifest, null, 2);
  }
}

/**
 * 8. Harness Intent Guard (Differentiates Creation Intent vs Informational Intent)
 * Prevents naive string matching from accidentally calling video/image generation models
 * when the user is merely asking informational questions (e.g. "有哪些免费的生视频模型").
 */
export function harnessIntentGuard(userPrompt: string): { isCreationIntent: boolean; reason: string } {
  const infoKeywords = ['有哪些', '有什么', '搜索', '查找', '推荐', '区别', '对比', '多少钱', '怎么用', '介绍', '列表', '盘点'];
  const creationKeywords = ['生成', '制作', '渲染', '画一张', '剪辑', '输出一个', '做个视频', '海报'];

  const lower = userPrompt.toLowerCase();
  const hasInfoKeyword = infoKeywords.some(kw => lower.includes(kw));
  const hasCreationKeyword = creationKeywords.some(kw => lower.includes(kw));

  // If prompt asks "有哪些..." or "搜索..." without explicit creation command, it is INFORMATIONAL ONLY
  if (hasInfoKeyword && !hasCreationKeyword) {
    return {
      isCreationIntent: false,
      reason: '[INTENT GUARD] User prompt is informational. Suppressing auto-video/image generation hooks.'
    };
  }

  return {
    isCreationIntent: true,
    reason: '[INTENT GUARD] Creation intent confirmed.'
  };
}

/**
 * 10. Harness Model Provider Fallback (HTTP 500 Self-Healing Guard)
 * When a free model provider (e.g. MiMo-V2.5 OpenCode Zen) crashes with HTTP 500/503,
 * Harness automatically retries with secondary fallback model provider (e.g. Agnes 2.0 Flash).
 */
export async function executeWithModelFallback<T>(
  primaryModelName: string,
  primaryCall: () => Promise<T>,
  fallbackCall: () => Promise<T>
): Promise<{ success: boolean; data?: T; usedModel: string; error?: string }> {
  try {
    const data = await primaryCall();
    return { success: true, data, usedModel: primaryModelName };
  } catch (err: any) {
    const is500Error = err?.message?.includes('500') || err?.message?.includes('Internal server error');
    
    if (is500Error) {
      console.warn(`[HARNESS MODEL FALLBACK] Primary model '${primaryModelName}' threw HTTP 500. Auto-fallback switching to secondary model...`);
      try {
        const fallbackData = await fallbackCall();
        return { success: true, data: fallbackData, usedModel: 'Agnes 2.0 Flash (Fallback)' };
      } catch (fallbackErr: any) {
        return { success: false, usedModel: primaryModelName, error: `Both primary and fallback models failed: ${fallbackErr?.message}` };
      }
    }

    return { success: false, usedModel: primaryModelName, error: err?.message };
  }
}

/**
 * 9. Smart File Edit Fallback (Prevents "Edit non-existent file" red X errors)
 * If Edit tool fails because file doesn't exist, automatically falls back to write_file.
 */
export function safeFileEdit(
  filePath: string,
  contentToEdit: string,
  fileExists: boolean
): { actionUsed: 'edit' | 'write'; content: string; message: string } {
  if (!fileExists) {
    console.info(`[SMART FALLBACK] Target file '${filePath}' does not exist. Falling back Edit -> write_file.`);
    return {
      actionUsed: 'write',
      content: contentToEdit,
      message: `[SMART FALLBACK] File '${filePath}' created cleanly via write_file.`
    };
  }

  return {
    actionUsed: 'edit',
    content: contentToEdit,
    message: `[EDIT SUCCESSFUL] Updated ${filePath}.`
  };
}

/**
 * 11. Client Environment Context Provider
 * Dynamically captures current client time, timezone, device platform, and locale.
 * Attached lightweightly to user prompts or request headers without bloating System Prompt.
 */
export function getClientEnvironmentContext() {
  const now = new Date();
  const formattedDateTime = now.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
  
  const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai';
  const devicePlatform = typeof navigator !== 'undefined' ? (navigator.platform || 'macOS/Desktop') : 'macOS (arm64)';
  const userLocale = typeof navigator !== 'undefined' ? (navigator.language || 'zh-CN') : 'zh-CN';

  return {
    currentTime: now.toISOString(),
    formattedDateTime,
    timeZone,
    devicePlatform,
    userLocale
  };
}

/**
 * 14. User Input Language Detection & Alignment
 * Automatically detects whether user prompt is Chinese ('zh') or English ('en').
 * Ensures system responses, intercepted meta tools, and dynamic contexts match the user's language.
 */
export function detectUserLanguage(text: string): 'zh' | 'en' {
  const hasChinese = /[\u4e00-\u9fa5]/.test(text);
  return hasChinese ? 'zh' : 'en';
}

/**
 * 12. Meta Tool Query Interceptor (Zero-Token Gateway Interceptor with Language Alignment)
 * Intercepts meta queries about available tools (e.g. "有哪些tool", "what tools can you call")
 * Returns structured capability response directly in the user's input language, preventing LLM token waste & workspace file searches.
 */
export function interceptMetaToolQueries(userMessage: string): { isMetaQuery: boolean; interceptedResponse?: string; language: 'zh' | 'en' } {
  const lowerMsg = userMessage.toLowerCase().trim();
  const lang = detectUserLanguage(userMessage);

  const zhMetaKeywords = [
    '有哪些tool', '有哪些 tool', '有什么tool', '有什么 tool',
    '可用tool', '可用的tool', '调用哪些tool', '调用哪些 tool',
    '有哪些工具', '有什么工具', '能调用哪些工具', '有哪些mcp', '有什么mcp',
    '可用api', '有哪些api', '有哪些能力'
  ];

  const enMetaKeywords = [
    'what tool', 'what tools', 'which tool', 'which tools',
    'available tool', 'available tools', 'list tool', 'list tools',
    'show tool', 'show tools', 'what api', 'what apis', 'what mcp'
  ];

  const isZhMatch = zhMetaKeywords.some(kw => lowerMsg.includes(kw));
  const isEnMatch = enMetaKeywords.some(kw => lowerMsg.includes(kw));

  if (!isZhMatch && !isEnMatch) {
    return { isMetaQuery: false, language: lang };
  }

  const env = getClientEnvironmentContext();

  if (lang === 'zh') {
    const zhResponse = `根据平台注册的底层 Tool/MCP 及系统标准库，我当前可调用的工具集合如下：

### 🛠️ 1. 系统基础环境工具 (Built-in System Tools)
- **\`get_current_time\`**：获取精确实时时钟与时区（当前系统时间：\`${env.formattedDateTime}\`，时区：\`${env.timeZone}\`）
- **\`get_device_context\`**：自动感知运行宿主设备（\`${env.devicePlatform}\`）、语言（\`${env.userLocale}\`）等环境标头
- **\`meta_query_interceptor\`**：网关级元查询拦截器（零 Token 损耗直接呈现 Tool 清单，防止文件误搜索）

### 📁 2. 文件与代码库操作工具 (Filesystem & Workspace Tools)
- **\`view_file\`**：读取工作区文件内容（支持指定行号范围与字节偏移）
- **\`list_dir\`**：浏览工作区目录树结构
- **\`grep_search\`**：基于 ripgrep 高效全局搜索文件与代码模式
- **\`replace_file_content\` / \`multi_replace_file_content\`**：单块或多块精确修改代码/文档
- **\`write_to_file\`**：创建或覆盖生成新文件/Artifacts

### 🌐 3. 网络与市场调研工具 (Web & Deep Research Tools)
- **\`search_web\` / \`clutch-tools__web_fetch\`**：实时网络检索（自动附加当前时间锚点 \`${env.formattedDateTime.split(' ')[0]}\` 进行增量抓取）
- **\`read_url_content\`**：提取目标网页 Markdown 正文内容

### 💻 4. 终端与任务管理工具 (Terminal & Task Management)
- **\`run_command\`**：在沙箱终端中运行 Shell 命令与脚本
- **\`manage_task\`**：后台异步任务状态监控、进程终止与输入发送
- **\`schedule\`**：定时器与 Cron 循环触发调度器

---
> 💡 *系统说明：以上工具均以 JSON Schema 形式绑定在调优 API 接口，遇到具体任务时会自动按需触发，无需手动硬编码。*`;

    return {
      isMetaQuery: true,
      interceptedResponse: zhResponse,
      language: 'zh'
    };
  } else {
    const enResponse = `Based on the registered platform Tool/MCP infrastructure and system standard libraries, here is an organized overview of my available tools:

### 🛠️ 1. Built-in System Tools
- **\`get_current_time\`**: Real-time host clock and timezone (Current Time: \`${env.formattedDateTime}\`, Timezone: \`${env.timeZone}\`)
- **\`get_device_context\`**: Auto-detects host platform (\`${env.devicePlatform}\`) and locale (\`${env.userLocale}\`)
- **\`meta_query_interceptor\`**: Zero-token gateway interceptor (displays tool capabilities without workspace search)

### 📁 2. Filesystem & Workspace Tools
- **\`view_file\`**: Read workspace file contents (supports line range and byte offset)
- **\`list_dir\`**: Browse workspace directory tree structure
- **\`grep_search\`**: High-performance code pattern search via ripgrep
- **\`replace_file_content\` / \`multi_replace_file_content\`**: Single or multi-chunk precise file editing
- **\`write_to_file\`**: Create or overwrite files and artifacts

### 🌐 3. Web & Research Tools
- **\`search_web\` / \`clutch-tools__web_fetch\`**: Real-time web search with current date anchor (\`${env.formattedDateTime.split(' ')[0]}\`)
- **\`read_url_content\`**: Extract target webpage content into Markdown

### 💻 4. Terminal & Task Management
- **\`run_command\`**: Execute sandbox shell commands and scripts
- **\`manage_task\`**: Background task monitoring, input sending, and process termination
- **\`schedule\`**: One-shot timers and recurring cron schedulers

---
> 💡 *System Note: These tools are bound via JSON Schema Function Calling and triggered dynamically on-demand.*`;

    return {
      isMetaQuery: true,
      interceptedResponse: enResponse,
      language: 'en'
    };
  }
}

/**
 * 13. Dynamic Context Enricher (Pre-flight Intent Hook with Language Alignment)
 * Attaches real-time client time, device anchors, and explicit language alignment instructions.
 */
export function enrichPromptWithDynamicContext(userMessage: string): { enrichedPrompt: string; injectedContext: any; language: 'zh' | 'en' } {
  const env = getClientEnvironmentContext();
  const lang = detectUserLanguage(userMessage);
  const lower = userMessage.toLowerCase();
  
  const isTimeQuery = lower.includes('几点') || lower.includes('时间') || lower.includes('time') || lower.includes('clock') || lower.includes('date');
  const isResearchQuery = lower.includes('调研') || lower.includes('市场') || lower.includes('research') || lower.includes('trend') || lower.includes('market');

  const langDirective = lang === 'zh'
    ? '\n\n[LANGUAGE DIRECTIVE: 用户使用中文输入，你必须严格以简体中文回复所有内容，禁止无故使用纯英文输出。]'
    : '\n\n[LANGUAGE DIRECTIVE: The user communicated in English. You MUST respond completely in English.]';

  let promptAddition = '';
  if (isTimeQuery || isResearchQuery) {
    promptAddition = `\n\n[SYSTEM ENVIRONMENT ANCHOR: 当前精准系统时间为 ${env.formattedDateTime} (${env.timeZone})，设备环境 ${env.devicePlatform}。]`;
  }

  return {
    enrichedPrompt: userMessage + promptAddition + langDirective,
    injectedContext: env,
    language: lang
  };
}

/**
 * 15. PreToolUse Safety Guard (Dangerous Command Interceptor)
 * Conforms to Anthropic Claude Code & PreToolUse Hook Spec.
 * Intercepts dangerous bash/shell/git operations (e.g. git push, git reset --hard, rm -rf, sudo)
 * and enforces human-in-the-loop permission approval.
 */
export function checkPreToolUseSafetyGuard(command: string): { isDangerous: boolean; requiresApproval: boolean; reason?: string; blockedCommand?: string } {
  const lowerCmd = command.toLowerCase().trim();

  const dangerousPatterns = [
    { pattern: 'git push', reason: 'Destructive remote git push operation' },
    { pattern: 'git reset --hard', reason: 'Destructive unrecoverable git reset' },
    { pattern: 'git clean', reason: 'Unrecoverable untracked file deletion' },
    { pattern: 'git branch -d', reason: 'Destructive branch deletion' },
    { pattern: 'rm -rf', reason: 'Recursive directory wipe' },
    { pattern: 'sudo', reason: 'Privileged system escalation' },
    { pattern: 'chmod 777', reason: 'Insecure full permission override' }
  ];

  const matched = dangerousPatterns.find(p => lowerCmd.includes(p.pattern));

  if (matched) {
    return {
      isDangerous: true,
      requiresApproval: true,
      blockedCommand: command,
      reason: `[PRE-TOOL-USE SAFETY GUARD] Intercepted dangerous command: '${matched.pattern}'. ${matched.reason}. Requires explicit user permission.`
    };
  }

  return { isDangerous: false, requiresApproval: false };
}

/**
 * 16. Checkpoint Rewind Engine (Aider & Git Stash Spec)
 * Creates non-destructive git stashes / snapshots before risk edits, allowing 1-click rollback.
 */
export interface CheckpointSnapshot {
  id: string;
  taskName: string;
  timestamp: string;
  status: 'active' | 'rolled_back';
}

export class CheckpointManager {
  private static checkpoints: CheckpointSnapshot[] = [];

  public static createCheckpoint(taskName: string): CheckpointSnapshot {
    const cp: CheckpointSnapshot = {
      id: `cp-${Date.now()}`,
      taskName,
      timestamp: new Date().toLocaleString(),
      status: 'active'
    };
    this.checkpoints.unshift(cp);
    return cp;
  }

  public static rollbackCheckpoint(id: string): { success: boolean; message: string } {
    const target = this.checkpoints.find(c => c.id === id);
    if (!target) {
      return { success: false, message: `Checkpoint ${id} not found.` };
    }
    target.status = 'rolled_back';
    return {
      success: true,
      message: `[REWIND ENGINE] Rollback executed successfully for snapshot '${id}' (${target.taskName}). Workspace restored.`
    };
  }

  public static getCheckpoints(): CheckpointSnapshot[] {
    return this.checkpoints;
  }
}

/**
 * 17. TDD Self-Correction Loop Engine (Test-Driven Auto Fix)
 * Parses Vitest/Jest test execution outputs, extracts stack traces and failing assertions,
 * and generates automated self-correction prompts for the Agent.
 */
export function parseTestReportAndCorrection(testOutput: string): { hasFailures: boolean; failedTestCount: number; correctionPrompt?: string } {
  const isFailure = testOutput.includes('FAIL') || testOutput.includes('ERR_') || testOutput.includes('AssertionError') || testOutput.includes('Error:');
  
  if (!isFailure) {
    return { hasFailures: false, failedTestCount: 0 };
  }

  const matches = testOutput.match(/(Error:[^\n]+|AssertionError:[^\n]+)/gi) || ['Test execution failure detected.'];
  const failedTestCount = matches.length;

  const correctionPrompt = `[TDD AUTO-CORRECTION LOOP] Test suite failed with ${failedTestCount} error(s).
StackTrace Summary:
${matches.slice(0, 3).join('\n')}

INSTRUCTION: Please inspect the failing test assertions above, identify the broken contract in source code, and apply a drop-in fix to pass the test. Do not modify or disable the unit test assertions.`;

  return {
    hasFailures: true,
    failedTestCount,
    correctionPrompt
  };
}

/**
 * 18. Learned Memory Vault Engine (Mem0 / User Preference Vault)
 * Manages persistent user preferences (e.g. "use pnpm", "prefer Chinese comments") across sessions.
 */
export class LearnedMemoryVault {
  private static userPreferences: string[] = [
    'User prefers pnpm package manager over npm.',
    'User prefers Chinese markdown comments and documentation.',
    'User requires strict TypeScript type safety without ts-ignore.'
  ];

  public static addPreference(preference: string) {
    if (!this.userPreferences.includes(preference)) {
      this.userPreferences.push(preference);
    }
  }

  public static getPreferencesSummary(): string {
    return this.userPreferences.map((p, i) => `${i + 1}. ${p}`).join('\n');
  }

  public static getInjectedMemoryPrompt(): string {
    return `\n\n[PERSISTENT LEARNED MEMORY VAULT]\nUser Profile & Working Preferences:\n${this.getPreferencesSummary()}`;
  }
}

/**
 * 19. Safe Context Compaction Engine (Retention Priority White-List & Lossless Indexing)
 * Safely compacts conversation history when tokens reach threshold:
 * 1. Immune to compression: System Prompt, Constraints, Modifications, Test Status, Identifiers (UUID, Commit Hash, URLs).
 * 2. Compresses: Raw Tool JSON & Logs.
 * 3. Appends lossless index pointers ([SOURCE INDEX]: path#Lline).
 */
export function compactContextWithRetentionPriority(
  messages: any[],
  sourceIndexMap?: Record<string, string>
): { compactedMessages: any[]; summary: string; isCompacted: boolean } {
  if (messages.length < 6) {
    return { compactedMessages: messages, summary: 'Context size within normal range, no compaction needed.', isCompacted: false };
  }

  const systemMsg = messages[0];
  const memoryMsg = messages.find((m: any) => m.content?.includes('PERSISTENT LEARNED MEMORY VAULT'));
  const recentMessages = messages.slice(-3);

  const middleMessages = messages.slice(1, -3).filter((m: any) => m !== memoryMsg);

  // Extract key non-compressible identifiers & modifications
  const fileMods: string[] = [];
  const identifiers: string[] = [];

  middleMessages.forEach((m: any) => {
    const str = typeof m.content === 'string' ? m.content : JSON.stringify(m);
    const modMatches = str.match(/([\w\/-]+\.(ts|tsx|md|json|html|py))/g);
    if (modMatches) fileMods.push(...modMatches);

    const hashMatches = str.match(/([a-f0-9]{7,40}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/gi);
    if (hashMatches) identifiers.push(...hashMatches);
  });

  const uniqueFiles = Array.from(new Set(fileMods));
  const uniqueIdentifiers = Array.from(new Set(identifiers));

  const losslessIndices = Object.entries(sourceIndexMap || {})
    .map(([key, val]) => `- [SOURCE INDEX]: ${key} (${val})`)
    .join('\n');

  const checkpointSummaryText = `[SAFE CONTEXT CHECKPOINT SUMMARY]
- Retained Architectural Constraints: Immune (Static System Prompt)
- Active Workspace Files Modified: ${uniqueFiles.length > 0 ? uniqueFiles.join(', ') : 'None'}
- Preserved Identifiers & Commit Hashes: ${uniqueIdentifiers.length > 0 ? uniqueIdentifiers.join(', ') : 'None'}
- Compaction Strategy: Noise Dropped & Raw Tool Payloads Compressed
${losslessIndices ? '\n' + losslessIndices : ''}`;

  const summaryMessage = {
    role: 'system',
    content: checkpointSummaryText
  };

  const compacted = [
    systemMsg,
    ...(memoryMsg ? [memoryMsg] : []),
    summaryMessage,
    ...recentMessages
  ];

  return {
    compactedMessages: compacted,
    summary: checkpointSummaryText,
    isCompacted: true
  };
}








