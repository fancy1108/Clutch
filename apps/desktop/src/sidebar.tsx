import React from 'react';
import { RepositoryFolder, MainView } from './types';
import { useLanguage } from './components/LanguageContext';
import { sendSidecarTestMessage } from './services/api';

interface SidebarProps {
  currentView: MainView;
  setView: (view: MainView) => void;
  folders: RepositoryFolder[];
  setFolders: React.Dispatch<React.SetStateAction<RepositoryFolder[]>>;
  activeFlow: string;
  setActiveFlow: (flow: string) => void;
  onResetSimulation: () => void;
  isOpenState: boolean;
  setIsOpenState: (open: boolean) => void;
  isMultiAgent?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  setView,
  folders,
  setFolders,
  activeFlow,
  setActiveFlow,
  onResetSimulation,
  isOpenState,
  setIsOpenState,
  isMultiAgent = true
}) => {
  const { t } = useLanguage();

  const toggleFolder = (folderName: string) => {
    setFolders(prev =>
      prev.map(f => (f.name === folderName ? { ...f, collapsed: !f.collapsed } : f))
    );
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
      {/* Collapse Toggle Handle */}
      <button
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

      {/* Main Sidebar Contents (Hidden completely when collapsed) */}
      <div className={`flex-1 flex flex-col gap-4 overflow-hidden h-full ${!isOpenState ? 'hidden' : ''}`}>
        {/* Top Window Dots (Mock MacOS Control Buttons) */}
        <div className="flex items-center justify-between mb-2 px-2">
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-[#ff5f57] hover:scale-105 transition-transform cursor-pointer" title={t("Close")} />
            <div className="w-3 h-3 rounded-full bg-[#febc2e] hover:scale-105 transition-transform cursor-pointer" title={t("Minimize")} />
            <div className="w-3 h-3 rounded-full bg-[#28c840] hover:scale-105 transition-transform cursor-pointer" title={t("Fullscreen")} />
          </div>
        </div>

        {/* Main Actions Panel */}
        <div className="space-y-1 mb-4 px-1">
          <button
            onClick={() => {
              onResetSimulation();
              setView('chat');
            }}
            className={`w-full flex items-center gap-3 p-2.5 rounded-lg transition-all text-left group ${
              currentView === 'chat' && activeFlow === 'Video Production'
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

        {/* Folders and Projects Header */}
        <div className="flex items-center justify-between text-on-surface-variant mb-1 px-3">
          <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant/70">
            {t("REPOSITORIES")}
          </span>
          <div className="flex gap-2">
            <span className="material-symbols-outlined text-[16px] cursor-pointer hover:text-primary" title={t("Filter list")}>
              filter_list
            </span>
            <span className="material-symbols-outlined text-[16px] cursor-pointer hover:text-primary" title={t("New folder")}>
              create_new_folder
            </span>
          </div>
        </div>

        {/* Main Folders Navigation Tree */}
        <nav className="flex-1 sidebar-scroll overflow-y-auto space-y-4 px-1 pb-4">
          {folders.map(folder => (
            <div key={folder.name} className="space-y-1">
              <div
                onClick={() => toggleFolder(folder.name)}
                className="flex items-center justify-between text-on-surface font-semibold p-1.5 rounded hover:bg-surface-bright transition-colors cursor-pointer group"
              >
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[18px] text-on-surface-variant">
                    {folder.collapsed ? 'folder' : 'folder_open'}
                  </span>
                  <span className="text-xs tracking-wide">{t(folder.name)}</span>
                </div>
                <span
                  onClick={(e) => {
                    e.stopPropagation();
                    onResetSimulation();
                    setView('chat');
                  }}
                  className="material-symbols-outlined text-[16px] opacity-0 group-hover:opacity-100 transition-opacity hover:text-primary hover:scale-110 p-0.5 rounded hover:bg-surface-container"
                  title={t("New Chat")}
                >
                  add
                </span>
              </div>

              {!folder.collapsed && (
                <div className="space-y-0.5 ml-4 border-l-2 border-outline-variant/20 pl-2">
                  {folder.items.length === 0 ? (
                    <p className="text-[11px] text-on-surface-variant/60 italic py-1 pl-2">
                      {t("No agents yet")}
                    </p>
                  ) : (
                    folder.items.map(item => {
                      const isItemActive = activeFlow === item.name || (item.isActive && activeFlow === "Video Production" && folder.name === "obsidian");
                      return (
                        <div
                          key={item.name}
                          onClick={() => handleFlowSelect(item.name)}
                          className={`w-full flex items-center justify-between p-2 rounded-lg text-left transition-all cursor-pointer ${
                            isItemActive
                              ? 'bg-surface-bright shadow-sm text-on-surface font-bold border border-outline-variant/40'
                              : 'text-on-surface-variant hover:bg-surface-bright hover:text-on-surface'
                          }`}
                        >
                          <span className="text-xs truncate max-w-[160px]">{t(item.name)}</span>
                          <div className="flex items-center gap-1.5 flex-shrink-0">
                            <span className="text-[9px] font-mono bg-surface-container-high px-1 rounded text-on-surface-variant/80">
                              {item.time}
                            </span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          ))}
        </nav>

        {/* Sidebar Footer settings */}
        <div className="mt-auto pt-3 border-t border-outline-variant/50 space-y-1">
          <button
            type="button"
            onClick={() => {
              void sendSidecarTestMessage().catch((error: unknown) => {
                console.error('[Clutch WS] test send failed:', error);
              });
            }}
            className="w-full flex items-center justify-center gap-2 p-2 rounded-lg text-left transition-all border border-dashed border-outline-variant/80 text-on-surface-variant hover:bg-surface-bright hover:text-on-surface text-[11px] font-mono"
          >
            [Test WS]
          </button>
          <button
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
