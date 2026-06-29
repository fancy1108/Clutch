import { useLanguage } from '../../LanguageContext';
import { PERMISSION_MODES } from '../../../services/permissionApi';
import { LegacyIcon } from '../../ui/LegacyIcon';

export function PermissionsStep() {
  const { t } = useLanguage();

  return (
    <div className="space-y-5">
      <div className="text-center">
        <h2 className="text-xl font-bold text-neutral-900">{t('Permission mode')}</h2>
        <p className="mt-2 text-sm text-neutral-500 max-w-md mx-auto leading-relaxed">
          {t('Only Ask before changes is active today. Other modes are still in development.')}
        </p>
      </div>

      <div className="space-y-2">
        {PERMISSION_MODES.map((mode) => {
          const isDefault = mode.id === 'ask';
          return (
            <div
              key={mode.id}
              aria-disabled="true"
              data-testid={`onboarding-permission-${mode.id}`}
              data-active={isDefault ? 'true' : 'false'}
              className={`rounded-xl border px-3 py-2.5 flex items-start gap-3 pointer-events-none select-none ${
                isDefault
                  ? 'border-primary/40 bg-primary/5 ring-1 ring-primary/20'
                  : 'border-neutral-200 bg-neutral-50/60 opacity-75'
              }`}
            >
              <LegacyIcon
                name={mode.icon}
                className={`text-[18px] mt-0.5 ${isDefault ? 'text-primary' : 'text-neutral-400'}`}
              />
              <div className="text-left flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className={`text-xs font-bold ${isDefault ? 'text-neutral-900' : 'text-neutral-500'}`}>
                    {t(mode.label)}
                  </p>
                  {isDefault ? (
                    <span className="text-[9px] font-bold uppercase tracking-wide text-primary bg-white px-1.5 py-0.5 rounded border border-primary/30">
                      {t('Current default')}
                    </span>
                  ) : (
                    <span className="text-[9px] font-medium text-neutral-400 uppercase tracking-wide">
                      {t('In development')}
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-neutral-500 mt-0.5">{t(mode.description)}</p>
              </div>
            </div>
          );
        })}
      </div>

      <p className="text-[11px] text-neutral-500 text-center max-w-md mx-auto leading-relaxed">
        {t('Permission onboarding footnote')}
      </p>
    </div>
  );
}
