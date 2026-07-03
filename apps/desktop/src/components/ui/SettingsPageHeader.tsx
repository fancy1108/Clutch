import React from 'react';
import { LegacyIcon } from './LegacyIcon';

export type SettingsPageHeaderProps = {
  icon: string;
  title: string;
  description: string;
  descriptionSecondary?: string;
  actions?: React.ReactNode;
  className?: string;
  isModalStyle?: boolean;
};

export const SettingsPageHeader: React.FC<SettingsPageHeaderProps> = ({
  icon,
  title,
  description,
  descriptionSecondary,
  actions,
  className = '',
  isModalStyle = false,
}) => (
  <div
    className={`flex items-center justify-between border-b border-neutral-100 pb-5 ${isModalStyle ? 'mr-12' : ''} ${className}`}
  >
    <div className="min-w-0 text-left">
      <h2 className="text-base font-bold text-neutral-800 tracking-tight flex items-center gap-2">
        <LegacyIcon name={icon} className="text-neutral-500 text-[20px] shrink-0" />
        <span>{title}</span>
      </h2>
      <p className="text-[11.5px] text-neutral-400 mt-1 leading-relaxed">{description}</p>
      {descriptionSecondary ? (
        <p className="text-[10px] text-neutral-400 mt-1 leading-relaxed">{descriptionSecondary}</p>
      ) : null}
    </div>
    {actions ? <div className="flex items-center gap-2 flex-shrink-0">{actions}</div> : null}
  </div>
);

export const SettingsPageShell: React.FC<{
  children: React.ReactNode;
  className?: string;
  wide?: boolean;
}> = ({ children, className = '', wide = false }) => (
  <div className={`flex-1 flex flex-col overflow-hidden bg-white select-text ${className}`}>
    <div className="flex-1 overflow-y-auto">
      <div className={wide ? 'w-full p-8 pr-14 space-y-6' : 'max-w-4xl mx-auto w-full p-8 space-y-6'}>
        {children}
      </div>
    </div>
  </div>
);
