import React from 'react';

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
      className="absolute bottom-full left-0 mb-1 min-w-[220px] max-h-48 overflow-y-auto bg-surface-bright border border-outline-variant rounded-lg shadow-lg py-1 z-[60]"
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
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
  testId?: string;
}) {
  return (
    <button
      type="button"
      data-testid={testId}
      onClick={onClick}
      className="w-full flex items-center gap-2 px-3 py-2 text-[11px] hover:bg-surface-container-low text-left"
    >
      <span
        className={`material-symbols-outlined text-[14px] w-4 flex-shrink-0 ${
          selected ? 'text-primary opacity-100' : 'opacity-0'
        }`}
      >
        check
      </span>
      <span className={`truncate ${selected ? 'text-primary font-bold' : 'text-on-surface'}`}>
        {children}
      </span>
    </button>
  );
}

export function FooterMenuAction({
  onClick,
  children,
  testId,
}: {
  onClick: () => void;
  children: React.ReactNode;
  testId?: string;
}) {
  return (
    <button
      type="button"
      data-testid={testId}
      onClick={onClick}
      className="w-full text-left px-3 py-2 pl-9 text-[11px] text-on-surface-variant border-t border-outline-variant/40 hover:bg-surface-container-low"
    >
      {children}
    </button>
  );
}
