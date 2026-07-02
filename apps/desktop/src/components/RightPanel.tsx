import React from 'react';
import { CONTENT_TOP_WITH_BANNER } from '../constants/layout';
import { RightTab, UncommittedFile, ClutchRunStatus } from '../types';
import type { FileTreeNode } from '../services/workspaceApi';
import { loadWorkflowById } from '../services/workflowApi';
import { useLanguage, translateRunStatus } from './LanguageContext';
import { LegacyIcon } from './ui/LegacyIcon';
import { UnderDevelopmentNotice } from './ui/UnderDevelopmentNotice';
import { OverviewDispatchLog } from './terminal-orchestra/OverviewDispatchLog';
import { BTN_ICON } from './ui/buttonStyles';

interface RightPanelProps {
  activeTab: RightTab;
  setActiveTab: (tab: RightTab) => void;
  clutchStatus: ClutchRunStatus;
  activeNodeId?: string;
  activeAgent?: string;
  workflowId?: string;
  workflowName?: string;
  currentInstruction?: string;
  sessionTokens?: number;
  sessionCostUsd?: number;
  tokenInput?: number;
  tokenOutput?: number;
  uncommitted: UncommittedFile[];
  terminalLogs: string[];
  isOpen: boolean;
  setIsOpen: (val: boolean) => void;
  selectedSidebarWidth?: number;
  rightSidebarWidth?: number;
  onPreviewFile?: (file: { name: string; content: string }) => void;
  isMultiAgent?: boolean;
  sessionAgentName?: string;
  modelName?: string;
  workspaceFiles?: FileTreeNode[];
  onOpenWorkspaceFile?: (path: string) => void;
  workspaceAuthorized?: boolean;
  onClearTerminal?: () => void;
  dispatchLog?: import('../types').DispatchLogEntry[];
  showTerminalOrchestraOverview?: boolean;
}

type WorkflowStepView = {
  id: string;
  label: string;
  agent: string;
};

const RIGHT_TAB_LABELS: Record<RightTab, string> = {
  overview: 'Overview',
  files: 'Files',
  flow: 'Flow',
  changes: 'Changes',
  terminal: 'Terminal',
};

