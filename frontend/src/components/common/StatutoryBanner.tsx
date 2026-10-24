'use client';

import React from 'react';
import { ShieldAlert, Info, Sparkles } from 'lucide-react';
import { useApp } from '@/lib/app-context';

export const StatutoryBanner: React.FC = () => {
  const { isDemoMode, evaluatorMode } = useApp();
  const showSampleValues = evaluatorMode || isDemoMode;

  return (
    <div className="bg-white border-b border-ink-line px-6 py-2 flex flex-wrap items-center justify-between text-xs text-ink gap-2">
      {/* Left: Statutory Safeguard Banner */}
      <div className="flex items-center gap-2">
        <span className="flex items-center gap-1 font-bold text-blossom-700 bg-blossom-100 px-2 py-0.5 rounded border border-blossom-300">
          <ShieldAlert className="w-3.5 h-3.5 text-blossom-600" /> Statutory Safeguard
        </span>
        <span className="text-ink">
          Automation supports the approval workflow. Statutory scrutiny, inspections and final decisions are strictly reserved for the Competent Authority.
        </span>
      </div>

      {/* Right: Sample Value Badge & AI draft note */}
      <div className="flex items-center gap-2">
        {showSampleValues && (
          <span className="badge-sample-value flex items-center gap-1" title="Values can be compiled directly from APH 2024-27 PDF">
            <Info className="w-3 h-3 text-amber-700" /> Sample values, configurable
          </span>
        )}
        <span className="bg-slate-100 text-ink-muted text-[11px] px-2 py-0.5 rounded font-medium flex items-center gap-1 border border-ink-line">
          <Sparkles className="w-3 h-3 text-blossom-600" /> AI drafts require named human approval
        </span>
      </div>
    </div>
  );
};
