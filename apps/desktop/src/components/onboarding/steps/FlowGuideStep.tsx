import { ChevronRight, MapPin, Settings2 } from 'lucide-react';

import { useLanguage } from '../../LanguageContext';

const SETUP_STEP_KEYS = [
  'Create a new workflow (or pick a built-in template)',
  'Drag nodes onto the canvas and connect them',
  'Bind an AI Agent to each task node, then Save',
  'In chat: Workflow menu → select your flow → send a task',
] as const;

export function FlowGuideStep() {
  const { t } = useLanguage();

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-xl font-bold text-neutral-900">{t('Workflows (Flow)')}</h2>
        <p className="mt-2 text-sm text-neutral-500">{t('Chain multiple Agents with a visual workflow.')}</p>
      </div>

      <div className="rounded-xl border border-neutral-200 bg-neutral-50/60 p-4 space-y-2">
        <p className="text-[10px] font-bold uppercase tracking-wide text-neutral-500 flex items-center gap-1.5">
          <MapPin className="h-3.5 w-3.5" aria-hidden />
          {t('Where to find it')}
        </p>
        <div
          className="flex items-center justify-center gap-2 flex-wrap"
          data-testid="onboarding-flow-entry"
        >
          <span className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs font-semibold text-neutral-800">
            <Settings2 className="h-3.5 w-3.5 text-neutral-500" aria-hidden />
            {t('Settings')}
          </span>
          <ChevronRight className="h-4 w-4 text-neutral-300" aria-hidden />
          <span className="inline-flex items-center rounded-lg border border-neutral-900 bg-neutral-900 px-3 py-2 text-xs font-semibold text-white">
            {t('Workflows SOP')}
          </span>
        </div>
      </div>

      <div className="rounded-xl border border-neutral-200 p-4 space-y-3 text-left">
        <p className="text-[10px] font-bold uppercase tracking-wide text-neutral-500">
          {t('Quick setup')}
        </p>
        <ol className="space-y-2.5">
          {SETUP_STEP_KEYS.map((key, index) => (
            <li key={key} className="flex items-start gap-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-neutral-900 text-[11px] font-bold text-white">
                {index + 1}
              </span>
              <span className="text-xs text-neutral-700 leading-relaxed pt-0.5">{t(key)}</span>
            </li>
          ))}
        </ol>
      </div>

      <p className="text-[10px] text-neutral-400 text-center">
        {t('Single-Agent chat does not need a Flow.')}
      </p>
    </div>
  );
}
