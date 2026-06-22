import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './sidebar';
import { ChatFeed } from './components/ChatFeed';
import { RightPanel } from './components/RightPanel';
import { WorkflowOrchestration } from './components/WorkflowOrchestration';
import { AgentManager, AgentLogo } from './components/AgentManager';
import AiToolsManager from './components/AiToolsManager';
import { SkillsRegistry } from './components/SkillsRegistry';
import { McpServerHub } from './components/McpServerHub';
import { ModelsManager } from './components/ModelsManager';
import { ThemeManager, THEME_PRESETS } from './components/ThemeManager';
import { SystemPreferencesModal } from './components/SystemPreferencesModal';
import { MainView, RightTab, ChatMessage, UncommittedFile } from './types';
import {
  initialConfiguredModels,
  initialFolders,
  initialChatMessages,
  secondaryChatMessages,
  uncommittedFiles,
  initialTerminalLogs
} from './mockData';
import { LanguageProvider, useLanguage } from './components/LanguageContext';
import { loadFlowState, submitChatMessage, approveNode, rejectNode, retryNodeWithInstructions, reassignToBuilder } from './services/api';
import { clutchStore, DEFAULT_RUN_ID, useClutchState } from './services/clutchState';
import type { RunStatus } from './types';


function MainLayout() {
  const { t } = useLanguage();
  const { state: clutchState, connected } = useClutchState();

  useEffect(() => {
    void clutchStore.connect(DEFAULT_RUN_ID);
  }, []);

  const runStatus: RunStatus =
    clutchState.status === 'awaiting_human' ? 'running' : (clutchState.status as RunStatus);
  const terminalLogs =
    connected && clutchState.terminal_logs.length > 0
      ? clutchState.terminal_logs
      : initialTerminalLogs;

  // Navigation & Structure views
  const [currentView, setView] = useState<MainView>('chat');
  const [currentFlowName, setCurrentFlowName] = useState<string>('Video Production');
  const [isMultiAgent, setIsMultiAgent] = useState<boolean>(true);
  const [themeId, setThemeId] = useState<string>('pristine-light');

  // Active selected model state
  const [selectedModel, setSelectedModel] = useState<string>('DeepSeek V4Pro');
  const [configuredModels, setConfiguredModels] = useState<Array<{
    id: string;
    name: string;
    provider: string;
    contextWindow: string;
    temperature: number;
    description: string;
    isCustom?: boolean;
    endpoint?: string;
    apiKey?: string;
  }>>(initialConfiguredModels);

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

  // Chat / file mock state (M2 replaces with WS events)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(initialChatMessages);
  const [uncommitted, setUncommitted] = useState<UncommittedFile[]>(uncommittedFiles);

  // Close unified settings dialog on ESC key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setView(prev => (prev === 'agents' || prev === 'settings' || prev === 'tools' || prev === 'workflows' || prev === 'skills' || prev === 'mcp' || prev === 'models' || prev === 'appearance') ? 'chat' : prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleStopRun = () => {
    void clutchStore.send({ action: 'stop_run' });
  };

  const handleApprove = async () => {
    void clutchStore.send({ action: 'human_decision', decision: 'approve' });
    const res = await approveNode();
    setRightTab('overview');
    setChatMessages(prev => [...prev, ...res.messages]);
    setUncommitted(prev => prev.filter(f => f.name === 'src/video-core/utils.ts'));
  };

  const handleReject = async () => {
    void clutchStore.send({ action: 'human_decision', decision: 'reject' });
    const res = await rejectNode();
    setChatMessages(prev => [...prev, ...res.messages]);
  };

  const handleRetryWithInstructions = async (instructions: string) => {
    void clutchStore.send({ action: 'human_decision', decision: 'retry', instructions });
    setRightTab('terminal');
    const res = await retryNodeWithInstructions(instructions);

    setChatMessages(prev => [...prev, ...res.messages]);
    setRightTab('overview');
    setUncommitted(prev => prev.filter(f => f.name === 'src/video-core/utils.ts'));
  };

  // Chat Input Box State
  const [inputValue, setInputValue] = useState<string>('');

  const handleFlowSelect = async (flow: string) => {
    setCurrentFlowName(flow);
    const res = await loadFlowState(flow);
    setChatMessages(res.messages);
    setUncommitted(res.uncommitted);
  };

  const handleReassignToBuilder = async () => {
    setRightTab('terminal');
    const res = await reassignToBuilder();
    setChatMessages(prev => [...prev, ...res.messages]);
    setRightTab('overview');
    setUncommitted(prev => prev.filter(f => f.name === 'src/video-core/utils.ts'));
  };

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;
    
    // UI optimistic update
    const timeNow = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setChatMessages(prev => [...prev, {
      id: `user-${Date.now()}`,
      agent: 'User',
      avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=100',
      time: timeNow,
      text: text,
      isUser: true,
    }]);

    const resMsg = await submitChatMessage(text, currentFlowName, runStatus);
    setChatMessages(prev => [...prev, resMsg]);
  };

  const handleResetSimulation = () => {
    setChatMessages(initialChatMessages);
    setUncommitted(uncommittedFiles);
    setRightTab('overview');
    setCurrentFlowName('Video Production');
  };

  const currentThemeObj = THEME_PRESETS.find(t => t.id === themeId) || THEME_PRESETS[0];
  const themeVars = currentThemeObj.variables;

  return (
    <div 
      style={themeVars as React.CSSProperties}
      className="relative h-screen max-h-screen bg-background text-on-surface overflow-hidden flex flex-col font-sans select-none"
    >
      
      {/* 1. Header component */}
      <Header
        currentFlow={currentFlowName}
        folders={folders}
        isMultiAgent={isMultiAgent}
        setIsMultiAgent={setIsMultiAgent}
        onGoBack={handleResetSimulation}
        setView={setView}
        sidebarOpen={sidebarOpen}
        selectedModel={selectedModel}
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
        {true && (
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
                    {previewFile.content.split('\n').map((line, i) => {
                      if (line.startsWith('# ')) {
                        return <h1 key={i} className="text-lg font-bold text-neutral-900 border-b border-outline pb-3 mb-4 flex items-center gap-2">{line.replace('# ', '')}</h1>;
                      }
                      if (line.startsWith('## ')) {
                        return <h2 key={i} className="text-sm font-bold text-neutral-900 mt-5 mb-2 flex items-center gap-2">{line.replace('## ', '')}</h2>;
                      }
                      if (line.startsWith('### ')) {
                        return <h3 key={i} className="text-xs font-bold text-neutral-800 mt-4 mb-1.5">{line.replace('### ', '')}</h3>;
                      }
                      if (line.startsWith('- ')) {
                        let htmlContent = line.replace('- ', '');
                        htmlContent = htmlContent.replace(/\*\*(.*?)\*\*/g, '<strong class="text-neutral-900 font-semibold">$1</strong>');
                        htmlContent = htmlContent.replace(/`([^`]+)`/g, '<code class="bg-neutral-100 text-neutral-900 px-1 py-0.5 rounded font-mono text-[11px] border border-neutral-200/60 mx-0.5">$1</code>');
                        htmlContent = htmlContent.replace(/\[\[(.*?)\]\]/g, '<span class="text-[#897FDB] font-medium hover:underline cursor-pointer">[[ $1 ]]</span>');
                        
                        return (
                          <div key={i} className="flex items-start gap-2 pl-1 my-1.5 text-neutral-600">
                            <span className="w-1 h-1.5 mt-2 rounded bg-neutral-400 flex-shrink-0" />
                            <span dangerouslySetInnerHTML={{ __html: htmlContent }} />
                          </div>
                        );
                      }
                      
                      const pContent = line.replace(/\*\*(.*?)\*\*/g, '<strong class="text-neutral-900 font-semibold">$1</strong>').replace(/`([^`]+)`/g, '<code class="bg-neutral-100 text-neutral-900 px-1 py-0.5 rounded font-mono text-[11px] border border-neutral-200/60 mx-0.5">$1</code>');
                      return <p key={i} className={line.trim() ? "my-2 text-neutral-600" : "h-1"} dangerouslySetInnerHTML={{ __html: pContent }} />;
                    })}
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
                onApprove={handleApprove}
                onReject={handleReject}
                onRetryWithInstructions={handleRetryWithInstructions}
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
        <SystemPreferencesModal
          currentView={currentView}
          setView={setView}
          isMultiAgent={isMultiAgent}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
          configuredModels={configuredModels}
          setConfiguredModels={setConfiguredModels}
          themeId={themeId}
          setThemeId={setThemeId}
        />

      </div>

      {/* 3. Footer Bar Component */}
      <footer 
        style={{ left: `${selectedSidebarWidth}px` }}
        className="fixed bottom-0 right-0 h-8 bg-background border-t border-outline-variant flex items-center justify-between px-6 z-50 text-[11px] text-on-surface-variant/80 select-none transition-all duration-300"
      >
        <div className="flex items-center gap-6">
          <span 
            onClick={() => console.warn("Simulated action: switching workspace branches of target repo...")}
            className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low hover:text-on-surface transition-colors cursor-pointer font-medium"
          >
            <span className="material-symbols-outlined text-[15px] text-on-surface-variant">fork_right</span> 
            {t("Branch: main")}
            <span className="material-symbols-outlined text-[13px]">keyboard_arrow_down</span>
          </span>

          <span 
            onClick={() => setView('models')}
            className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low hover:text-on-surface transition-colors cursor-pointer font-medium text-on-surface-variant"
          >
            <span className="material-symbols-outlined text-[15px] text-on-surface-variant animate-pulse">layers</span> 
            {t("Model")}: {selectedModel} 
            <span className="material-symbols-outlined text-[13px]">keyboard_arrow_down</span>
          </span>

          {isMultiAgent ? (
            <span 
              onClick={() => setView('workflows')}
              className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low text-primary font-bold transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-[15px] text-primary">movie</span> 
              {t("Workflow")}: {t(currentFlowName)} 
              <span className="material-symbols-outlined text-[13px]">keyboard_arrow_down</span>
            </span>
          ) : (
            <span 
              onClick={() => setView('agents')}
              className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low text-primary font-bold transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-[15px] text-primary">smart_toy</span> 
              {t("Active Agent")}: {t("Orchestrator")} 
              <span className="material-symbols-outlined text-[13px]">keyboard_arrow_down</span>
            </span>
          )}
        </div>

        <div className="font-semibold text-on-surface-variant/70 italic mr-2 select-text">
          Clutch v2.4.1
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <LanguageProvider>
      <MainLayout />
    </LanguageProvider>
  );
}
