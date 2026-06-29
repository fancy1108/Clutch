export type OnboardingStepId =
  | 'welcome'
  | 'workspace'
  | 'models'
  | 'tools'
  | 'flowGuide'
  | 'permissions'
  | 'ready';

export const STEPPER_STEPS: OnboardingStepId[] = [
  'workspace',
  'models',
  'tools',
  'flowGuide',
  'permissions',
  'ready',
];

interface OnboardingStepperProps {
  current: OnboardingStepId;
}

export function OnboardingStepper({ current }: OnboardingStepperProps) {
  const activeIndex = STEPPER_STEPS.indexOf(current);

  return (
    <div className="flex items-center justify-center gap-2" data-testid="onboarding-stepper">
      {STEPPER_STEPS.map((step, index) => {
        const filled = activeIndex >= 0 && index <= activeIndex;
        return (
          <span
            key={step}
            data-testid={`onboarding-step-dot-${step}`}
            className={`h-2 w-2 rounded-full transition-colors ${
              filled ? 'bg-neutral-900' : 'bg-neutral-300'
            }`}
            aria-hidden
          />
        );
      })}
    </div>
  );
}
