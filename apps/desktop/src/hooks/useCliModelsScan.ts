import { useCallback, useEffect, useState } from 'react';
import { useLanguage } from '../components/LanguageContext';
import { useCliScanNotice } from '../components/CliScanNotice';
import {
  fetchCliModelsConfig,
  type CliModelsScan,
} from '../services/cliConfigApi';
import {
  getCachedModelsScan,
  markModelsAutoScanned,
  saveModelsScanCache,
  shouldAutoScanModels,
} from '../services/cliModelsScanCache';

function scanSuccessMessage(
  agentType: string,
  payload: CliModelsScan,
  t: (key: string) => string,
): string {
  if (agentType === 'opencode-cli' || agentType === 'mimo-cli') {
    const modelCount = payload.catalog?.length ?? 0;
    const authCount = payload.auth_providers?.length ?? 0;
    return t('Scan complete — {models} models, {providers} credential providers found.')
      .replace('{models}', String(modelCount))
      .replace('{providers}', String(authCount));
  }
  if (agentType === 'claude-cli') {
    return t('Scan complete — {count} providers found.').replace(
      '{count}',
      String(payload.providers.length),
    );
  }
  const modelCount = payload.available_models?.length ?? payload.catalog?.length ?? 0;
  return t('Scan complete — {count} models found.').replace('{count}', String(modelCount));
}

function scanningMessage(agentType: string, t: (key: string) => string): string {
  if (agentType === 'mimo-cli') return t('Scanning MiMo Code configuration…');
  if (agentType === 'opencode-cli') return t('Scanning OpenCode configuration…');
  if (agentType === 'claude-cli') return t('Scanning Claude Code configuration…');
  return t('Scanning local config…');
}

function scanFailureMessage(agentType: string, t: (key: string) => string): string {
  if (agentType === 'mimo-cli') return t('Failed to scan MiMo Code models.');
  if (agentType === 'opencode-cli') return t('Failed to scan OpenCode models.');
  if (agentType === 'claude-cli') return t('Failed to scan Claude Code models.');
  return t('Failed to scan models.');
}

export function useCliModelsScan(agentType: string) {
  const { t } = useLanguage();
  const [data, setData] = useState<CliModelsScan | null>(() => getCachedModelsScan(agentType));
  const [loading, setLoading] = useState(() => !getCachedModelsScan(agentType));
  const [error, setError] = useState<string | null>(null);
  const { notice, setNotice, dismissNotice } = useCliScanNotice();

  const refresh = useCallback(
    async (options?: { manual?: boolean }) => {
      const manual = options?.manual ?? false;
      const hasCache = Boolean(getCachedModelsScan(agentType));
      const background = !manual && hasCache;
      if (!background) setLoading(true);
      setError(null);
      if (manual) {
        setNotice({
          tone: 'info',
          message: scanningMessage(agentType, t),
        });
      } else {
        setNotice(null);
      }
      try {
        const payload = await fetchCliModelsConfig(agentType);
        setData(payload);
        saveModelsScanCache(agentType, payload);
        if (!manual) {
          markModelsAutoScanned(agentType);
        }
        if (manual) {
          setNotice({
            tone: 'success',
            message: scanSuccessMessage(agentType, payload, t),
          });
        }
      } catch (err) {
        setData(null);
        const errMsg =
          err instanceof Error ? err.message : scanFailureMessage(agentType, t);
        setError(errMsg);
        if (manual) {
          setNotice({ tone: 'error', message: errMsg });
        }
      } finally {
        if (!background) setLoading(false);
      }
    },
    [agentType, setNotice, t],
  );

  useEffect(() => {
    const cached = getCachedModelsScan(agentType);
    if (cached) {
      setData(cached);
      setLoading(false);
    }
    if (!shouldAutoScanModels(agentType)) {
      return;
    }
    void refresh({ manual: false });
    // Only re-run when the agent tab panel mounts for a different agent type.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentType]);

  return {
    data,
    loading,
    error,
    notice,
    dismissNotice,
    refresh: () => refresh({ manual: true }),
    refreshSilent: () => refresh({ manual: false }),
  };
}
