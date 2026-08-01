import React from 'react';
import { APP_INPUT_DOCK_BOTTOM_PX } from '../constants/layout';
import type { BackgroundJob, ClutchRunStatus, ClutchState } from '../types';
import { clutchStore } from '../services/clutchState';
import type { Attachment } from './ChatInputBar';
import { ChatInputBar } from './ChatInputBar';
import { BTN_SM } from './ui/buttonStyles';
import { LegacyIcon } from './ui/LegacyIcon';
import { ForegroundShellBar } from './ForegroundShellBar';
import { DiagnosticsIssuesStrip } from './DiagnosticsIssuesStrip';
import { WorktreeIsolationBar } from './WorktreeIsolationBar';
import { BackgroundJobsBar } from './BackgroundJobsBar';
import { OrchestratorBar } from './terminal-orchestra/OrchestratorBar';
import type { PendingChatMessage } from '../services/chatPendingQueue';
import type { ScannedSkill } from '../services/skillsApi';
import type { FileTreeNode } from '../services/workspaceApi';
import type { PermissionMode } from '../services/permissionApi';
import type { SessionRecord } from '../services/runApi';
import type { WorkspaceViewMode } from '../services/workspaceViewMode';
import type { chatChromeForHost } from '../platform/chrome/chatChrome';

export interface ChatFeedDockProps {
  showTerminalWorkspace: boolean;
  terminalDockRef: React.RefObject<HTMLDivElement | null>;
  dockRef: React.RefObject<HTMLDivElement | null>;
  leftChromePad: number;
  rightChromePad: number;
  chatChrome: ReturnType<typeof chatChromeForHost>;
  terminalBarRef: React.RefObject<HTMLDivElement | null>;
  sessionRunId: string;
  clutchOrchestraState: ClutchState;
  inputValue: string;
  setInputValue: (val: string) => void;
  permissionMode: PermissionMode;
  onPermissionModeChange?: (mode: PermissionMode) => void;
  workspaceFiles: FileTreeNode[];
  sessions: SessionRecord[];
  skills: ScannedSkill[];
  setOrchestratorBarFocused: (focused: boolean) => void;
  mentionableAgents: Array<{ id: string; name: string; logo?: string; dispatchTarget: string; agentType?: string }>;
  selectedMentionAgentId: string | null;
  onMentionAgentChange?: (agentId: string | null) => void;
  isRunning: boolean;
  awaitingHuman: boolean;
  isPlainLlmChat: boolean;
  isRefining: boolean;
  currentFlowName: string;
  onStopRun?: () => boolean | void;
  t: (key: string) => string;
  awaitingQuestion: boolean;
  awaitingPlan: boolean;
  hitlBusy: boolean;
  setHitlBusy: (busy: boolean) => void;
  onApprove?: () => void;
  onReject?: () => void;
  pendingQuestionMessage: { questionCard?: { allowCustom?: boolean } } | null;
  hillInstructions: string;
  setHillInstructions: (val: string) => void;
  canSubmitPlanRevise: boolean;
  submitPlanRevise: () => void;
  onRetryWithInstructions?: (instructions: string) => void;
  isTerminalDispatchHistoryReadonly: boolean;
  workspaceViewMode: WorkspaceViewMode;
  foregroundShell: ClutchState['foreground_shell'];
  chatDiagnostics: NonNullable<ClutchState['chat_diagnostics']>;
  worktreeIsolation: ClutchState['worktree_isolation'];
  bgJobs: BackgroundJob[];
  bgJobToast: string | null;
  handleSendWithAttachments: (text: string, attachments: Attachment[]) => void;
  handleStopWithQueueClear: () => boolean;
  onContinueRun?: () => void;
  pendingMessages: PendingChatMessage[];
  removePending: (id: string) => void;
  selectedWorkflowId: string | null;
  selectedWorkflowName: string;
  onClearSelectedWorkflow?: () => void;
  isMultiAgent: boolean;
  shellSessionStatus?: string;
  shellPoolBlockerRunIds: string[];
  shellPoolBlockers: Array<{ run_id: string; title?: string; agent_name?: string }>;
  shellPoolQueuePosition: number;
  shellPoolQueueDepth: number;
  clutchStatus: ClutchRunStatus;
  onSelectSession?: (session: SessionRecord) => void;
  resolveAgentLogo?: (agentName: string) => string | undefined;
  workflowAgentSteps: Array<{ nodeId: string; agentName: string; agentType: string; toolId?: string; agentRef?: string; label?: string }>;
  mcpServerIds?: string[];
  showMcpBindingBadge: boolean;
  onOpenMcpBind?: () => void;
  onSlashCommand?: (id: import('../services/slashCommands').SlashCommandId) => void | Promise<void>;
  slashNotice: string | null;
  onDismissSlashNotice?: () => void;
  handleRewindFiles?: () => void;
}

