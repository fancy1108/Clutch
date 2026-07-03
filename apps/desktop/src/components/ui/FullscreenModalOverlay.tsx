import { createPortal } from 'react-dom';
import type { ReactNode } from 'react';

interface FullscreenModalOverlayProps {
  children: ReactNode;
  onBackdropClick?: () => void;
}

/** Viewport-filling backdrop for nested settings dialogs (portals above SystemPreferencesModal). */
export function FullscreenModalOverlay({ children, onBackdropClick }: FullscreenModalOverlayProps) {
  if (typeof document === 'undefined') return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center animate-fade-in select-none"
      data-testid="fullscreen-modal-overlay"
    >
      <div
        className="absolute inset-0 bg-neutral-900/40 backdrop-blur-xs"
        aria-hidden={!onBackdropClick}
        onClick={onBackdropClick}
      />
      <div className="relative z-10 w-full max-h-[100dvh] flex items-center justify-center p-4 md:p-6 pointer-events-none">
        <div className="pointer-events-auto max-h-full w-full flex justify-center">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
