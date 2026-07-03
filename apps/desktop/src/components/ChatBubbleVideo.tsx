import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Play, Download } from 'lucide-react';
import { useLanguage } from './LanguageContext';
import { BTN_FOCUS, BTN_SM } from './ui/buttonStyles';
import { isSidecarApiPath, sidecarAuthedHttpUrl, sidecarFetch, sidecarHttpUrl } from '../services/sidecarUrl';

type ChatBubbleVideoProps = {
  src: string;
  title?: string;
};

function filenameFromUrl(url: string): string {
  try {
    const name = new URL(url, 'http://localhost').pathname.split('/').pop();
    if (name && name.includes('.')) return name;
  } catch {
    /* ignore */
  }
  return 'clutch-video.mp4';
}

async function resolvePlaybackSrc(src: string): Promise<string> {
  const trimmed = src.trim();
  if (isSidecarApiPath(trimmed)) {
    return sidecarAuthedHttpUrl(trimmed);
  }
  return trimmed;
}

async function downloadVideo(src: string, filename: string): Promise<void> {
  const trimmed = src.trim();
  let fetchUrl = trimmed;
  if (isSidecarApiPath(trimmed)) {
    if (trimmed.startsWith('/api/')) {
      fetchUrl = sidecarHttpUrl(trimmed);
    } else {
      const url = new URL(trimmed);
      fetchUrl = sidecarHttpUrl(`${url.pathname}${url.search}`);
    }
  }
  const response = isSidecarApiPath(trimmed)
    ? await sidecarFetch(fetchUrl)
    : await fetch(fetchUrl);
  if (!response.ok) {
    throw new Error(`Download failed (${response.status})`);
  }
  const blob = await response.blob();
  const blobUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = blobUrl;
  anchor.download = filename;
  anchor.rel = 'noopener';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(blobUrl);
}

export function ChatBubbleVideo({ src, title }: ChatBubbleVideoProps) {
  const { t } = useLanguage();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playbackSrc, setPlaybackSrc] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [frameReady, setFrameReady] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setPlaybackSrc(null);
    setError(null);
    setFrameReady(false);
    void resolvePlaybackSrc(src)
      .then((resolved) => {
        if (!cancelled) setPlaybackSrc(resolved);
      })
      .catch(() => {
        if (!cancelled) setError(t('Could not load video.'));
      });
    return () => {
      cancelled = true;
    };
  }, [src, t]);

  const togglePlayback = useCallback(() => {
    const el = videoRef.current;
    if (!el) return;
    if (el.paused) {
      void el.play().catch(() => setError(t('Could not play video.')));
    } else {
      el.pause();
    }
  }, [t]);

  const primeFirstFrame = useCallback(() => {
    const el = videoRef.current;
    if (!el || frameReady) return;
    try {
      if (el.readyState >= 1 && el.duration > 0) {
        el.currentTime = Math.min(0.05, el.duration / 100);
      }
      setFrameReady(true);
    } catch {
      setFrameReady(true);
    }
  }, [frameReady]);

  const handleDownload = useCallback(async () => {
    setDownloading(true);
    setError(null);
    try {
      await downloadVideo(src, filenameFromUrl(src));
    } catch (err) {
      setError(err instanceof Error ? err.message : t('Download failed.'));
    } finally {
      setDownloading(false);
    }
  }, [src, t]);

  const loading = !playbackSrc && !error;

  return (
    <div className="flex flex-col gap-2 w-full max-w-lg">
      <div className="relative overflow-hidden rounded-xl border border-outline-variant/30 shadow-sm bg-surface-container-low">
        {loading ? (
          <div className="flex min-h-[10rem] w-full items-center justify-center px-4 py-6 text-sm text-on-surface-variant">
            {t('Loading...')}
          </div>
        ) : null}
        {playbackSrc ? (
          <video
            ref={videoRef}
            src={playbackSrc}
            className={`block w-full h-auto max-h-[min(24rem,70vh)] object-contain bg-surface-container-low${error ? ' invisible absolute inset-0' : ''}`}
            playsInline
            preload="auto"
            onLoadedMetadata={primeFirstFrame}
            onLoadedData={primeFirstFrame}
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onEnded={() => setPlaying(false)}
            onClick={togglePlayback}
            onError={() => setError(t('Could not load video.'))}
          />
        ) : null}
        {error ? (
          <div
            className="flex min-h-[10rem] w-full flex-col items-center justify-center gap-2 px-4 py-6 text-center"
            role="alert"
          >
            <p className="text-sm text-on-surface-variant">{error}</p>
          </div>
        ) : null}
        {!playing && !error && playbackSrc ? (
          <button
            type="button"
            className={`group absolute inset-0 flex items-center justify-center bg-neutral-900/[0.04] hover:bg-neutral-900/[0.07] transition-all duration-300 cursor-pointer ${BTN_FOCUS}`}
            onClick={togglePlayback}
            aria-label={t('Play')}
          >
            <span className="flex items-center justify-center size-14 rounded-full bg-white/95 backdrop-blur-sm border border-outline-variant/40 text-neutral-900 shadow-md group-hover:bg-white group-hover:shadow-lg transition-all duration-300">
              <Play className="size-6 ml-0.5" fill="currentColor" strokeWidth={0} aria-hidden />
            </span>
          </button>
        ) : null}
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className={`${BTN_SM} inline-flex items-center gap-1.5`}
          onClick={() => void handleDownload()}
          disabled={downloading || !playbackSrc}
          aria-label={t('Download video')}
        >
          <Download className="size-3.5" />
          {downloading ? t('Downloading…') : t('Download')}
        </button>
        {title ? (
          <span className="text-[11px] text-on-surface-variant truncate">{title}</span>
        ) : null}
      </div>
      {error && playbackSrc ? (
        <a
          href={playbackSrc}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[12px] text-primary hover:underline"
        >
          {t('Open video in browser')}
        </a>
      ) : null}
    </div>
  );
}
