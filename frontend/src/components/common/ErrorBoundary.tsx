'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, ShieldAlert } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an unhandled exception:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="p-8 m-4 rounded-2xl bg-white border border-rose-200 shadow-sm flex flex-col items-center justify-center text-center animate-fade-in">
          <div className="w-14 h-14 rounded-2xl bg-rose-50 border border-rose-100 flex items-center justify-center mb-4 text-rose-600 shadow-inner">
            <ShieldAlert className="w-7 h-7" />
          </div>
          <h2 className="text-lg font-bold text-slate-900 mb-1">
            Application View Temporarily Interrupted
          </h2>
          <p className="text-xs text-slate-500 max-w-md mb-4">
            An unexpected error occurred while rendering this view. Your session and data are secure.
          </p>

          {this.state.error && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 max-w-lg w-full mb-6 text-left">
              <div className="flex items-center gap-1.5 text-rose-700 font-bold text-xs mb-1">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Error Diagnostic:</span>
              </div>
              <p className="text-[11px] font-mono text-slate-700 break-words">
                {this.state.error.message || 'Unknown runtime error'}
              </p>
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              onClick={this.handleReset}
              className="px-4 py-2 bg-blossom-600 hover:bg-blossom-700 text-white rounded-xl text-xs font-bold transition-all shadow-sm flex items-center gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Reload View
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-all border border-slate-200"
            >
              Refresh Application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
