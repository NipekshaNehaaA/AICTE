'use client';

import React from 'react';
import { useApp } from '@/lib/app-context';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { StatutoryBanner } from '@/components/common/StatutoryBanner';
import { ComplianceCopilotDrawer } from '@/components/copilot/ComplianceCopilotDrawer';
import { LoginPage } from '@/components/auth/LoginPage';

import { SystemLoadingPage } from '@/components/loading/SystemLoadingPage';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isSystemLoading, setIsSystemLoading, isDemoMode, evaluatorMode, toggleEvaluatorMode } = useApp();
  const isEvalActive = evaluatorMode || isDemoMode;

  // Step 1: System Boot & Initialization Loading Page
  if (isSystemLoading) {
    return <SystemLoadingPage onComplete={() => setIsSystemLoading(false)} />;
  }

  // Step 2: Standalone Government Login & Persona Selection Page
  if (!isAuthenticated) {
    return <LoginPage />;
  }

  // When authenticated, render full application shell
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {isEvalActive && (
          <div
            id="evaluator-mode-banner"
            className="bg-amber-500 text-slate-950 px-6 py-1.5 text-xs font-bold flex items-center justify-between tracking-wide shadow-sm border-b border-amber-600 shrink-0"
          >
            <div className="flex items-center gap-2">
              <span className="px-1.5 py-0.5 bg-black text-amber-300 rounded text-[10px] font-black uppercase tracking-wider">
                EVALUATOR MODE ACTIVE
              </span>
              <span>
                Evaluation Sandbox Active • 1-Click Personas & Time Travel Enabled • Synthetic Evaluation Docket
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-[11px] font-mono font-medium opacity-90 hidden md:inline">
                EVALUATOR_MODE=true
              </span>
              <button
                onClick={() => toggleEvaluatorMode(false)}
                className="px-2 py-0.5 bg-slate-900 hover:bg-black text-amber-300 rounded text-[10px] font-bold transition-all shadow-xs"
                title="Deactivate Evaluator Mode and switch to standard Production Portal"
              >
                Exit Evaluator Mode
              </button>
            </div>
          </div>
        )}
        <TopBar />
        <StatutoryBanner />
        <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
        </main>
      </div>

      {/* AICTE Institutional Compliance & APH Copilot (Global) */}
      <ComplianceCopilotDrawer />
    </div>
  );
};
