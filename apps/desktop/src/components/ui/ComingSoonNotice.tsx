import React from 'react';
import { useLanguage } from '../LanguageContext';
import { LegacyIcon } from './LegacyIcon';

type ComingSoonNoticeProps = {
  agentLabel?: string;
  featureLabel?: string;
  className?: string;
};

export const ComingSoonNotice: React.FC<ComingSoonNoticeProps> = ({
  agentLabel,
  featureLabel,
  className = '',
}) => {
  const { t } = useLanguage();
  const feature = featureLabel ?? t('This capability');
  const agent = agentLabel ?? t('this agent type');

  return (
    <div
      className={`flex items-start gap-2 px-3 py-2.5 rounded-lg bg-neutral-50 border border-neutral-200 text-neutral-700 ${className}`}
    >
      <LegacyIcon name="schedule" className="text-[14px] shrink-0 mt-0.5 text-neutral-500" />
      <p className="text-[10px] leading-relaxed">
        {t('{feature} management for {agent} is coming soon. Configure it in the CLI native environment for now.')
          .replace('{feature}', feature)
          .replace('{agent}', agent)}
      </p>
    </div>
  );
};