export const RightPanel: React.FC<RightPanelProps> = ({
  activeTab,
  setActiveTab,
  clutchStatus,
  activeNodeId = '',
  activeAgent = '',
  workflowId = '',
  workflowName = '',
  currentInstruction = '',
  sessionTokens = 0,
  sessionCostUsd = 0,
  tokenInput = 0,
  tokenOutput = 0,
  uncommitted,
  terminalLogs,
  isOpen,
  setIsOpen,
  isMultiAgent = true,
  sessionAgentName = '',
  modelName = '',
  workspaceFiles = [],
  onOpenWorkspaceFile,
  workspaceAuthorized = false,
  onClearTerminal,
  dispatchLog = [],
  showTerminalOrchestraOverview = false,
}) => {
  const { t, language } = useLanguage();
  const [selectedFile, setSelectedFile] = React.useState<string>('');
  const [expandedFiles, setExpandedFiles] = React.useState<Record<string, boolean>>({});
  const [workflowSteps, setWorkflowSteps] = React.useState<WorkflowStepView[]>([]);

  React.useEffect(() => {
    if (activeTab === 'files') {
      setExpandedFiles({});
    }
  }, [activeTab, workspaceFiles]);

  React.useEffect(() => {
    if (!workflowId) {
      setWorkflowSteps([]);
      return;
    }

    let cancelled = false;
    void (async () => {
      try {
        const workflow = await loadWorkflowById(workflowId);
        if (cancelled) return;
        setWorkflowSteps(
          workflow.nodes
            .filter((node) => node.type === 'agent_task')
            .map((node) => ({
              id: node.id,
              label: String((node.data as { label?: string }).label ?? node.id),
              agent: String((node.data as { agent?: string }).agent ?? '—'),
            })),
        );
      } catch {
        if (!cancelled) setWorkflowSteps([]);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [workflowId]);

  const toggleExpand = (dir: string) => {
    setExpandedFiles((prev) => ({ ...prev, [dir]: !prev[dir] }));
  };

  const getActiveFileDiff = () => {
    const file = uncommitted.find((f) => f.name === selectedFile);
    return file ? file.diffs : null;
  };

  const isIdle = clutchStatus === 'idle';
  const hasWorkflow = Boolean(workflowId);
  const workflowLabel = workflowName || workflowId;
  const tokenTotal = sessionTokens || tokenInput + tokenOutput;
  const inputPct = tokenTotal > 0 ? Math.round((tokenInput / tokenTotal) * 100) : 0;
  const outputPct = tokenTotal > 0 ? 100 - inputPct : 0;
  const showFlowTab = isMultiAgent;
  const visibleTabs = (['overview', 'files', 'flow', 'changes', 'terminal'] as RightTab[])
    .filter((tab) => tab !== 'flow' || showFlowTab);

  const statusLabel = translateRunStatus(clutchStatus, language);

  const renderStateSummary = () => (
    <div className="p-3 border border-outline-variant/30 rounded-xl bg-surface-container-low/40 font-mono text-[11px] leading-relaxed space-y-1">
      <p>
        {t('workflow')}: <span className="text-on-surface font-bold">{workflowLabel || '—'}</span>
      </p>
      {workflowName && workflowId && workflowName !== workflowId ? (
        <p>
          {t('workflow_id')}: <span className="text-on-surface font-bold">{workflowId}</span>
        </p>
      ) : null}
      <p>
        {t('active_node')}: <span className="text-on-surface font-bold">{activeNodeId || '—'}</span>
      </p>
      <p>
        {t('active_agent')}: <span className="text-on-surface font-bold">{activeAgent || '—'}</span>
      </p>
      <p>
        {t('status')}: <span className="text-on-surface font-bold uppercase">{statusLabel}</span>
      </p>
      {isIdle && hasWorkflow ? (
        <p className="pt-1 border-t border-outline-variant/20 text-on-surface-variant">
          {t('Workflow selected — send a message to start')}
        </p>
      ) : null}
      {currentInstruction ? (
        <p className="pt-1 border-t border-outline-variant/20">
          {t('instruction')}: <span className="text-on-surface">{currentInstruction}</span>
        </p>
      ) : null}
    </div>
  );

  const renderSingleAgentSummary = () => {
    const agentLabel = sessionAgentName || activeAgent || '—';
    return (
      <div className="p-3 border border-outline-variant/30 rounded-xl bg-surface-container-low/40 font-mono text-[11px] leading-relaxed space-y-1">
        <p>
          {t('Active Agent')}: <span className="text-on-surface font-bold">{agentLabel}</span>
        </p>
        {modelName ? (
          <p>
            {t('Model')}: <span className="text-on-surface font-bold">{modelName}</span>
          </p>
        ) : null}
        <p>
          {t('status')}: <span className="text-on-surface font-bold uppercase">{statusLabel}</span>
        </p>
        {currentInstruction ? (
          <p className="pt-1 border-t border-outline-variant/20">
            instruction: <span className="text-on-surface">{currentInstruction}</span>
          </p>
        ) : null}
      </div>
    );
  };

  const renderWorkflowSteps = (compact = false) => {
    if (workflowSteps.length === 0) {
      return (
        <div className="p-6 border border-dashed border-outline-variant/50 rounded-xl text-center space-y-2">
          <LegacyIcon name="account_tree" className="text-[24px] text-on-surface-variant/50" />
          <p className="text-[11px] text-on-surface-variant leading-relaxed">{t('Workflow steps unavailable')}</p>
        </div>
      );
    }

    return (
      <ol className={compact ? 'space-y-1.5' : 'space-y-2'}>
        {workflowSteps.map((step, index) => {
          const isActive = step.id === activeNodeId;
          return (
            <li
              key={step.id}
              className={`rounded-xl border ${
                compact ? 'p-2' : 'p-3'
              } ${
                isActive
                  ? 'border-primary bg-primary/5 ring-1 ring-primary/20'
                  : 'border-outline-variant/30 bg-surface-container-low/30'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-[10.5px] font-bold text-on-surface-variant uppercase tracking-wider">
                    {index + 1}. {step.id}
                  </p>
                  <p className={`font-bold text-on-surface truncate ${compact ? 'text-[11px]' : 'text-xs'}`}>
                    {step.label}
                  </p>
                  <p className="text-[11px] text-on-surface-variant font-mono mt-0.5">{step.agent}</p>
                </div>
                {isActive ? (
                  <span className="text-[10px] font-bold uppercase text-primary whitespace-nowrap">
                    {statusLabel}
                  </span>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>
    );
  };

  const renderFileNodes = (nodes: FileTreeNode[], depth = 0): React.ReactNode =>
    nodes.map((node) => {
      const isFolder = node.type === 'folder';
      const isExpanded = expandedFiles[node.path] ?? false;
      return (
        <div key={node.path} className="space-y-1">
          <div
            draggable
            onDragStart={(e) => {
              e.dataTransfer.setData('text/plain', node.path);
              e.dataTransfer.effectAllowed = 'copy';
            }}
            onClick={() => {
              if (isFolder) {
                toggleExpand(node.path);
              } else {
                onOpenWorkspaceFile?.(node.path);
              }
            }}
            className="flex items-center gap-2 p-1.5 hover:bg-surface-container-low rounded cursor-grab active:cursor-grabbing transition-colors"
            style={{ paddingLeft: `${depth * 8 + 6}px` }}
            title={`${t('Drag to chat')}: ${node.path}`}
          >
            {isFolder ? (
              <>
                <LegacyIcon
                  name="chevron_right"
                  className={`text-[16px] transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                />
                <LegacyIcon
                  name={isExpanded ? 'folder_open' : 'folder'}
                  className="text-[16px] text-on-surface-variant"
                />
              </>
            ) : (
              <>
                <span className="w-4" />
                <LegacyIcon name="description" className="text-[16px] text-on-surface-variant" />
              </>
            )}
            <span className="truncate">{node.name}</span>
          </div>
          {isFolder && isExpanded && node.children && node.children.length > 0 && (
            <div className="border-l border-outline-variant/30 ml-3">
              {renderFileNodes(node.children, depth + 1)}
            </div>
          )}
        </div>
      );
    });


  return (
    <aside
      className={`fixed right-0 bottom-0 border-l border-outline-variant bg-white flex flex-col z-30 transition-all duration-300 ${
        isOpen ? 'w-[300px]' : 'w-[0px] border-l-0'
      }`}
      style={{ top: CONTENT_TOP_WITH_BANNER, overflow: 'visible' }}
    >
      <button
        data-testid="right-panel-toggle"
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`absolute top-4 w-6 h-6 bg-white border border-neutral-300 rounded-full flex items-center justify-center z-50 shadow-md hover:shadow-lg hover:bg-neutral-50 hover:border-neutral-450 transition-all cursor-pointer text-neutral-600 hover:text-neutral-900 duration-200 hover:scale-110 active:scale-95 ${
          isOpen ? '-left-3' : '-left-6'
        }`}
            title={isOpen ? t('Collapse Panel') : t('Expand Panel')}
      >
        <LegacyIcon
          name={isOpen ? 'chevron_right' : 'chevron_left'}
          className="text-[13px] font-bold"
        />
      </button>

      <div className={`flex-grow flex flex-col h-full overflow-hidden ${!isOpen ? 'hidden' : ''}`}>
        <div
          className="grid h-11 border-b border-outline-variant overflow-hidden select-none bg-surface-container-low/40"
          style={{ gridTemplateColumns: `repeat(${visibleTabs.length}, minmax(0, 1fr))` }}
        >
          {visibleTabs.map((tab) => {
            const isActive = activeTab === tab;
            return (
              <button
                key={tab}
                data-testid={`right-tab-${tab}`}
                onClick={() => setActiveTab(tab)}
                className={`relative h-11 min-w-0 overflow-hidden px-1 text-xs font-bold whitespace-nowrap tracking-wide capitalize transition-[background-color,color] ${
                  isActive
                    ? 'text-primary bg-white'
                    : 'text-on-surface-variant hover:text-on-surface'
                }`}
              >
                <span className="block truncate">{t(RIGHT_TAB_LABELS[tab])}</span>
                <span
                  className={`absolute bottom-0 left-1/2 h-[3px] w-5 -translate-x-1/2 rounded-full bg-primary transition-opacity ${
                    isActive ? 'opacity-100' : 'opacity-0'
                  }`}
                  aria-hidden
                />
              </button>
            );
          })}
        </div>

        <div className="flex-1 overflow-y-auto sidebar-scroll p-5 select-none bg-white">
          {activeTab === 'overview' && (
            <div className="space-y-6 animate-fade-in text-xs">
              {showTerminalOrchestraOverview ? (
                <section>
                  <p className="text-[10px] text-on-surface-variant leading-relaxed mb-3 p-2.5 rounded-xl bg-surface-container-low border border-outline-variant/30">
                    <strong className="text-on-surface">{t('Handoff')}</strong>
                    {' '}
                    {t('Handoff overview tip')}
                  </p>
                  <h4 className="text-[10px] font-bold text-on-surface-variant/75 uppercase tracking-widest mb-3">
                    {t('Dispatch records')}
                  </h4>
                  <OverviewDispatchLog entries={dispatchLog} />
                </section>
              ) : null}
              {isMultiAgent ? (
                <>
                  {renderStateSummary()}
                  {hasWorkflow ? (
                    <section>
                      <h4 className="text-[10px] font-bold text-on-surface-variant/75 uppercase tracking-widest mb-3">
                        {t('Workflow step execution')}
                      </h4>
                      {renderWorkflowSteps(true)}
                    </section>
                  ) : isIdle ? (
                    <div className="p-6 border border-dashed border-outline-variant/50 rounded-xl text-center space-y-2">
                      <LegacyIcon name="monitoring" className="text-[24px] text-on-surface-variant/50" />
                      <p className="text-xs text-on-surface-variant leading-relaxed">
                        {t('No active workflow overview')}
                      </p>
                    </div>
                  ) : null}
                </>
              ) : (
                <>
                  {renderSingleAgentSummary()}
                  {isIdle && tokenTotal === 0 ? (
                    <div className="p-6 border border-dashed border-outline-variant/50 rounded-xl text-center space-y-2">
                      <LegacyIcon name="smart_toy" className="text-[24px] text-on-surface-variant/50" />
                      <p className="text-xs text-on-surface-variant leading-relaxed">
                        {t('No session activity yet')}
                      </p>
                    </div>
                  ) : null}
                </>
              )}
              {tokenTotal > 0 ? (
                <section>
                  <h4 className="text-[10px] font-bold text-on-surface-variant/75 uppercase tracking-widest mb-4">
                    {t('Session Token Analytics')}
                  </h4>
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="p-3 border border-neutral-200 bg-neutral-50/50 rounded-xl">
                        <p className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider mb-1">{t('Total Tokens')}</p>
                        <p className="text-base font-extrabold text-neutral-900 font-mono">{tokenTotal.toLocaleString()}</p>
                      </div>
                      <div className="p-3 border border-neutral-200 bg-neutral-50/50 rounded-xl">
                        <p className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider mb-1">{t('Estimated Cost')}</p>
                        <p className="text-base font-extrabold text-neutral-900 font-mono">${sessionCostUsd.toFixed(4)}</p>
                      </div>
                    </div>

                    <div className="p-3 border border-neutral-200 rounded-xl space-y-2">
                      <div className="flex items-center justify-between text-[10px] font-bold text-neutral-800">
                        <span>{t('Token Distribution')}</span>
                        <span className="text-zinc-500 font-normal font-mono">{t('Input vs Output')}</span>
                      </div>
                      <div className="w-full h-3 rounded-full overflow-hidden flex bg-neutral-100 border border-neutral-200/50">
                        <div
                          className="h-full bg-neutral-900 transition-all duration-300"
                          style={{ width: `${inputPct}%` }}
                          title={`Input: ${tokenInput} tokens (${inputPct}%)`}
                        />
                        <div
                          className="h-full bg-neutral-400 transition-all duration-300"
                          style={{ width: `${outputPct}%` }}
                          title={`Output: ${tokenOutput} tokens (${outputPct}%)`}
                        />
                      </div>
                      <div className="flex justify-between text-[9px] font-mono pt-1">
                        <span>{t('Input')} ({inputPct}%): {tokenInput.toLocaleString()}</span>
                        <span>{t('Output')} ({outputPct}%): {tokenOutput.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                </section>
              ) : null}
            </div>
          )}

          {activeTab === 'files' && (
            <div className="space-y-4 animate-fade-in text-xs select-none">
              <h4 className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-3">
                {t('Workspace Folder Structure')}
              </h4>
              <div className="space-y-1 font-mono font-medium text-xs text-on-surface-variant pl-1">
                {!workspaceAuthorized ? (
                  <p className="text-[11px] text-on-surface-variant/70 italic p-2">
                    {t('Authorize workspace files hint')}
                  </p>
                ) : workspaceFiles.length === 0 ? (
                  <p className="text-[11px] text-on-surface-variant/70 italic p-2">{t('Workspace folder empty')}</p>
                ) : (
                  renderFileNodes(workspaceFiles)
                )}
              </div>
            </div>
          )}

          {activeTab === 'flow' && showFlowTab && (
            <div className="space-y-4 animate-fade-in text-xs select-none">
              <h4 className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-3">
                {t('Workflow step execution')}
              </h4>
              {hasWorkflow ? (
                <>
                  {renderStateSummary()}
                  {renderWorkflowSteps()}
                </>
              ) : (
                <div className="p-6 border border-dashed border-outline-variant/50 rounded-xl text-center space-y-2">
                  <LegacyIcon name="account_tree" className="text-[24px] text-on-surface-variant/50" />
                  <p className="text-xs text-on-surface-variant leading-relaxed">
                    {t('Select or create a workflow')}
                  </p>
                  <p className="text-[11px] text-on-surface-variant/70 leading-relaxed">
                    {t('No active workflow overview')}
                  </p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'changes' && (
            <div className="space-y-4 animate-fade-in text-xs select-none">
              <h4 className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                {t('Uncommitted changes')} ({uncommitted.length})
              </h4>

              {uncommitted.length === 0 ? (
                <div className="py-8 text-center bg-surface-container-low/40 rounded-xl border border-dashed border-outline-variant mt-2 text-on-surface-variant/60">
                  <LegacyIcon name="difference" className="text-[28px] mb-2" />
                  <p className="text-[11px] font-medium">{t('No uncommitted changes')}</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {uncommitted.map((file) => {
                    const isActive = file.name === selectedFile;
                    return (
                      <div
                        key={file.name}
                        onClick={() => setSelectedFile(file.name)}
                        className={`flex items-center justify-between p-2 rounded-lg transition-colors cursor-pointer group ${
                          isActive
                            ? 'bg-surface-container-low border border-outline-variant/30 font-bold'
                            : 'hover:bg-surface-container-low'
                        }`}
                      >
                        <div className="flex items-center gap-3 overflow-hidden">
                          <span
                            className={`text-[10px] font-bold w-4 text-center ${
                              file.status === 'A' ? 'text-green-500' : 'text-amber-500'
                            }`}
                          >
                            {file.status}
                          </span>
                          <span className="text-xs truncate text-on-surface">{file.name}</span>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onOpenWorkspaceFile?.(file.name);
                          }}
                          className={BTN_ICON}
                          title={t('Preview file')}
                          aria-label={t('Preview file')}
                        >
                          <LegacyIcon name="visibility" className="text-[15px]" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}

              {uncommitted.length > 0 && getActiveFileDiff() && (
                <div className="mt-6 border border-outline-variant/20 rounded-xl overflow-hidden bg-white shadow-xs">
                  <div className="flex items-center justify-between px-3 py-2 bg-surface-container/30 border-b border-outline-variant/20">
                    <div className="flex items-center gap-2">
                      <LegacyIcon name="description" className="text-[14px]" />
                      <span className="font-mono text-[10px] font-bold text-on-surface-variant/90 truncate max-w-[140px]">
                        {selectedFile}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => onOpenWorkspaceFile?.(selectedFile)}
                      className="flex items-center gap-1.5 px-2 py-1 bg-neutral-900 hover:bg-black text-white text-[9.5px] font-bold rounded-lg transition-all shadow-xs active:scale-95"
                    >
                      <LegacyIcon name="visibility" className="text-[12px]" />
                      {t('Preview Full')}
                    </button>
                  </div>

                  <div className="font-mono text-[9px] leading-relaxed bg-white overflow-hidden text-on-surface select-text">
                    {getActiveFileDiff()?.map((diffLine, i) => {
                      let bgClass = '';
                      let indicator = ' ';

                      if (diffLine.type === 'addition') {
                        bgClass = 'bg-green-50 text-green-800';
                        indicator = '+';
                      } else if (diffLine.type === 'deletion') {
                        bgClass = 'bg-red-50 text-red-800 line-through';
                        indicator = '-';
                      }

                      return (
                        <div key={i} className={`flex ${bgClass}`}>
                          <div className="w-7 pb-0.5 text-center text-[8px] text-on-surface-variant/40 border-r border-outline-variant/10 select-none bg-surface-container/20">
                            {diffLine.lineNum}
                          </div>
                          <div className="px-3 pb-0.5 select-all whitespace-pre tracking-wide">
                            {indicator} {diffLine.text}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'terminal' && (
            <div className="space-y-4 animate-fade-in h-full flex flex-col text-xs">
              <div className="flex items-center justify-between">
                <h4 className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                  {t('Terminal logs')}
                </h4>
                <button
                  type="button"
                  data-testid="terminal-clear-btn"
                  onClick={() => onClearTerminal?.()}
                  className="text-[9px] font-semibold text-on-surface bg-surface-container-high px-2 py-1 rounded"
                >
                  {t('Clear')}
                </button>
              </div>

              <div className="flex-1 bg-black text-green-400 font-mono text-[10px] p-4 rounded-xl space-y-1.5 h-[340px] overflow-y-auto terminal-scroll select-all border border-neutral-800 shadow-md">
                {terminalLogs.length === 0 ? (
                  <p className="text-neutral-500 font-sans text-[11px]">{t('No terminal logs yet')}</p>
                ) : (
                  terminalLogs.map((log, i) => {
                    let colorClass = 'text-green-400/90';
                    if (log.includes('WARNING') || log.includes('FAILED')) {
                      colorClass = 'text-red-400 font-semibold';
                    } else if (log.includes('PASSED') || log.includes('SUCCESS')) {
                      colorClass = 'text-emerald-400 font-bold';
                    }

                    return (
                      <div key={i} className={`${colorClass} leading-normal`}>
                        <span className="text-white select-none mr-1.5">$</span>
                        {log}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};
