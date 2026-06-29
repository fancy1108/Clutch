import type { ReactNode } from 'react';

interface OnboardingShellProps {
  testId?: string;
  header: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  footerNote?: ReactNode;
}

/** Fixed top/bottom chrome; scrollable body with viewport safe margins. */
export function OnboardingShell({ testId, header, children, footer, footerNote }: OnboardingShellProps) {
  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-neutral-100/90 p-4 backdrop-blur-sm font-sans sm:p-6">
      <div
        data-testid={testId}
        className="flex max-h-[calc(100dvh-2rem)] w-full max-w-xl flex-col overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-xl sm:max-h-[calc(100dvh-3rem)]"
      >
        <header className="shrink-0 px-6 pb-3 pt-5">{header}</header>

        <div className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto overscroll-contain px-6 py-4">
          {children}
        </div>

        {footerNote ? (
          <div className="shrink-0 border-t border-neutral-100 bg-white px-6 py-2.5">{footerNote}</div>
        ) : null}

        {footer ? (
          <footer className="shrink-0 border-t border-neutral-100 bg-neutral-50/50 px-6 py-4">{footer}</footer>
        ) : null}
      </div>
    </div>
  );
}
