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
  const {
    isAuthenticated,
    isSystemLoading,
    setIsSystemLoading,
    workspace,
    setWorkspace,
    sandboxOverride,
  } = useApp();

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
        {workspace === 'sandbox' ? (
          <div
            id="sandbox-workspace-banner"
            data-testid="banner-sandbox-workspace"
            className="bg-amber-500 text-slate-950 px-6 py-1.5 text-xs font-bold flex flex-wrap items-center justify-between tracking-wide shadow-sm border-b border-amber-600 shrink-0"
          >
            <div className="flex items-center gap-2">
              <span className="px-1.5 py-0.5 bg-black text-amber-300 rounded text-[10px] font-black uppercase tracking-wider">
                SANDBOX WORKSPACE (aicte_sandbox.db)
              </span>
              <span>
                Synthetic Data Active • Time Travel &amp; Demo Scripts Enabled • {sandboxOverride?.override_email || sandboxOverride?.override_whatsapp ? (
                  <span className="underline font-bold">Messages sent to: {sandboxOverride.override_email || sandboxOverride.override_whatsapp}</span>
                ) : (
                  <span>Synthetic addresses (messages skipped unless override set)</span>
                )}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-[11px] font-mono font-medium opacity-90 hidden md:inline">
                ws=sandbox
              </span>
              <button
                type="button"
                data-testid="btn-switch-to-live"
                onClick={() => setWorkspace('live')}
                className="px-2.5 py-0.5 bg-slate-900 hover:bg-black text-amber-300 rounded text-[10px] font-bold transition-all shadow-xs"
                title="Switch to clean Live production workspace"
              >
                Switch to Live Workspace →
              </button>
            </div>
          </div>
        ) : (
          <div
            id="live-workspace-banner"
            data-testid="banner-live-workspace"
            className="bg-emerald-700 text-white px-6 py-1 text-xs font-bold flex items-center justify-between tracking-wide shadow-sm border-b border-emerald-800 shrink-0"
          >
            <div className="flex items-center gap-2">
              <span className="px-1.5 py-0.5 bg-white text-emerald-800 rounded text-[10px] font-black uppercase tracking-wider">
                LIVE PRODUCTION (aicte_live.db)
              </span>
              <span>Strict Regulatory Ledger • Hardware TOTP MFA Required</span>
            </div>
            <button
              type="button"
              data-testid="btn-switch-to-sandbox"
              onClick={() => setWorkspace('sandbox')}
              className="px-2 py-0.5 bg-emerald-900 hover:bg-emerald-950 text-emerald-100 rounded text-[10px] font-bold transition-all"
              title="Switch to Demo Sandbox workspace"
            >
              Switch to Sandbox →
            </button>
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