export function ChatFeedDock({
  showTerminalWorkspace,
  terminalDockRef,
  dockRef,
  leftChromePad,
  rightChromePad,
  chatChrome,
  terminalBarRef,
  sessionRunId,
  clutchOrchestraState,
  inputValue,
  setInputValue,
  permissionMode,
  onPermissionModeChange,
  workspaceFiles,
  sessions,
  skills,
  setOrchestratorBarFocused,
  mentionableAgents,
  selectedMentionAgentId,
  onMentionAgentChange,
  isRunning,
  awaitingHuman,
  isPlainLlmChat,
  isRefining,
  currentFlowName,
  onStopRun,
  t,
  awaitingQuestion,
  awaitingPlan,
  hitlBusy,
  setHitlBusy,
  onApprove,
  onReject,
  pendingQuestionMessage,
  hillInstructions,
  setHillInstructions,
  canSubmitPlanRevise,
  submitPlanRevise,
  onRetryWithInstructions,
  isTerminalDispatchHistoryReadonly,
  workspaceViewMode,
  foregroundShell,
  chatDiagnostics,
  worktreeIsolation,
  bgJobs,
  bgJobToast,
  handleSendWithAttachments,
  handleStopWithQueueClear,
  onContinueRun,
  pendingMessages,
  removePending,
  selectedWorkflowId,
  selectedWorkflowName,
  onClearSelectedWorkflow,
  isMultiAgent,
  shellSessionStatus,
  shellPoolBlockerRunIds,
  shellPoolBlockers,
  shellPoolQueuePosition,
  shellPoolQueueDepth,
  clutchStatus,
  onSelectSession,
  resolveAgentLogo,
  workflowAgentSteps,
  mcpServerIds,
  showMcpBindingBadge,
  onOpenMcpBind,
  onSlashCommand,
  slashNotice,
  onDismissSlashNotice,
  handleRewindFiles,
}: ChatFeedDockProps) {
  return (
    <div
      ref={showTerminalWorkspace ? terminalDockRef : dockRef}
      data-testid={showTerminalWorkspace ? 'terminal-orchestrator-dock' : undefined}
      style={{
        left: `${leftChromePad - 6}px`,
        right: `${rightChromePad - 6}px`,
        bottom: APP_INPUT_DOCK_BOTTOM_PX,
      }}
      className={`fixed flex justify-center ${chatChrome.chatEdgePaddingClass} z-40 transition-all duration-300 select-none`}
    >
      {showTerminalWorkspace ? (
        <div ref={terminalBarRef} className={`w-full ${chatChrome.chatMaxWidthClass}`}>
          <OrchestratorBar
            sessionRunId={sessionRunId}
            drafts={clutchOrchestraState.pending_handoff_drafts ?? []}
            inputValue={inputValue}
            setInputValue={setInputValue}
            permissionMode={permissionMode}
            onPermissionModeChange={onPermissionModeChange ?? (() => {})}
            workspaceFiles={workspaceFiles}
            sessions={sessions}
            skills={skills}
            onFocusChange={setOrchestratorBarFocused}
            mentionableAgents={mentionableAgents}
            selectedMentionAgentId={selectedMentionAgentId}
            onMentionAgentChange={onMentionAgentChange}
          />
        </div>
      ) : isRunning && !awaitingHuman && !isPlainLlmChat && !isRefining ? (
        <div className={`w-full ${chatChrome.chatMaxWidthClass} bg-white border border-outline-variant p-3 shadow-xl rounded-xl flex items-center justify-between`}>
          <div className="flex items-center gap-3">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-black opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-black" />
            </span>
            <div className="text-left">
              <p className="text-[10px] font-bold tracking-wider text-on-surface-variant uppercase">
                {t('Workflow running')}
                {currentFlowName ? ` · ${currentFlowName}` : ''}
              </p>
              <p className="text-xs text-on-surface mt-0.5 font-medium">
                {t('Receiving sidecar events')}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onStopRun}
            className="px-3.5 py-1.5 bg-neutral-900 hover:bg-black text-white font-bold rounded-lg text-[10px] uppercase tracking-wider flex items-center gap-1.5"
          >
            <LegacyIcon name="cancel" className="text-[13px]" />
            Stop
          </button>
        </div>
      ) : awaitingHuman ? (
        <div className={`w-full ${chatChrome.chatMaxWidthClass} flex flex-col gap-1.5`}>
          <div
            className="flex items-center gap-2 rounded-xl border border-outline-variant/30 bg-white px-2.5 py-1.5 shadow-sm"
            role="group"
            aria-label={
              awaitingQuestion
                ? t('Awaiting your choice')
                : awaitingPlan
                  ? t('Awaiting plan approval')
                  : t('Needs approval')
            }
          >
            <span className="text-[11px] text-on-surface-variant shrink-0 truncate font-medium">
              {awaitingQuestion
                ? t('Pick an option in the question card above')
                : awaitingPlan
                  ? t('Awaiting plan approval')
                  : t('Needs approval')}
            </span>
            <div className="ml-auto flex items-center gap-1.5 shrink-0">
              {!awaitingQuestion ? (
                <button
                  type="button"
                  data-testid="chat-approve"
                  disabled={hitlBusy}
                  onClick={() => {
                    setHitlBusy(true);
                    onApprove?.();
                  }}
                  className={`${BTN_SM} bg-neutral-900 hover:bg-black text-white border border-neutral-900`}
                >
                  {awaitingPlan ? t('Approve plan') : t('Allow')}
                </button>
              ) : null}
              <button
                type="button"
                data-testid="chat-reject"
                disabled={hitlBusy}
                onClick={() => {
                  setHitlBusy(true);
                  onReject?.();
                }}
                className={`${BTN_SM} bg-neutral-100 hover:bg-neutral-200 text-neutral-800 border border-neutral-200/80`}
              >
                {awaitingQuestion
                  ? t('Cancel question')
                  : awaitingPlan
                    ? t('Cancel plan')
                    : t('Reject')}
              </button>
            </div>
          </div>
          {(awaitingQuestion
            ? pendingQuestionMessage?.questionCard?.allowCustom !== false
            : true) ? (
            <div className="flex items-center gap-1.5 px-0.5">
              <input
                type="text"
                value={hillInstructions}
                onChange={(e) => setHillInstructions(e.target.value)}
                disabled={hitlBusy}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    if (awaitingPlan && canSubmitPlanRevise && !hitlBusy) {
                      submitPlanRevise();
                      return;
                    }
                    if (hillInstructions.trim() && !hitlBusy) {
                      setHitlBusy(true);
                      onRetryWithInstructions?.(hillInstructions.trim());
                      setHillInstructions('');
                    }
                  }
                }}
                placeholder={
                  awaitingQuestion
                    ? t('Or type your own answer…')
                    : awaitingPlan
                      ? t('Suggest plan changes…')
                      : t('Retry with note…')
                }
                className="min-w-0 flex-1 rounded-lg border border-outline-variant/30 bg-surface-container-low px-2.5 py-1.5 text-[11px] text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none focus:ring-1 focus:ring-neutral-900/15"
              />
              <button
                type="button"
                disabled={hitlBusy || (awaitingPlan ? !canSubmitPlanRevise : !hillInstructions.trim())}
                onClick={() => {
                  if (awaitingPlan) {
                    submitPlanRevise();
                    return;
                  }
                  if (hillInstructions.trim() && !hitlBusy) {
                    setHitlBusy(true);
                    onRetryWithInstructions?.(hillInstructions.trim());
                    setHillInstructions('');
                  }
                }}
                className={
                  !hitlBusy && (awaitingPlan ? canSubmitPlanRevise : hillInstructions.trim())
                    ? `${BTN_SM} bg-neutral-900 text-white border border-neutral-900`
                    : `${BTN_SM} bg-transparent text-on-surface-variant/40 border border-transparent cursor-not-allowed`
                }
              >
                {awaitingQuestion
                  ? t('Submit')
                  : awaitingPlan
                    ? t('Revise')
                    : t('Retry')}
              </button>
            </div>
          ) : null}
        </div>
      ) : isTerminalDispatchHistoryReadonly ? (
        <div className="w-full flex justify-center">
          <OrchestratorBar
            sessionRunId={sessionRunId}
            drafts={[]}
            inputValue=""
            setInputValue={() => {}}
            permissionMode={permissionMode}
            onPermissionModeChange={onPermissionModeChange ?? (() => {})}
            workspaceFiles={workspaceFiles}
            sessions={sessions}
            skills={skills}
            mentionableAgents={mentionableAgents}
            selectedMentionAgentId={selectedMentionAgentId}
            onMentionAgentChange={onMentionAgentChange}
            readOnly
          />
        </div>
      ) : workspaceViewMode === 'chat' ? (
        <div className="w-full flex flex-col items-center rounded-2xl bg-background/95 backdrop-blur-sm pt-1">
          {foregroundShell ? (
            <ForegroundShellBar
              shell={foregroundShell}
              t={t}
              onMoveToBackground={() => {
                void clutchStore.send({ action: 'move_fg_to_background' });
              }}
            />
          ) : null}
          {chatDiagnostics.length ? (
            <DiagnosticsIssuesStrip issues={chatDiagnostics} t={t} />
          ) : null}
          {isPlainLlmChat ? (
            <WorktreeIsolationBar
              worktree={worktreeIsolation}
              t={t}
              onMerge={() => {
                void clutchStore.send({ action: 'merge_worktree' });
              }}
              onDiscard={() => {
                void clutchStore.send({ action: 'discard_worktree' });
              }}
            />
          ) : null}
          <BackgroundJobsBar
            jobs={bgJobs}
            t={t}
            onKillJob={(jobId) => {
              clutchStore.optimisticKillBgJob(jobId);
              void clutchStore.send({ action: 'kill_bg_job', job_id: jobId });
            }}
          />
          {bgJobToast ? (
            <div
              data-testid="bg-job-failure-toast"
              className="w-full max-w-3xl mx-auto px-3 pb-2"
            >
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-[12px] font-medium text-rose-800">
                {bgJobToast}
              </div>
            </div>
          ) : null}
          <ChatInputBar
            inputValue={inputValue}
            setInputValue={setInputValue}
            onSendMessage={handleSendWithAttachments}
            isRunning={isRunning}
            isPlainLlmChat={isPlainLlmChat}
            onStopRun={handleStopWithQueueClear}
            onContinueRun={onContinueRun}
            awaitingContinue={Boolean(clutchOrchestraState.awaiting_continue)}
            pendingMessages={pendingMessages}
            onRemovePendingMessage={removePending}
            selectedWorkflowId={selectedWorkflowId}
            selectedWorkflowName={selectedWorkflowName}
            onClearSelectedWorkflow={onClearSelectedWorkflow}
            isMultiAgent={isMultiAgent}
            workspaceFiles={workspaceFiles}
            sessions={sessions}
            skills={skills}
            permissionMode={permissionMode}
            onPermissionModeChange={onPermissionModeChange ?? (() => {})}
            shellSessionStatus={shellSessionStatus}
            shellPoolBlockerRunIds={shellPoolBlockerRunIds}
            shellPoolBlockers={shellPoolBlockers}
            shellPoolQueuePosition={shellPoolQueuePosition}
            shellPoolQueueDepth={shellPoolQueueDepth}
            currentRunId={sessionRunId}
            clutchStatus={clutchStatus}
            onSelectSession={onSelectSession}
            resolveAgentLogo={resolveAgentLogo}
            onDismissHybridNotice={() => clutchStore.clearShellSessionNotice()}
            isFlowRefining={isRefining}
            workflowAgents={workflowAgentSteps}
            mentionableAgents={mentionableAgents}
            selectedMentionAgentId={selectedMentionAgentId}
            onMentionAgentChange={onMentionAgentChange}
            mcpServerIds={mcpServerIds}
            showMcpBindingBadge={showMcpBindingBadge}
            onOpenMcpBind={onOpenMcpBind}
            onSlashCommand={onSlashCommand}
            slashNotice={slashNotice}
            onDismissSlashNotice={onDismissSlashNotice}
            onRewindFiles={isPlainLlmChat ? handleRewindFiles : undefined}
            onEnableWorktree={
              isPlainLlmChat
                ? () => {
                    void clutchStore.send({ action: 'enable_worktree' });
                  }
                : undefined
            }
            worktreeActive={Boolean(worktreeIsolation?.enabled)}
          />
        </div>
      ) : null}
    </div>
  );
}
