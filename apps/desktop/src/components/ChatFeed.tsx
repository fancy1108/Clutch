import React from 'react';
import {
  APP_HEADER_HEIGHT_PX,
  WORKSPACE_CHROME_ROW_TOP_PX,
} from '../constants/layout';
import { BTN_PRIMARY, BTN_SECONDARY } from './ui/buttonStyles';
import { LegacyIcon } from './ui/LegacyIcon';
import { deleteChatMessage } from '../services/clutchState';
import { AgentLiveActivity, TypingDots } from './AgentLiveActivity';
import { TodoCardView } from './TodoCardView';
import { SubtaskCardView } from './SubtaskCardView';
import { BackgroundJobChip } from './BackgroundJobsBar';
import { GoalBarView } from './GoalBarView';
import { AgentChatAvatar } from './AgentChatAvatar';
import { TerminalOrchestraWorkspace } from './terminal-orchestra/TerminalOrchestraWorkspace';
import { TerminalOrchestraEmptyState } from './terminal-orchestra/TerminalOrchestraEmptyState';
import { TerminalDispatchHistoryFeed } from './terminal-orchestra/TerminalDispatchHistoryFeed';
import { XTERM_KEEPALIVE_STYLE } from './terminal-orchestra/terminalLaneLayout';
import {
  useChatFeedController,
  configuredEngineToRuntimeLabel,
  type UseChatFeedControllerParams,
} from '../hooks/useChatFeedController';
import { AgentMessageLabel, ChatMessageBubbleRow } from './ChatMessageBubble';
import { ChatFeedDock } from './ChatFeedDock';

export { configuredEngineToRuntimeLabel };

export type ChatFeedProps = UseChatFeedControllerParams;

