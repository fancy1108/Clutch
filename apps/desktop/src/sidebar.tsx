import React, { useMemo, useState } from 'react';
import { RepositoryFolder, MainView } from './types';
import { useLanguage } from './components/LanguageContext';
import type { SessionRecord } from './services/runApi';
import type { WorkspaceInfo } from './services/workspaceApi';

interface SidebarProps {
  currentView: MainView;
  setView: (view: MainView) => void;
  folders: RepositoryFolder[];
  setFolders: React.Dispatch<React.SetStateAction<RepositoryFolder[]>>;
  activeFlow: string;
  setActiveFlow: (flow: string) => void;
  onNewChat: () => void;
  isOpenState: boolean;
  setIsOpenState: (open: boolean) => void;
  isMultiAgent?: boolean;
  sessions?: SessionRecord[];
  activeSessionId?: string;
  workspaces?: WorkspaceInfo[];
  activeWorkspaceId?: string | null;
  onAddWorkspace?: () => void;
  onSelectWorkspace?: (workspaceId: string) => void;
  onSelectSession?: (session: SessionRecord) => void;
  onNewChatInWorkspace?: (workspaceId: string) => void;
}

function formatRelativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.max(1, Math.floor(diffMs / 60000));
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

function sessionLabel(session: SessionRecord): string {
  if (session.title?.trim()) return session.title.trim();
  if (session.workflow_id) return session.workflow_id;
  return session.run_id;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  setView,
  folders,
  setFolders,
  activeFlow,
  setActiveFlow,
  onNewChat,
  isOpenState,
  setIsOpenState,
  isMultiAgent = true,
  sessions = [],
  activeSessionId = '',
  workspaces = [],
  activeWorkspaceId = null,
  onAddWorkspace,
  onSelectWorkspace,
  onSelectSession,
  onNewChatInWorkspace,
}) => {
  const { t } = useLanguage();
  const [collapsedWorkspaces, setCollapsedWorkspaces] = useState<Record<string, boolean>>({});

  const sessionsByWorkspace = useMemo(() => {
    const map = new Map<string, SessionRecord[]>();
    for (const session of sessions) {
      const workspaceId = session.workspace_id;
      if (!workspaceId) continue;
      const bucket = map.get(workspaceId) ?? [];
      bucket.push(session);
      map.set(workspaceId, bucket);
    }
    return map;
  }, [sessions]);

  const toggleWorkspace = (workspaceId: string) => {
    setCollapsedWorkspaces((prev) => ({ ...prev, [workspaceId]: !prev[workspaceId] }));
    onSelectWorkspace?.(workspaceId);
  };

  const handleFlowSelect = (flowName: string) => {
    setActiveFlow(flowName);
    setView('chat');
  };

  return (
    <aside
      className={`fixed h-screen left-0 top-0 border-r border-outline-variant bg-surface flex flex-col transition-all duration-300 z-50 ${
        isOpenState ? 'w-[280px] p-5' : 'w-[0px] p-0 border-r-0'
      }`}
      style={{ overflow: 'visible' }}
    >
      <button
        data-testid="sidebar-toggle"
        onClick={() => setIsOpenState(!isOpenState)}
        className={`absolute top-[88px] w-6 h-6 bg-surface-bright border border-outline rounded-full flex items-center justify-center z-50 shadow-md hover:shadow-lg hover:bg-surface-container hover:border-on-surface/30 transition-all cursor-pointer text-on-surface-variant hover:text-on-surface duration-200 hover:scale-110 active:scale-95 ${
          isOpenState ? '-right-3' : '-right-6'
        }`}
        title={isOpenState ? t('Collapse Sidebar') : t('Expand Sidebar')}
      >
        <span className="material-symbols-outlined text-[13px] font-bold">
          {isOpenState ? 'chevron_left' : 'chevron_right'}
        </span>
      </button>

      <div className={`flex-1 flex flex-col gap-4 overflow-hidden h-full ${!isOpenState ? 'hidden' : ''}`}>
        <div className="flex items-center justify-between mb-2 px-2">
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-[#ff5f57] hover:scale-105 transition-transform cursor-pointer" title={t("Close")} />
            <div className="w-3 h-3 rounded-full bg-[#febc2e] hover:scale-105 transition-transform cursor-pointer" title={t("Minimize")} />
            <div className="w-3 h-3 rounded-full bg-[#28c840] hover:scale-105 transition-transform cursor-pointer" title={t("Fullscreen")} />
          </div>
        </div>

        <div className="space-y-1 mb-4 px-1">
          <button
            data-testid="nav-new-chat"
            onClick={onNewChat}
            className={`w-full flex items-center gap-3 p-2.5 rounded-lg transition-all text-left group ${
              currentView === 'chat'
                ? 'bg-surface-bright shadow-sm text-on-surface font-semibold border border-outline-variant/50'
                : 'text-on-surface-variant hover:bg-surface-bright hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-[20px] text-on-surface-variant group-hover:text-primary">
              chat
            </span>
            <span className="text-xs font-semibold tracking-wide">{t("New Chat")}</span>
          </button>

          <button
            data-testid="nav-agents"
            onClick={() => setView('agents')}
            className={`w-full flex items-center gap-3 p-2.5 rounded-lg transition-all text-left group ${
              currentView === 'agents'
                ? 'bg-surface-bright shadow-sm text-on-surface font-semibold border border-outline-variant/50'
                : 'text-on-surface-variant hover:bg-surface-bright hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-[20px] text-on-surface-variant group-hover:text-primary">
              smart_toy
            </span>
            <span className="text-xs font-semibold tracking-wide">{t("AI Agents")}</span>
          </button>

          {isMultiAgent && (
            <button
              data-testid="nav-workflows"
              onClick={() => setView('workflows')}
              className={`w-full flex items-center gap-3 p-2.5 rounded-lg transition-all text-left group ${
                currentView === 'workflows'
                  ? 'bg-surface-bright shadow-sm text-on-surface font-semibold border border-outline-variant/60'
                  : 'text-on-surface-variant hover:bg-surface-bright hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[20px] text-on-surface-variant group-hover:text-primary">
                account_tree
              </span>
              <span className="text-xs font-semibold tracking-wide">{t("Workflows SOP")}</span>
            </button>
          )}
        </div>

        <div className="flex items-center justify-between text-on-surface-variant mb-1 px-3">
          <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant/70">
            {t('Projects')}
          </span>
          <div className="flex gap-2">
            <span
              data-testid="nav-add-workspace"
              className="material-symbols-outlined text-[16px] cursor-pointer hover:text-primary"
              title={t('Add project folder')}
              onClick={() => onAddWorkspace?.()}
            >
              create_new_folder
            </span>
          </div>
        </div>

        <nav className="flex-1 sidebar-scroll overflow-y-auto space-y-2 px-1 pb-4">
          {workspaces.length === 0 && (
            <p className="text-[11px] text-on-surface-variant/60 italic px-3 py-2 leading-relaxed">
              {t('No repositories yet. Use Add project folder or Authorize workspace to begin.')}
            </p>
          )}
          {workspaces.map((repo) => {
            const isActiveWorkspace = repo.id === activeWorkspaceId;
            const collapsed = collapsedWorkspaces[repo.id] ?? false;
            const projectSessions = sessionsByWorkspace.get(repo.id) ?? [];

            return (
              <div key={repo.id} className="space-y-0.5">
                <div
                  className={`flex items-center justify-between p-1.5 rounded-lg transition-colors group ${
                    isActiveWorkspace
                      ? 'bg-surface-container-low/80'
                      : 'hover:bg-surface-bright'
                  }`}
                >
                  <button
                    type="button"
                    data-testid={`workspace-row-${repo.id}`}
                    onClick={() => toggleWorkspace(repo.id)}
                    className="flex items-center gap-2 flex-1 min-w-0 text-left"
                    title={repo.workspace_path}
                  >
                    <span className="material-symbols-outlined text-[18px] text-on-surface-variant">
                      {collapsed ? 'folder' : 'folder_open'}
                    </span>
                    <span className="text-xs font-semibold truncate">{repo.name}</span>
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onNewChatInWorkspace?.(repo.id);
                    }}
                    className="material-symbols-outlined text-[16px] opacity-60 group-hover:opacity-100 hover:text-primary p-0.5 rounded"
                    title={t('New Chat')}
                  >
                    add
                  </button>
                </div>

                {!collapsed && (
                  <div className="space-y-0.5 ml-4 border-l-2 border-outline-variant/20 pl-2">
                    {projectSessions.length === 0 ? (
                      <p className="text-[11px] text-on-surface-variant/60 italic py-1 pl-2">
                        {t('No sessions in this project yet')}
                      </p>
                    ) : (
                      projectSessions.map((session) => {
                        const isActiveSession = session.run_id === activeSessionId;
                        return (
                          <button
                            key={session.run_id}
                            type="button"
                            data-testid={`sidebar-session-${session.run_id}`}
                            onClick={() => onSelectSession?.(session)}
                            className={`w-full flex items-center justify-between p-2 rounded-lg text-left transition-all ${
                              isActiveSession
                                ? 'bg-surface-bright shadow-sm text-on-surface font-bold border border-outline-variant/40'
                                : 'text-on-surface-variant hover:bg-surface-bright hover:text-on-surface'
                            }`}
                          >
                            <span className="text-xs truncate max-w-[150px]">{sessionLabel(session)}</span>
                            <span className="text-[9px] font-mono text-on-surface-variant/70 flex-shrink-0">
                              {formatRelativeTime(session.started_at)}
                            </span>
                          </button>
                        );
                      })
                    )}
                  </div>
                )}
              </div>
            );
          })}

        </nav>

        <div className="mt-auto pt-3 border-t border-outline-variant/50 space-y-1">
          <button
            data-testid="nav-settings"
            onClick={() => setView('settings')}
            className={`w-full flex items-center gap-3 p-2 rounded-lg text-left transition-all group ${
              currentView === 'settings' ? 'bg-surface-bright shadow-sm text-on-surface font-semibold border border-outline-variant/60' : 'text-on-surface-variant hover:bg-surface-bright'
            }`}
          >
            <span className="material-symbols-outlined text-[20px] text-on-surface-variant group-hover:text-primary">
              settings
            </span>
            <span className="text-xs font-semibold tracking-wide">{t("Settings")}</span>
          </button>
        </div>
      </div>
    </aside>
  );
};
