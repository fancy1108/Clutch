import React, { useEffect, useMemo, useRef, useState } from 'react';
import { RepositoryFolder, MainView } from './types';
import { useLanguage } from './components/LanguageContext';
import type { SessionRecord } from './services/runApi';
import type { RepositoryGroup, WorkspaceInfo } from './services/workspaceApi';

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
  repositoryGroups?: RepositoryGroup[];
  activeWorkspaceId?: string | null;
  onAddWorkspace?: () => void;
  onCreateRepositoryGroup?: () => void;
  onToggleRepositoryGroup?: (groupId: string, collapsed: boolean) => void;
  onSelectWorkspace?: (workspaceId: string) => void;
  onSelectSession?: (session: SessionRecord) => void;
  onNewChatInWorkspace?: (workspaceId: string) => void;
  onDeleteWorkspace?: (workspaceId: string) => void;
  onDeleteSession?: (runId: string) => void;
  onDeleteRepositoryGroup?: (groupId: string) => void;
  onRenameRepositoryGroup?: (groupId: string) => void;
  onMoveWorkspaceToGroup?: (workspaceId: string, targetGroupId: string) => void;
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
  repositoryGroups = [],
  activeWorkspaceId = null,
  onAddWorkspace,
  onCreateRepositoryGroup,
  onToggleRepositoryGroup,
  onSelectWorkspace,
  onSelectSession,
  onNewChatInWorkspace,
  onDeleteWorkspace,
  onDeleteSession,
  onDeleteRepositoryGroup,
  onRenameRepositoryGroup,
  onMoveWorkspaceToGroup,
}) => {
  const { t } = useLanguage();
  const [repoFilter, setRepoFilter] = useState('');
  const [collapsedWorkspaces, setCollapsedWorkspaces] = useState<Record<string, boolean>>({});
  const [dragOverGroupId, setDragOverGroupId] = useState<string | null>(null);
  const [draggingWorkspaceId, setDraggingWorkspaceId] = useState<string | null>(null);
  const [pointerDragActive, setPointerDragActive] = useState(false);
  const [defaultGroupCollapsed, setDefaultGroupCollapsed] = useState(false);
  const pointerDragRef = useRef<{
    workspaceId: string;
    startX: number;
    startY: number;
    active: boolean;
  } | null>(null);
  const suppressWorkspaceClickRef = useRef(false);

  const DRAG_THRESHOLD_PX = 6;

  useEffect(() => {
    const resolveDropGroupId = (clientX: number, clientY: number): string | null => {
      const el = document.elementFromPoint(clientX, clientY);
      const groupEl = el?.closest('[data-drop-group-id]');
      return groupEl?.getAttribute('data-drop-group-id') ?? null;
    };

    const handlePointerMove = (e: MouseEvent) => {
      const drag = pointerDragRef.current;
      if (!drag) return;

      if (!drag.active) {
        const dist = Math.hypot(e.clientX - drag.startX, e.clientY - drag.startY);
        if (dist < DRAG_THRESHOLD_PX) return;
        drag.active = true;
        suppressWorkspaceClickRef.current = true;
        setPointerDragActive(true);
      }

      setDragOverGroupId(resolveDropGroupId(e.clientX, e.clientY));
    };

    const handlePointerUp = (e: MouseEvent) => {
      const drag = pointerDragRef.current;
      if (!drag) return;

      if (drag.active) {
        const groupId = resolveDropGroupId(e.clientX, e.clientY);
        if (groupId) {
          onMoveWorkspaceToGroup?.(drag.workspaceId, groupId);
        }
      }

      pointerDragRef.current = null;
      setDraggingWorkspaceId(null);
      setDragOverGroupId(null);
      setPointerDragActive(false);
    };

    window.addEventListener('mousemove', handlePointerMove);
    window.addEventListener('mouseup', handlePointerUp);
    return () => {
      window.removeEventListener('mousemove', handlePointerMove);
      window.removeEventListener('mouseup', handlePointerUp);
    };
  }, [onMoveWorkspaceToGroup]);

  useEffect(() => {
    if (!pointerDragActive) return;
    const prevCursor = document.body.style.cursor;
    const prevUserSelect = document.body.style.userSelect;
    document.body.style.cursor = 'grabbing';
    document.body.style.userSelect = 'none';
    return () => {
      document.body.style.cursor = prevCursor;
      document.body.style.userSelect = prevUserSelect;
    };
  }, [pointerDragActive]);
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    type: 'workspace' | 'session' | 'group';
    targetId: string;
  } | null>(null);

  useEffect(() => {
    const handleClose = () => setContextMenu(null);
    window.addEventListener('click', handleClose);
    window.addEventListener('contextmenu', handleClose);
    return () => {
      window.removeEventListener('click', handleClose);
      window.removeEventListener('contextmenu', handleClose);
    };
  }, []);

  const handleContextMenu = (e: React.MouseEvent, type: 'workspace' | 'session' | 'group', targetId: string) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      type,
      targetId,
    });
  };

  const startWorkspacePointerDrag = (workspaceId: string, e: React.MouseEvent) => {
    if (e.button !== 0) return;
    pointerDragRef.current = {
      workspaceId,
      startX: e.clientX,
      startY: e.clientY,
      active: false,
    };
    setDraggingWorkspaceId(workspaceId);
  };

  const handleWorkspaceRowClick = (workspaceId: string) => {
    if (suppressWorkspaceClickRef.current) {
      suppressWorkspaceClickRef.current = false;
      return;
    }
    toggleWorkspace(workspaceId);
  };

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

  const filterText = repoFilter.trim().toLowerCase();
  const matchesFilter = (value: string) =>
    !filterText || value.toLowerCase().includes(filterText);

  const groupedWorkspaceIds = useMemo(() => {
    const ids = new Set<string>();
    for (const group of repositoryGroups) {
      for (const workspaceId of group.workspace_ids) {
        ids.add(workspaceId);
      }
    }
    return ids;
  }, [repositoryGroups]);

  const visibleWorkspaces = useMemo(
    () =>
      workspaces.filter(
        (workspace) =>
          matchesFilter(workspace.name) || matchesFilter(workspace.workspace_path),
      ),
    [workspaces, filterText],
  );

  const visibleGroups = useMemo(
    () =>
      repositoryGroups.filter((group) => {
        if (matchesFilter(group.name)) return true;
        return group.workspace_ids.some((workspaceId) => {
          const workspace = workspaces.find((item) => item.id === workspaceId);
          if (!workspace) return false;
          return matchesFilter(workspace.name) || matchesFilter(workspace.workspace_path);
        });
      }),
    [repositoryGroups, workspaces, filterText],
  );

  const ungroupedWorkspaces = useMemo(
    () => visibleWorkspaces.filter((workspace) => !groupedWorkspaceIds.has(workspace.id)),
    [visibleWorkspaces, groupedWorkspaceIds],
  );

  const toggleWorkspace = (workspaceId: string) => {
    setCollapsedWorkspaces((prev) => ({ ...prev, [workspaceId]: !prev[workspaceId] }));
    onSelectWorkspace?.(workspaceId);
  };

  const handleFlowSelect = (flowName: string) => {
    setActiveFlow(flowName);
    setView('chat');
  };

  const renderWorkspaceRow = (repo: WorkspaceInfo) => {
    const isActiveWorkspace = repo.id === activeWorkspaceId;
    const isDragging = draggingWorkspaceId === repo.id;
    const collapsed = collapsedWorkspaces[repo.id] ?? false;
    const projectSessions = sessionsByWorkspace.get(repo.id) ?? [];

    return (
      <div key={repo.id} className="space-y-0.5">
        <div
          onContextMenu={(e) => handleContextMenu(e, 'workspace', repo.id)}
          className={`flex items-center justify-between p-1.5 rounded-lg transition-colors group ${
            isActiveWorkspace ? 'bg-surface-container-low/80' : 'hover:bg-surface-bright'
          } ${isDragging && pointerDragActive ? 'opacity-50 ring-1 ring-primary/30' : ''}`}
        >
          <div
            onMouseDown={(e) => startWorkspacePointerDrag(repo.id, e)}
            onClick={() => handleWorkspaceRowClick(repo.id)}
            data-testid={`workspace-row-${repo.id}`}
            className="flex items-center gap-2 flex-1 min-w-0 text-left cursor-grab active:cursor-grabbing"
            title={repo.workspace_path}
          >
            <span className="material-symbols-outlined text-[18px] text-on-surface-variant">
              {collapsed ? 'folder' : 'folder_open'}
            </span>
            <span className="text-xs font-semibold truncate">{repo.name}</span>
          </div>
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
                    onContextMenu={(e) => handleContextMenu(e, 'session', session.run_id)}
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
              data-testid="nav-new-repo-group"
              className="material-symbols-outlined text-[16px] cursor-pointer hover:text-primary"
              title={t('New project group')}
              onClick={() => onCreateRepositoryGroup?.()}
            >
              folder_special
            </span>
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

        <input
          data-testid="repo-filter"
          type="search"
          value={repoFilter}
          onChange={(event) => setRepoFilter(event.target.value)}
          placeholder={t('Filter projects')}
          className="mx-2 mb-2 w-[calc(100%-1rem)] rounded-lg border border-outline-variant/60 bg-surface-bright px-3 py-1.5 text-[11px] text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none focus:border-primary/50"
        />

        <nav className="flex-1 sidebar-scroll overflow-y-auto space-y-2 px-1 pb-4">
          {workspaces.length === 0 && repositoryGroups.length === 0 && (
            <p className="text-[11px] text-on-surface-variant/60 italic px-3 py-2 leading-relaxed">
              {t('No repositories yet. Use Add project folder or Authorize workspace to begin.')}
            </p>
          )}
          {visibleGroups.map((group) => {
            const groupCollapsed = group.collapsed;
            const groupWorkspaces = group.workspace_ids
              .map((workspaceId) => visibleWorkspaces.find((item) => item.id === workspaceId))
              .filter((item): item is WorkspaceInfo => Boolean(item));
            const isDragOver = dragOverGroupId === group.id;

            return (
              <div
                key={group.id}
                className={`space-y-1 rounded-lg transition-all ${
                  isDragOver ? 'bg-primary/5 ring-1 ring-primary/20 border border-primary/10 p-1' : ''
                }`}
                data-testid={`repo-group-${group.id}`}
                data-drop-group-id={group.id}
              >
                <button
                  type="button"
                  data-testid={`repo-group-toggle-${group.id}`}
                  data-drop-group-id={group.id}
                  onClick={() => onToggleRepositoryGroup?.(group.id, !groupCollapsed)}
                  onContextMenu={(e) => handleContextMenu(e, 'group', group.id)}
                  className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left hover:bg-surface-bright transition-colors"
                >
                  <span className="material-symbols-outlined text-[16px] text-on-surface-variant">
                    folder_special
                  </span>
                  <span className="text-[11px] font-bold uppercase tracking-wide text-on-surface-variant/80 truncate">
                    {group.name}
                  </span>
                </button>
                {!groupCollapsed && (
                  <div className="space-y-1 ml-2 border-l border-outline-variant/30 pl-2">
                    {groupWorkspaces.length === 0 ? (
                      <p className="text-[11px] text-on-surface-variant/60 italic py-1 pl-2">
                        {t('No projects in this group yet')}
                      </p>
                    ) : (
                      groupWorkspaces.map((repo) => renderWorkspaceRow(repo))
                    )}
                  </div>
                )}
              </div>
            );
          })}
          {ungroupedWorkspaces.length > 0 && (() => {
            const isDragOver = dragOverGroupId === '__default__';
            return (
              <div
                className={`space-y-1 rounded-lg transition-all ${
                  isDragOver ? 'bg-primary/5 ring-1 ring-primary/20 border border-primary/10 p-1' : ''
                }`}
                data-testid="repo-group-default"
                data-drop-group-id="__default__"
              >
                <button
                  type="button"
                  data-testid="repo-group-default-toggle"
                  data-drop-group-id="__default__"
                  onClick={() => setDefaultGroupCollapsed(!defaultGroupCollapsed)}
                  className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left hover:bg-surface-bright transition-colors"
                >
                  <span className="material-symbols-outlined text-[16px] text-on-surface-variant">
                    folder_special
                  </span>
                  <span className="text-[11px] font-bold uppercase tracking-wide text-on-surface-variant/80 truncate">
                    {t('Default Group')}
                  </span>
                </button>
                {!defaultGroupCollapsed && (
                  <div className="space-y-1 ml-2 border-l border-outline-variant/30 pl-2">
                    {ungroupedWorkspaces.map((repo) => renderWorkspaceRow(repo))}
                  </div>
                )}
              </div>
            );
          })()}
          {workspaces.length > 0 &&
            visibleGroups.length === 0 &&
            ungroupedWorkspaces.length === 0 &&
            filterText && (
              <p className="text-[11px] text-on-surface-variant/60 italic px-3 py-2">
                {t('No projects match your filter')}
              </p>
            )}

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
      {contextMenu && (
        <div
          className="fixed bg-surface-bright border border-outline-variant rounded-lg shadow-lg py-1 z-[100] min-w-[120px]"
          style={{ top: contextMenu.y, left: contextMenu.x }}
          onClick={(e) => e.stopPropagation()}
        >
          {contextMenu.type === 'group' && (
            <>
              <button
                type="button"
                className="w-full text-left px-3 py-2 text-xs text-on-surface hover:bg-surface-container transition-colors flex items-center gap-2"
                onClick={() => {
                  const { targetId } = contextMenu;
                  setContextMenu(null);
                  onRenameRepositoryGroup?.(targetId);
                }}
              >
                <span className="material-symbols-outlined text-[16px]">edit</span>
                {t('Rename')}
              </button>
              <button
                type="button"
                className="w-full text-left px-3 py-2 text-xs text-rose-600 hover:bg-rose-50 hover:text-rose-700 transition-colors flex items-center gap-2"
                onClick={() => {
                  const { targetId } = contextMenu;
                  setContextMenu(null);
                  onDeleteRepositoryGroup?.(targetId);
                }}
              >
                <span className="material-symbols-outlined text-[16px]">delete</span>
                {t('Delete Group')}
              </button>
            </>
          )}

          {contextMenu.type === 'workspace' && (
            <>
              <div className="relative group/submenu">
                <button
                  type="button"
                  className="w-full text-left px-3 py-2 text-xs text-on-surface hover:bg-surface-container transition-colors flex items-center justify-between gap-2 cursor-pointer"
                >
                  <span className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-[16px]">folder_shared</span>
                    {t('Move to Group')}
                  </span>
                  <span className="material-symbols-outlined text-[14px]">chevron_right</span>
                </button>
                <div className="hidden group-hover/submenu:block absolute left-[calc(100%-4px)] top-0 bg-surface-bright border border-outline-variant rounded-lg shadow-lg py-1 min-w-[140px] max-h-[200px] overflow-y-auto z-[101]">
                  <button
                    type="button"
                    onClick={() => {
                      onMoveWorkspaceToGroup?.(contextMenu.targetId, '__default__');
                      setContextMenu(null);
                    }}
                    className="w-full text-left px-3 py-1.5 text-xs text-on-surface hover:bg-surface-container transition-colors truncate flex items-center gap-1.5"
                  >
                    <span className="material-symbols-outlined text-[14px] text-on-surface-variant">folder_special</span>
                    {t('Default Group')}
                  </button>
                  {repositoryGroups.map((g) => (
                    <button
                      key={g.id}
                      type="button"
                      onClick={() => {
                        onMoveWorkspaceToGroup?.(contextMenu.targetId, g.id);
                        setContextMenu(null);
                      }}
                      className="w-full text-left px-3 py-1.5 text-xs text-on-surface hover:bg-surface-container transition-colors truncate flex items-center gap-1.5"
                    >
                      <span className="material-symbols-outlined text-[14px] text-on-surface-variant">folder_special</span>
                      {g.name}
                    </button>
                  ))}
                </div>
              </div>

              <button
                type="button"
                className="w-full text-left px-3 py-2 text-xs text-rose-600 hover:bg-rose-50 hover:text-rose-700 transition-colors flex items-center gap-2"
                onClick={() => {
                  const { targetId } = contextMenu;
                  setContextMenu(null);
                  onDeleteWorkspace?.(targetId);
                }}
              >
                <span className="material-symbols-outlined text-[16px]">delete</span>
                {t('Delete')}
              </button>
            </>
          )}

          {contextMenu.type === 'session' && (
            <button
              type="button"
              className="w-full text-left px-3 py-2 text-xs text-rose-600 hover:bg-rose-50 hover:text-rose-700 transition-colors flex items-center gap-2"
              onClick={() => {
                const { targetId } = contextMenu;
                setContextMenu(null);
                onDeleteSession?.(targetId);
              }}
            >
              <span className="material-symbols-outlined text-[16px]">delete</span>
              {t('Delete')}
            </button>
          )}
        </div>
      )}
    </aside>
  );
};
