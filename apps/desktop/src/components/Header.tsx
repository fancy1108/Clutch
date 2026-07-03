import React from 'react';
import { useLanguage } from './LanguageContext';
import { BTN_ICON } from './ui/buttonStyles';
import { LegacyIcon } from './ui/LegacyIcon';
import { SIDEBAR_COLLAPSED_WIDTH_PX, SIDEBAR_EXPANDED_WIDTH_PX } from '../constants/layout';

interface HeaderProps {
  currentFlow: string;
  workspaceName?: string;
  onPickWorkspace?: () => void;
  folders?: any[];
  onToggleSidebar: () => void;
  sidebarOpen?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  currentFlow,
  workspaceName,
  onPickWorkspace,
  folders,
  onToggleSidebar,
  sidebarOpen = true,
}) => {
  const { language, setLanguage, t } = useLanguage();

  // Dynamically resolve parent folder/project name
  const parentFolder = folders?.find((folder) =>
    folder.items.some((item: { name: string }) => item.name === currentFlow),
  );

  const parentLabel = workspaceName
    || (parentFolder
      ? parentFolder.name.charAt(0).toUpperCase() + parentFolder.name.slice(1)
      : 'Workspace');

  return (
    <header
      className="fixed top-0 right-0 h-[64px] bg-background/85 backdrop-blur-md border-b border-outline-variant z-40 flex items-center justify-between px-2 select-none transition-[left] duration-200 ease-out"
      style={{ left: sidebarOpen ? SIDEBAR_EXPANDED_WIDTH_PX : SIDEBAR_COLLAPSED_WIDTH_PX }}
    >
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onToggleSidebar}
          className={`${BTN_ICON} w-7 h-7 rounded-full text-on-surface`}
          title={sidebarOpen ? t('Collapse Sidebar') : t('Expand Sidebar')}
          aria-label={sidebarOpen ? t('Collapse Sidebar') : t('Expand Sidebar')}
        >
          <LegacyIcon name={sidebarOpen ? 'chevron_left' : 'chevron_right'} className="text-[19px] leading-none" />
        </button>
        <nav className="flex items-center gap-2 text-xs font-semibold tracking-wide text-on-surface-variant">
          <span
            onClick={onPickWorkspace}
            className="hover:text-primary cursor-pointer font-bold transition-colors"
            title={t("Select workspace")}
          >
            {t(parentLabel)}
          </span>
          <span className="text-outline-variant text-[10px] select-none">/</span>
          <span className="text-on-surface font-extrabold">
            {t(currentFlow)}
          </span>
        </nav>
      </div>

      <div className="flex items-center gap-3">

        {/* Language Switcher Toggle */}
        <div className="flex items-center bg-surface-container-low p-1 rounded-lg border border-outline-variant/30">
          <button
            data-testid="lang-en"
            onClick={() => setLanguage('en')}
            className={`px-3 py-1.5 text-[11px] rounded-md transition-all cursor-pointer ${
              language === 'en'
                ? 'bg-surface-bright text-on-surface font-bold shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface font-medium'
            }`}
          >
            English
          </button>
          <button
            data-testid="lang-zh"
            onClick={() => setLanguage('zh')}
            className={`px-3 py-1.5 text-[11px] rounded-md transition-all cursor-pointer ${
              language === 'zh'
                ? 'bg-surface-bright text-on-surface font-bold shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface font-medium'
            }`}
          >
            中文
          </button>
        </div>
      </div>
    </header>
  );
};
