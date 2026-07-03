import React from 'react';
import type { WorkspaceInfo } from '../../../services/workspaceApi';
import type { MainView } from '../../../types';
import { LegacyIcon } from '../../../components/ui/LegacyIcon';
import { NAV_CONFIG } from '../navConfig';

export type SidebarCollapsedRailProps = {
  currentView: MainView;
  isMultiAgent: boolean;
  workspaces: WorkspaceInfo[];
  activeWorkspaceId: string | null;
  onNewChat: () => void;
  setView: (view: MainView) => void;
  onAddWorkspace?: () => void;
  onSelectWorkspace?: (workspaceId: string) => void;
  showCollapsedTooltip: (label: string, anchor: HTMLElement) => void;
  hideCollapsedTooltip: () => void;
  t: (key: string) => string;
};

function collapsedMicroLabel(value: string, maxLen = 3): string {
  const trimmed = value.trim();
  if (!trimmed) return '·';
  return trimmed.length <= maxLen ? trimmed : trimmed.slice(0, maxLen);
}

export const SidebarCollapsedRailMacos: React.FC<SidebarCollapsedRailProps> = ({
  currentView,
  isMultiAgent,
  workspaces,
  activeWorkspaceId,
  onNewChat,
  setView,
  onAddWorkspace,
  onSelectWorkspace,
  t,
}) => {
  const collapsedNavButton = (
    key: string,
    icon: string,
    title: string,
    shortLabel: string,
    onClick: () => void,
    active = false,
  ) => (
    <button
      key={key}
      type="button"
      onClick={onClick}
      aria-label={title}
      title={title}
      className={`flex w-full flex-col items-center justify-center gap-0.5 rounded-lg border py-1 transition-[background-color,border-color,color,box-shadow] ${
        active
          ? 'border-outline-variant/60 bg-surface-bright text-on-surface shadow-sm'
          : 'border-transparent text-on-surface-variant hover:bg-surface-bright hover:text-on-surface'
      }`}
    >
      <LegacyIcon name={icon} className="text-[17px]" />
      <span className="max-w-[48px] truncate text-center text-[8px] font-medium leading-none">
        {shortLabel}
      </span>
    </button>
  );

  return (
    <div className="flex h-full min-h-0 flex-col items-center gap-2 overflow-hidden pt-3 pb-2">
      <div className="flex w-full flex-col items-stretch gap-0.5">
        {collapsedNavButton('chat', NAV_CONFIG.chat.icon, t(NAV_CONFIG.chat.labelKey), t(NAV_CONFIG.chat.shortLabelKey), onNewChat, currentView === 'chat')}
        {collapsedNavButton('agents', NAV_CONFIG.agents.icon, t(NAV_CONFIG.agents.labelKey), t(NAV_CONFIG.agents.shortLabelKey), () => setView('agents'), currentView === 'agents')}
        {isMultiAgent
          ? collapsedNavButton('workflows', NAV_CONFIG.workflows.icon, t(NAV_CONFIG.workflows.labelKey), t(NAV_CONFIG.workflows.shortLabelKey), () => setView('workflows'), currentView === 'workflows')
          : null}
        {collapsedNavButton('add-workspace', NAV_CONFIG.addWorkspace.icon, t(NAV_CONFIG.addWorkspace.labelKey), t(NAV_CONFIG.addWorkspace.shortLabelKey), () => onAddWorkspace?.())}
      </div>

      <div className="h-px w-8 bg-outline-variant/60" />

      <div className="flex min-h-0 w-full flex-1 flex-col items-center gap-1 overflow-y-auto overflow-x-hidden sidebar-scroll px-1">
        {workspaces.map((repo) => {
          const isActiveWorkspace = repo.id === activeWorkspaceId;
          const microLabel = collapsedMicroLabel(repo.name);
          return (
            <button
              key={repo.id}
              type="button"
              data-testid={`collapsed-workspace-${repo.id}`}
              onClick={() => onSelectWorkspace?.(repo.id)}
              aria-label={repo.name}
              title={repo.name}
              className={`flex w-full flex-col items-center justify-center gap-0.5 rounded-lg border py-1 transition-[background-color,border-color,color,box-shadow] ${
                isActiveWorkspace
                  ? 'border-outline-variant/70 bg-surface-bright text-on-surface shadow-sm'
                  : 'border-transparent text-on-surface-variant hover:bg-surface-bright hover:text-on-surface'
              }`}
            >
              <LegacyIcon name={isActiveWorkspace ? 'folder_open' : 'folder'} className="text-[17px]" />
              <span className="max-w-[48px] truncate text-center text-[8px] font-medium leading-none">
                {microLabel}
              </span>
            </button>
          );
        })}
      </div>

      <div className="h-px w-8 bg-outline-variant/60" />

      {collapsedNavButton('settings', NAV_CONFIG.settings.icon, t(NAV_CONFIG.settings.labelKey), t(NAV_CONFIG.settings.shortLabelKey), () => setView('settings'), currentView === 'settings')}
    </div>
  );
};
