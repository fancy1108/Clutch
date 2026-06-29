import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, Info, Loader2, RefreshCw } from 'lucide-react';
import { isTauri } from '@tauri-apps/api/core';

import { useLanguage } from '../../LanguageContext';
import { pollHealth } from '../../../services/onboardingApi';
import {
  runEnvironmentChecks,
  type EnvCheckTier,
  type EnvRequirementId,
  type EnvRequirementResult,
} from '../../../services/environmentCheck';
import { BTN_GHOST } from '../../ui/buttonStyles';

interface WelcomeStepProps {
  onHealthyChange: (healthy: boolean) => void;
}

const REQUIREMENT_LABELS: Record<EnvRequirementId, string> = {
  macos: 'macOS 14+ recommended',
  arch: 'Apple Silicon recommended for local models',
  disk: '~500 MB disk space for app data',
  network: 'Network required for cloud LLM providers',
  gatekeeper: 'Unsigned DMG: allow in System Settings if macOS blocks launch',
};

const ENV_HINTS: Record<EnvRequirementId, Record<EnvCheckTier, string>> = {
  macos: {
    ok: 'Your macOS version meets our recommendation.',
    warn: 'Older macOS detected — you can still use Clutch, but it is less tested on this version.',
    info: 'Could not verify macOS version (common on recent Macs). macOS 14+ is recommended.',
  },
  arch: {
    ok: 'Apple Silicon — best experience for local models like Ollama.',
    warn: 'Intel Mac detected — local models may run slower; cloud models and CLI tools work normally.',
    info: 'Could not detect chip type. Local model speed depends on your hardware.',
  },
  disk: {
    ok: 'Enough storage available for app data.',
    warn: 'Low storage — saving workspace or preferences may fail. Free up ~500 MB.',
    info: 'Could not measure free disk space. Please keep ~500 MB available.',
  },
  network: {
    ok: 'Online — you can configure cloud LLM providers.',
    warn: 'Offline or no internet — skip cloud models and use a local CLI instead.',
    info: 'Network status unknown.',
  },
  gatekeeper: {
    ok: 'Clutch is running — Gatekeeper step passed.',
    warn: '—',
    info: 'Install from Clutch.app. If macOS blocks launch, see INSTALL.md.',
  },
};

function tierIcon(tier: EnvCheckTier) {
  if (tier === 'ok') {
    return <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-600" aria-hidden />;
  }
  if (tier === 'warn') {
    return <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-600" aria-hidden />;
  }
  return <Info className="h-3.5 w-3.5 shrink-0 text-sky-600" aria-hidden />;
}

function tierRowClass(tier: EnvCheckTier): string {
  if (tier === 'ok') return 'border-emerald-100 bg-emerald-50/40';
  if (tier === 'warn') return 'border-amber-100 bg-amber-50/50';
  return 'border-sky-100 bg-sky-50/40';
}

function EnvRequirementRow({
  id,
  tier,
  t,
}: {
  id: EnvRequirementId;
  tier: EnvCheckTier;
  t: (key: string) => string;
}) {
  const hintKey = ENV_HINTS[id][tier];
  if (hintKey === '—') return null;
  return (
    <li
      className={`rounded-lg border px-2.5 py-2 space-y-0.5 ${tierRowClass(tier)}`}
      data-testid={`onboarding-env-${id}`}
      data-tier={tier}
    >
      <div className="flex items-start gap-2">
        {tierIcon(tier)}
        <span className="font-medium text-neutral-800 leading-snug">{t(REQUIREMENT_LABELS[id])}</span>
      </div>
      <p className="pl-5 text-[10px] text-neutral-600 leading-relaxed">{hintKey ? t(hintKey) : null}</p>
    </li>
  );
}

export function WelcomeStep({ onHealthyChange }: WelcomeStepProps) {
  const { t } = useLanguage();
  const [checking, setChecking] = useState(true);
  const [healthy, setHealthy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [envChecks, setEnvChecks] = useState<EnvRequirementResult[] | null>(null);

  const check = async () => {
    setChecking(true);
    setError(null);
    const [result, env] = await Promise.all([pollHealth(), runEnvironmentChecks(isTauri())]);
    setEnvChecks(env);
    setHealthy(result.ok);
    if (!result.ok) {
      setError(result.message ?? t('Sidecar not ready'));
    }
    setChecking(false);
  };

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      const env = await runEnvironmentChecks(isTauri());
      if (!cancelled) setEnvChecks(env);

      for (let attempt = 0; attempt < 20; attempt += 1) {
        const result = await pollHealth();
        if (cancelled) return;
        if (result.ok) {
          setHealthy(true);
          setChecking(false);
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
      if (!cancelled) {
        setHealthy(false);
        setError(t('Sidecar not ready'));
        setChecking(false);
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [t]);

  useEffect(() => {
    onHealthyChange(healthy);
  }, [healthy, onHealthyChange]);

  const hasEnvWarnings = envChecks?.some((item) => item.tier === 'warn') ?? false;

  return (
    <div className="space-y-6 text-center">
      <div className="mx-auto h-14 w-14 rounded-2xl bg-neutral-900 text-white flex items-center justify-center text-xl font-bold">
        C
      </div>
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 tracking-tight">{t('Welcome to Clutch')}</h1>
        <p className="mt-2 text-sm text-neutral-500 max-w-md mx-auto leading-relaxed">
          {t('Local AI multi-agent orchestration for developers — supervise workflows, not black boxes.')}
        </p>
      </div>

      <div className="text-left max-w-md mx-auto rounded-xl border border-neutral-200 bg-neutral-50/80 p-4 text-[11px] text-neutral-600 space-y-2">
        <p className="font-semibold text-neutral-800">{t('Environment requirements')}</p>
        <p className="text-[10px] text-neutral-500 leading-relaxed">
          {t('✓ Met  ·  ⚠ Recommendation (you can continue)  ·  ℹ Informational only')}
        </p>
        {envChecks ? (
          <ul className="space-y-1.5">
            {envChecks.map((item) => (
              <EnvRequirementRow key={item.id} id={item.id} tier={item.tier} t={t} />
            ))}
          </ul>
        ) : (
          <p className="text-[10px] text-neutral-500 flex items-center gap-2">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            {t('Checking environment…')}
          </p>
        )}
        {hasEnvWarnings ? (
          <p className="text-[10px] text-amber-800 bg-amber-50 border border-amber-100 rounded-lg px-2.5 py-2">
            {t('Yellow items are recommendations only — not blockers. You can continue once Sidecar is ready.')}
          </p>
        ) : null}
      </div>

      <div className="flex flex-col items-center gap-3">
        {checking ? (
          <p className="text-xs text-neutral-500 flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            {t('Waiting for Clutch sidecar…')}
          </p>
        ) : healthy ? (
          <p className="text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
            {t('Sidecar ready')}
          </p>
        ) : (
          <div className="space-y-2">
            <p className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
              {error ?? t('Sidecar not ready')}
            </p>
            <p className="text-[10px] text-neutral-500">{t('See INSTALL.md §8 for troubleshooting')}</p>
            <button type="button" onClick={() => void check()} className={`${BTN_GHOST} text-[11px]`}>
              <RefreshCw className="h-3.5 w-3.5" />
              {t('Retry')}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
