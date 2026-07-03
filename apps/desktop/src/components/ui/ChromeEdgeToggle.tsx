import React from 'react';
import { LegacyIcon } from './LegacyIcon';

const TOGGLE_CLASS =
  'w-6 h-6 bg-white border border-neutral-300 rounded-full flex items-center justify-center z-[100] shadow-md hover:shadow-lg hover:bg-neutral-50 hover:border-neutral-450 transition-all cursor-pointer text-neutral-600 hover:text-neutral-900 duration-200 hover:scale-110 active:scale-95';

type ChromeEdgeToggleProps = {
  testId: string;
  icon: 'chevron_left' | 'chevron_right';
  title: string;
  onClick: () => void;
  className?: string;
  style?: React.CSSProperties;
};

export const ChromeEdgeToggle: React.FC<ChromeEdgeToggleProps> = ({
  testId,
  icon,
  title,
  onClick,
  className = '',
  style,
}) => (
  <button
    type="button"
    data-testid={testId}
    onClick={onClick}
    className={`${TOGGLE_CLASS} ${className}`.trim()}
    style={style}
    title={title}
    aria-label={title}
  >
    <LegacyIcon name={icon} className="text-[13px] font-bold" />
  </button>
);
