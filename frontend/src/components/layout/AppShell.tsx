'use client';

import React from 'react';
import { useApp } from '@/lib/app-context';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { StatutoryBanner } from '@/components/common/StatutoryBanner';
import { ComplianceCopilotDrawer } from '@/components/copilot/ComplianceCopilotDrawer';
import { LoginPage } from '@/components/auth/LoginPage';

import { SystemLoadingPage } from '@/components/loading/SystemLoadingPage';

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isSystemLoading, setIsSystemLoading } = useApp();

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
        <TopBar />
        <StatutoryBanner />
        <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
          {children}
        </main>
      </div>

      {/* AICTE Institutional Compliance & APH Copilot (Global) */}
      <ComplianceCopilotDrawer />
    </div>
  );
};
