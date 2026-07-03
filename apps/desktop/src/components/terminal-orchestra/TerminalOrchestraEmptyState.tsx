import React from 'react';
import { Terminal } from 'lucide-react';
import { useLanguage } from '../LanguageContext';
import { TerminalSessionStatsBar } from './TerminalSessionStatsBar';

interface TerminalOrchestraEmptyStateProps {
  sessionRunId: string;
}

export const TerminalOrchestraEmptyState: React.FC<TerminalOrchestraEmptyStateProps> = ({
  sessionRunId,
}) => {
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
        {t('Mention an agent to open a terminal')}
      </h2>
      <p className="text-[13px] leading-relaxed text-on-surface-variant max-w-md mb-4">
        {t('Type @Agent in the bar below to launch that agent\'s CLI. Clear the mention to close the terminal pane.')}
      </p>
      <div className="w-full max-w-lg space-y-2">
        <div className="rounded-xl border border-outline-variant/30 bg-surface-container-low/60 px-4 py-3 text-left space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
            {t('Example prompts')}
          </p>
          <p className="font-mono text-[12px] text-on-surface">
            <span className="text-primary">@Claude Code</span> {t('Summarize this repo and list open tasks')}
          </p>
          <p className="font-mono text-[12px] text-on-surface">
            <span className="text-primary">@OpenCode</span> {t('from')}{' '}
            <span className="text-primary">@Claude Code</span> {t('Continue the API implementation')}
          </p>
        </div>
        <TerminalSessionStatsBar sessionRunId={sessionRunId} visible />
      </div>
    </div>
  );
};
