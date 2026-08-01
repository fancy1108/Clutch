import React, { useRef, useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './sidebar';
import { ChatFeed } from './components/ChatFeed';
import { DesignWorkspace } from './components/design/DesignWorkspace';
import { getDesignSession, type CodingHandoff } from './services/designApi';
import { RightPanel } from './components/RightPanel';
import { WorkflowOrchestration } from './components/WorkflowOrchestration';
import { AgentManager } from './components/AgentManager';
import AiToolsManager from './components/AiToolsManager';
import { SkillsRegistry } from './components/SkillsRegistry';
import { McpServerHub } from './components/McpServerHub';
import { ModelsManager } from './components/ModelsManager';
import { ThemeManager } from './components/ThemeManager';
import { SystemPreferencesModal } from './components/SystemPreferencesModal';
import { PromptModal } from './components/PromptModal';
import { AppErrorBoundary } from './components/AppErrorBoundary';
import { FooterMenuAction, FooterMenuItem, FooterMenuPanel, FooterMenuSection } from './components/FooterMenu';
import { MainView, type Agent, type AppWorkspaceMode } from './types';
import { fetchAgents } from './services/agentApi';
import { getAgentDisplayName, isBuiltinAgent } from './services/builtinAgent';
import { isWindowsHost, useHostOs } from './platform/hostOs';
import { LanguageProvider, useLanguage } from './components/LanguageContext';
import { OnboardingWizard } from './components/onboarding/OnboardingWizard';
import { CONTENT_TOP_WITH_BANNER, SIDEBAR_COLLAPSED_WIDTH_PX, SIDEBAR_EXPANDED_WIDTH_PX, CHROME_PANEL_TOGGLE_TOP_CSS, CHROME_PANEL_TOGGLE_HALF_PX } from './constants/layout';
import { ChromeEdgeToggle } from './components/ui/ChromeEdgeToggle';
import { BrandLogo } from './components/BrandLogo';
import { clutchMarkUrl } from './assets/brand';
import { DevOnboardingToolsEmptyPreview } from './components/onboarding/DevOnboardingToolsEmptyPreview';
import { fetchOnboardingState } from './services/onboardingApi';
import { clutchStore, useClutchState, createSessionRunId } from './services/clutchState';
import { createSession } from './services/runApi';
import { agentTypeFromAgent, isClutchAgentType } from './services/agentTypes';
import { isArchivedTerminalHistoryView, sessionHasTerminalHistory } from './services/terminalOrchestraUtils';
import { modelKindMenuSuffix } from './services/modelsApi';
import { LegacyIcon } from './components/ui/LegacyIcon';
import { useAppSettings } from './hooks/useAppSettings';
import { useAppWorkspace, type AppPromptModalState } from './hooks/useAppWorkspace';
import { useAppSession } from './hooks/useAppSession';

function MainLayout() {
  const { t } = useLanguage();
  const hostOs = useHostOs();
  const isWindows = isWindowsHost(hostOs);
  const { state: clutchState } = useClutchState();

  const [currentView, setView] = useState<MainView>('chat');
  const [promptModal, setPromptModal] = useState<AppPromptModalState | null>(null);
  const refreshSessionsRef = useRef<() => Promise<void>>(() => Promise.resolve());
  const workspacePickErrorRef = useRef<(message: string) => void>(() => {});

  const isTurnInProgress =
    clutchState.status === 'running' || clutchState.status === 'awaiting_human';

  const settings = useAppSettings({
    t,
    isTurnInProgress,
    onModelSwitchError: (message) => workspacePickErrorRef.current(message),
  });

  const ws = useAppWorkspace({
    t,
    setPromptModal,
    refreshSessions: () => refreshSessionsRef.current(),
  });
  workspacePickErrorRef.current = ws.setWorkspacePickError;

  const session = useAppSession({
    t,
    settings,
    workspace: ws,
    setPromptModal,
    setView,
    currentView,
  });
  refreshSessionsRef.current = () => session.refreshSessions();

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<{ view?: MainView }>).detail;
      if (detail?.view) {
        setView(detail.view);
      }
    };
    window.addEventListener('clutch-navigate-settings', handler);
    return () => window.removeEventListener('clutch-navigate-settings', handler);
  }, []);

  const {
    appVersion,
    sessionRunId,
    highlightedDispatchEntryId,
    setHighlightedDispatchEntryId,
    highlightedLogIndex,
    clutchStatus,
    chatMessages,
    terminalLogs,
    appMode,
    currentFlowName,
    setCurrentFlowName,
    selectedWorkflowId,
    workflowAgentSteps,
    isMultiAgent,
    sidebarOpen,
    setSidebarOpen,
    rightPanelOpen,
    setRightPanelOpen,
    folders,
    setFolders,
    sessions,
    loadingSessionId,
    shellSnapshotRunIds,
    branchMenuOpen,
    agentMenuOpen,
    workflowMenuOpen,
    footerWorkflows,
    closeFooterMenus,
    selectedAgentId,
    workspaceViewMode,
    configuredAgents,
    inputValue,
    setInputValue,
    rightTab,
    setRightTab,
    uncommitted,
    slashNotice,
    chatSkills,
    selectedSidebarWidth,
    rightSidebarWidth,
    effectiveWorkflowId,
    effectiveWorkflowName,
    selectedAgentName,
    isPlainLlmFooter,
    hideFooterSessionControls,
    footerSelectableAgents,
    mentionableAgents,
    activeWorkflowLabel,
    hasWorkflowSelection,
    multiAgentFooterName,
    showFooterModel,
    agentBoundModelId,
    footerEffectiveModelId,
    footerEffectiveModelName,
    isWorkflowChat,
    chatActiveAgentName,
    chatActiveAgentAvatar,
    customAgentEngineLabel,
    chatRuntimeEngineHint,
    chatLlmModelName,
    resolveAgentLogo,
    selectedAgent,
    hasCliAgents,
    sessionTitle,
    historySessionViewRunId,
    handleSetIsMultiAgent,
    handleActivateAgent,
    handleWorkspaceViewModeChange,
    handleViewToolStepInTerminal,
    syncSelectedAgentFromMention,
    handleClearTerminal,
    handleStopRun,
    handleContinueRun,
    handleApprove,
    handleReject,
    handleRetryWithInstructions,
    handleAnswerQuestion,
    dismissSlashNotice,
    handleSlashCommand,
    bindWorkflowForChat,
    handleFlowSelect,
    handleUseWorkflowInChat,
    toggleWorkflowMenu,
    toggleAgentMenu,
    handleFooterAgentSelect,
    handleNewChat,
    handleNewDesign,
    handleDesignBusyChange,
    handleAppModeChange,
    handleSelectSession,
    handleNewChatInWorkspace,
    handleDeleteSession,
    handleSendMessage,
    clearWorkflowSelection,
    selectDefaultAgent,
    promptLeaveTerminal,
    permissionMode,
    handlePermissionModeChange,
  } = session;

  const { themeVars } = settings;
  const {
    workspace,
    workspaces,
    repositoryGroups,
    activeWorkspaceId,
    workspaceFiles,
    workspacePickError,
    workspaceGit,
    previewFile,
    setPreviewFile,
    previewToast,
    handlePickWorkspace,
    handleSelectWorkspace,
    handleCreateRepositoryGroup,
    handleToggleRepositoryGroup,
    handleDeleteRepositoryGroup,
    handleRenameRepositoryGroup,
    handleMoveWorkspaceToGroup,
    handleOpenWorkspaceFile,
    handlePreviewSnippet,
    handleDeleteWorkspace,
  } = ws;

  const {
    themeId,
    fontSize,
    userAvatar,
    setUserAvatar,
    userName,
    setUserName,
    setThemeId,
    setFontSize,
    selectedModel,
    setSelectedModel,
    activeModelId,
    setActiveModelId,
    configuredModels,
    setConfiguredModels,
    modelMenuOpen,
    toggleModelMenu,
    handleFooterModelSelect,
  } = settings;

  return (
    <div 
      style={themeVars as React.CSSProperties}
      data-platform={hostOs}
      data-font-size={fontSize}
      className="relative h-screen max-h-screen bg-background text-on-surface overflow-hidden flex flex-col font-sans select-none"
    >
      {/* 1. Header component */}
      <Header
        currentFlow={currentFlowName || clutchState.workflow_id || (appMode === 'design' ? t('New Design') : t('New session'))}
        workspaceName={workspace?.name}
        onPickWorkspace={() => { void handlePickWorkspace(); }}
        folders={folders}
        sidebarOpen={sidebarOpen}
        appMode={appMode}
        onAppModeChange={handleAppModeChange}
      />

      {!isWindows ? (
      <ChromeEdgeToggle
        testId="workspace-sidebar-toggle"
        icon={sidebarOpen ? 'chevron_left' : 'chevron_right'}
        title={sidebarOpen ? t('Collapse Sidebar') : t('Expand Sidebar')}
        onClick={() => setSidebarOpen((open) => !open)}
        className="fixed transition-[left] duration-300 ease-out"
        style={{
          top: CHROME_PANEL_TOGGLE_TOP_CSS,
          left: selectedSidebarWidth - CHROME_PANEL_TOGGLE_HALF_PX,
        }}
      />
      ) : null}

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
          appMode={appMode}
          onNewChat={() => {
            if (appMode === 'design') {
              void handleNewDesign();
            } else {
              void handleNewChat();
            }
          }}
          isOpenState={sidebarOpen}
          setIsOpenState={setSidebarOpen}
          isMultiAgent={isMultiAgent}
          sessions={sessions}
          shellSnapshotRunIds={shellSnapshotRunIds}
          activeSessionId={sessionRunId}
          loadingSessionId={loadingSessionId}
          clutchStatus={clutchStatus}
          workspaces={workspaces}
          repositoryGroups={repositoryGroups}
          activeWorkspaceId={activeWorkspaceId}
          onAddWorkspace={() => { void handlePickWorkspace(); }}
          onCreateRepositoryGroup={() => { void handleCreateRepositoryGroup(); }}
          onToggleRepositoryGroup={(groupId, collapsed) => {
            void handleToggleRepositoryGroup(groupId, collapsed);
          }}
          onSelectWorkspace={(id) => { void handleSelectWorkspace(id); }}
          onSelectSession={(session) => { void handleSelectSession(session); }}
          onNewChatInWorkspace={(id) => { void handleNewChatInWorkspace(id); }}
          onDeleteWorkspace={(id) => { void handleDeleteWorkspace(id); }}
          onDeleteSession={(id) => { void handleDeleteSession(id); }}
          onDeleteRepositoryGroup={(groupId) => { handleDeleteRepositoryGroup(groupId); }}
          onRenameRepositoryGroup={(groupId) => { handleRenameRepositoryGroup(groupId); }}
          onMoveWorkspaceToGroup={(wsId, grpId) => { void handleMoveWorkspaceToGroup(wsId, grpId); }}
        />

        {/* Main workspace + right rail (Coding chat / Design canvas / file preview) */}
        {previewFile ? (
            <div 
              style={{ paddingLeft: `${selectedSidebarWidth}px`, paddingRight: `${rightSidebarWidth}px`, paddingTop: CONTENT_TOP_WITH_BANNER }}
              className="flex-1 flex flex-col bg-white h-screen overflow-hidden animate-fade-in relative z-30 transition-all duration-300"
            >
              {/* File Preview Header */}
              <div className="h-14 border-b border-outline-variant/60 flex items-center justify-between px-6 bg-neutral-50/50 flex-shrink-0 select-none">
                <div className="flex items-center gap-3">
                  <LegacyIcon
                    name={
                      previewFile.mediaSrc
                        ? 'image'
                        : previewFile.name.endsWith('.md')
                          ? 'markdown'
                          : 'code'
                    }
                    className="text-[20px] text-neutral-500"
                  />
                  <div className="flex flex-col justify-center">
                    <h3 className="text-xs font-bold text-neutral-900 font-mono tracking-tight flex items-center gap-1">
                      {previewFile.name.includes('/') && (
                        <span className="text-neutral-400 font-medium">{previewFile.name.split('/').slice(0, -1).join('/')}/</span>
                      )}
                      <span>{previewFile.name.split('/').pop()}</span>
                    </h3>
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => {
                      if (previewFile.mediaSrc) {
                        void navigator.clipboard.writeText(previewFile.name);
                        return;
                      }
                      void navigator.clipboard.writeText(previewFile.content);
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-neutral-500 hover:text-neutral-900 hover:bg-neutral-200/50 rounded-lg text-[11px] font-semibold transition-colors"
                  >
                    <LegacyIcon name="content_copy" className="text-[16px]" />
                    Copy
                  </button>
                  <button
                    type="button"
                    onClick={() => setPreviewFile(null)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-neutral-500 hover:text-neutral-900 hover:bg-neutral-200/50 rounded-lg text-[11px] font-semibold transition-colors"
                  >
                    <LegacyIcon name="close" className="text-[16px]" />
                    Close
                  </button>
                </div>
              </div>

              {/* Code/Markdown/Image Content Viewer */}
              <div className="flex-1 overflow-y-auto p-8 font-mono text-xs text-neutral-800 bg-[#f9f9f9] select-text leading-relaxed">
                {previewFile.mediaSrc ? (
                  <div className="max-w-5xl mx-auto flex items-center justify-center min-h-[calc(100vh-10rem)]">
                    <img
                      src={previewFile.mediaSrc}
                      alt={previewFile.name}
                      className="max-h-[calc(100vh-12rem)] max-w-full object-contain rounded-xl border border-outline-variant/40 bg-white shadow-sm"
                    />
                  </div>
                ) : previewFile.plain ? (
                  <div className="max-w-4xl mx-auto space-y-2">
                    <p className="text-[11px] font-semibold text-neutral-500 font-sans">
                      Large file: plain view
                    </p>
                    <pre className="bg-neutral-900 text-neutral-200 p-6 rounded-xl text-[11px] shadow-sm overflow-auto max-h-[calc(100vh-10rem)] whitespace-pre border border-neutral-800">
                      {previewFile.content}
                    </pre>
                  </div>
                ) : previewFile.name.endsWith('.md') ? (
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
        ) : appMode === 'design' ? (
          <div
            style={{
              paddingLeft: `${selectedSidebarWidth}px`,
              paddingRight: `${rightSidebarWidth}px`,
              paddingTop: CONTENT_TOP_WITH_BANNER,
              paddingBottom: '32px',
            }}
            className="flex-1 flex flex-col h-screen overflow-hidden relative z-20 transition-all duration-300"
          >
            <DesignWorkspace
              key={sessionRunId}
              runId={sessionRunId}
              workspaceReady={Boolean(workspace)}
              modelLabel={selectedModel}
              onOpenModels={() => setView('models')}
              onBusyChange={handleDesignBusyChange}
              onSessionTitle={(title, meta) => {
                setCurrentFlowName(title);
                // Title + device — never force status=running (races with ready after generate).
                const device =
                  meta?.device === 'app' || meta?.device === 'web' ? meta.device : undefined;
                setSessions((prev) =>
                  prev.map((s) =>
                    s.run_id === sessionRunId
                      ? {
                          ...s,
                          title: title.slice(0, 80),
                          mode: 'design' as const,
                          ...(device ? { device } : {}),
                        }
                      : s,
                  ),
                );
                void createSession({
                  run_id: sessionRunId,
                  title,
                  mode: 'design',
                }).catch(() => {});
              }}
              onSendToCoding={(handoff: CodingHandoff) => {
                void (async () => {
                  await handleNewChat();
                  setInputValue(handoff.instruction);
                  setAppMode('coding');
                  setView('chat');
                })();
              }}
            />
          </div>
        ) : (
            <>
              <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden">
              <ChatFeed
                messages={chatMessages}
                hybridExecutions={clutchState.hybrid_executions}
                inputValue={inputValue}
                setInputValue={setInputValue}
                onSendMessage={handleSendMessage}
                sessionTitle={sessionTitle}
                sessionRunId={sessionRunId}
                clutchStatus={clutchStatus}
                currentFlowName={currentFlowName || clutchState.workflow_id}
                selectedSidebarWidth={selectedSidebarWidth}
                rightSidebarWidth={rightSidebarWidth}
                sidebarOpen={sidebarOpen}
                rightPanelOpen={rightPanelOpen}
                onStopRun={handleStopRun}
                onContinueRun={handleContinueRun}
                isMultiAgent={isMultiAgent}
                onApprove={handleApprove}
                onReject={handleReject}
                onRetryWithInstructions={handleRetryWithInstructions}
                onAnswerQuestion={handleAnswerQuestion}
                workspaceAuthorized={Boolean(workspace)}
                onPickWorkspace={() => { void handlePickWorkspace(); }}
                onOpenWorkflows={() => setView('workflows')}
                workspacePickError={workspacePickError}
                selectedWorkflowId={selectedWorkflowId}
                selectedWorkflowName={currentFlowName}
                onClearSelectedWorkflow={() => {
                  clearWorkflowSelection();
                  selectDefaultAgent();
                }}
                activeWorkflowId={clutchState.workflow_id}
                llmModelName={chatLlmModelName}
                activeAgentName={chatActiveAgentName}
                activeAgentAvatar={chatActiveAgentAvatar}
                activeNodeId={clutchState.active_node_id}
                workflowAgentSteps={workflowAgentSteps}
                resolveAgentLogo={resolveAgentLogo}
                engineHint={chatRuntimeEngineHint}
                activeAgentType={selectedAgent ? agentTypeFromAgent(selectedAgent) : ''}
                workspaceViewMode={workspaceViewMode}
                onWorkspaceViewModeChange={handleWorkspaceViewModeChange}
                onLeaveTerminalConfirm={promptLeaveTerminal}
                highlightedDispatchEntryId={highlightedDispatchEntryId}
                hasCliAgents={hasCliAgents}
                workspaceFiles={workspaceFiles}
                sessions={sessions}
                skills={chatSkills}
                permissionMode={permissionMode}
                onPermissionModeChange={handlePermissionModeChange}
                shellSessionStatus={clutchState.shell_session_status}
                shellPoolBlockerRunIds={clutchState.shell_pool_blocker_run_ids}
                shellPoolBlockers={clutchState.shell_pool_blockers}
                shellPoolQueuePosition={clutchState.shell_pool_queue_position}
                shellPoolQueueDepth={clutchState.shell_pool_queue_depth}
                userAvatar={userAvatar}
                userName={userName}
                terminalLogs={terminalLogs}
                onClearTerminal={handleClearTerminal}
                mentionableAgents={mentionableAgents}
                selectedMentionAgentId={selectedAgentId}
                onMentionAgentChange={syncSelectedAgentFromMention}
                workspacePath={workspace?.workspace_path}
                isHistorySessionView={historySessionViewRunId === sessionRunId}
                onOpenWorkspaceFile={(path) => { void handleOpenWorkspaceFile(path); }}
                onPreviewSnippet={handlePreviewSnippet}
                onViewToolStepInTerminal={handleViewToolStepInTerminal}
                mcpServerIds={selectedAgent?.mcpServerIds}
                showMcpBindingBadge={
                  Boolean(selectedAgent && isClutchAgentType(selectedAgent) && !selectedWorkflowId && !clutchState.workflow_id)
                }
                onOpenMcpBind={() => setView('agents')}
                onSlashCommand={handleSlashCommand}
                slashNotice={slashNotice}
                onDismissSlashNotice={dismissSlashNotice}
                onSelectSession={(session) => { void handleSelectSession(session); }}
              />
              </div>
            </>
        )}

        {/* Right collapsible rail — Coding + Design (Design defaults collapsed) */}
        {(appMode === 'coding' || appMode === 'design') && !['workflows', 'agents', 'tools', 'skills', 'mcp', 'models', 'appearance', 'settings'].includes(currentView) ? (
              <RightPanel
                activeTab={rightTab}
                setActiveTab={setRightTab}
                clutchStatus={clutchStatus}
                activeNodeId={clutchState.active_node_id}
                activeAgent={clutchState.active_agent}
                workflowId={effectiveWorkflowId}
                workflowName={effectiveWorkflowName}
                currentInstruction={clutchState.current_instruction}
                sessionTokens={clutchState.session_tokens}
                sessionCostUsd={clutchState.session_cost_usd}
                tokenInput={clutchState.token_input}
                tokenOutput={clutchState.token_output}
                runStats={clutchState.run_stats}
                uncommitted={uncommitted}
                terminalLogs={terminalLogs}
                isOpen={rightPanelOpen}
                setIsOpen={setRightPanelOpen}
                isMultiAgent={isMultiAgent}
                sessionAgentName={selectedAgentName}
                modelName={footerEffectiveModelName}
                workspaceFiles={workspaceFiles}
                onOpenWorkspaceFile={(path) => { void handleOpenWorkspaceFile(path); }}
                highlightedLogIndex={highlightedLogIndex}
                workspaceAuthorized={Boolean(workspace)}
                onClearTerminal={handleClearTerminal}
                dispatchLog={clutchState.dispatch_log ?? []}
                showTerminalOrchestraOverview={
                  appMode === 'coding'
                  && isPlainLlmFooter
                  && (workspaceViewMode === 'terminal' || sessionHasTerminalHistory(clutchState))
                }
                terminalHistoryReadOnly={
                  appMode === 'coding'
                  && isPlainLlmFooter
                  && isArchivedTerminalHistoryView(clutchState, workspaceViewMode)
                }
                onSelectDispatchEntry={(id) => setHighlightedDispatchEntryId(id)}
                workflowAgentSteps={workflowAgentSteps}
                messages={chatMessages}
              />
        ) : null}
        {/* Unified Settings & Agent Controller Dialog Modal */}
        <SystemPreferencesModal
          currentView={currentView}
          setView={setView}
          isMultiAgent={isMultiAgent}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
          activeModelId={activeModelId}
          setActiveModelId={setActiveModelId}
          configuredModels={configuredModels}
          setConfiguredModels={setConfiguredModels}
          themeId={themeId}
          setThemeId={setThemeId}
          workspaceLabel={workspace?.name ?? workspace?.workspace_path?.split('/').pop() ?? null}
          sessionActive={clutchStatus !== 'idle' && clutchStatus !== 'failed'}
          onUseWorkflowInChat={handleUseWorkflowInChat}
          onSelectWorkflow={bindWorkflowForChat}
          onClearSelectedWorkflow={clearWorkflowSelection}
          selectedWorkflowId={selectedWorkflowId}
          activeAgentId={selectedAgentId}
          onActivateAgent={handleActivateAgent}
          userAvatar={userAvatar}
          setUserAvatar={setUserAvatarState}
          userName={userName}
          setUserName={setUserName}
          fontSize={fontSize}
          setFontSize={setFontSize}
        />

      </div>

      {/* 3. Footer Bar Component */}
      <footer 
        style={{ left: `${selectedSidebarWidth}px` }}
        className="fixed bottom-0 right-0 h-8 bg-background border-t border-outline-variant flex items-center justify-between px-6 z-50 text-[11px] text-on-surface-variant/80 select-none transition-all duration-300"
      >
        <div className="flex items-center gap-6">
          <div className="relative">
            <button
              type="button"
              data-testid="footer-branch-trigger"
              onClick={() => {
                const next = !branchMenuOpen;
                closeFooterMenus();
                setBranchMenuOpen(next);
              }}
              className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low hover:text-on-surface transition-colors cursor-pointer font-medium whitespace-nowrap"
              aria-label={`${t('Branch')}: ${workspaceGit.branch || '—'}`}
            >
              <LegacyIcon name="account_tree" className="text-[15px] text-on-surface-variant" />
              {t('Branch')}: {workspaceGit.branch || '—'}
              <LegacyIcon name="keyboard_arrow_down" className="text-[13px]" />
            </button>
            {branchMenuOpen ? (
              <FooterMenuPanel testId="footer-branch-menu">
                {workspaceGit.branches.length === 0 ? (
                  <p className="px-3 py-2 pl-9 text-[11px] text-on-surface-variant">{t('Not a git repository')}</p>
                ) : (
                  workspaceGit.branches.map((branch) => (
                    <FooterMenuItem
                      key={branch}
                      testId={`footer-branch-item-${branch}`}
                      selected={branch === workspaceGit.branch}
                      onClick={() => setBranchMenuOpen(false)}
                    >
                      {branch}
                    </FooterMenuItem>
                  ))
                )}
              </FooterMenuPanel>
            ) : null}
          </div>

          {!hideFooterSessionControls ? (
            <>
          {hasWorkflowSelection ? (
            <span
              data-testid="footer-model-disabled"
              className="flex items-center gap-1.5 px-2 py-1 rounded font-medium text-on-surface-variant cursor-default whitespace-nowrap"
              title={t('Model is determined by the selected workflow')}
            >
              <LegacyIcon name="layers" className="text-[15px] text-on-surface-variant" />
              {t("Model")}: —
            </span>
          ) : showFooterModel ? (
            <div className="relative">
              {agentBoundModelId && appMode !== 'design' ? (
                <span
                  data-testid="footer-model-trigger"
                  className="flex items-center gap-1.5 px-2 py-1 rounded font-medium text-on-surface-variant whitespace-nowrap cursor-default"
                  title={t('Model is bound on this agent')}
                >
                  <LegacyIcon name="layers" className="text-[15px] text-on-surface-variant" />
                  {t("Model")}: {footerEffectiveModelName}
                </span>
              ) : (
                <>
              <button
                type="button"
                data-testid="footer-model-trigger"
                onClick={toggleModelMenu}
                className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low hover:text-on-surface transition-colors cursor-pointer font-medium text-on-surface-variant whitespace-nowrap"
                aria-label={`${t("Model")}: ${footerEffectiveModelName}`}
              >
                <LegacyIcon name="layers" className="text-[15px] text-on-surface-variant" />
                {t("Model")}: {footerEffectiveModelName}
                <LegacyIcon name="keyboard_arrow_down" className="text-[13px]" />
              </button>
              {modelMenuOpen ? (
                <FooterMenuPanel testId="footer-model-menu">
                  <FooterMenuAction
                    testId="footer-model-manage"
                    onClick={() => {
                      setModelMenuOpen(false);
                      setView('models');
                    }}
                  >
                    {t('Manage models...')}
                  </FooterMenuAction>
                  {configuredModels.length === 0 ? (
                    <p className="px-3 py-2 pl-9 text-[11px] text-on-surface-variant">{t('No models configured')}</p>
                  ) : (
                    (() => {
                      const chatModels = configuredModels.filter(
                        (m) => m.available && (m.modelKind ?? 'chat') === 'chat',
                      );
                      const imageModels = configuredModels.filter(
                        (m) => m.available && m.modelKind === 'image',
                      );
                      const videoModels = configuredModels.filter(
                        (m) => m.available && m.modelKind === 'video',
                      );
                      const renderGroup = (
                        label: string,
                        models: typeof configuredModels,
                      ) =>
                        models.length > 0 ? (
                          <React.Fragment key={label}>
                            <FooterMenuSection label={label} />
                            {models.map((model) => (
                              <FooterMenuItem
                                key={model.id}
                                testId={`footer-model-item-${model.id}`}
                                selected={model.id === footerEffectiveModelId}
                                onClick={() => handleFooterModelSelect(model.id)}
                              >
                                {model.name}
                                {modelKindMenuSuffix(model.modelKind)}
                              </FooterMenuItem>
                            ))}
                          </React.Fragment>
                        ) : null;
                      return (
                        <>
                          {renderGroup(t('Chat models'), chatModels)}
                          {renderGroup(t('Image models'), imageModels)}
                          {renderGroup(t('Video models'), videoModels)}
                        </>
                      );
                    })()
                  )}
                </FooterMenuPanel>
              ) : null}
                </>
              )}
            </div>
          ) : !hasWorkflowSelection && customAgentEngineLabel ? (
            <span
              data-testid="footer-engine-label"
              className="flex items-center gap-1.5 px-2 py-1 rounded font-medium text-on-surface-variant cursor-default whitespace-nowrap"
              title={t('Model is provided by the selected agent tool')}
            >
              <LegacyIcon name="bolt" className="text-[15px] text-on-surface-variant" />
              {t('Engine')}: {customAgentEngineLabel}
            </span>
          ) : null}

          {isMultiAgent ? (
            <>
              <div className="relative">
                {appMode === 'design' ? (
                  <span
                    data-testid="footer-agent-trigger"
                    className="flex items-center gap-1.5 px-2 py-1 rounded font-medium text-on-surface-variant cursor-default whitespace-nowrap opacity-70"
                    title={t('Design uses the Model LLM, not CLI agents')}
                    aria-label={`${t('Active Agent')}: ${t('Clutch Agent')}`}
                  >
                    <LegacyIcon name="smart_toy" className="text-[15px]" />
                    {t('Active Agent')}: {t('Clutch Agent')}
                  </span>
                ) : (
                  <>
                    <button
                      type="button"
                      data-testid="footer-agent-trigger"
                      onClick={toggleAgentMenu}
                      className={`flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low transition-colors cursor-pointer font-medium whitespace-nowrap ${
                        selectedAgentId
                          ? 'text-primary font-bold'
                          : 'text-on-surface-variant'
                      }`}
                      aria-label={`${t('Active Agent')}: ${multiAgentFooterName}`}
                    >
                      <LegacyIcon name="smart_toy" className="text-[15px]" />
                      {t('Active Agent')}: {multiAgentFooterName}
                      <LegacyIcon name="keyboard_arrow_down" className="text-[13px]" />
                    </button>
                    {agentMenuOpen ? (
                      <FooterMenuPanel testId="footer-agent-menu">
                        <FooterMenuAction
                          testId="footer-agent-manage"
                          onClick={() => {
                            setAgentMenuOpen(false);
                            setView('agents');
                          }}
                        >
                          {t('Manage agents...')}
                        </FooterMenuAction>
                        {footerSelectableAgents.map((agent) => (
                          <FooterMenuItem
                            key={agent.id}
                            testId={`footer-agent-item-${agent.id}`}
                            selected={agent.id === selectedAgentId}
                            onClick={() => handleFooterAgentSelect(agent)}
                          >
                            {getAgentDisplayName(agent)}
                          </FooterMenuItem>
                        ))}
                      </FooterMenuPanel>
                    ) : null}
                  </>
                )}
              </div>
              <div className="relative">
                {appMode === 'design' ? (
                  <span
                    data-testid="footer-workflow-trigger"
                    className="flex items-center gap-1.5 px-2 py-1 rounded font-medium text-on-surface-variant cursor-default whitespace-nowrap opacity-70"
                    title={t('Workflows are available in Coding mode')}
                    aria-label={`${t('Workflow')}: —`}
                  >
                    <LegacyIcon name="fork_right" className="text-[15px]" />
                    {t('Workflow')}: —
                  </span>
                ) : (
                  <>
                    <button
                      type="button"
                      data-testid="footer-workflow-trigger"
                      onClick={() => { void toggleWorkflowMenu(); }}
                      className={`flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low transition-colors cursor-pointer font-medium whitespace-nowrap ${
                        hasWorkflowSelection
                          ? 'text-primary font-bold'
                          : 'text-on-surface-variant'
                      }`}
                      aria-label={`${t('Workflow')}: ${activeWorkflowLabel}`}
                    >
                      <LegacyIcon name="fork_right" className="text-[15px]" />
                      {t('Workflow')}: {activeWorkflowLabel}
                      <LegacyIcon name="keyboard_arrow_down" className="text-[13px]" />
                    </button>
                    {workflowMenuOpen ? (
                      <FooterMenuPanel testId="footer-workflow-menu">
                        <FooterMenuAction
                          testId="footer-workflow-manage"
                          onClick={() => {
                            setWorkflowMenuOpen(false);
                            setView('workflows');
                          }}
                        >
                          {t('Manage workflows...')}
                        </FooterMenuAction>
                        {footerWorkflows.length === 0 ? (
                          <p className="px-3 py-2 pl-9 text-[11px] text-on-surface-variant">{t('No workflows yet')}</p>
                        ) : (
                          footerWorkflows.map((workflow) => (
                            <FooterMenuItem
                              key={workflow.id}
                              testId={`footer-workflow-item-${workflow.id}`}
                              selected={workflow.id === (selectedWorkflowId || clutchState.workflow_id)}
                              onClick={() => {
                                bindWorkflowForChat(workflow.id, workflow.name);
                                setWorkflowMenuOpen(false);
                              }}
                            >
                              {workflow.name}
                            </FooterMenuItem>
                          ))
                        )}
                      </FooterMenuPanel>
                    ) : null}
                  </>
                )}
              </div>
            </>
          ) : appMode === 'design' ? (
            <span
              data-testid="footer-agent-trigger"
              className="flex items-center gap-1.5 px-2 py-1 rounded font-medium text-on-surface-variant cursor-default whitespace-nowrap opacity-70"
              title={t('Design uses the Model LLM, not CLI agents')}
              aria-label={`${t('Active Agent')}: ${t('Clutch Agent')}`}
            >
              <LegacyIcon name="smart_toy" className="text-[15px]" />
              {t('Active Agent')}: {t('Clutch Agent')}
            </span>
          ) : (
            <div className="relative">
              <button
                type="button"
                data-testid="footer-agent-trigger"
                onClick={toggleAgentMenu}
                className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low text-primary font-bold transition-colors cursor-pointer whitespace-nowrap"
                aria-label={`${t("Active Agent")}: ${selectedAgentName}`}
              >
                <LegacyIcon name="smart_toy" className="text-[15px] text-primary" />
                {t("Active Agent")}: {selectedAgentName}
                <LegacyIcon name="keyboard_arrow_down" className="text-[13px]" />
              </button>
              {agentMenuOpen ? (
                <FooterMenuPanel testId="footer-agent-menu">
                  <FooterMenuAction
                    testId="footer-agent-manage"
                    onClick={() => {
                      setAgentMenuOpen(false);
                      setView('agents');
                    }}
                  >
                    {t('Manage agents...')}
                  </FooterMenuAction>
                  {footerSelectableAgents.map((agent) => (
                    <FooterMenuItem
                      key={agent.id}
                      testId={`footer-agent-item-${agent.id}`}
                      selected={agent.id === selectedAgentId}
                      onClick={() => handleFooterAgentSelect(agent)}
                    >
                      {getAgentDisplayName(agent)}
                    </FooterMenuItem>
                  ))}
                </FooterMenuPanel>
              ) : null}
            </div>
          )}
            </>
          ) : null}
        </div>

        <div
          className="flex items-center gap-1.5 font-semibold text-on-surface-variant/70 italic mr-2 select-text"
          data-testid="footer-app-brand"
        >
          <BrandLogo
            src={clutchMarkUrl}
            alt=""
            rounded="none"
            className="w-3.5 h-3.5 rounded-sm flex items-center justify-center flex-shrink-0 bg-black"
            imgClassName="w-full h-full object-cover block"
          />
          <span>Clutch v{appVersion}</span>
        </div>
      {promptModal && (
        <PromptModal
          isOpen={promptModal.isOpen}
          title={promptModal.title}
          message={promptModal.message}
          hasInput={promptModal.hasInput}
          placeholder={promptModal.placeholder}
          defaultValue={promptModal.defaultValue}
          onConfirm={promptModal.onConfirm}
          onCancel={() => setPromptModal(null)}
        />
      )}
      </footer>
      {previewToast ? (
        <div
          className="fixed bottom-16 left-1/2 -translate-x-1/2 z-[80] max-w-md px-4 py-2 rounded-xl bg-neutral-900 text-white text-[12px] font-medium shadow-xl"
          role="status"
        >
          {previewToast}
        </div>
      ) : null}
    </div>
  );
}


export default function App() {
  if (import.meta.env.DEV && new URLSearchParams(window.location.search).get('dev_tools_empty') === '1') {
    return (
      <LanguageProvider>
        <DevOnboardingToolsEmptyPreview />
      </LanguageProvider>
    );
  }

  return (
    <LanguageProvider>
      <AppErrorBoundary>
        <AppGate />
      </AppErrorBoundary>
    </LanguageProvider>
  );
}


function AppGate() {
  const [onboardingCompleted, setOnboardingCompleted] = useState<boolean | null>(null);

  useEffect(() => {
    void fetchOnboardingState()
      .then((done) => setOnboardingCompleted(done))
      .catch(() => setOnboardingCompleted(false));
  }, []);

  if (onboardingCompleted === null) {
    return (
      <div className="h-screen flex items-center justify-center bg-background text-on-surface-variant text-sm font-sans">
        …
      </div>
    );
  }

  if (!onboardingCompleted) {
    return (
      <OnboardingWizard
        onComplete={() => {
          setOnboardingCompleted(true);
        }}
      />
    );
  }

  return <MainLayout />;
}
