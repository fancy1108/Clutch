import React from 'react';
import { LegacyIcon } from './ui/LegacyIcon';

/** Shared chip chrome for footer status items. */
export const FOOTER_CHIP_CLASS =
  'flex items-center gap-1 min-w-0 px-1.5 py-1 rounded font-medium whitespace-nowrap';
export const FOOTER_CHIP_BUTTON_CLASS =
  `${FOOTER_CHIP_CLASS} hover:bg-surface-container-low hover:text-on-surface transition-colors cursor-pointer`;

/** Hide idle (em-dash) chips once the footer container gets tight. */
export function footerIdleHiddenClass(idle: boolean): string {
  return idle ? '@max-[42rem]/footer:hidden' : '';
}

export function FooterFieldLabel({ children }: { children: React.ReactNode }) {
  return <span className="shrink-0 @max-[48rem]/footer:hidden">{children}:&nbsp;</span>;
}

export function FooterFieldValue({
  children,
  title,
}: {
  children: React.ReactNode;
  title?: string;
}) {
  const tip = title ?? (typeof children === 'string' ? children : undefined);
  return (
    <span
      className="min-w-0 truncate max-w-[7rem] @min-[40rem]/footer:max-w-[10rem] @min-[56rem]/footer:max-w-[14rem] @max-[28rem]/footer:hidden"
      title={tip}
    >
      {children}
    </span>
  );
}

export function FooterFieldChevron() {
  return (
    <LegacyIcon
      name="keyboard_arrow_down"
      className="text-[13px] shrink-0 @max-[36rem]/footer:hidden"
    />
  );
}

export function FooterMenuPanel({
  children,
  testId,
}: {
  children: React.ReactNode;
  testId?: string;
}) {
  return (
    <div
      data-testid={testId}
      className="absolute bottom-full left-0 mb-1 min-w-[240px] max-h-48 overflow-y-auto bg-surface-bright border border-outline-variant rounded-lg shadow-lg py-1 z-[60]"
    >
      {children}
    </div>
  );
}

export function FooterMenuItem({
  selected,
  onClick,
  children,
  testId,
  actions,
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
  testId?: string;
  actions?: React.ReactNode;
}) {
  const rowClass =
    'w-full flex items-center gap-2 px-3 py-2 text-[11px] hover:bg-surface-container-low text-left';
  const check = (
    <LegacyIcon
      name="check"
      className={`text-[14px] w-4 flex-shrink-0 ${selected ? 'text-primary opacity-100' : 'opacity-0'}`}
    />
  );
  const label = (
    <span className={`truncate min-w-0 ${selected ? 'text-primary font-bold' : 'text-on-surface'}`}>
      {children}
    </span>
  );
  if (!actions) {
    return (
      <button type="button" data-testid={testId} onClick={onClick} className={rowClass}>
        {check}
        {label}
      </button>
    );
  }
  return (
    <div className={`${rowClass} group`}>
      <button
        type="button"
        data-testid={testId}
        onClick={onClick}
        className="flex-1 min-w-0 flex items-center gap-2 text-left"
      >
        {check}
        {label}
      </button>
      <div className="flex items-center gap-0.5 shrink-0">{actions}</div>
    </div>
  );
}

export function FooterMenuRowIcon({
  name,
  label,
  onClick,
  testId,
  danger,
}: {
  name: string;
  label: string;
  onClick: () => void;
  testId?: string;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      data-testid={testId}
      title={label}
      aria-label={label}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className={`p-1 rounded transition-colors cursor-pointer ${
        danger
          ? 'text-on-surface-variant hover:text-rose-700 hover:bg-rose-50'
          : 'text-on-surface-variant hover:text-emerald-700 hover:bg-emerald-50'
      }`}
    >
      <LegacyIcon name={name} className="text-[14px]" />
    </button>
  );
}

export function FooterMenuSection({ label }: { label: string }) {
  return (
    <div className="px-3 pt-2 pb-1 text-[9px] font-bold uppercase tracking-wider text-on-surface-variant/80">
      {label}
    </div>
  );
}

export function FooterMenuAction({
  onClick,
  children,
  testId,
  placement = 'top',
}: {
  onClick: () => void;
  children: React.ReactNode;
  testId?: string;
  /** Manage actions sit at the top of footer menus by default. */
  placement?: 'top' | 'bottom';
}) {
  const dividerClass =
    placement === 'top'
      ? 'border-b border-outline-variant/40'
      : 'border-t border-outline-variant/40';
  return (
    <button
      type="button"
      data-testid={testId}
      onClick={onClick}
      className={`w-full text-left px-3 py-2 pl-9 text-[11px] text-on-surface-variant hover:bg-surface-container-low ${dividerClass}`}
    >
      {children}
    </button>
  );
}
