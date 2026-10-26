'use client';

import React from 'react';
import { useApp } from '@/lib/app-context';
import {
  LayoutDashboard,
  FileCheck2,
  CalendarCheck,
  ShieldCheck,
  FileText,
  Workflow,
  Sparkles,
  Sliders,
  History,
  AlertTriangle,
  Building2,
  Lock,
  Bell,
} from 'lucide-react';

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  rolesAllowed: string[];
  badge?: string;
  isDifferentiator?: boolean;
}

export const Sidebar: React.FC = () => {
  const { activeNavTab, setActiveNavTab, currentUser } = useApp();

  const navItems: NavItem[] = [
    {
      id: 'dashboard',
      label: 'Executive Dashboard',
      icon: <LayoutDashboard className="w-5 h-5" />,
      rolesAllowed: [
        'INSTITUTION_USER',
        'REGIONAL_OFFICER',
        'REGIONAL_DIRECTOR',
        'BUREAU_OFFICER',
        'BUREAU_HEAD',
        'SCRUTINY_MEMBER',
        'COMMITTEE_MEMBER',
        'SAC_SHC_MEMBER',
        'SUPER_ADMIN',
        'AUDITOR',
      ],
      badge: 'National',
    },
    {
      id: 'applications',
      label: 'Applications & Routing',
      icon: <FileCheck2 className="w-5 h-5" />,
      rolesAllowed: [
        'INSTITUTION_USER',
        'REGIONAL_OFFICER',
        'REGIONAL_DIRECTOR',
        'BUREAU_OFFICER',
        'BUREAU_HEAD',
        'SCRUTINY_MEMBER',
        'SAC_SHC_MEMBER',
        'SUPER_ADMIN',
        'AUDITOR',
      ],
      badge: 'APH Engine',
    },
    {
      id: 'case',
      label: 'Single Case Docket',
      icon: <FileText className="w-5 h-5 text-blossom-600" />,
      rolesAllowed: [
        'INSTITUTION_USER',
        'REGIONAL_OFFICER',
        'REGIONAL_DIRECTOR',
        'BUREAU_OFFICER',
        'BUREAU_HEAD',
        'SCRUTINY_MEMBER',
        'COMMITTEE_MEMBER',
        'SAC_SHC_MEMBER',
        'SUPER_ADMIN',
        'AUDITOR',
      ],
      badge: 'Docket',
    },
    {
      id: 'public-tracking',
      label: 'Public Status Portal',
      icon: <Building2 className="w-5 h-5 text-blue-600" />,
      rolesAllowed: [
        'INSTITUTION_USER',
        'REGIONAL_OFFICER',
        'REGIONAL_DIRECTOR',
        'BUREAU_OFFICER',
        'BUREAU_HEAD',
        'SCRUTINY_MEMBER',
        'COMMITTEE_MEMBER',
        'SAC_SHC_MEMBER',
        'SUPER_ADMIN',
        'AUDITOR',
      ],
      badge: 'DPDP Safe',
    },
    {
      id: 'evc',
      label: 'EVC Inspections Hub',
      icon: <CalendarCheck className="w-5 h-5" />,
      rolesAllowed: [
        'REGIONAL_OFFICER',
        'REGIONAL_DIRECTOR',
        'BUREAU_OFFICER',
        'BUREAU_HEAD',
        'COMMITTEE_MEMBER',
        'SUPER_ADMIN',
        'AUDITOR',
      ],
      badge: 'Smart Panel',
    },
    {
      id: 'compliance',
      label: 'Undertakings & Leases',
      icon: <ShieldCheck className="w-5 h-5" />,
      rolesAllowed: [
        'INSTITUTION_USER',
        'REGIONAL_OFFICER',
        'REGIONAL_DIRECTOR',
        'BUREAU_OFFICER',
        'BUREAU_HEAD',
        'SCRUTINY_MEMBER',
        'SUPER_ADMIN',
        'AUDITOR',
      ],
      badge: 'Expiry Clocks',
    },
    {
      id: 'notifications',
      label: 'Notification Center',
      icon: <Bell className="w-5 h-5 text-blossom-600" />,
      rolesAllowed: [
        'INSTITUTION_USER',
        'REGIONAL_OFFICER',
        'REGIONAL_DIRECTOR',
        'BUREAU_OFFICER',
        'BUREAU_HEAD',
        'SCRUTINY_MEMBER',
        'COMMITTEE_MEMBER',
        'SAC_SHC_MEMBER',
        'SUPER_ADMIN',
        'AUDITOR',
      ],
      badge: 'Real-Time',
    },
    // Signature Differentiators
    {
      id: 'next-best-action',
      label: 'Next-Best-Action Queue',
      icon: <Sparkles className="w-5 h-5 text-blossom-600" />,
      rolesAllowed: ['REGIONAL_OFFICER', 'REGIONAL_DIRECTOR', 'BUREAU_OFFICER', 'BUREAU_HEAD', 'SUPER_ADMIN'],
      isDifferentiator: true,
      badge: 'Risk-Ranked',
    },
    {
      id: 'aph-compiler',
      label: 'APH-to-Rules Compiler',
      icon: <Workflow className="w-5 h-5 text-blossom-600" />,
      rolesAllowed: ['BUREAU_OFFICER', 'BUREAU_HEAD', 'SUPER_ADMIN', 'AUDITOR'],
      isDifferentiator: true,
      badge: 'Provenance',
    },
    {
      id: 'what-if',
      label: 'What-If Simulation Lab',
      icon: <Sliders className="w-5 h-5 text-blossom-600" />,
      rolesAllowed: ['REGIONAL_OFFICER', 'REGIONAL_DIRECTOR', 'BUREAU_OFFICER', 'BUREAU_HEAD', 'SUPER_ADMIN'],
      isDifferentiator: true,
    },
    {
      id: 'audit',
      label: 'Hash-Chained Audit Trail',
      icon: <History className="w-5 h-5" />,
      rolesAllowed: [
        'REGIONAL_OFFICER',
        'REGIONAL_DIRECTOR',
        'BUREAU_OFFICER',
        'BUREAU_HEAD',
        'SCRUTINY_MEMBER',
        'SAC_SHC_MEMBER',
        'SUPER_ADMIN',
        'AUDITOR',
      ],
      badge: 'SHA-256',
    },
    {
      id: 'security-anomalies',
      label: 'Anomalies & Integrity',
      icon: <AlertTriangle className="w-5 h-5 text-roseState-700" />,
      rolesAllowed: [
        'REGIONAL_OFFICER',
        'REGIONAL_DIRECTOR',
        'BUREAU_OFFICER',
        'BUREAU_HEAD',
        'SUPER_ADMIN',
        'AUDITOR',
      ],
    },
  ];

  const visibleItems = navItems.filter((item) =>
    item.rolesAllowed.includes(currentUser.role)
  );

  return (
    <aside className="w-64 bg-white border-r border-ink-line flex flex-col h-screen sticky top-0 z-30 select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-ink-line bg-surface-white">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blossom-100 border border-blossom-300 flex items-center justify-center font-bold text-ink-strong shadow-soft">
            <Building2 className="w-6 h-6 text-blossom-600" />
          </div>
          <div>
            <div className="text-xs font-bold text-blossom-600 uppercase tracking-wider">AICTE National Portal</div>
            <div className="text-sm font-bold text-ink-strong leading-tight">Approval & Compliance</div>
          </div>
        </div>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 p-3 overflow-y-auto space-y-1">
        <div className="px-3 py-1.5 text-[11px] font-bold text-ink-muted uppercase tracking-wider">
          Main Workflows
        </div>
        {visibleItems.map((item) => {
          const isActive = activeNavTab === item.id;
          return (
            <button
              key={item.id}
              data-testid={`nav-${item.id}`}
              onClick={() => setActiveNavTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-blossom-100 text-ink-strong font-semibold shadow-soft border-l-4 border-blossom-600'
                  : 'text-ink hover:bg-slate-50 hover:text-ink-strong'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className={isActive ? 'text-blossom-600' : 'text-ink'}>
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    item.isDifferentiator
                      ? 'bg-blossom-300 text-ink-strong border border-blossom-600/30'
                      : 'bg-slate-100 text-ink-muted'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Authority Boundary Quick Legend */}
      <div className="p-3 border-t border-ink-line bg-slate-50/50">
        <div className="text-[11px] font-bold text-ink-muted uppercase tracking-wider mb-2 flex items-center gap-1.5">
          <Lock className="w-3.5 h-3.5 text-ink-slate" /> Authority Matrix
        </div>
        <div className="grid grid-cols-3 gap-1 text-[10px] text-center font-bold">
          <div className="bg-mint-100 text-mint-700 py-1 rounded border border-mint-700/20" title="Rules Engine Automates">
            AUTO
          </div>
          <div className="bg-blossom-100 text-ink py-1 rounded border border-blossom-300" title="LLM Drafts Only">
            SUGGEST
          </div>
          <div className="bg-ink text-ink-ivory py-1 rounded" title="Officer Reserve">
            HUMAN
          </div>
        </div>
      </div>

      {/* User Scope Footer */}
      <div className="p-3 border-t border-ink-line bg-surface-white">
        <div className="text-xs font-semibold text-ink-strong truncate">{currentUser.name}</div>
        <div className="text-[11px] text-ink-muted flex items-center justify-between mt-0.5">
          <span className="truncate">{currentUser.roleLabel}</span>
          <span className="bg-slate-100 text-ink px-1.5 py-0.5 rounded text-[10px] font-bold ml-1 shrink-0">
            {currentUser.regionCode}
          </span>
        </div>
        {currentUser.role === 'INSTITUTION_USER' && currentUser.institutionName && (
          <div className="text-[10px] text-ink-muted truncate mt-1 bg-amber-50 p-1.5 rounded border border-amber-200">
            <div className="font-semibold text-ink-strong truncate">{currentUser.institutionName}</div>
            {currentUser.institutionPid && (
              <div className="font-mono text-[9px] text-amber-800 mt-0.5">PID: {currentUser.institutionPid}</div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
};
