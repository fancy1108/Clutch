import React from 'react';

export class AppErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error) {
    console.error('[Clutch] UI crashed:', error);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="h-screen flex flex-col items-center justify-center gap-3 bg-background text-on-surface px-6 text-center font-sans">
          <p className="text-sm font-semibold">Clutch UI encountered an error</p>
          <p className="text-xs text-on-surface-variant max-w-md break-words">
            {this.state.error.message}
          </p>
          <button
            type="button"
            className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-outline-variant/40 hover:bg-surface-container-high"
            onClick={() => window.location.reload()}
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
