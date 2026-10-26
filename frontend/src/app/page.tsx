'use client';

import React from 'react';
import { useApp } from '@/lib/app-context';
import { ApplicationsView } from '@/components/workflow/ApplicationsView';
import { EVCView } from '@/components/evc/EVCView';
import { ComplianceView } from '@/components/compliance/ComplianceView';
import { NextBestActionQueueView } from '@/components/differentiators/NextBestActionQueueView';
import { APHCompilerView } from '@/components/differentiators/APHCompilerView';
import { WhatIfSimulatorView } from '@/components/differentiators/WhatIfSimulatorView';
import { SecurityAnomaliesView } from '@/components/differentiators/SecurityAnomaliesView';
import { AuditLedgerView } from '@/components/audit/AuditLedgerView';
import { NotificationCenterView } from '@/components/notifications/NotificationCenterView';
import { StakeholderTrackingView } from '@/components/dashboard/StakeholderTrackingView';
import { OpeningExecutiveDashboard } from '@/components/dashboard/OpeningExecutiveDashboard';
import { CasePageView } from '@/components/case/CasePageView';
import { PublicTrackingView } from '@/components/tracking/PublicTrackingView';

export default function HomePage() {
  const { activeNavTab, currentUser } = useApp();

  // Dynamic Navigation Views
  if (activeNavTab === 'case') return <CasePageView />;
  if (activeNavTab === 'public-tracking') return <PublicTrackingView />;
  if (activeNavTab === 'applications') return <ApplicationsView />;
  if (activeNavTab === 'evc') return <EVCView />;
  if (activeNavTab === 'compliance') return <ComplianceView />;
  if (activeNavTab === 'notifications') return <NotificationCenterView />;
  if (activeNavTab === 'next-best-action') return <NextBestActionQueueView />;
  if (activeNavTab === 'aph-compiler') return <APHCompilerView />;
  if (activeNavTab === 'what-if') return <WhatIfSimulatorView />;
  if (activeNavTab === 'audit') return <AuditLedgerView />;
  if (activeNavTab === 'security-anomalies') return <SecurityAnomaliesView />;

  // Institution User landing: Land on their own institution dashboard, not national command center
  if (currentUser.role === 'INSTITUTION_USER') {
    return (
      <div className="space-y-6 animate-fade-in pb-12">
        <StakeholderTrackingView defaultTab="INSTITUTION_TRACKER" />
      </div>
    );
  }

  // Default: Grand Opening Executive Dashboard + Stakeholder Tracking Workspaces
  return (
    <div className="space-y-8 animate-fade-in pb-12">
      {/* 1. Grand Opening National Command & Control Dashboard */}
      <OpeningExecutiveDashboard />

      {/* 2. Stakeholder Operational Workspaces & Tracking */}
      <div className="pt-4 border-t border-ink-line">
        <div className="mb-4">
          <h2 className="text-base font-bold text-ink-strong flex items-center gap-2">
            <span>Stakeholder Operational Consoles & Worklists</span>
            <span className="text-[10px] bg-slate-100 text-ink-muted px-2 py-0.5 rounded font-mono font-medium">
              Role-Filtered
            </span>
          </h2>
          <p className="text-xs text-ink-muted mt-0.5">
            Switch between assigned official queues, institutional real-time application tracker, committee conflict-declared evaluation desks, and public citizen tracking.
          </p>
        </div>
        <StakeholderTrackingView />
      </div>
    </div>
  );
}
