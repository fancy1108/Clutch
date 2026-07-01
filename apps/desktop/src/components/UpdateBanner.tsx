import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { useLanguage } from './LanguageContext';
import { BTN_GHOST_SM, BTN_PRIMARY_SM } from './ui/buttonStyles';
import {
  dismissAppUpdate,
  downloadAppUpdate,
  fetchAppUpdate,
  installAppUpdate,
  shouldCheckForAppUpdates,
  type AppUpdatePhase,
  type AppUpdateProgress,
} from '../services/appUpdater';
import type { Update } from '@tauri-apps/plugin-updater';

function progressPercent(progress: AppUpdateProgress): number {
  if (!progress.totalBytes || progress.totalBytes <= 0) return 0;
  return Math.min(100, Math.round((progress.downloadedBytes / progress.totalBytes) * 100));
}

export const UpdateBanner: React.FC = () => {
  const { t } = useLanguage();
  const [phase, setPhase] = useState<AppUpdatePhase>('idle');
  const [version, setVersion] = useState('');
  const [progress, setProgress] = useState<AppUpdateProgress>({ downloadedBytes: 0 });
  const [busy, setBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const pendingUpdateRef = useRef<Update | null>(null);

  useEffect(() => {
    if (!shouldCheckForAppUpdates()) return;

    let cancelled = false;
    const timer = window.setTimeout(() => {
      void fetchAppUpdate().then((update) => {
        if (cancelled || !update) return;
        pendingUpdateRef.current = update;
        setVersion(update.version);
        setPhase('available');
      });
    }, 4000);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      void pendingUpdateRef.current?.close();
    };
  }, []);

  const handleDismiss = useCallback(() => {
    if (version) dismissAppUpdate(version);
    void pendingUpdateRef.current?.close();
    pendingUpdateRef.current = null;
    setErrorMessage(null);
    setPhase('idle');
  }, [version]);

  const handleDownload = useCallback(async () => {
    const update = pendingUpdateRef.current;
    if (!update || busy) return;

    setBusy(true);
    setErrorMessage(null);
    setPhase('downloading');
    try {
      await downloadAppUpdate(update, setProgress);
      setPhase('ready');
    } catch (err) {
      console.warn('[Clutch] Update download failed:', err);
      setErrorMessage(t('Update download failed. Check your connection and try again.'));
      setPhase('available');
    } finally {
      setBusy(false);
    }
  }, [busy, t]);

  const handleInstall = useCallback(async () => {
    const update = pendingUpdateRef.current;
    if (!update || busy) return;

    setBusy(true);
    setErrorMessage(null);
    try {
      await installAppUpdate(update);
    } catch (err) {
      console.warn('[Clutch] Update install failed:', err);
      setErrorMessage(t('Update install failed. Try again or download from GitHub Releases.'));
      setPhase('ready');
      setBusy(false);
    }
  }, [busy, t]);

  if (phase === 'idle') return null;

  const pct = progressPercent(progress);
  const versionLabel = `v${version}`;
  const versionHint = t('New version available: {{version}}').replace('{{version}}', versionLabel);
  const showSpinner = phase === 'downloading' || (phase === 'ready' && busy);

  return (
    <div
      className="flex shrink-0 items-center gap-1 min-w-0"
      role="status"
      aria-live="polite"
      data-testid="update-pill"
    >
      {phase === 'available' && (
        <>
          <button
            type="button"
            onClick={() => { void handleDownload(); }}
            disabled={busy}
            title={errorMessage || versionHint}
            aria-label={errorMessage || versionHint}
            className={BTN_PRIMARY_SM}
          >
            {t('Update')}
          </button>
          <button type="button" onClick={handleDismiss} className={`${BTN_GHOST_SM} px-2`}>
            {t('Later')}
          </button>
        </>
      )}

      {phase === 'downloading' && (
        <button type="button" disabled className={BTN_PRIMARY_SM}>
          <Loader2 className="size-3 shrink-0 animate-spin" aria-hidden />
          <span className="font-mono text-[10px] tabular-nums">{pct}%</span>
        </button>
      )}

      {phase === 'ready' && (
        <button
          type="button"
          onClick={() => { void handleInstall(); }}
          disabled={busy}
          title={versionHint}
          className={BTN_PRIMARY_SM}
        >
          {showSpinner ? <Loader2 className="size-3 shrink-0 animate-spin" aria-hidden /> : null}
          {t('Restart')}
        </button>
      )}
    </div>
  );
};
