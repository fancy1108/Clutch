import { useLanguage } from '../../LanguageContext';
import { PERMISSION_MODES, type PermissionMode } from '../../../services/permissionApi';
import { LegacyIcon } from '../../ui/LegacyIcon';

interface PermissionsStepProps {
  mode: PermissionMode;
  onModeChange: (mode: PermissionMode) => void;
}

export function PermissionsStep({ mode, onModeChange }: PermissionsStepProps) {
  const { t } = useLanguage();
  const resolved = mode === 'explore' ? 'ask' : mode;

  return (
    <div className="space-y-5">
      <div className="text-center">
        <h2 className="text-xl font-bold text-neutral-900">{t('Permission mode')}</h2>
        <p className="mt-2 text-sm text-neutral-500 max-w-md mx-auto leading-relaxed">
          {t('Choose how Clutch Agent may edit files and run tools. You can change this anytime in chat.')}
        </p>
      </div>

      <div className="space-y-2">
        {PERMISSION_MODES.map((item) => {
          const selected = item.id === resolved;
          const isDefault = item.id === 'auto_edit';
          return (
            <button
              key={item.id}
              type="button"
              data-testid={`onboarding-permission-${item.id}`}
              data-active={selected ? 'true' : 'false'}
              onClick={() => onModeChange(item.id)}
              className={`w-full rounded-xl border px-3 py-2.5 flex items-start gap-3 text-left transition-colors ${
                selected
                  ? 'border-primary/40 bg-primary/5 ring-1 ring-primary/20'
                  : 'border-neutral-200 bg-white hover:border-neutral-300 hover:bg-neutral-50/80'
              }`}
            >
              <LegacyIcon
                name={item.icon}
                className={`text-[18px] mt-0.5 flex-shrink-0 ${
                  selected ? 'text-primary' : 'text-neutral-400'
                }`}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p
                    className={`text-xs font-bold ${
                      selected ? 'text-neutral-900' : 'text-neutral-700'
                    }`}
                  >
                    {item.label}
                  </p>
                  {isDefault ? (
                    <span className="text-[9px] font-bold uppercase tracking-wide text-primary bg-white px-1.5 py-0.5 rounded border border-primary/30">
                      {t('Recommended default')}
                    </span>
                  ) : null}
                  {selected && !isDefault ? (
                    <span className="text-[9px] font-bold uppercase tracking-wide text-neutral-500 bg-neutral-100 px-1.5 py-0.5 rounded">
                      {t('Selected')}
                    </span>
                  ) : null}
                </div>
                <p className="text-[10px] text-neutral-500 mt-0.5 leading-snug">
                  {t(item.description)}
                </p>
              </div>
              {selected ? (
                <LegacyIcon name="check" className="text-[16px] text-primary mt-0.5 flex-shrink-0" />
              ) : null}
            </button>
          );
        })}
      </div>

      <p className="text-[11px] text-neutral-500 text-center max-w-md mx-auto leading-relaxed">
        {t('Permission onboarding footnote')}
      </p>
    </div>
  );
}
