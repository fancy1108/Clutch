import React from 'react';
import type { WorkspaceInfo } from '../../../services/workspaceApi';
import type { MainView } from '../../../types';
import { LegacyIcon } from '../../../components/ui/LegacyIcon';
import { NAV_CONFIG } from '../navConfig';
import type { SidebarCollapsedRailProps } from './SidebarCollapsedRail.macos';

export const SidebarCollapsedRailWindows: React.FC<SidebarCollapsedRailProps> = ({
  currentView,
  isMultiAgent,
  workspaces,
  activeWorkspaceId,
  onNewChat,
  setView,
  onAddWorkspace,
  onSelectWorkspace,
  showCollapsedTooltip,
  hideCollapsedTooltip,
  t,
  appMode,
}) => {
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

  return (
    <div className="flex h-full flex-col items-center gap-3 overflow-hidden pt-[76px] pb-2">
      <div className="flex flex-col items-center gap-1">
        {collapsedNavButton('chat', NAV_CONFIG.chat.icon, t(NAV_CONFIG.chat.labelKey), onNewChat, currentView === 'chat')}
        {appMode !== 'design' ? (
          <>
            {collapsedNavButton('agents', NAV_CONFIG.agents.icon, t(NAV_CONFIG.agents.labelKey), () => setView('agents'), currentView === 'agents')}
            {isMultiAgent
              ? collapsedNavButton('workflows', NAV_CONFIG.workflows.icon, t(NAV_CONFIG.workflows.labelKey), () => setView('workflows'), currentView === 'workflows')
              : null}
          </>
        ) : null}
        {collapsedNavButton('add-workspace', NAV_CONFIG.addWorkspace.icon, t(NAV_CONFIG.addWorkspace.labelKey), () => onAddWorkspace?.())}
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

      {collapsedNavButton('settings', NAV_CONFIG.settings.icon, t(NAV_CONFIG.settings.labelKey), () => setView('settings'), currentView === 'settings')}
    </div>
  );
};
