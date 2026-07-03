import React, { useEffect, useMemo, useRef, useState } from 'react';
import { RepositoryFolder, MainView } from './types';
import { useLanguage } from './components/LanguageContext';
import type { SessionRecord } from './services/runApi';
import type { RepositoryGroup, WorkspaceInfo } from './services/workspaceApi';
import { LegacyIcon } from './components/ui/LegacyIcon';
import { UpdateBanner } from './components/UpdateBanner';
import { BTN_ICON_SM } from './components/ui/buttonStyles';
import { SIDEBAR_COLLAPSED_WIDTH_PX, SIDEBAR_EXPANDED_WIDTH_PX } from './constants/layout';

interface SidebarProps {
  currentView: MainView;
  setView: (view: MainView) => void;
  folders: RepositoryFolder[];
  setFolders: React.Dispatch<React.SetStateAction<RepositoryFolder[]>>;
  activeFlow: string;
  setActiveFlow: (flow: string) => void;
  onNewChat: () => void;
  isOpenState: boolean;
  isMultiAgent?: boolean;
  sessions?: SessionRecord[];
  shellSnapshotRunIds?: ReadonlySet<string>;
  activeSessionId?: string;
  loadingSessionId?: string | null;
  clutchStatus?: string;
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
  isMultiAgent = true,
  sessions = [],
  shellSnapshotRunIds,
  activeSessionId = '',
  loadingSessionId = null,
  clutchStatus = '',
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
  const [collapsedTooltip, setCollapsedTooltip] = useState<{ label: string; top: number } | null>(null);
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

