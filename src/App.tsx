import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './sidebar';
import { ChatFeed } from './components/ChatFeed';
import { RightPanel } from './components/RightPanel';
import { WorkflowOrchestration } from './components/WorkflowOrchestration';
import { AgentManager, AgentLogo } from './components/AgentManager';
import AiToolsManager from './components/AiToolsManager';
import { MainView, RightTab, RunStatus, ChatMessage, UncommittedFile } from './types';
import {
  initialFolders,
  initialChatMessages,
  secondaryChatMessages,
  uncommittedFiles,
} from './mockData';
import {
  VideoManifestRegistry,
  UniversalArtifactRegistry,
  getClientEnvironmentContext,
  interceptMetaToolQueries,
  enrichPromptWithDynamicContext
} from './agentSanitizer';

export default function App() {
  // Navigation & Structure views
  const [currentView, setView] = useState<MainView>('chat');
  const [currentFlowName, setCurrentFlowName] = useState<string>('Video Production');
  const [isMultiAgent, setIsMultiAgent] = useState<boolean>(true);

  // Column Collapsing states
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);
  const [rightPanelOpen, setRightPanelOpen] = useState<boolean>(true);

  // File Preview state
  const [previewFile, setPreviewFile] = useState<{ name: string; content: string } | null>(null);

  // Repository list folders state
  const [folders, setFolders] = useState(initialFolders);

  // Sidebar selector width for calculations
  const selectedSidebarWidth = sidebarOpen ? 280 : 0;
  const rightSidebarWidth = rightPanelOpen ? 300 : 0;

  // Active Tab inside the right side panel (Overview, Files, Flow, Changes, Terminal)
  const [rightTab, setRightTab] = useState<RightTab>('overview');

  useEffect(() => {
    if (!isMultiAgent && rightTab === 'flow') {
      setRightTab('overview');
    }
    if (!isMultiAgent && currentView === 'workflows') {
      setView('chat');
    }
  }, [isMultiAgent, rightTab, currentView]);

  // Simulated Execution engine states
  const [runStatus, setRunStatus] = useState<RunStatus>('running');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(initialChatMessages);
  const [uncommitted, setUncommitted] = useState<UncommittedFile[]>(uncommittedFiles);
  const [terminalLogs, setTerminalLogs] = useState<string[]>(initialTerminalLogs);

  // Close unified settings dialog on ESC key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setView(prev => (prev === 'agents' || prev === 'settings' || prev === 'tools' || prev === 'workflows') ? 'chat' : prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleStopRun = () => {
    setRunStatus('failed');
    setTerminalLogs(prev => [
      ...prev,
      `[ORCHESTRATOR] Automatic repair workflow paused by supervisor.`
    ]);
  };

  // Chat Input Box State
  const [inputValue, setInputValue] = useState<string>('');

  // Handle switching folders/repos
  const handleFlowSelect = (flow: string) => {
    setCurrentFlowName(flow);
    if (flow === 'Missing bug fix in AI a...') {
      // Load different initial failures matching bugs
      setChatMessages([
        {
          id: 'bug-1',
          agent: 'Orchestrator',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p',
          time: '12:10 PM',
          text: 'Initiated issue scan in target repository branch main: looking block parsing crashes in src/main.tsx.'
        },
        {
          id: 'bug-2',
          agent: 'Builder',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b',
          time: '12:12 PM',
          text: 'Determined missing React import definition or JSX mismatch parameters. Resolving...',
        }
      ]);
      setRunStatus('passed');
    } else if (flow === 'Video Production' || flow === 'Vibe coding workspac...') {
      setChatMessages(initialChatMessages);
      setRunStatus('failed');
      setTerminalLogs(initialTerminalLogs);
      setUncommitted(uncommittedFiles);
    } else {
      setChatMessages([
        {
          id: 'gen-1',
          agent: 'Orchestrator',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p',
          time: '2:15 PM',
          text: `Ready stream established. No active validation failures recorded inside ${flow}.`
        }
      ]);
      setRunStatus('passed');
    }
  };

  // Simulated validation loop correction
  const handleReassignToBuilder = () => {
    setRunStatus('running');
    setRightTab('terminal');

    // Step 1 of simulation
    setTerminalLogs(prev => [
      ...prev,
      `[USER] Issued Re-assign to Builder command. Start Round 2 Repair.`,
      `[ORCHESTRATOR] Initializing hot patch subtask: Create missing verify.md`,
      `[BUILDER] Writing template checklist inside docs/verify.md...`,
    ]);

    // Step 2 of simulation
    setTimeout(() => {
      setTerminalLogs(prev => [
        ...prev,
        `[BUILDER] File docs/verify.md generated correctly. Adding artifact reference to manifest.`,
        `[BUILDER] Recompiled src/video-core/processor.ts. Code size: 104 KB`,
        `[BUILDER] Pushing latest commit changes to validation engine...`,
        `[EVALUATOR] Spawning compliance test runner ...`,
        `[EVALUATOR] TEST STATUS: 2 compliance modules executed. 0 warnings.`,
        `[EVALUATOR] PASS: verify.md successfully parsed.`
      ]);
    }, 1500);

    // Final outcome state
    setTimeout(() => {
      setRunStatus('passed');
      setRightTab('overview');

      // Append success message highlights
      setChatMessages(prev => [
        ...prev,
        {
          id: 'repair-success-builder',
          agent: 'Builder',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b',
          time: 'Just now',
          text: 'Repair successfully executed! I created docs/verify.md in workspace and committed processor.ts with the optimized validation checks.',
          codeHighlight: {
            file: 'docs/verify.md & src/video-core/processor.ts',
            lineCount: 2
          }
        },
        {
          id: 'repair-success-evaluator',
          agent: 'Evaluator',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCmb7VGaQXE-4sYnIZR3VrcHVAPhv4Px14kMlkayJj8kVm8htTWITmPi26wsj8P6B9RrqykIWj81S2ilmGR0e8cXhA1gjc3U-Nw0DsgHV3HvVmBskuoUksIt6YM6Z3ORjFtRhBphqAXxRKf9ke-zYcPs0TcEFKxw_bwGXSDiAKV5CL7kZf9i6lSZDe91ccUNjaAIsgTMKEEvYc7bZpXYz3D5dClulRwbNru5SZB-1E5FM0A2qMPs-IAfiR8OB1-cUvFh3WYKx9qlGgN',
          time: 'Just now',
          status: 'COMPLETED',
          text: 'Validation passed successfully on Round 2! verify.md checklist exists. Contrast ratios and file integrity conform fully to Vibe SOP limits.'
        }
      ]);

      // Remove the converted assets from changes view
      setUncommitted(prev => prev.filter(f => f.name === 'src/video-core/utils.ts'));

      // Print final deploy summary inside terminal
      setTerminalLogs(prev => [
        ...prev,
        `[EVALUATOR] SUCCESS: Gate check succeeded. Exit code 0.`,
        `[ORCHESTRATOR] Video Production pipeline completed. Ready to publish.`
      ]);
    }, 3200);
  };

  const handleResetSimulation = () => {
    setRunStatus('failed');
    setChatMessages(initialChatMessages);
    setUncommitted(uncommittedFiles);
    setTerminalLogs(initialTerminalLogs);
    setRightTab('overview');
    setCurrentFlowName('Video Production');
  };

  // Helper to parse and render Markdown tables, headers, lists, code, and links cleanly
  const parseAndRenderMarkdownBlocks = (text: string) => {
    const lines = text.split('\n');
    const blocks: Array<{ type: 'paragraph' | 'heading' | 'bullet' | 'table' | 'hr'; content: any }> = [];

    let i = 0;
    while (i < lines.length) {
      const line = lines[i];

      // Check for Markdown Table (starts with |)
      if (line.trim().startsWith('|')) {
        const tableLines: string[] = [];
        while (i < lines.length && lines[i].trim().startsWith('|')) {
          tableLines.push(lines[i].trim());
          i++;
        }

        if (tableLines.length >= 2) {
          const parseRow = (rowStr: string) =>
            rowStr
              .split('|')
              .map(c => c.trim())
              .filter((c, idx, arr) => (idx > 0 && idx < arr.length - 1) || (arr.length <= 2 && c !== ''));

          const headers = parseRow(tableLines[0]);
          const bodyLines = tableLines.slice(1).filter(l => !/^\|[\s:-|-]+\|$/.test(l));
          const rows = bodyLines.map(parseRow);

          blocks.push({
            type: 'table',
            content: { headers, rows }
          });
          continue;
        }
      }

      if (line.startsWith('# ')) {
        blocks.push({ type: 'heading', content: { level: 1, text: line.replace('# ', '') } });
      } else if (line.startsWith('## ')) {
        blocks.push({ type: 'heading', content: { level: 2, text: line.replace('## ', '') } });
      } else if (line.startsWith('### ')) {
        blocks.push({ type: 'heading', content: { level: 3, text: line.replace('### ', '') } });
      } else if (line.startsWith('- ') || line.startsWith('* ')) {
        blocks.push({ type: 'bullet', content: line.replace(/^[-*]\s+/, '') });
      } else if (line.trim() === '---' || line.trim() === '***') {
        blocks.push({ type: 'hr', content: null });
      } else {
        blocks.push({ type: 'paragraph', content: line });
      }

      i++;
    }

    const renderInline = (str: string) => {
      let formatted = str
        .replace(/\*\*(.*?)\*\*/g, '<strong class="text-neutral-900 font-semibold">$1</strong>')
        .replace(/`([^`]+)`/g, '<code class="bg-neutral-100 text-neutral-900 px-1.5 py-0.5 rounded font-mono text-[11px] border border-neutral-200/60 mx-0.5">$1</code>')
        .replace(/\[\[(.*?)\]\]/g, '<span class="text-[#897FDB] font-medium hover:underline cursor-pointer">[[ $1 ]]</span>');
      return <span dangerouslySetInnerHTML={{ __html: formatted }} />;
    };

    return blocks.map((blk, idx) => {
      if (blk.type === 'table') {
        const { headers, rows } = blk.content;
        return (
          <div key={idx} className="my-4 overflow-x-auto rounded-xl border border-neutral-200 shadow-2xs bg-white select-text">
            <table className="w-full text-left border-collapse font-sans text-xs">
              <thead>
                <tr className="bg-neutral-100/80 text-neutral-900 border-b border-neutral-200 font-bold">
                  {headers.map((h: string, hIdx: number) => (
                    <th key={hIdx} className="px-3.5 py-2.5 border-r border-neutral-200/60 last:border-r-0 font-bold text-neutral-800">
                      {renderInline(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row: string[], rIdx: number) => (
                  <tr key={rIdx} className="hover:bg-neutral-50/80 transition-colors odd:bg-neutral-50/30 border-b border-neutral-100 last:border-b-0">
                    {row.map((cell: string, cIdx: number) => (
                      <td key={cIdx} className="px-3.5 py-2 border-r border-neutral-200/40 last:border-r-0 text-neutral-700 font-medium">
                        {renderInline(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }

      if (blk.type === 'heading') {
        const { level, text } = blk.content;
        if (level === 1) return <h1 key={idx} className="text-lg font-bold text-neutral-900 border-b border-neutral-200 pb-3 mb-4 mt-2">{renderInline(text)}</h1>;
        if (level === 2) return <h2 key={idx} className="text-sm font-bold text-neutral-900 mt-5 mb-2">{renderInline(text)}</h2>;
        return <h3 key={idx} className="text-xs font-bold text-neutral-800 mt-4 mb-1.5">{renderInline(text)}</h3>;
      }

      if (blk.type === 'bullet') {
        return (
          <div key={idx} className="flex items-start gap-2 pl-1 my-1.5 text-neutral-600">
            <span className="w-1.5 h-1.5 mt-1.5 rounded-full bg-neutral-400 flex-shrink-0" />
            <span>{renderInline(blk.content)}</span>
          </div>
        );
      }

      if (blk.type === 'hr') {
        return <hr key={idx} className="my-4 border-neutral-200" />;
      }

      return (
        <p key={idx} className={blk.content.trim() ? "my-2 text-neutral-600 leading-relaxed" : "h-1"}>
          {renderInline(blk.content)}
        </p>
      );
    });
  };

  // Submit typed prompts with deterministic task completion (有始有终)
  const handleSendMessage = (text: string) => {
    const env = getClientEnvironmentContext();
    const timeNow = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // 1. Mark task start
    setRunStatus('running');

    // 2. Append custom User query into chat stream
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      agent: 'Orchestrator',
      avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=100',
      time: timeNow,
      text: text
    };

    setChatMessages(prev => [...prev, userMessage]);

    // Check zero-token Meta Query Interception gate
    const metaCheck = interceptMetaToolQueries(text);

    if (metaCheck.isMetaQuery && metaCheck.interceptedResponse) {
      setTerminalLogs(prev => [
        ...prev,
        `[META QUERY INTERCEPTOR] Direct zero-token capability map dispatched for prompt: "${text}". Blocked workspace file search.`
      ]);

      setTimeout(() => {
        const reply: ChatMessage = {
          id: `reply-meta-${Date.now()}`,
          agent: 'Clutch Agent',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p',
          time: timeNow,
          status: 'COMPLETED',
          text: metaCheck.interceptedResponse!,
          executionTime: '0.01s intercept',
          tokens: '0 tokens (Zero-Token Gateway Interceptor)'
        };
        setChatMessages(prev => [...prev, reply]);
        setRunStatus('passed');
      }, 400);
      return;
    }

    const { enrichedPrompt, injectedContext, language } = enrichPromptWithDynamicContext(text);

    // 3. Log start of agent execution in terminal with dynamic context
    setTerminalLogs(prev => [
      ...prev,
      `[AGENT HARNESS] Task initiated for prompt: "${text}" [Language: ${language.toUpperCase()}]`,
      `[DYNAMIC ENVIRONMENT CONTEXT] Injected time anchor: ${injectedContext.formattedDateTime} (${injectedContext.timeZone}), OS: ${injectedContext.devicePlatform}`,
      `[AGENT HARNESS] Executing code-driven deterministic tool pipeline...`
    ]);

    // 4. Trigger automated matching agent reply and complete task cleanly (有始有终)
    setTimeout(() => {
      let reply: ChatMessage;
      const lowerText = text.toLowerCase();
      
      if (lowerText.includes('几点') || lowerText.includes('时间') || lowerText.includes('时钟') || lowerText.includes('日期') || lowerText.includes('time') || lowerText.includes('clock') || lowerText.includes('date')) {
        const textContent = language === 'zh'
          ? `当前精确系统时间为：**${env.formattedDateTime}** (${env.timeZone})\n运行设备环境：\`${env.devicePlatform}\` (语言: \`${env.userLocale}\`)\n\n已通过基础系统工具 \`get_current_time\` 和 \`get_device_context\` 自动实时读取完成，无需硬编码于系统提示词。`
          : `Current exact system time is: **${env.formattedDateTime}** (${env.timeZone})\nRunning device environment: \`${env.devicePlatform}\` (Locale: \`${env.userLocale}\`)\n\nRetrieved in real-time via built-in system tools \`get_current_time\` and \`get_device_context\`.`;

        reply = {
          id: `reply-time-${Date.now()}`,
          agent: 'Clutch Agent',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p',
          time: timeNow,
          status: 'COMPLETED',
          text: textContent,
          workedTime: '0.1s',
          summarySteps: { filesCount: 0, foldersCount: 0, searchesCount: 1 },
          steps: [
            { type: 'command', action: 'Invoked', target: 'get_current_time' },
            { type: 'command', action: 'Invoked', target: 'get_device_context' }
          ],
          executionTime: '0.02s execution',
          tokens: '120 tokens'
        };
      } else if (lowerText.includes('调研') || lowerText.includes('市场') || lowerText.includes('竞品') || lowerText.includes('趋势') || lowerText.includes('research') || lowerText.includes('market')) {
        const textContent = language === 'zh'
          ? `### 📊 市场调研分析报告 (截至基准时间: ${env.formattedDateTime.split(' ')[0]})\n\n已自动挂载客户端动态环境标头 (**系统时间: ${env.formattedDateTime}**, **设备: ${env.devicePlatform}**) 进行实时增量检索。\n\n#### 1. 行业动态与最新趋势\n- 自动带有动态时间锚点 \`${env.formattedDateTime.split(' ')[0]}\` 过滤，排除历史过时研报。\n- 检索到当前季度 AI Agent 与智能体开发工具栈最新市场份额与用户主流配置。\n\n#### 2. 用户环境契合度\n- 当前运行平台为 **${env.devicePlatform}**，符合高效开发者终端集成与本地 IPC 通信标杆。\n\n#### 3. 调研结论\n- 建立动态时间过滤机制后，调研检索精准度提升 **40%**，有效防止抓取旧版过时数据。`
          : `### 📊 Market Research Report (Baseline Anchor: ${env.formattedDateTime.split(' ')[0]})\n\nAutomatically attached dynamic client environment headers (**System Time: ${env.formattedDateTime}**, **Platform: ${env.devicePlatform}**) for real-time incremental research.\n\n#### 1. Industry Dynamics & Latest Trends\n- Filtered using dynamic time anchor \`${env.formattedDateTime.split(' ')[0]}\` to eliminate outdated historical reports.\n- Retrieved latest market shares and user configurations for current-quarter AI Agent toolstacks.\n\n#### 2. User Environment Alignment\n- Current platform: **${env.devicePlatform}**, meeting developer terminal integration standards.\n\n#### 3. Strategic Conclusion\n- Time-anchor filtering increased research accuracy by **40%**, preventing outdated baseline references.`;

        reply = {
          id: `reply-research-${Date.now()}`,
          agent: 'Market Researcher Agent',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b',
          time: timeNow,
          status: 'COMPLETED',
          text: textContent,
          workedTime: '3s',
          summarySteps: { filesCount: 1, foldersCount: 0, searchesCount: 3 },
          steps: [
            { type: 'thought', action: 'Injected', target: `TimeAnchor: ${env.formattedDateTime}` },
            { type: 'search', action: 'Executed', target: `search_web with anchor ${env.formattedDateTime.split(' ')[0]}` }
          ],
          executionTime: '0.5s search',
          tokens: '890 tokens'
        };
      } else if (lowerText.includes('img') || lowerText.includes('image') || lowerText.includes('图片') || lowerText.includes('海报') || lowerText.includes('封面')) {
        const latestImg = UniversalArtifactRegistry.getLatestArtifact('image', '金华');
        const imgFile = latestImg ? latestImg.filename : 'jinhua_culture_banner.png';
        const imgTask = latestImg ? latestImg.taskName : '金华免费活动宣传图片海报';

        reply = {
          id: `reply-${Date.now()}`,
          agent: 'Builder',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b',
          time: timeNow,
          status: 'COMPLETED',
          text: `已通过 Universal Artifact Manifest 校验！
刚为你生成的【${imgTask}】视觉产物为：
🖼️ .clutch/generated/images/${imgFile}

全高精素材已保存归档，可直接查看或下载。`,
          workedTime: '5s',
          summarySteps: { filesCount: 2, foldersCount: 1, searchesCount: 2 },
          steps: [
            { type: 'file', action: 'Matched', target: imgFile },
            { type: 'command', action: 'Executed', target: 'clutch-tools__generate_image' }
          ],
          executionTime: '0.4s lookup',
          tokens: '920 tokens'
        };
      } else if (lowerText.includes('video') || lowerText.includes('视频') || lowerText.includes('宣传') || text.trim() === '?' || lowerText.includes('哪个')) {
        const latestVideo = UniversalArtifactRegistry.getLatestArtifact('video', '金华');
        const videoFile = latestVideo ? latestVideo.filename : 'task_421nKh4auHNQP7HbyfdmJSrGjdWEjr09.mp4';
        const taskTitle = latestVideo ? latestVideo.taskName : '金华免费活动宣传视频';

        reply = {
          id: `reply-${Date.now()}`,
          agent: 'Builder',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b',
          time: timeNow,
          status: 'COMPLETED',
          text: `已通过 Universal Artifact Manifest 清单精准确认！
刚为你生成的【${taskTitle}】对应文件为：
🎥 .clutch/generated/videos/${videoFile}

该视频已成功生成并挂载至当前任务上下文，可直接预览或导出使用。`,
          workedTime: '15s',
          summarySteps: { filesCount: 3, foldersCount: 1, searchesCount: 4 },
          steps: [
            { type: 'search', action: 'Matched', target: 'manifest.json' },
            { type: 'command', action: 'Executed', target: 'clutch-tools__generate_video' },
            { type: 'file', action: 'Verified', target: videoFile }
          ],
          executionTime: '0.6s lookup',
          tokens: '1,840 tokens'
        };
      } else if (lowerText.includes('help') || lowerText.includes('status')) {
        reply = {
          id: `reply-${Date.now()}`,
          agent: 'Orchestrator',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p',
          time: timeNow,
          status: 'COMPLETED',
          text: `Dynamic analysis scan initialized. Task pipeline execution completed with 0 errors. Current pipeline status is set to: [PASSED].`,
          executionTime: '0.4s execution',
          tokens: '840 tokens'
        };
      } else if (lowerText.includes('test') || lowerText.includes('verify')) {
        reply = {
          id: `reply-${Date.now()}`,
          agent: 'Evaluator',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCmb7VGaQXE-4sYnIZR3VrcHVAPhv4Px14kMlkayJj8kVm8htTWITmPi26wsj8P6B9RrqykIWj81S2ilmGR0e8cXhA1gjc3U-Nw0DsgHV3HvVmBskuoUksIt6YM6Z3ORjFtRhBphqAXxRKf9ke-zYcPs0TcEFKxw_bwGXSDiAKV5CL7kZf9i6lSZDe91ccUNjaAIsgTMKEEvYc7bZpXYz3D5dClulRwbNru5SZB-1E5FM0A2qMPs-IAfiR8OB1-cUvFh3WYKx9qlGgN',
          time: timeNow,
          status: 'COMPLETED',
          text: `Validation suite triggered automatically! Checking contrast conformance scores. Verification passed 100%.`,
          executionTime: '1.2s execution',
          tokens: '1,420 tokens'
        };
      } else {
        reply = {
          id: `reply-${Date.now()}`,
          agent: 'Builder',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b',
          time: timeNow,
          status: 'COMPLETED',
          text: `任务“${text}”已全流程分析并顺利完成！核心模块与产出已整理归档，一切检查通过。`,
          executionTime: '0.8s iteration',
          tokens: '1,150 tokens'
        };
      }

      // Append completed agent reply
      setChatMessages(prev => [...prev, reply]);

      // Deterministically finalize task status and clear Working... loading indicator
      setRunStatus('passed');

      // Log task finish in terminal
      setTerminalLogs(prev => [
        ...prev,
        `[AGENT HARNESS] Task completed successfully. Status: PASSED (Exit Code 0).`,
        `[AGENT HARNESS] Working state cleared and response returned to user.`
      ]);
    }, 1500);
  };

  return (
    <div className="relative h-screen max-h-screen bg-background text-on-surface overflow-hidden flex flex-col font-sans select-none">
      
      {/* 1. Header component */}
      <Header
        currentFlow={currentFlowName}
        folders={folders}
        isMultiAgent={isMultiAgent}
        setIsMultiAgent={setIsMultiAgent}
        onGoBack={handleResetSimulation}
        setView={setView}
        sidebarOpen={sidebarOpen}
      />

      {/* 2. Side Panel components layout */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left navigation drawer */}
        <Sidebar
          currentView={currentView}
          setView={setView}
          folders={folders}
          setFolders={setFolders}
          activeFlow={currentFlowName}
          setActiveFlow={handleFlowSelect}
          onResetSimulation={handleResetSimulation}
          isOpenState={sidebarOpen}
          setIsOpenState={setSidebarOpen}
          isMultiAgent={isMultiAgent}
        />

        {/* Central screen switcher with Right component based on Left tab selections */}
        {(currentView === 'chat' || currentView === 'agents' || currentView === 'settings') && (
          previewFile ? (
            <div 
              style={{ paddingLeft: `${selectedSidebarWidth}px`, paddingTop: '64px' }}
              className="flex-1 flex flex-col bg-white h-screen overflow-hidden animate-fade-in relative z-30 transition-all duration-300"
            >
              {/* File Preview Header */}
              <div className="h-14 border-b border-outline-variant/60 flex items-center justify-between px-6 bg-neutral-50/50 flex-shrink-0 select-none">
                <div className="flex items-center gap-3">
                  <span className="material-symbols-outlined text-[20px] text-neutral-500">
                    {previewFile.name.endsWith('.md') ? 'markdown' : 'code'}
                  </span>
                  <div className="flex flex-col justify-center">
                    <h3 className="text-xs font-bold text-neutral-900 font-mono tracking-tight flex items-center gap-1">
                      {previewFile.name.includes('/') && (
                        <span className="text-neutral-400 font-medium">{previewFile.name.split('/').slice(0, -1).join('/')}/</span>
                      )}
                      <span>{previewFile.name.split('/').pop()}</span>
                    </h3>
                  </div>
                </div>

                <button
                  onClick={() => setPreviewFile(null)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-neutral-500 hover:text-neutral-900 hover:bg-neutral-200/50 rounded-lg text-[11px] font-semibold transition-colors"
                >
                  <span className="material-symbols-outlined text-[16px]">close</span>
                  Close
                </button>
              </div>

              {/* Code/Markdown Content Viewer */}
              <div className="flex-1 overflow-y-auto p-8 font-mono text-xs text-neutral-800 bg-[#f9f9f9] select-text leading-relaxed">
                {previewFile.name.endsWith('.md') ? (
                  <div className="max-w-3xl mx-auto space-y-3 font-sans text-[13px] text-neutral-700 leading-relaxed bg-white border border-outline p-8 rounded-xl shadow-xs">
                    {parseAndRenderMarkdownBlocks(previewFile.content)}
                  </div>
                ) : (
                  <div className="max-w-4xl mx-auto bg-neutral-900 text-neutral-200 p-6 rounded-xl font-mono text-[11px] shadow-sm select-text overflow-x-auto border border-neutral-800">
                    <table className="w-full">
                      <tbody>
                        {previewFile.content.split('\n').map((line, index) => (
                          <tr key={index} className="hover:bg-neutral-800/40 leading-relaxed">
                            <td className="text-neutral-500 text-right pr-4 select-none w-8 border-r border-neutral-800 text-[10px] font-semibold">{index + 1}</td>
                            <td className="pl-4 whitespace-pre font-mono text-neutral-300">{line || ' '}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <>
              <ChatFeed
                messages={chatMessages}
                inputValue={inputValue}
                setInputValue={setInputValue}
                onSendMessage={handleSendMessage}
                runStatus={runStatus}
                currentFlowName={currentFlowName}
                selectedSidebarWidth={selectedSidebarWidth}
                rightSidebarWidth={rightSidebarWidth}
                onStopRun={handleStopRun}
                isMultiAgent={isMultiAgent}
                onPreviewFile={(file) => setPreviewFile(file)}
              />
              <RightPanel
                activeTab={rightTab}
                setActiveTab={setRightTab}
                runStatus={runStatus}
                onReassign={handleReassignToBuilder}
                uncommitted={uncommitted}
                terminalLogs={terminalLogs}
                isOpen={rightPanelOpen}
                setIsOpen={setRightPanelOpen}
                selectedSidebarWidth={selectedSidebarWidth}
                rightSidebarWidth={rightSidebarWidth}
                onPreviewFile={setPreviewFile}
                isMultiAgent={isMultiAgent}
              />
            </>
          )
        )}

        {/* Unified Settings & Agent Controller Dialog Modal */}
        {(currentView === 'agents' || currentView === 'settings' || currentView === 'workflows' || currentView === 'tools') && (
          <div className="fixed inset-0 bg-neutral-900/10 backdrop-blur-xs flex items-center justify-center z-[100] animate-fade-in p-6 select-none leading-normal">
            {/* Click backdrop to close */}
            <div className="absolute inset-0" onClick={() => setView('chat')} />

            {/* Modal Body Container (Exactly 1040x640) */}
            <div 
              style={{ width: '1040px', height: '640px' }}
              className="bg-white rounded-[24px] shadow-xl border border-neutral-200/50 flex overflow-hidden relative z-10 transition-all duration-300 animate-scale-up"
            >
              
              {/* Modal Split View */}
              <div className="flex-1 flex overflow-hidden min-h-0 bg-[#fbfbfa]">
                
                {/* Modal Left Sidebar Selector (Exactly as provided) */}
                <div className="w-[240px] bg-neutral-50/45 border-r border-neutral-200/40 flex flex-col p-6 justify-between flex-shrink-0">
                  <div className="space-y-1.5 text-left">
                    <p className="font-bold text-[10px] uppercase tracking-widest text-neutral-400 mb-3.5 px-3">
                      System Preferences
                    </p>
                    
                    <button
                      onClick={() => setView('settings')}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-xs transition-all border ${
                        currentView === 'settings'
                          ? 'bg-white text-neutral-800 font-extrabold border-neutral-200/40 shadow-2xs'
                          : 'text-neutral-500 hover:bg-neutral-100/40 hover:text-neutral-800 border-transparent'
                      }`}
                    >
                      <span className="material-symbols-outlined text-[18px]">settings</span>
                      <span className="text-xs">General</span>
                    </button>

                    <button
                      onClick={() => setView('tools')}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-xs transition-all border ${
                        currentView === 'tools'
                          ? 'bg-white text-neutral-800 font-extrabold border-neutral-200/40 shadow-2xs'
                          : 'text-neutral-500 hover:bg-neutral-100/40 hover:text-neutral-800 border-transparent'
                      }`}
                    >
                      <span className="material-symbols-outlined text-[18px]">handyman</span>
                      <span className="text-xs">AI Tools</span>
                    </button>

                    <button
                      onClick={() => setView('agents')}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-xs transition-all border ${
                        currentView === 'agents'
                          ? 'bg-white text-neutral-800 font-extrabold border-neutral-200/40 shadow-2xs'
                          : 'text-neutral-500 hover:bg-neutral-100/40 hover:text-neutral-800 border-transparent'
                      }`}
                    >
                      <span className="material-symbols-outlined text-[18px]">smart_toy</span>
                      <span className="text-xs">AI Agents</span>
                    </button>

                    {isMultiAgent && (
                      <button
                        onClick={() => setView('workflows')}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left text-xs transition-all border ${
                          currentView === 'workflows'
                            ? 'bg-white text-neutral-800 font-extrabold border-neutral-200/40 shadow-2xs'
                            : 'text-neutral-500 hover:bg-neutral-100/40 hover:text-neutral-800 border-transparent'
                        }`}
                      >
                        <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: currentView === 'workflows' ? "'FILL' 1" : undefined }}>
                          account_tree
                        </span>
                        <span className="text-xs">Workflows</span>
                      </button>
                    )}

                    {/* Placeholder Categories for visual alignment */}
                    <button
                      onClick={() => alert("Models Configuration: GPT-4o, Gemini 2.x configured.")}
                      className="w-full flex items-center gap-3 px-3 py-2 text-neutral-400/80 hover:text-neutral-600 rounded-lg text-left text-xs transition-all border border-transparent"
                    >
                      <span className="material-symbols-outlined text-[18px]">layers</span>
                      <span className="text-xs">Models Config</span>
                    </button>

                    <button
                      onClick={() => alert("MCP servers registered locally.")}
                      className="w-full flex items-center gap-3 px-3 py-2 text-neutral-400/80 hover:text-neutral-600 rounded-lg text-left text-xs transition-all border border-transparent"
                    >
                      <span className="material-symbols-outlined text-[18px]">terminal</span>
                      <span className="text-xs">MCP Registry</span>
                    </button>

                    <button
                      onClick={() => alert("Appearance settings loaded.")}
                      className="w-full flex items-center gap-3 px-3 py-2 text-neutral-400/80 hover:text-neutral-600 rounded-lg text-left text-xs transition-all border border-transparent"
                    >
                      <span className="material-symbols-outlined text-[18px]">palette</span>
                      <span className="text-xs">Appearance</span>
                    </button>
                  </div>

                  <div className="space-y-2 select-none">
                    {/* Sidebar Stats footer in modal */}
                    <div className="bg-neutral-100/40 p-4 rounded-xl border border-neutral-200/30 space-y-2 select-text">
                      <p className="text-[9px] text-neutral-400 font-mono font-bold uppercase tracking-wider text-left">Status Overview</p>
                      <div className="space-y-1 text-[10px] font-medium text-neutral-500 text-left">
                        <div className="flex justify-between">
                          <span>Workspace:</span>
                          <span className="font-semibold text-neutral-800">v2.4.1</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Session:</span>
                          <span className="font-mono text-green-600 font-bold">● ACTIVE</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Modal Right Detail Panel */}
                <div className="flex-1 overflow-hidden flex flex-col bg-white">
                  {currentView === 'agents' ? (
                    <AgentManager isModalStyle={true} />
                  ) : currentView === 'workflows' ? (
                    <WorkflowOrchestration isModalStyle={true} onClose={() => setView('chat')} />
                  ) : currentView === 'tools' ? (
                    <AiToolsManager isModalStyle={true} />
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center p-10 text-center select-none bg-white">
                      <span className="material-symbols-outlined text-[32px] text-neutral-300 font-variation-light mb-2">construction</span>
                      <p className="text-xs font-bold text-neutral-400">Feature under active development</p>
                    </div>
                  )}
                </div>

              </div>

              {/* Floating Top-Right Close Button */}
              <button
                onClick={() => setView('chat')}
                className="absolute top-4 right-4 z-50 w-7 h-7 bg-neutral-100/60 hover:bg-neutral-200/60 text-neutral-500 hover:text-neutral-800 rounded-full flex items-center justify-center transition-all group cursor-pointer border border-neutral-250/10"
                title="Close Panel"
              >
                <span className="material-symbols-outlined text-[15px] group-hover:rotate-90 transition-transform">
                  close
                </span>
              </button>

            </div>
          </div>
        )}

      </div>

      {/* 3. Footer Bar Component */}
      <footer 
        style={{ left: `${selectedSidebarWidth}px` }}
        className="fixed bottom-0 right-0 h-8 bg-white border-t border-outline-variant flex items-center justify-between px-6 z-50 text-[11px] text-on-surface-variant/80 select-none transition-all duration-300"
      >
        <div className="flex items-center gap-6">
          <span 
            onClick={() => alert("Simulated action: switching workspace branches of target repo...")}
            className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low hover:text-on-surface transition-colors cursor-pointer font-medium"
          >
            <span className="material-symbols-outlined text-[15px] text-on-surface-variant">fork_right</span> 
            Branch: main 
            <span className="material-symbols-outlined text-[13px]">keyboard_arrow_down</span>
          </span>

          <span 
            onClick={() => alert("Available modes: Local, Staging, Cloud run...")}
            className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low hover:text-on-surface transition-colors cursor-pointer font-medium"
          >
            <span className="material-symbols-outlined text-[15px] text-on-surface-variant">lan</span> 
            Mode: Local 
            <span className="material-symbols-outlined text-[13px]">keyboard_arrow_down</span>
          </span>

          {isMultiAgent ? (
            <span 
              onClick={() => setView('workflows')}
              className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low text-primary font-bold transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-[15px] text-primary">movie</span> 
              Flow: {currentFlowName} 
              <span className="material-symbols-outlined text-[13px]">keyboard_arrow_down</span>
            </span>
          ) : (
            <span 
              onClick={() => setView('agents')}
              className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low text-primary font-bold transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-[15px] text-primary">smart_toy</span> 
              AI Agent: Orchestrator 
              <span className="material-symbols-outlined text-[13px]">keyboard_arrow_down</span>
            </span>
          )}
        </div>

        <div className="font-semibold text-on-surface-variant/70 italic mr-2 select-text">
          Clutch v1.3.0
        </div>
      </footer>
    </div>
  );
}
