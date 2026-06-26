import React from 'react';
import { useLanguage } from './LanguageContext';
import { BTN_ICON } from './ui/buttonStyles';
import { LegacyIcon } from './ui/LegacyIcon';

interface HeaderProps {
  currentFlow: string;
  workspaceName?: string;
  onPickWorkspace?: () => void;
  folders?: any[];
  isMultiAgent: boolean;
  setIsMultiAgent: (val: boolean) => void;
  onGoBack?: () => void;
  setView: (view: any) => void;
  sidebarOpen?: boolean;
  selectedModel?: string;
}

export const Header: React.FC<HeaderProps> = ({
  currentFlow,
  workspaceName,
  onPickWorkspace,
  folders,
  isMultiAgent,
  setIsMultiAgent,
  onGoBack,
  setView,
  sidebarOpen = true,
  selectedModel
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
    <header className={`fixed top-0 right-0 h-[64px] bg-background/85 backdrop-blur-md border-b border-outline-variant z-40 flex items-center justify-between px-10 select-none transition-all duration-300 ${
      sidebarOpen ? 'left-[280px]' : 'left-0'
    }`}>
      <div className="flex items-center gap-4">
        {onGoBack && (
          <button
            onClick={onGoBack}
            className={`${BTN_ICON} w-8 h-8 rounded-full text-on-surface`}
            title={t("Go Back")}
            aria-label={t("Go Back")}
          >
            <LegacyIcon name="chevron_left" className="text-[20px] leading-none" />
          </button>
        )}
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
        {/* Single / Multi-Agent mode toggle */}
        <div className="flex items-center bg-surface-container-low p-1 rounded-lg border border-outline-variant/30">
          <button
            data-testid="agent-mode-single"
            onClick={() => setIsMultiAgent(false)}
            className={`px-3 py-1.5 text-[11px] rounded-md transition-all cursor-pointer ${
              !isMultiAgent
                ? 'bg-surface-bright text-on-surface font-bold shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface font-medium'
            }`}
          >
            {t("Single Agent")}
          </button>
          <button
            data-testid="agent-mode-multi"
            onClick={() => setIsMultiAgent(true)}
            className={`px-3 py-1.5 text-[11px] rounded-md transition-all cursor-pointer ${
              isMultiAgent
                ? 'bg-surface-bright text-on-surface font-bold shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface font-medium'
            }`}
          >
            {t("Multi-Agent")}
          </button>
        </div>

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
