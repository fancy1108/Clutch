import { useCallback, useEffect, useMemo, useState } from 'react';

import { useLanguage } from '../LanguageContext';
import { completeOnboarding } from '../../services/onboardingApi';
import { fetchModelsConfig, mapModelConfigToUi } from '../../services/modelsApi';
import type { WorkspaceInfo } from '../../services/workspaceApi';
import { BTN_GHOST, BTN_PRIMARY } from '../ui/buttonStyles';
import { OnboardingLanguageToggle } from './OnboardingLanguageToggle';
import { OnboardingShell } from './OnboardingShell';
import { OnboardingStepper, type OnboardingStepId } from './OnboardingStepper';
import { FlowGuideStep } from './steps/FlowGuideStep';
import { ModelsStep } from './steps/ModelsStep';
import { PermissionsStep } from './steps/PermissionsStep';
import { ReadyStep } from './steps/ReadyStep';
import { ToolsStep } from './steps/ToolsStep';
import { WelcomeStep } from './steps/WelcomeStep';
import { WorkspaceStep } from './steps/WorkspaceStep';

const STEP_ORDER: OnboardingStepId[] = [
  'welcome',
  'workspace',
  'models',
  'tools',
  'flowGuide',
  'permissions',
  'ready',
];

export interface OnboardingCompleteResult {
  agentId: string | null;
}

interface OnboardingWizardProps {
  onComplete: (result: OnboardingCompleteResult) => void;
}

export function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const { t } = useLanguage();
  const [step, setStep] = useState<OnboardingStepId>('welcome');
  const [workspace, setWorkspace] = useState<WorkspaceInfo | null>(null);
  const [modelReady, setModelReady] = useState(false);
  const [toolsReady, setToolsReady] = useState(false);
  const [welcomeHealthy, setWelcomeHealthy] = useState(false);
  const [provisionedAgentId, setProvisionedAgentId] = useState<string | null>(null);
  const [defaultAgentName, setDefaultAgentName] = useState<string | null>(null);
  const [activeModelLabel, setActiveModelLabel] = useState('—');
  const [launching, setLaunching] = useState(false);
  const [launchError, setLaunchError] = useState<string | null>(null);

  const stepIndex = STEP_ORDER.indexOf(step);
  const showStepper = step !== 'welcome';

  const refreshActiveModelLabel = useCallback(async () => {
    try {
      const config = await fetchModelsConfig();
      const mapped = mapModelConfigToUi(config);
      const active = mapped.models.find((m) => m.id === mapped.activeModelId);
      setActiveModelLabel(active?.name ?? '—');
    } catch {
      setActiveModelLabel('—');
    }
  }, []);

  useEffect(() => {
    if (step === 'ready') {
      void refreshActiveModelLabel();
    }
  }, [step, refreshActiveModelLabel, modelReady]);

  const canContinue = useMemo(() => {
    switch (step) {
      case 'welcome':
        return welcomeHealthy;
      case 'workspace':
        return Boolean(workspace);
      case 'models':
        return true;
      case 'tools':
        return modelReady || toolsReady;
      case 'flowGuide':
      case 'permissions':
        return true;
      case 'ready':
        return true;
      default:
        return false;
    }
  }, [step, workspace, modelReady, toolsReady, welcomeHealthy]);

  const goBack = () => {
    if (stepIndex <= 0) return;
    setStep(STEP_ORDER[stepIndex - 1]);
  };

  const goNext = () => {
    if (stepIndex >= STEP_ORDER.length - 1) return;
    if (!canContinue && step !== 'welcome') return;
    setStep(STEP_ORDER[stepIndex + 1]);
  };

  const handleLaunch = async () => {
    setLaunching(true);
    setLaunchError(null);
    try {
      await completeOnboarding();
      if (provisionedAgentId) {
        localStorage.setItem('clutch_active_agent_id', provisionedAgentId);
      }
      onComplete({ agentId: provisionedAgentId });
    } catch (err) {
      setLaunchError(err instanceof Error ? err.message : t('Could not finish onboarding'));
      setLaunching(false);
    }
  };

  const header = (
    <div className="flex items-center justify-between">
      <div className="w-24" />
      {showStepper ? <OnboardingStepper current={step} /> : <div className="h-2 w-24" />}
      <OnboardingLanguageToggle />
    </div>
  );

  const footerNote =
    step === 'tools' && !canContinue ? (
      <p className="text-[10px] text-neutral-500 text-center">{t('Onboarding model or tools required')}</p>
    ) : launchError ? (
      <p className="text-xs text-rose-700 text-center">{launchError}</p>
    ) : null;

  const footer =
    step === 'welcome' ? (
      <div className="flex justify-center">
        <button
          type="button"
          data-testid="onboarding-welcome-continue"
          disabled={!welcomeHealthy}
          onClick={goNext}
          className={`${BTN_PRIMARY} min-w-[8rem]`}
        >
          {t('Continue')}
        </button>
      </div>
    ) : step === 'ready' ? (
      <button
        type="button"
        data-testid="onboarding-launch"
        disabled={launching}
        onClick={() => void handleLaunch()}
        className={`${BTN_PRIMARY} w-full`}
      >
        {launching ? t('Launching…') : t('Launch workspace →')}
      </button>
    ) : (
      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          data-testid="onboarding-back"
          onClick={goBack}
          disabled={stepIndex <= 1}
          className={BTN_GHOST}
        >
          {t('Back')}
        </button>
        <button
          type="button"
          data-testid="onboarding-continue"
          disabled={!canContinue}
          onClick={goNext}
          className={BTN_PRIMARY}
        >
          {t('Continue')}
        </button>
      </div>
    );

  return (
    <OnboardingShell testId="onboarding-wizard" header={header} footer={footer} footerNote={footerNote}>
      {step === 'welcome' && <WelcomeStep onHealthyChange={setWelcomeHealthy} />}
      {step === 'workspace' && (
        <WorkspaceStep workspace={workspace} onWorkspaceSelected={setWorkspace} />
      )}
      {step === 'models' && (
        <ModelsStep modelReady={modelReady} onModelReady={setModelReady} onSkip={goNext} />
      )}
      {step === 'tools' && (
        <ToolsStep
          modelReady={modelReady}
          toolsReady={toolsReady}
          onToolsReady={setToolsReady}
          onAgentProvisioned={(id, name) => {
            setProvisionedAgentId(id);
            setDefaultAgentName(name);
          }}
          onSkip={goNext}
        />
      )}
      {step === 'flowGuide' && <FlowGuideStep />}
      {step === 'permissions' && <PermissionsStep />}
      {step === 'ready' && (
        <ReadyStep
          workspace={workspace}
          modelReady={modelReady}
          toolsReady={toolsReady}
          activeModelLabel={activeModelLabel}
          defaultAgentName={defaultAgentName}
        />
      )}
    </OnboardingShell>
  );
}