export const ChatFeed: React.FC<ChatFeedProps> = (props) => {
  const c = useChatFeedController(props);

  return (
    <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden relative w-full">
      <section
        style={{
          paddingLeft: `${c.leftChromePad}px`,
          paddingRight: `${c.rightChromePad}px`,
          paddingTop: APP_HEADER_HEIGHT_PX,
          paddingBottom: c.isTerminalLayout
            ? c.terminalInputReservePx
            : Math.max(c.chatScrollBottomPad, c.awaitingHuman ? 200 : 120),
        }}
        className={`flex-1 min-h-0 flex flex-col box-border transition-all duration-300 bg-background ${
          c.isTerminalLayout
            ? 'overflow-hidden pb-1 items-stretch px-4'
            : `overflow-y-auto overscroll-contain items-stretch ${c.chatChrome.chatEdgePaddingClass}`
        }`}
      >
        <div
          className={`w-full min-w-0 ${
            c.isTerminalLayout
              ? 'flex-1 min-h-0 flex flex-col max-w-none h-full'
              : `${c.chatChrome.chatMaxWidthClass} mx-auto ${c.chatChrome.messageListSpacingClass} py-4`
          }`}
        >
          {c.showWorkspaceReadonlyChrome ? (
            <div className={c.workspaceChromeRowClass()} style={{ paddingTop: WORKSPACE_CHROME_ROW_TOP_PX }}>
              <span
                data-testid="workspace-view-readonly-label"
                className="inline-flex items-center gap-1.5 rounded-xl border border-outline-variant/40 px-3 py-1.5 text-[11px] font-bold whitespace-nowrap shadow-sm bg-surface-container-low text-on-surface-variant"
              >
                {c.t('Chat mode')}
                <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded-md bg-neutral-100 text-on-surface-variant/80">
                  {c.t('Read-only')}
                </span>
              </span>
            </div>
          ) : c.showWorkspaceViewToggle ? (
            <div
              className={c.workspaceChromeRowClass()}
              style={{ paddingTop: WORKSPACE_CHROME_ROW_TOP_PX }}
            >
              <div
                data-testid="workspace-view-toggle"
                className="inline-flex items-center rounded-xl border border-outline-variant/40 overflow-hidden text-xs font-bold whitespace-nowrap shadow-sm bg-surface-container-low"
              >
                <button
                  type="button"
                  data-testid="workspace-view-chat"
                  onClick={() => c.handleWorkspaceViewChange('chat')}
                  className={`inline-flex items-center justify-center px-3 h-7 text-[11px] leading-none transition-colors ${
                    c.workspaceViewMode === 'chat'
                      ? 'bg-neutral-900 text-white'
                      : 'bg-transparent text-on-surface-variant hover:bg-surface-container-high'
                  }`}
                >
                  {c.t('Chat mode')}
                </button>
                <button
                  type="button"
                  data-testid="workspace-view-terminal"
                  onClick={() => c.handleWorkspaceViewChange('terminal')}
                  className={`inline-flex items-center justify-center px-3 h-7 text-[11px] leading-none transition-colors border-l border-outline-variant/40 ${
                    c.workspaceViewMode === 'terminal'
                      ? 'bg-neutral-900 text-white'
                      : 'bg-transparent text-on-surface-variant hover:bg-surface-container-high'
                  }`}
                >
                  {c.t('Terminal mode')}
                </button>
              </div>
            </div>
          ) : null}
          {c.workspaceViewMode === 'chat' && c.showEmptyState && (
            <div className="flex flex-col items-center justify-center text-center py-16 px-6 space-y-5">
              <div className="w-14 h-14 rounded-2xl bg-surface-container-low border border-outline-variant/40 flex items-center justify-center">
                <LegacyIcon name={c.isMultiAgent ? 'hub' : 'smart_toy'} className="text-[28px] text-on-surface-variant" />
              </div>
              <div className="space-y-2 max-w-md">
                <h2
                  data-testid="chat-supervised-title"
                  className="text-lg font-bold text-on-surface tracking-tight"
                >
                  {c.isMultiAgent ? c.t('Start a supervised session') : c.t('Start a single agent session')}
                </h2>
                <p className="text-sm text-on-surface-variant leading-relaxed">
                  {c.isMultiAgent
                    ? c.t('Select a workspace and start a workflow, or type an instruction below. Clutch will orchestrate AI Agents and ask for your approval when needed.')
                    : c.t('Select a workspace and type an instruction below to chat with the agent directly.')}
                </p>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-2">
                {c.workspacePickError && (
                  <p className="w-full text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                    {c.workspacePickError}
                  </p>
                )}
                {!c.workspaceAuthorized && (
                  <button
                    type="button"
                    data-testid="chat-authorize-workspace"
                    onClick={c.onPickWorkspace}
                    className={BTN_PRIMARY}
                  >
                    {c.t('Authorize workspace')}
                  </button>
                )}
                {c.workspaceAuthorized && c.isMultiAgent && (
                  <button
                    type="button"
                    data-testid="chat-open-workflows"
                    onClick={c.onOpenWorkflows}
                    className={BTN_SECONDARY}
                  >
                    {c.t('Choose workflow')}
                  </button>
                )}
              </div>
            </div>
          )}

          {c.keepTerminalMounted ? (
            <div
              ref={c.terminalStageRef}
              className={c.isTerminalLayout ? 'flex flex-1 flex-col min-h-0 min-w-0 w-full' : undefined}
              style={c.isTerminalLayout ? undefined : XTERM_KEEPALIVE_STYLE}
              aria-hidden={c.isTerminalLayout ? undefined : true}
            >
              <TerminalOrchestraWorkspace
                visible={c.isTerminalLayout}
                clutchStatus={c.clutchStatus}
                sessionRunId={c.sessionRunId}
                barFocused={c.orchestratorBarFocused}
                configuredAgents={c.mentionableAgents}
                sessionDispatched={c.sessionDispatched}
                previewAgentType={c.terminalPreviewAgentType}
                previewAgentId={c.sessionDispatched ? null : c.inputTerminalMention?.agentId ?? null}
                previewAgentName={c.sessionDispatched ? null : c.inputTerminalMention?.name ?? null}
                layoutChromeKey={c.terminalLayoutChromeKey}
                layoutObserveRef={c.terminalStageRef}
                onOpenWorkspaceFile={c.onOpenWorkspaceFile}
              />
            </div>
          ) : c.isPlainLlmChat && c.hasCliAgents && c.isTerminalLayout ? (
            <TerminalOrchestraEmptyState sessionRunId={c.sessionRunId} />
          ) : null}

          {c.isTerminalLayout ? (
            <div
              data-testid="terminal-input-gap"
              className="shrink-0 w-full"
              style={{ height: c.terminalBarHeight }}
              aria-hidden
            />
          ) : null}

          {c.isTerminalDispatchHistoryReadonly ? (
            <div className={`w-full ${c.chatChrome.chatMaxWidthClass} mx-auto ${c.chatChrome.messageListSpacingClass} py-4`}>
              <TerminalDispatchHistoryFeed
                entries={c.clutchOrchestraState.dispatch_log ?? []}
                highlightedEntryId={c.highlightedDispatchEntryId}
                userAvatar={c.userAvatar}
                userName={c.userName}
                mentionableAgents={c.mentionableAgents}
                workspacePath={c.workspacePath}
                onOpenWorkspaceFile={c.onOpenWorkspaceFile}
              />
            </div>
          ) : null}

          {c.workspaceViewMode === 'chat' && props.messages.map((msg, messageIndex) => (
            <ChatMessageBubbleRow
              key={msg.id}
              msg={msg}
              messageIndex={messageIndex}
              chatChrome={c.chatChrome}
              t={c.t}
              renderMarkdown={c.renderMarkdown}
              isPlainLlmChat={c.isPlainLlmChat}
              llmModelName={c.llmModelName}
              userName={c.userName}
              userAvatar={c.userAvatar}
              hybridExecutions={c.hybridExecutions}
              workflowAgentSteps={c.workflowAgentSteps}
              workflowReplyStepIndex={c.workflowReplyStepIndex}
              resolveAgentLogo={c.resolveAgentLogo}
              onOpenWorkspaceFile={c.onOpenWorkspaceFile}
              onViewToolStepInTerminal={c.onViewToolStepInTerminal}
              onContextMenu={c.handleMessageContextMenu}
              awaitingPlan={c.awaitingPlan}
              pendingPlanMessage={c.pendingPlanMessage}
              planStepComments={
                c.awaitingPlan && msg === c.pendingPlanMessage
                  ? c.planStepComments
                  : undefined
              }
              onPlanStepCommentChange={
                c.awaitingPlan && msg === c.pendingPlanMessage
                  ? (index, value) => {
                      c.setPlanStepComments((prev) => {
                        const next = [...prev];
                        next[index] = value;
                        return next;
                      });
                    }
                  : undefined
              }
              awaitingHuman={c.awaitingHuman}
              pendingQuestionMessage={c.pendingQuestionMessage}
              hitlBusy={c.hitlBusy}
              setHitlBusy={c.setHitlBusy}
              onAnswerQuestion={c.onAnswerQuestion}
              activeAgentName={c.activeAgentName}
            />
          ))}

          {c.workspaceViewMode === 'chat' &&
            c.feedFallbackBgJobs.map((job) => (
              <div key={`bg-feed-${job.id}`} className="w-full flex justify-start mb-4">
                <div className={c.chatChrome.thinkingRowClass}>
                  <div className="w-8 shrink-0" aria-hidden />
                  <div className="flex-1 min-w-0 max-w-full">
                    <BackgroundJobChip job={job} t={c.t} variant="feed" />
                  </div>
                </div>
              </div>
            ))}

          {c.workspaceViewMode === 'chat' && c.showThinking && (
            <div ref={c.thinkingRef} className="w-full flex justify-start mb-4">
              <div className={c.chatChrome.thinkingRowClass}>
                <AgentChatAvatar
                  src={c.thinkingAgentLogo || c.activeAgentAvatar}
                  alt={c.thinkingAgentName || c.t('Clutch Agent')}
                />

                <div className="flex-1 space-y-1.5 min-w-0">
                  <div className="flex items-center gap-2">
                    <AgentMessageLabel
                      agent={c.thinkingAgentName || c.t('Clutch Agent')}
                      statusHint={
                        c.shellSessionStatus === 'queued_pool'
                          ? c.t('Queued for shell...')
                          : c.showLiveActivity
                            ? c.t('Working…')
                            : c.t('Thinking...')
                      }
                      runtimeEngine={c.isPlainLlmChat ? undefined : c.engineHint}
                      workflowAgentType={c.thinkingAgentType || undefined}
                      isPlainLlmChat={c.isPlainLlmChat}
                      activeAgentName={c.activeAgentName}
                      llmModelName={c.llmModelName}
                      engineHint={c.engineHint}
                      t={c.t}
                    />
                  </div>

                  {c.showLiveActivity ? (
                    <div className="min-w-0" data-testid="chat-live-process">
                      <AgentLiveActivity
                        steps={c.liveActivitySteps}
                        reasoningContent={c.liveReasoning}
                        live
                        onOpenFile={c.onOpenWorkspaceFile}
                        onViewInTerminal={c.onViewToolStepInTerminal}
                      />
                      {c.showInlineLiveTodos ? (
                        <TodoCardView todos={c.liveTodos} t={c.t} live />
                      ) : null}
                      {c.liveSubtasks.length > 0 ? (
                        <SubtaskCardView
                          cards={c.liveSubtasks}
                          t={c.t}
                          live
                          onViewInTerminal={c.onViewToolStepInTerminal}
                        />
                      ) : null}
                    </div>
                  ) : (
                    <div
                      className={`${c.chatChrome.thinkingBubblePaddingClass} bg-surface-container-low rounded-2xl rounded-tl-none border border-outline-variant/30 shadow-sm flex items-center gap-2 min-h-9`}
                      data-testid="chat-thinking-dots"
                      role="status"
                      aria-busy="true"
                      aria-label={c.t('Thinking...')}
                    >
                      <TypingDots />
                      <span className="text-[11px] text-on-surface-variant">{c.t('Thinking...')}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {c.workspaceViewMode === 'chat' && !c.showThinking && c.showLiveActivity && c.awaitingHuman ? (
            <div className="w-full flex justify-start mb-4">
              <div className={c.chatChrome.thinkingRowClass}>
                <div className="w-8 shrink-0" aria-hidden />
                <div className="flex-1 overflow-hidden min-w-0" data-testid="chat-live-process">
                  <AgentLiveActivity
                    steps={c.liveActivitySteps}
                    reasoningContent={c.liveReasoning}
                    live
                    defaultOpen
                    onOpenFile={c.onOpenWorkspaceFile}
                    onViewInTerminal={c.onViewToolStepInTerminal}
                  />
                  {c.showInlineLiveTodos ? (
                    <TodoCardView todos={c.liveTodos} t={c.t} live />
                  ) : null}
                </div>
              </div>
            </div>
          ) : null}

          {c.workspaceViewMode === 'chat' ? (
            <div ref={c.bottomRef} style={{ scrollMarginBottom: c.chatScrollBottomPad }} className="h-2 shrink-0" aria-hidden />
          ) : null}
        </div>
      </section>

      {c.workspaceViewMode === 'chat' && c.showGoalBar && c.liveGoal ? (
        <div
          data-testid="goal-sticky-rail"
          className="pointer-events-none absolute z-25"
          style={{
            top: APP_HEADER_HEIGHT_PX + (c.pinLiveTodos ? 72 : 0),
            left: c.leftChromePad,
            right: c.rightChromePad,
          }}
        >
          <div className={`w-full bg-background pt-2 ${c.chatChrome.chatEdgePaddingClass}`}>
            <div className="pointer-events-auto w-full">
              <GoalBarView goal={c.liveGoal} t={c.t} />
            </div>
          </div>
        </div>
      ) : null}

      {c.workspaceViewMode === 'chat' && c.pinLiveTodos ? (
        <div
          data-testid="todo-sticky-rail"
          className="pointer-events-none absolute z-30"
          style={{
            top: APP_HEADER_HEIGHT_PX,
            left: c.leftChromePad,
            right: c.rightChromePad,
          }}
        >
          <div className={`w-full bg-background pt-3 ${c.chatChrome.chatEdgePaddingClass}`}>
            <div className="pointer-events-auto w-full">
              <TodoCardView todos={c.liveTodos} t={c.t} live pinned />
            </div>
          </div>
          <div
            className="w-full h-6 bg-gradient-to-b from-background via-background/90 to-transparent"
            aria-hidden
          />
        </div>
      ) : null}

      <ChatFeedDock
        showTerminalWorkspace={c.showTerminalWorkspace}
        terminalDockRef={c.terminalDockRef}
        dockRef={c.dockRef}
        leftChromePad={c.leftChromePad}
        rightChromePad={c.rightChromePad}
        chatChrome={c.chatChrome}
        terminalBarRef={c.terminalBarRef}
        sessionRunId={c.sessionRunId}
        clutchOrchestraState={c.clutchOrchestraState}
        inputValue={c.inputValue}
        setInputValue={c.setInputValue}
        permissionMode={c.permissionMode}
        onPermissionModeChange={c.onPermissionModeChange}
        workspaceFiles={c.workspaceFiles}
        sessions={c.sessions}
        skills={c.skills}
        setOrchestratorBarFocused={c.setOrchestratorBarFocused}
        mentionableAgents={c.mentionableAgents}
        selectedMentionAgentId={c.selectedMentionAgentId}
        onMentionAgentChange={c.onMentionAgentChange}
        isRunning={c.isRunning}
        awaitingHuman={c.awaitingHuman}
        isPlainLlmChat={c.isPlainLlmChat}
        isRefining={c.isRefining}
        currentFlowName={c.currentFlowName}
        onStopRun={c.onStopRun}
        t={c.t}
        awaitingQuestion={c.awaitingQuestion}
        awaitingPlan={c.awaitingPlan}
        hitlBusy={c.hitlBusy}
        setHitlBusy={c.setHitlBusy}
        onApprove={c.onApprove}
        onReject={c.onReject}
        pendingQuestionMessage={c.pendingQuestionMessage}
        hillInstructions={c.hillInstructions}
        setHillInstructions={c.setHillInstructions}
        canSubmitPlanRevise={c.canSubmitPlanRevise}
        submitPlanRevise={c.submitPlanRevise}
        onRetryWithInstructions={c.onRetryWithInstructions}
        isTerminalDispatchHistoryReadonly={c.isTerminalDispatchHistoryReadonly}
        workspaceViewMode={c.workspaceViewMode}
        foregroundShell={c.foregroundShell}
        chatDiagnostics={c.chatDiagnostics}
        worktreeIsolation={c.worktreeIsolation}
        bgJobs={c.bgJobs}
        bgJobToast={c.bgJobToast}
        handleSendWithAttachments={c.handleSendWithAttachments}
        handleStopWithQueueClear={c.handleStopWithQueueClear}
        onContinueRun={c.onContinueRun}
        pendingMessages={c.pendingMessages}
        removePending={c.removePending}
        selectedWorkflowId={c.selectedWorkflowId}
        selectedWorkflowName={c.selectedWorkflowName}
        onClearSelectedWorkflow={c.onClearSelectedWorkflow}
        isMultiAgent={c.isMultiAgent}
        shellSessionStatus={c.shellSessionStatus}
        shellPoolBlockerRunIds={c.shellPoolBlockerRunIds}
        shellPoolBlockers={c.shellPoolBlockers}
        shellPoolQueuePosition={c.shellPoolQueuePosition}
        shellPoolQueueDepth={c.shellPoolQueueDepth}
        clutchStatus={c.clutchStatus}
        onSelectSession={c.onSelectSession}
        resolveAgentLogo={c.resolveAgentLogo}
        workflowAgentSteps={c.workflowAgentSteps}
        mcpServerIds={c.mcpServerIds}
        showMcpBindingBadge={c.showMcpBindingBadge}
        onOpenMcpBind={c.onOpenMcpBind}
        onSlashCommand={c.onSlashCommand}
        slashNotice={c.slashNotice}
        onDismissSlashNotice={c.onDismissSlashNotice}
        handleRewindFiles={c.handleRewindFiles}
      />

      {c.messageContextMenu ? (
        <div
          className="fixed bg-surface-bright border border-outline-variant rounded-lg shadow-lg py-1 z-[100] min-w-[120px]"
          style={{ top: c.messageContextMenu.y, left: c.messageContextMenu.x }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            className="w-full text-left px-3 py-2 text-xs text-on-surface hover:bg-surface-container-low transition-colors flex items-center gap-2"
            data-testid="fork-session-menu"
            onClick={() => {
              void c.handleForkSession(c.messageContextMenu!.messageIndex);
              c.setMessageContextMenu(null);
            }}
          >
            <LegacyIcon name="fork_right" className="text-[16px]" />
            {c.t('Fork session here')}
          </button>
          <button
            type="button"
            className="w-full text-left px-3 py-2 text-xs text-rose-600 hover:bg-rose-50 hover:text-rose-700 transition-colors flex items-center gap-2"
            onClick={() => {
              deleteChatMessage(c.messageContextMenu!.messageId);
              c.setMessageContextMenu(null);
            }}
          >
            <LegacyIcon name="delete" className="text-[16px]" />
            {c.t('Delete message')}
          </button>
        </div>
      ) : null}
    </div>
  );
};
