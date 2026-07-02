import React from 'react';
import { Terminal } from 'lucide-react';
import { useLanguage } from '../LanguageContext';

export const TerminalOrchestraEmptyState: React.FC = () => {
  const { t } = useLanguage();

  return (
    <div
      data-testid="terminal-orchestra-empty"
      className="flex flex-1 flex-col items-center justify-center min-h-0 px-8 py-12 text-center"
    >
      <div className="w-12 h-12 rounded-2xl border border-outline-variant/30 bg-surface-container-low flex items-center justify-center mb-4">
        <Terminal className="w-5 h-5 text-on-surface-variant" strokeWidth={1.75} />
      </div>
      <h2 className="text-sm font-semibold text-on-surface mb-2">
        {t('Terminal empty state title')}
      </h2>
      <p className="text-[13px] leading-relaxed text-on-surface-variant max-w-md mb-4">
        {t('Terminal empty state body')}
      </p>
      <div className="w-full max-w-lg rounded-xl border border-outline-variant/30 bg-surface-container-low/60 px-4 py-3 text-left space-y-2">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
          {t('Terminal empty state examples')}
        </p>
        <p className="font-mono text-[12px] text-on-surface">
          <span className="text-primary">@Claude Code</span> {t('Terminal empty state example task')}
        </p>
        <p className="font-mono text-[12px] text-on-surface">
          <span className="text-primary">@OpenCode</span> {t('Terminal empty state from hint')}{' '}
          <span className="text-primary">@Claude Code</span> {t('Terminal empty state handoff task')}
        </p>
      </div>
    </div>
  );
};
