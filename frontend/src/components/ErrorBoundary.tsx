import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught React application error:', error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-[100dvh] w-full flex items-center justify-center p-6 bg-slate-50 dark:bg-[#0b0f19] text-slate-800 dark:text-slate-100">
          <div className="w-full max-w-md p-8 rounded-[32px] bg-white/95 dark:bg-[#111625]/95 backdrop-blur-2xl border border-slate-200/80 dark:border-white/10 shadow-2xl text-center space-y-5">
            <div className="w-14 h-14 rounded-2xl bg-amber-500/15 text-amber-600 dark:text-amber-400 flex items-center justify-center mx-auto shadow-xs">
              <AlertTriangle className="w-7 h-7" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                Something went wrong
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 leading-relaxed">
                An unexpected interface error occurred. You can reload the page to restore the application state.
              </p>
            </div>

            {this.state.error && (
              <div className="p-3 rounded-2xl bg-black/[0.03] dark:bg-black/40 border border-slate-200 dark:border-white/10 text-left">
                <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block mb-1">
                  Error Details
                </span>
                <p className="text-xs font-mono text-red-600 dark:text-red-400 break-words line-clamp-3">
                  {this.state.error.message || String(this.state.error)}
                </p>
              </div>
            )}

            <button
              type="button"
              onClick={this.handleReload}
              className="inline-flex items-center justify-center gap-2 w-full py-3 px-5 rounded-2xl text-xs font-semibold bg-blue-600 text-white hover:bg-blue-500 active:scale-98 transition-all shadow-md cursor-pointer"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Reload Application</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
