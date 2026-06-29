import React from 'react';
import { useLanguage } from '../LanguageContext';
import { LegacyIcon } from './LegacyIcon';

type UnderDevelopmentNoticeProps = {
  variant?: 'banner' | 'compact';
  className?: string;
};

export const UnderDevelopmentNotice: React.FC<UnderDevelopmentNoticeProps> = ({
  variant = 'banner',
  className = '',
}) => {
  const { t } = useLanguage();

  if (variant === 'compact') {
    return (
      <div
        className={`flex items-start gap-2 px-3 py-2 rounded-lg bg-amber-50/90 border border-amber-200/70 text-amber-900 ${className}`}
      >
        <LegacyIcon name="construction" className="text-[14px] shrink-0 mt-0.5 text-amber-700" />
        <p className="text-[10px] leading-relaxed font-medium">{t('Feature under active development')}</p>
      </div>
    );
  }

  return (
    <div
      className={`flex items-center gap-2 px-3 py-2.5 rounded-xl bg-amber-50/90 border border-amber-200/70 text-amber-900 ${className}`}
    >
      <LegacyIcon name="construction" className="text-[16px] shrink-0 text-amber-700" />
      <p className="text-[11px] font-semibold leading-snug">{t('Feature under active development')}</p>
    </div>
  );
};
