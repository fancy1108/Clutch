import { useState } from 'react';
import { FolderOpen } from 'lucide-react';
import { isTauri } from '@tauri-apps/api/core';

import { useLanguage } from '../../LanguageContext';
import { addWorkspace, type WorkspaceInfo } from '../../../services/workspaceApi';
import { pickWorkspaceFolder } from '../../../services/pickWorkspaceFolder';
import { BTN_PRIMARY } from '../../ui/buttonStyles';

interface WorkspaceStepProps {
  workspace: WorkspaceInfo | null;
  onWorkspaceSelected: (workspace: WorkspaceInfo) => void;
}

export function WorkspaceStep({ workspace, onWorkspaceSelected }: WorkspaceStepProps) {
  const { t } = useLanguage();
  const [picking, setPicking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePick = async () => {
    if (!isTauri()) {
      setError(t('Use Clutch.app to complete first-time setup'));
      return;
    }
    setPicking(true);
    setError(null);
    try {
      const path = await pickWorkspaceFolder(t('Select project folder'));
      if (!path) return;
      const info = await addWorkspace(path);
      onWorkspaceSelected(info);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('Workspace authorize failed'));
    } finally {
      setPicking(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-xl font-bold text-neutral-900">{t('Choose your workspace')}</h2>
        <p className="mt-2 text-sm text-neutral-500 max-w-md mx-auto">
          {t('Clutch reads and writes only inside the project folder you authorize.')}
        </p>
      </div>

      {!isTauri() && (
        <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-center">
          {t('Use Clutch.app to complete first-time setup')}
        </p>
      )}

      {workspace ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50/80 px-4 py-3 text-left">
          <p className="text-[10px] font-bold uppercase tracking-wide text-emerald-800">{t('Selected')}</p>
          <p className="text-sm font-mono text-emerald-950 mt-1 break-all">{workspace.workspace_path}</p>
        </div>
      ) : (
        <button
          type="button"
          data-testid="onboarding-pick-workspace"
          disabled={picking || !isTauri()}
          onClick={() => void handlePick()}
          className={`${BTN_PRIMARY} w-full max-w-sm mx-auto flex items-center justify-center gap-2`}
        >
          <FolderOpen className="h-4 w-4" />
          {picking ? t('Selecting…') : t('Select project folder')}
        </button>
      )}

      {error && (
        <p className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2 text-center">
          {error}
        </p>
      )}
    </div>
  );
}
