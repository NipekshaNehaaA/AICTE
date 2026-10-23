'use client';

import React, { useState } from 'react';
import { useApp, SAMPLE_REGIONS } from '@/lib/app-context';
import {
  FileText,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Flame,
  Calendar,
  Building,
  TrendingUp,
  ShieldCheck,
  ArrowUpRight,
  Sparkles,
  Layers,
  Sliders,
  FileCheck2,
  Scale,
  Bot,
  ExternalLink,
  ChevronRight,
  Filter,
  Users,
  AlertCircle,
  HelpCircle,
  ArrowRight,
  Landmark,
  ShieldAlert,
} from 'lucide-react';

export const OpeningExecutiveDashboard: React.FC = () => {
  const {
    currentUser,
    currentRegion,
    setRegionByCode,
    virtualDate,
    virtualDaysOffset,
    setActiveNavTab,
  } = useApp();

  const [selectedPipelineFilter, setSelectedPipelineFilter] = useState<string>('ALL');

  // Simulated Macro Metrics across Regions
  const regionalMetrics = [
    { code: 'SWRO', name: 'South-Western (Bengaluru)', cases: 42, onTrack: 88, overdue: 2, avgDays: 4.8, evcNeeded: 12 },
    { code: 'WRO', name: 'Western (Mumbai)', cases: 54, onTrack: 85, overdue: 4, avgDays: 5.6, evcNeeded: 18 },
    { code: 'SRO', name: 'Southern (Chennai)', cases: 38, onTrack: 92, overdue: 1, avgDays: 4.2, evcNeeded: 9 },
    { code: 'NRO', name: 'Northern (Kanpur)', cases: 35, onTrack: 86, overdue: 3, avgDays: 5.1, evcNeeded: 11 },
    { code: 'NWRO', name: 'North-Western (Chandigarh)', cases: 28, onTrack: 93, overdue: 1, avgDays: 3.9, evcNeeded: 7 },
    { code: 'ERO', name: 'Eastern (Kolkata)', cases: 22, onTrack: 90, overdue: 1, avgDays: 4.4, evcNeeded: 6 },
    { code: 'CRO', name: 'Central (Bhopal)', cases: 19, onTrack: 95, overdue: 0, avgDays: 3.7, evcNeeded: 4 },
  ];

  const stageBreakdown = [
    { stage: 'SCRUTINY', label: '1. Scrutiny & Verification', count: 24, sla: '7 Days', status: 'ON_TRACK', desc: 'Document verification by Scrutiny Committee' },
    { stage: 'DEFICIENT', label: '2. Deficiency Cure Window', count: 7, sla: '15 Days', status: 'PAUSED', desc: 'Clock paused while with institutions (Clause 1.8(f))' },
    { stage: 'EVC', label: '3. Expert Visit Inspection', count: 12, sla: '15 Days', status: 'AT_RISK', desc: 'Annexure-16 on-site/virtual panel review' },
    { stage: 'SAC_SHC', label: '4. Standing Hearing (SAC/SHC)', count: 5, sla: '10 Days', status: 'ON_TRACK', desc: 'Representations for rejected/deficient cases' },
    { stage: 'COUNCIL', label: '5. Council Final Decision', count: 162, sla: 'Annual Cycle', status: 'APPROVED', desc: 'Statutory Letter of Approval / EoA granted' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* 1. EXECUTIVE COMMAND HEADER BAR */}
      <div className="bg-white rounded-2xl border border-ink-line p-6 shadow-soft flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-blossom-600 text-white flex items-center justify-center font-bold shadow-soft">
              <Landmark className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-ink-strong">
                  National AICTE Approval & Compliance Command Center
                </h1>
                <span className="bg-blossom-100 text-blossom-700 text-[10px] font-bold px-2 py-0.5 rounded border border-blossom-300">
                  APH 2024–27 Cycle
                </span>
              </div>
              <p className="text-xs text-ink-muted">
                Executive real-time monitoring across 7 Regional Offices • Scope:{' '}
                <strong className="text-ink">{currentRegion.name} ({currentRegion.code})</strong>
              </p>
            </div>
          </div>
        </div>

        {/* Demo Clock & Active User Strip */}
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-[10px] text-ink-muted uppercase font-bold tracking-wider">Active Evaluator</div>
            <div className="text-xs font-bold text-ink-strong">{currentUser.name}</div>
            <span className="text-[10px] bg-slate-100 text-ink px-1.5 py-0.2 rounded font-medium">
              {currentUser.roleLabel}
            </span>
          </div>

          <div className="h-8 w-px bg-slate-200 hidden sm:block" />

          <div className="text-right">
            <div className="text-[10px] text-ink-muted uppercase font-bold tracking-wider">Simulation Clock</div>
            <div className="text-xs font-mono font-bold text-ink-strong">
              {virtualDate.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
            </div>
            {virtualDaysOffset > 0 ? (
              <span className="text-[10px] font-bold text-roseState-700 bg-roseState-100 px-1.5 py-0.2 rounded">
                +{virtualDaysOffset}d Advanced
              </span>
            ) : (
              <span className="text-[10px] font-bold text-mint-700 bg-mint-100 px-1.5 py-0.2 rounded">
                Current Time
              </span>
            )}
          </div>
        </div>
      </div>

      {/* 2. REGIONAL OFFICE SCOPE QUICK PILLS */}
      <div className="bg-white rounded-xl border border-ink-line p-3 shadow-soft flex items-center justify-between gap-2 overflow-x-auto">
        <div className="text-[11px] font-bold uppercase tracking-wider text-ink-muted flex items-center gap-1.5 shrink-0 px-2">
          <Filter className="w-3.5 h-3.5 text-blossom-600" />
          <span>Regional Corridors:</span>
        </div>
        <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5">
          {SAMPLE_REGIONS.map((reg) => {
            const isSelected = currentRegion.code === reg.code;
            return (
              <button
                key={reg.code}
                onClick={() => setRegionByCode(reg.code)}
                className={`text-xs font-semibold px-3 py-1.5 rounded-lg border transition-all shrink-0 flex items-center gap-1.5 ${
                  isSelected
                    ? 'bg-blossom-600 text-white border-blossom-600 shadow-soft font-bold'
                    : 'bg-slate-50 text-ink hover:bg-slate-100 border-ink-line'
                }`}
              >
                <span>{reg.code}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                    isSelected ? 'bg-white/20 text-white' : 'bg-slate-200 text-ink-muted'
                  }`}
                >
                  {reg.activeCasesCount}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* 3. SIX MACRO KPI TILES (SECTION 10 IMPACT METRICS) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
        {/* KPI 1: Active Cases */}
        <div
          onClick={() => setActiveNavTab('applications')}
          className="bg-white rounded-xl border border-ink-line p-4 shadow-soft hover:border-blossom-300 hover:shadow-card transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-ink-muted uppercase">Active Cases</span>
            <div className="w-7 h-7 rounded-lg bg-blossom-100 text-blossom-600 flex items-center justify-center group-hover:scale-110 transition-transform">
              <FileText className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-ink-strong">
            {currentRegion.activeCasesCount}
          </div>
          <div className="mt-1 text-[11px] text-mint-700 font-semibold flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            <span>88% On-Track</span>
          </div>
        </div>

        {/* KPI 2: SLA Timeliness */}
        <div
          onClick={() => setActiveNavTab('next-best-action')}
          className="bg-white rounded-xl border border-ink-line p-4 shadow-soft hover:border-blossom-300 hover:shadow-card transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-ink-muted uppercase">SLA Health</span>
            <div className="w-7 h-7 rounded-lg bg-mint-100 text-mint-700 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Clock className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-ink-strong">
            94.2%
          </div>
          <div className="mt-1 text-[11px] text-ink-muted">
            Avg Turnaround: <strong>4.8d</strong>
          </div>
        </div>

        {/* KPI 3: EVC Queue */}
        <div
          onClick={() => setActiveNavTab('evc')}
          className="bg-white rounded-xl border border-ink-line p-4 shadow-soft hover:border-blossom-300 hover:shadow-card transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-ink-muted uppercase">EVC Inspection</span>
            <div className="w-7 h-7 rounded-lg bg-blossom-100 text-blossom-600 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Calendar className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-ink-strong">
            12
          </div>
          <div className="mt-1 text-[11px] text-blossom-700 font-semibold">
            8 Panels Confirmed
          </div>
        </div>

        {/* KPI 4: Document Registry */}
        <div
          onClick={() => setActiveNavTab('compliance')}
          className="bg-white rounded-xl border border-ink-line p-4 shadow-soft hover:border-blossom-300 hover:shadow-card transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-ink-muted uppercase">Doc Registry</span>
            <div className="w-7 h-7 rounded-lg bg-amberState-100 text-amberState-700 flex items-center justify-center group-hover:scale-110 transition-transform">
              <FileCheck2 className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-ink-strong">
            18
          </div>
          <div className="mt-1 text-[11px] text-amberState-700 font-semibold">
            2 Expiring in 30d
          </div>
        </div>

        {/* KPI 5: Hours Saved (Section 10) */}
        <div className="bg-white rounded-xl border border-ink-line p-4 shadow-soft">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-ink-muted uppercase">Hours Saved</span>
            <div className="w-7 h-7 rounded-lg bg-mint-100 text-mint-700 flex items-center justify-center">
              <TrendingUp className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-ink-strong">
            540+ hrs
          </div>
          <div className="mt-1 text-[11px] text-mint-700 font-semibold">
            Auto-Handled
          </div>
        </div>

        {/* KPI 6: Unassigned Cases */}
        <div className="bg-white rounded-xl border border-ink-line p-4 shadow-soft">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-ink-muted uppercase">Unassigned</span>
            <div className="w-7 h-7 rounded-lg bg-mint-100 text-mint-700 flex items-center justify-center">
              <Users className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-mint-700">
            0
          </div>
          <div className="mt-1 text-[11px] text-mint-700 font-semibold">
            Target Met (Zero)
          </div>
        </div>
      </div>

      {/* 4. VISUAL APH APPROVAL MOVEMENT PIPELINE & DEFICIENCY PAUSE */}
      <div className="bg-white rounded-2xl border border-ink-line p-6 shadow-soft space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink-line pb-3">
          <div>
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-blossom-600" />
              <h2 className="text-sm font-bold text-ink-strong uppercase tracking-wider">
                End-to-End Approval Movement Pipeline (APH Table 2.3)
              </h2>
            </div>
            <p className="text-xs text-ink-muted mt-0.5">
              Live case distribution across statutory stages. Notice how Stage 2 holds paused clocks during deficiency rectification.
            </p>
          </div>

          <button
            onClick={() => setActiveNavTab('applications')}
            className="text-xs font-bold text-blossom-700 hover:text-blossom-800 flex items-center gap-1"
          >
            <span>Open Application Workspace</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Visual Stage Pipeline Flow */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {stageBreakdown.map((stg, i) => (
            <div
              key={stg.stage}
              className={`p-4 rounded-xl border flex flex-col justify-between transition-all ${
                stg.status === 'PAUSED'
                  ? 'bg-amberState-100/40 border-amberState-700/30 shadow-xs'
                  : stg.status === 'AT_RISK'
                  ? 'bg-blossom-100/40 border-blossom-300 shadow-xs'
                  : 'bg-slate-50 border-ink-line'
              }`}
            >
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-ink-muted">
                    SLA: {stg.sla}
                  </span>
                  {stg.status === 'PAUSED' ? (
                    <span className="text-[9px] font-bold px-1.5 py-0.2 bg-amberState-100 text-amberState-700 rounded border border-amberState-700/30">
                      Clock Paused
                    </span>
                  ) : stg.status === 'APPROVED' ? (
                    <span className="text-[9px] font-bold px-1.5 py-0.2 bg-mint-100 text-mint-700 rounded border border-mint-700/30">
                      Completed
                    </span>
                  ) : (
                    <span className="text-[9px] font-bold px-1.5 py-0.2 bg-white text-ink-strong rounded border border-ink-line">
                      Active
                    </span>
                  )}
                </div>

                <div className="text-xs font-bold text-ink-strong pt-1">
                  {stg.label}
                </div>
                <div className="text-[10px] text-ink-muted leading-relaxed">
                  {stg.desc}
                </div>
              </div>

              <div className="pt-3 mt-3 border-t border-slate-200 flex items-baseline justify-between">
                <span className="text-2xl font-bold font-mono text-ink-strong">{stg.count}</span>
                <span className="text-[11px] text-ink-muted">cases</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 5. INTERACTIVE OPERATIONAL LAUNCHPAD & CORRIDOR HEATMAP */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Signature Differentiators Launchpad (2 Cols) */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-ink-line p-6 shadow-soft space-y-4">
          <div className="flex items-center justify-between border-b border-ink-line pb-3">
            <div>
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-blossom-600" />
                <h2 className="text-sm font-bold text-ink-strong uppercase tracking-wider">
                  Operational Launchpad & Signature Differentiators
                </h2>
              </div>
              <p className="text-xs text-ink-muted mt-0.5">
                Quick-launch statutory engines and high-impact operational workflows.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Launchpad Card 1: Next-Best-Action & SHAP */}
            <div
              onClick={() => setActiveNavTab('next-best-action')}
              className="p-4 rounded-xl border border-ink-line bg-[#FAFAFA] hover:bg-blossom-100/30 hover:border-blossom-300 transition-all cursor-pointer group flex items-start gap-3"
            >
              <div className="w-9 h-9 rounded-lg bg-blossom-100 text-blossom-600 flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
                <Sparkles className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-ink-strong">Next-Best-Action Queue</span>
                  <span className="text-[9px] font-bold bg-mint-100 text-mint-700 px-1.5 py-0.2 rounded">TreeSHAP XAI</span>
                </div>
                <p className="text-[11px] text-ink-muted leading-relaxed">
                  Ranks work queue by Breach Risk &times; Student Impact. Decomposable into mathematical Shapley values.
                </p>
              </div>
            </div>

            {/* Launchpad Card 2: What-If Capacity Simulator */}
            <div
              onClick={() => setActiveNavTab('what-if')}
              className="p-4 rounded-xl border border-ink-line bg-[#FAFAFA] hover:bg-blossom-100/30 hover:border-blossom-300 transition-all cursor-pointer group flex items-start gap-3"
            >
              <div className="w-9 h-9 rounded-lg bg-mint-100 text-mint-700 flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
                <Sliders className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-ink-strong">What-If Capacity Simulator</span>
                  <span className="text-[9px] font-bold bg-blossom-100 text-blossom-700 px-1.5 py-0.2 rounded">Shock Lab</span>
                </div>
                <p className="text-[11px] text-ink-muted leading-relaxed">
                  Simulate inspector shortages and regional staffing cuts to model live SLA failure points and affected student seats.
                </p>
              </div>
            </div>

            {/* Launchpad Card 3: Document Integrity & Fraud Detector */}
            <div
              onClick={() => setActiveNavTab('security-anomalies')}
              className="p-4 rounded-xl border border-ink-line bg-[#FAFAFA] hover:bg-blossom-100/30 hover:border-blossom-300 transition-all cursor-pointer group flex items-start gap-3"
            >
              <div className="w-9 h-9 rounded-lg bg-roseState-100 text-roseState-700 flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-ink-strong">Document Integrity & Fraud</span>
                  <span className="text-[9px] font-bold bg-roseState-100 text-roseState-700 px-1.5 py-0.2 rounded">SHA-256 Collision</span>
                </div>
                <p className="text-[11px] text-ink-muted leading-relaxed">
                  Catches cross-institution duplicate lease file hashes, altered metadata, and area mismatches before approval.
                </p>
              </div>
            </div>

            {/* Launchpad Card 4: Cryptographic Audit Ledger */}
            <div
              onClick={() => setActiveNavTab('audit')}
              className="p-4 rounded-xl border border-ink-line bg-[#FAFAFA] hover:bg-blossom-100/30 hover:border-blossom-300 transition-all cursor-pointer group flex items-start gap-3"
            >
              <div className="w-9 h-9 rounded-lg bg-slate-100 text-ink-strong flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
                <Scale className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-ink-strong">Cryptographic Audit Chain</span>
                  <span className="text-[9px] font-bold bg-slate-200 text-ink px-1.5 py-0.2 rounded">Merkle Verified</span>
                </div>
                <p className="text-[11px] text-ink-muted leading-relaxed">
                  Non-repudiable SHA-256 chained ledger with live in-app tampering simulation and integrity verifier.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Regional Performance Corridor Heatmap (1 Col) */}
        <div className="bg-white rounded-2xl border border-ink-line p-6 shadow-soft space-y-4">
          <div className="flex items-center justify-between border-b border-ink-line pb-3">
            <div>
              <h2 className="text-sm font-bold text-ink-strong uppercase tracking-wider">
                Regional Corridors
              </h2>
              <p className="text-xs text-ink-muted mt-0.5">
                Workload & On-Track Compliance
              </p>
            </div>
            <span className="text-[10px] font-bold text-mint-700 bg-mint-100 px-2 py-0.5 rounded">
              7 Active Offices
            </span>
          </div>

          <div className="space-y-2.5">
            {regionalMetrics.map((r) => (
              <div
                key={r.code}
                onClick={() => setRegionByCode(r.code)}
                className={`p-2.5 rounded-xl border text-xs transition-all cursor-pointer flex items-center justify-between ${
                  currentRegion.code === r.code
                    ? 'bg-blossom-100/50 border-blossom-300 shadow-xs'
                    : 'bg-[#FAFAFA] border-ink-line hover:bg-slate-100'
                }`}
              >
                <div>
                  <div className="font-bold text-ink-strong flex items-center gap-1.5">
                    <span>{r.code}</span>
                    <span className="text-[11px] font-normal text-ink-muted">({r.name.split(' ')[0]})</span>
                  </div>
                  <div className="text-[10px] text-ink-muted mt-0.5">
                    {r.cases} Cases • Avg: {r.avgDays}d
                  </div>
                </div>

                <div className="text-right">
                  <div className="font-mono font-bold text-mint-700">
                    {r.onTrack}% On-Track
                  </div>
                  {r.overdue > 0 ? (
                    <div className="text-[10px] font-semibold text-roseState-700">
                      {r.overdue} Overdue
                    </div>
                  ) : (
                    <div className="text-[10px] font-semibold text-mint-700">
                      0 Overdue
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 6. STATUTORY SAFEGUARD & DPDP ASSURANCE FOOTER */}
      <div className="bg-white rounded-xl border border-ink-line p-4 shadow-soft flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-mint-700" />
          <span className="text-ink-strong font-semibold">
            Regulatory Assurance:
          </span>
          <span className="text-ink-muted">
            All state transitions and SLA escalations are governed strictly by deterministic rules. LLM assistants remain strictly advisory (SUGGEST-ONLY).
          </span>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-ink-muted font-medium">
          <span>• APH 2024–27 Aligned</span>
          <span>• DPDP Act 2023 Compliant</span>
          <span>• SHA-256 Non-Repudiable Ledger</span>
        </div>
      </div>
    </div>
  );
};
