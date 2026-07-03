import { useLanguage } from '../../LanguageContext';
import type { WorkspaceInfo } from '../../../services/workspaceApi';

interface ReadyStepProps {
  workspace: WorkspaceInfo | null;
  modelReady: boolean;
  toolsReady: boolean;
  activeModelLabel: string;
  defaultAgentName: string | null;
}

function executionPathLabel(modelReady: boolean, toolsReady: boolean, t: (key: string) => string): string {
  if (modelReady && toolsReady) return t('Both cloud model and local CLI');
  if (modelReady) return t('Cloud model');
  if (toolsReady) return t('Local CLI');
  return '—';
}

function credentialStoreLabel(t: (key: string) => string): string {
  const platform = typeof navigator !== 'undefined' ? navigator.platform : '';
  if (/Mac/i.test(platform)) return t('Keys stored in macOS Keychain');
  if (/Win/i.test(platform)) return t('Keys stored in Windows Credential Manager');
  return t('Keys stored securely by the operating system when supported');
}

export function ReadyStep({
  workspace,
  modelReady,
  toolsReady,
  activeModelLabel,
  defaultAgentName,
}: ReadyStepProps) {
  const { t } = useLanguage();

  const summary = [
    { label: t('Active model'), value: modelReady ? activeModelLabel : t('Not configured (CLI path)') },
    {
      label: t('Workspace'),
      value: workspace?.name ?? workspace?.workspace_path?.split('/').pop() ?? '—',
    },
    { label: t('Execution path'), value: executionPathLabel(modelReady, toolsReady, t) },
    { label: t('Permission'), value: t('Default ask (read-only)') },
  ];

  if (toolsReady && defaultAgentName) {
    summary.push({ label: t('Default agent'), value: defaultAgentName });
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-xl font-bold text-neutral-900">{t('Ready to launch')}</h2>
        <p className="mt-2 text-sm text-neutral-500">{t('Review your setup, then open the workspace.')}</p>
      </div>

      <div className="grid grid-cols-2 gap-2 max-w-md mx-auto">
        {summary.map((row) => (
          <div key={row.label} className="rounded-xl border border-neutral-200 bg-neutral-50/80 p-3 text-left">
            <p className="text-[9px] font-bold uppercase tracking-wide text-neutral-400">{row.label}</p>
            <p className="text-xs font-semibold text-neutral-900 mt-1 break-words">{row.value}</p>
          </div>
        ))}
      </div>

      <p className="text-[10px] text-neutral-500 text-center">
        {credentialStoreLabel(t)}
      </p>
      <p className="text-[10px] text-neutral-400 text-center">{t('Full permission mode selection coming soon')}</p>
    </div>
  );
}
