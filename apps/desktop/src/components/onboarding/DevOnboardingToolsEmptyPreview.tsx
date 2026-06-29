import { useState } from 'react';

import { useLanguage } from '../LanguageContext';
import { OnboardingLanguageToggle } from './OnboardingLanguageToggle';
import { OnboardingShell } from './OnboardingShell';
import { OnboardingStepper } from './OnboardingStepper';
import { ToolsStep } from './steps/ToolsStep';
import { BTN_GHOST, BTN_PRIMARY } from '../ui/buttonStyles';

/** Dev-only fullscreen preview: `http://localhost:3000/?dev_tools_empty=1` */
export function DevOnboardingToolsEmptyPreview() {
  const { t } = useLanguage();
  const [toolsReady, setToolsReady] = useState(false);

  const header = (
    <div className="flex items-center justify-between">
      <div className="w-24" />
      <OnboardingStepper current="tools" />
      <OnboardingLanguageToggle />
    </div>
  );

  const footer = (
    <div className="flex items-center justify-between gap-3">
      <button type="button" className={BTN_GHOST} disabled>
        {t('Back')}
      </button>
      <button type="button" className={`${BTN_PRIMARY} opacity-50 cursor-not-allowed`} disabled>
        {t('Continue')}
      </button>
    </div>
  );

  const footerNote = !toolsReady ? (
    <p className="text-[10px] text-neutral-500 text-center">{t('Onboarding model or tools required')}</p>
  ) : null;

  return (
    <OnboardingShell
      testId="onboarding-tools-empty-preview"
      header={header}
      footer={footer}
      footerNote={footerNote}
    >
      <ToolsStep
        debugForceEmpty
        modelReady={false}
        toolsReady={toolsReady}
        onToolsReady={setToolsReady}
        onAgentProvisioned={() => undefined}
        onSkip={() => undefined}
      />
    </OnboardingShell>
  );
}