  const showDefaultGroup = useMemo(() => {
    if (workspaces.length === 0) return false;
    if (ungroupedWorkspaces.length > 0) return true;
    if (repositoryGroups.length > 0) {
      if (!filterText) return true;
      const defaultGroupNameEn = 'default group';
      const defaultGroupNameZh = t('Default Group').toLowerCase();
      return defaultGroupNameZh.includes(filterText) || defaultGroupNameEn.includes(filterText);
    }
    return false;
  }, [workspaces.length, ungroupedWorkspaces.length, repositoryGroups.length, filterText, t]);

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
          className={`flex items-center justify-between p-1.5 rounded-lg border border-transparent transition-colors group ${
            isActiveWorkspace ? 'bg-surface-container-low/80' : 'hover:bg-surface-bright'
          } ${isDragging && pointerDragActive ? 'opacity-50 ring-1 ring-primary/30' : ''}`}
        >
          <div
            onMouseDown={(e) => startWorkspacePointerDrag(repo.id, e)}
            onClick={() => handleWorkspaceRowClick(repo.id)}
            data-testid={`workspace-row-${repo.id}`}
            className="flex items-center gap-2 flex-1 min-w-0 text-left cursor-grab active:cursor-grabbing"
          >
            <LegacyIcon
              name={collapsed ? 'folder' : 'folder_open'}
              className="text-[18px] text-on-surface-variant"
            />
            <span className="text-[13px] font-normal text-on-surface-variant/80 truncate">
              {repo.name}
            </span>
          </div>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onNewChatInWorkspace?.(repo.id);
            }}
            className={BTN_ICON_SM}
            aria-label={t('New Chat')}
          >
            <LegacyIcon name="add" className="text-[16px]" />
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
                const isRunning =
                  (session.run_id === activeSessionId && clutchStatus === 'running') ||
                  session.status === 'running';
                const isLoadingSession = session.run_id === loadingSessionId;
                const hasSnapshot = shellSnapshotRunIds?.has(session.run_id) ?? false;
                return (
                  <button
                    key={session.run_id}
                    type="button"
                    data-testid={`sidebar-session-${session.run_id}`}
                    onClick={() => onSelectSession?.(session)}
                    onContextMenu={(e) => handleContextMenu(e, 'session', session.run_id)}
                    aria-label={sessionLabel(session)}
                    className={`relative w-full overflow-hidden flex items-center justify-between p-2 rounded-lg border text-left transition-[background-color,border-color,color,box-shadow] ${
                      isActiveSession
                        ? 'bg-surface-bright shadow-sm text-on-surface-variant/80 font-normal border-outline-variant/40'
                        : 'border-transparent text-on-surface-variant hover:bg-surface-bright hover:text-on-surface'
                    }`}
                  >
                    <span className="flex items-center gap-1.5 min-w-0">
                      {isRunning ? (
                        <LegacyIcon
                          name="progress_activity"
                          className="text-[12px] text-primary flex-shrink-0 animate-spin"
                          aria-hidden
                        />
                      ) : null}
                      <span className="text-[12.5px] text-on-surface-variant/80 truncate max-w-[130px]">
                        {sessionLabel(session)}
                      </span>
                    </span>
                    <span className="text-[9px] font-mono text-on-surface-variant/70 flex-shrink-0">
                      {formatRelativeTime(session.started_at)}
                    </span>
                    {isLoadingSession ? (
                      <span className="absolute inset-x-2 bottom-0 h-[2px] overflow-hidden rounded-full bg-outline-variant/30" aria-hidden>
                        <span className="session-row-loading-bar absolute inset-y-0 w-1/2 rounded-full bg-primary/80" />
                      </span>
                    ) : null}
                  </button>
                );
              })
            )}
          </div>
        )}
      </div>
    );
  };

  const showCollapsedTooltip = (label: string, target: HTMLElement) => {
    const rect = target.getBoundingClientRect();
    setCollapsedTooltip({
      label,
      top: rect.top + rect.height / 2,
    });
  };

  const hideCollapsedTooltip = () => setCollapsedTooltip(null);

  const collapsedNavButton = (
    key: string,
    icon: string,
    title: string,
    onClick: () => void,
    active = false,
  ) => (
    <button
      key={key}
      type="button"
      onClick={onClick}
      aria-label={title}
      onMouseEnter={(event) => showCollapsedTooltip(title, event.currentTarget)}
      onMouseLeave={hideCollapsedTooltip}
      onFocus={(event) => showCollapsedTooltip(title, event.currentTarget)}
      onBlur={hideCollapsedTooltip}
      className={`flex h-9 w-9 items-center justify-center rounded-lg border transition-[background-color,border-color,color,box-shadow] ${
        active
          ? 'border-outline-variant/60 bg-surface-bright text-on-surface shadow-sm'
          : 'border-transparent text-on-surface-variant hover:bg-surface-bright hover:text-on-surface'
      }`}
    >
      <LegacyIcon name={icon} className="text-[18px]" />
    </button>
  );

  const renderCollapsedRail = () => (
    <div className="flex h-full flex-col items-center gap-3 overflow-hidden pt-[76px] pb-2">
      <div className="flex flex-col items-center gap-1">
        {collapsedNavButton('chat', 'chat', t('New Chat'), onNewChat, currentView === 'chat')}
        {collapsedNavButton('agents', 'smart_toy', t('AI Agents'), () => setView('agents'), currentView === 'agents')}
        {isMultiAgent
          ? collapsedNavButton('workflows', 'account_tree', t('Workflows SOP'), () => setView('workflows'), currentView === 'workflows')
          : null}
        {collapsedNavButton('add-workspace', 'create_new_folder', t('Add project folder'), () => onAddWorkspace?.())}
      </div>

      <div className="h-px w-8 bg-outline-variant/60" />

      <div className="flex min-h-0 w-full flex-1 flex-col items-center gap-1 overflow-y-auto overflow-x-hidden sidebar-scroll px-1">
        {workspaces.map((repo) => {
          const isActiveWorkspace = repo.id === activeWorkspaceId;
          return (
            <button
              key={repo.id}
              type="button"
              data-testid={`collapsed-workspace-${repo.id}`}
              onClick={() => onSelectWorkspace?.(repo.id)}
              aria-label={repo.name}
              onMouseEnter={(event) => showCollapsedTooltip(repo.name, event.currentTarget)}
              onMouseLeave={hideCollapsedTooltip}
              onFocus={(event) => showCollapsedTooltip(repo.name, event.currentTarget)}
              onBlur={hideCollapsedTooltip}
              className={`flex h-9 w-9 items-center justify-center rounded-lg border transition-[background-color,border-color,color,box-shadow] ${
                isActiveWorkspace
                  ? 'border-outline-variant/70 bg-surface-bright text-on-surface shadow-sm'
                  : 'border-transparent text-on-surface-variant hover:bg-surface-bright hover:text-on-surface'
              }`}
            >
              <LegacyIcon name={isActiveWorkspace ? 'folder_open' : 'folder'} className="text-[18px]" />
            </button>
          );
        })}
      </div>

      <div className="h-px w-8 bg-outline-variant/60" />

      {collapsedNavButton('settings', 'settings', t('Settings'), () => setView('settings'), currentView === 'settings')}
    </div>
  );

  return (
    <>
    <aside
      className={`fixed h-screen left-0 top-0 border-r border-outline-variant bg-surface flex flex-col overflow-hidden transition-[width] duration-200 ease-out z-50 ${
        isOpenState ? 'px-4 pt-5 pb-3' : 'p-2'
      }`}
      style={{
        width: isOpenState ? SIDEBAR_EXPANDED_WIDTH_PX : SIDEBAR_COLLAPSED_WIDTH_PX,
      }}
    >
      {isOpenState ? (
      <div className="flex-1 flex flex-col gap-3 overflow-hidden h-full">
        <div className="space-y-1 mb-4 px-1">
          <button
            data-testid="nav-new-chat"
            onClick={onNewChat}
            aria-label={t('New Chat')}
            className={`w-full flex items-center gap-2.5 p-2 rounded-lg border transition-[background-color,border-color,color,box-shadow] text-left group ${
              currentView === 'chat'
                ? 'bg-surface-bright shadow-sm text-on-surface font-semibold border-outline-variant/50'
                : 'border-transparent text-on-surface-variant hover:bg-surface-bright hover:text-on-surface'
            }`}
          >
            <LegacyIcon name="chat" className="text-[17px] text-on-surface-variant group-hover:text-primary" />
            <span className="text-xs font-semibold tracking-wide">{t("New Chat")}</span>
          </button>

          <button
            data-testid="nav-agents"
            onClick={() => setView('agents')}
            aria-label={t('AI Agents')}
            className={`w-full flex items-center gap-2.5 p-2 rounded-lg border transition-[background-color,border-color,color,box-shadow] text-left group ${
              currentView === 'agents'
                ? 'bg-surface-bright shadow-sm text-on-surface font-semibold border-outline-variant/50'
                : 'border-transparent text-on-surface-variant hover:bg-surface-bright hover:text-on-surface'
            }`}
          >
            <LegacyIcon name="smart_toy" className="text-[17px] text-on-surface-variant group-hover:text-primary" />
            <span className="text-xs font-semibold tracking-wide">{t("AI Agents")}</span>
          </button>

          {isMultiAgent ? (
            <button
              data-testid="nav-workflows"
              onClick={() => setView('workflows')}
              aria-label={t('Workflows SOP')}
              className={`w-full flex items-center gap-2.5 p-2 rounded-lg border transition-[background-color,border-color,color,box-shadow] text-left group ${
                currentView === 'workflows'
                  ? 'bg-surface-bright shadow-sm text-on-surface font-semibold border-outline-variant/60'
                  : 'border-transparent text-on-surface-variant hover:bg-surface-bright hover:text-on-surface'
              }`}
            >
              <LegacyIcon name="account_tree" className="text-[17px] text-on-surface-variant group-hover:text-primary" />
              <span className="text-xs font-semibold tracking-wide">{t("Workflows SOP")}</span>
            </button>
          ) : null}
        </div>

        <div className="flex items-center justify-between text-on-surface-variant px-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-on-surface-variant/70">
            {t('Projects')}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              data-testid="nav-new-repo-group"
              className={BTN_ICON_SM}
              aria-label={t('New project group')}
              onClick={() => onCreateRepositoryGroup?.()}
            >
              <LegacyIcon name="folder_special" className="text-[16px]" />
            </button>
            <button
              type="button"
              data-testid="nav-add-workspace"
              className={BTN_ICON_SM}
              aria-label={t('Add project folder')}
              onClick={() => onAddWorkspace?.()}
            >
              <LegacyIcon name="create_new_folder" className="text-[16px]" />
            </button>
          </div>
        </div>

        <input
          data-testid="repo-filter"
          type="search"
          value={repoFilter}
          onChange={(event) => setRepoFilter(event.target.value)}
          placeholder={t('Filter projects')}
          className="mx-1 mb-1 w-[calc(100%-0.5rem)] rounded-lg border border-outline-variant/60 bg-surface-bright px-2.5 py-1.5 text-[11px] text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none focus:border-primary/50"
        />

        <div className="mx-1 h-px bg-outline-variant/50" />

        <nav className="flex-1 sidebar-scroll overflow-y-auto space-y-2 px-1 pb-2">
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
                className={`space-y-1 rounded-lg border border-transparent transition-[background-color,border-color,box-shadow] ${
                  isDragOver ? 'bg-primary/5 ring-1 ring-primary/20 border-primary/10' : ''
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
                  aria-label={group.name}
                  className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left hover:bg-surface-bright transition-colors"
                >
                  <LegacyIcon name={groupCollapsed ? "folder_special" : "folder_special_open"} className="text-[16px] text-on-surface-variant" />
                  <span className="text-xs font-bold uppercase tracking-wide text-on-surface-variant/80 truncate">
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
          {showDefaultGroup && (() => {
            const isDragOver = dragOverGroupId === '__default__';
            return (
              <div
                className={`space-y-1 rounded-lg border border-transparent transition-[background-color,border-color,box-shadow] ${
                  isDragOver ? 'bg-primary/5 ring-1 ring-primary/20 border-primary/10' : ''
                }`}
                data-testid="repo-group-default"
                data-drop-group-id="__default__"
              >
                <button
                  type="button"
                  data-testid="repo-group-default-toggle"
                  data-drop-group-id="__default__"
                  onClick={() => setDefaultGroupCollapsed(!defaultGroupCollapsed)}
                  aria-label={t('Default Group')}
                  className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left hover:bg-surface-bright transition-colors"
                >
                  <LegacyIcon name={defaultGroupCollapsed ? "folder_special" : "folder_special_open"} className="text-[16px] text-on-surface-variant" />
                  <span className="text-xs font-bold uppercase tracking-wide text-on-surface-variant/80 truncate">
                    {t('Default Group')}
                  </span>
                </button>
                {!defaultGroupCollapsed && (
                  <div className="space-y-1 ml-2 border-l border-outline-variant/30 pl-2">
                    {ungroupedWorkspaces.length === 0 ? (
                      <p className="text-[11px] text-on-surface-variant/60 italic py-1 pl-2">
                        {t('No projects in this group yet')}
                      </p>
                    ) : (
                      ungroupedWorkspaces.map((repo) => renderWorkspaceRow(repo))
                    )}
                  </div>
                )}
              </div>
            );
          })()}
          {workspaces.length > 0 &&
            visibleGroups.length === 0 &&
            !showDefaultGroup &&
            filterText && (
              <p className="text-[11px] text-on-surface-variant/60 italic px-3 py-2">
                {t('No projects match your filter')}
              </p>
            )}

        </nav>

        <div className="mt-auto pt-1 border-t border-outline-variant/50 min-w-0">
          <div className="flex items-center gap-1 min-w-0">
            <button
              data-testid="nav-settings"
              onClick={() => setView('settings')}
              aria-label={t('Settings')}
              className={`flex-1 min-w-0 flex items-center justify-center gap-2 px-1.5 py-1 rounded-lg border text-center transition-[background-color,border-color,color,box-shadow] group ${
                currentView === 'settings' ? 'bg-surface-bright shadow-sm text-on-surface font-semibold border-outline-variant/60' : 'border-transparent text-on-surface-variant hover:bg-surface-bright'
              }`}
            >
              <LegacyIcon name="settings" className="text-[17px] shrink-0 text-on-surface-variant group-hover:text-primary" />
              <span className="text-[11px] font-semibold tracking-wide truncate">{t("Settings")}</span>
            </button>
            <UpdateBanner />
          </div>
        </div>
      </div>
      ) : (
        renderCollapsedRail()
      )}
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
                <LegacyIcon name="edit" className="text-[16px]" />
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
                <LegacyIcon name="delete" className="text-[16px]" />
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
                    <LegacyIcon name="folder_shared" className="text-[16px]" />
                    {t('Move to Group')}
                  </span>
                  <LegacyIcon name="chevron_right" className="text-[14px]" />
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
                    <LegacyIcon name="folder_special" className="text-[14px] text-on-surface-variant" />
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
                      <LegacyIcon name="folder_special" className="text-[14px] text-on-surface-variant" />
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
                <LegacyIcon name="delete" className="text-[16px]" />
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
              <LegacyIcon name="delete" className="text-[16px]" />
              {t('Delete')}
            </button>
          )}
        </div>
      )}
    </aside>
    {!isOpenState && collapsedTooltip ? (
      <div
        className="fixed z-[80] -translate-y-1/2 rounded-md border border-outline-variant/60 bg-surface-bright px-2.5 py-1.5 text-[11px] font-medium text-on-surface shadow-lg pointer-events-none whitespace-nowrap"
        style={{ left: SIDEBAR_COLLAPSED_WIDTH_PX + 8, top: collapsedTooltip.top }}
        role="tooltip"
      >
        {collapsedTooltip.label}
      </div>
    ) : null}
    </>
  );
};
