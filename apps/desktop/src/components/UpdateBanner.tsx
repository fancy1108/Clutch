import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { ArrowDownToLine, Download, RefreshCw } from 'lucide-react';
import { useLanguage } from './LanguageContext';
import { BTN_PRIMARY, BTN_SECONDARY } from './ui/buttonStyles';
import {
  BANNER_INFO,
  BANNER_PROGRESS_FILL,
  BANNER_PROGRESS_TRACK,
} from './ui/surfaceStyles';
import {
  APP_HEADER_HEIGHT_PX,
  UPDATE_BANNER_HEIGHT_VAR,
} from '../constants/layout';
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

function formatMegabytes(bytes: number): string {
  return (bytes / (1024 * 1024)).toFixed(1);
}

function progressPercent(progress: AppUpdateProgress): number {
  if (!progress.totalBytes || progress.totalBytes <= 0) return 0;
  return Math.min(100, Math.round((progress.downloadedBytes / progress.totalBytes) * 100));
}

function syncBannerHeight(el: HTMLElement | null): void {
  const h = el?.offsetHeight ?? 0;
  document.documentElement.style.setProperty(UPDATE_BANNER_HEIGHT_VAR, `${h}px`);
}

function clearBannerHeight(): void {
  document.documentElement.style.setProperty(UPDATE_BANNER_HEIGHT_VAR, '0px');
}

export const UpdateBanner: React.FC = () => {
  const { t } = useLanguage();
  const [phase, setPhase] = useState<AppUpdatePhase>('idle');
  const [version, setVersion] = useState('');
  const [progress, setProgress] = useState<AppUpdateProgress>({ downloadedBytes: 0 });
  const [busy, setBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const pendingUpdateRef = useRef<Update | null>(null);
  const bannerRef = useRef<HTMLDivElement>(null);

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
      clearBannerHeight();
    };
  }, []);

  useLayoutEffect(() => {
    if (phase === 'idle') {
      clearBannerHeight();
      return;
    }
    syncBannerHeight(bannerRef.current);
    const el = bannerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => syncBannerHeight(el));
    ro.observe(el);
    return () => {
      ro.disconnect();
      clearBannerHeight();
    };
  }, [phase, errorMessage, version, progress.downloadedBytes]);

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
  const downloadedLabel = formatMegabytes(progress.downloadedBytes);
  const totalLabel = progress.totalBytes ? formatMegabytes(progress.totalBytes) : '?';

  const phaseIcon =
    phase === 'ready' ? (
      <RefreshCw className="size-4 shrink-0 text-on-surface-variant" aria-hidden />
    ) : phase === 'downloading' ? (
      <ArrowDownToLine className="size-4 shrink-0 text-on-surface-variant" aria-hidden />
    ) : (
      <Download className="size-4 shrink-0 text-on-surface-variant" aria-hidden />
    );

  const showLater = phase === 'available' || phase === 'downloading';

  return (
    <div
      ref={bannerRef}
      className={`fixed left-0 right-0 z-[45] w-full flex-wrap ${BANNER_INFO}`}
      style={{ top: `${APP_HEADER_HEIGHT_PX}px` }}
      role="status"
      aria-live="polite"
    >
      <div className="flex min-w-0 flex-1 flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          {phaseIcon}
          {phase === 'available' && (
            <p className="truncate text-[13px] font-semibold text-on-surface leading-snug">
              {t('New version available: {{version}}').replace('{{version}}', `v${version}`)}
            </p>
          )}
          {phase === 'downloading' && (
            <>
              <p className="shrink-0 text-[13px] font-semibold font-mono text-on-surface leading-snug tabular-nums">
                {t('Downloading... {{done}} / {{total}} ({{percent}}%)')
                  .replace('{{done}}', downloadedLabel)
                  .replace('{{total}}', totalLabel)
                  .replace('{{percent}}', String(pct))}
              </p>
              <div className={`hidden sm:block ${BANNER_PROGRESS_TRACK}`}>
                <div
                  className={BANNER_PROGRESS_FILL}
                  style={{ transform: `scaleX(${Math.max(pct, 4) / 100})` }}
                />
              </div>
            </>
          )}
          {phase === 'ready' && (
            <p className="truncate text-[13px] font-semibold text-on-surface leading-snug">
              {t('Update {{version}} downloaded. Restart to install.').replace('{{version}}', `v${version}`)}
            </p>
          )}
        </div>
        {errorMessage && (
          <p className="text-[12px] font-medium leading-snug text-rose-700 sm:max-w-[min(420px,40vw)]">
            {errorMessage}
          </p>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-2">
        {phase === 'available' && (
          <button
            type="button"
            onClick={() => { void handleDownload(); }}
            disabled={busy}
            className={BTN_PRIMARY}
          >
            {t('Download update')}
          </button>
        )}
        {phase === 'ready' && (
          <button
            type="button"
            onClick={() => { void handleInstall(); }}
            disabled={busy}
            className={BTN_PRIMARY}
          >
            {t('Restart to install')}
          </button>
        )}
        {showLater && (
          <button
            type="button"
            onClick={handleDismiss}
            disabled={busy && phase === 'downloading'}
            className={BTN_SECONDARY}
          >
            {t('Later')}
          </button>
        )}
      </div>
    </div>
  );
};
