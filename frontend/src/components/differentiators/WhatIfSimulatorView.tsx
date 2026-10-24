'use client';

import React, { useState, useEffect } from 'react';
import { apiFetch } from '@/lib/api';
import {
  Sliders,
  AlertTriangle,
  Users,
  Clock,
  TrendingDown,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  RefreshCw,
  FolderOpen,
  BarChart3,
} from 'lucide-react';

export const WhatIfSimulatorView: React.FC = () => {
  const [inspectorShortage, setInspectorShortage] = useState(30);
  const [staffingLevel, setStaffingLevel] = useState(70);
  const [simulationResult, setSimulationResult] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiFetch<any>('/api/v1/differentiators/what-if-simulate', {
        method: 'POST',
        body: JSON.stringify({
          inspector_shortage_percent: inspectorShortage,
          staffing_level_percent: staffingLevel,
        }),
      });
      setSimulationResult(data);
    } catch (err: any) {
      console.error('Simulation error', err);
      setError(err.message || 'Failed to compute capacity simulation.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runSimulation();
  }, [inspectorShortage, staffingLevel]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-ink-line p-4 shadow-soft flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-blossom-600" />
            <h1 className="text-lg font-bold text-ink-strong">
              What-If Capacity & Bottleneck Simulator
            </h1>
            <span className="bg-blossom-100 text-blossom-700 text-[10px] font-bold px-2 py-0.5 rounded border border-blossom-300">
              Signature Differentiator 4
            </span>
          </div>
          <p className="text-xs text-ink-muted mt-0.5">
            Test operational shocks (committee availability, staffing cuts) to model SLA failure points and student impacts.
          </p>
        </div>
      </div>

      {/* Control Sliders Card */}
      <div className="bg-white rounded-xl border border-ink-line p-6 shadow-soft space-y-6">
        <h2 className="text-sm font-bold text-ink-strong uppercase tracking-wider">
          Simulation Parameters
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Slider 1: Inspector Shortage */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold">
              <span className="text-ink-strong">EVC Committee Inspectors Unavailable</span>
              <span className="font-mono text-blossom-700 bg-blossom-100 px-2 py-0.5 rounded font-bold">
                {inspectorShortage}% Shortage
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="50"
              step="5"
              value={inspectorShortage}
              onChange={(e) => setInspectorShortage(parseInt(e.target.value))}
              className="w-full accent-blossom-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-ink-muted">
              <span>0% (Full Pool)</span>
              <span>25% (Moderate)</span>
              <span>50% (Severe Shortage)</span>
            </div>
          </div>

          {/* Slider 2: Regional Staffing */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold">
              <span className="text-ink-strong">Regional Office Staffing Level</span>
              <span className="font-mono text-blossom-700 bg-blossom-100 px-2 py-0.5 rounded font-bold">
                {staffingLevel}% Capacity
              </span>
            </div>
            <input
              type="range"
              min="40"
              max="100"
              step="5"
              value={staffingLevel}
              onChange={(e) => setStaffingLevel(parseInt(e.target.value))}
              className="w-full accent-blossom-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-ink-muted">
              <span>40% (Extreme Shortage)</span>
              <span>70% (Peak Season)</span>
              <span>100% (Full Staffing)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 bg-rose-50 rounded-xl border border-rose-200 text-center shadow-soft">
          <AlertTriangle className="w-6 h-6 text-rose-600 mx-auto mb-1.5" />
          <h3 className="text-xs font-bold text-rose-900">Simulation Interrupted</h3>
          <p className="text-[11px] text-rose-700 max-w-md mx-auto mt-0.5 mb-3">{error}</p>
          <button
            onClick={runSimulation}
            className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-lg shadow-sm inline-flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            Recalculate
          </button>
        </div>
      )}

      {/* Loading Indicator */}
      {loading && (
        <div className="p-8 bg-white rounded-xl border border-ink-line text-center shadow-soft">
          <RefreshCw className="w-6 h-6 text-blossom-600 animate-spin mx-auto mb-2" />
          <p className="text-xs font-bold text-ink-strong">Simulating Capacity & Bottleneck Shocks...</p>
        </div>
      )}

      {/* Comparative Impact: Baseline vs After Shock Side-by-Side */}
      {simulationResult && !loading && !error && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-ink-strong uppercase tracking-wider flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-blossom-600" />
              Comparative Impact Analysis: Baseline vs After Shock
            </h2>
            <span className="text-[11px] font-mono bg-slate-100 text-ink-muted px-2.5 py-0.5 rounded border border-ink-line">
              Active Workload: {simulationResult.impact_projections?.total_active_workload || 30} Applications
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Column 1: Baseline Operations */}
            <div className="bg-white rounded-xl border border-mint-700/30 p-5 shadow-soft bg-mint-100/10 space-y-4">
              <div className="flex items-center justify-between border-b border-mint-200 pb-3">
                <div>
                  <span className="text-[10px] font-extrabold uppercase tracking-wider text-mint-800 bg-mint-100 px-2 py-0.5 rounded border border-mint-300">
                    Baseline Operations
                  </span>
                  <h3 className="text-sm font-bold text-ink-strong mt-1">Normal Statutory Capacity</h3>
                  <p className="text-[11px] text-ink-muted">100% regional staffing • 0% committee shortage</p>
                </div>
                <div className="text-right">
                  <span className="text-xs font-bold text-mint-800 bg-mint-100 px-2.5 py-1 rounded-full border border-mint-300">
                    {simulationResult.baseline?.operational_status || 'NORMAL CAPACITY'}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-white rounded-lg border border-mint-200">
                  <span className="text-[10px] font-bold text-ink-muted uppercase">Baseline Breaches</span>
                  <div className="text-2xl font-bold font-mono text-ink-strong mt-0.5">
                    {simulationResult.baseline?.predicted_sla_breaches ?? 2} <span className="text-xs font-normal text-ink-muted">Cases</span>
                  </div>
                  <div className="text-[11px] text-mint-800 font-medium mt-0.5">
                    Overdue Rate: {simulationResult.baseline?.projected_overdue_rate ?? '6.7%'}
                  </div>
                </div>

                <div className="p-3 bg-white rounded-lg border border-mint-200">
                  <span className="text-[10px] font-bold text-ink-muted uppercase">At-Risk Student Seats</span>
                  <div className="text-2xl font-bold font-mono text-ink-strong mt-0.5">
                    {(simulationResult.baseline?.at_risk_student_seats ?? 360).toLocaleString()}
                  </div>
                  <div className="text-[11px] text-ink-muted mt-0.5">
                    Statutory margin maintained
                  </div>
                </div>
              </div>
            </div>

            {/* Column 2: After Shock Operations */}
            <div className="bg-white rounded-xl border border-roseState-700/30 p-5 shadow-soft bg-roseState-100/20 space-y-4">
              <div className="flex items-center justify-between border-b border-roseState-200 pb-3">
                <div>
                  <span className="text-[10px] font-extrabold uppercase tracking-wider text-roseState-700 bg-roseState-100 px-2 py-0.5 rounded border border-roseState-300">
                    After Operational Shock
                  </span>
                  <h3 className="text-sm font-bold text-rose-900 mt-1">
                    {staffingLevel}% Staffing • {inspectorShortage}% Shortage
                  </h3>
                  <p className="text-[11px] text-ink-muted">
                    Effective delay multiplier: {simulationResult.simulation_parameters?.effective_slowdown || '1.6x'}
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-xs font-bold text-roseState-700 bg-roseState-100 px-2.5 py-1 rounded-full border border-roseState-300">
                    {simulationResult.after_shock?.operational_status || 'BOTTLENECK SURGE'}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-white rounded-lg border border-roseState-200">
                  <span className="text-[10px] font-bold text-roseState-700 uppercase">Projected Breaches</span>
                  <div className="text-2xl font-bold font-mono text-roseState-700 mt-0.5">
                    {simulationResult.after_shock?.predicted_sla_breaches ?? simulationResult.impact_projections?.predicted_sla_breaches} <span className="text-xs font-normal text-ink-muted">Cases</span>
                  </div>
                  <div className="text-[11px] text-roseState-700 font-medium mt-0.5">
                    Overdue Rate: {simulationResult.after_shock?.projected_overdue_rate ?? simulationResult.impact_projections?.projected_overdue_rate}
                  </div>
                </div>

                <div className="p-3 bg-white rounded-lg border border-roseState-200">
                  <span className="text-[10px] font-bold text-roseState-700 uppercase">At-Risk Student Seats</span>
                  <div className="text-2xl font-bold font-mono text-roseState-700 mt-0.5">
                    {(simulationResult.after_shock?.at_risk_student_seats ?? simulationResult.impact_projections?.at_risk_student_seats ?? 0).toLocaleString()}
                  </div>
                  <div className="text-[11px] text-roseState-700 mt-0.5">
                    Delayed intake approvals
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Shock Delta Summary Ribbon */}
          {simulationResult.delta && (
            <div className="p-4 bg-gradient-to-r from-amber-50 to-rose-50 rounded-xl border border-amber-200 flex flex-wrap items-center justify-between gap-3 text-xs shadow-xs">
              <div className="flex items-center gap-2 font-bold text-amber-900">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>Shock Sensitivity Delta:</span>
              </div>
              <div className="flex flex-wrap items-center gap-6 font-mono text-xs">
                <div>
                  <span className="text-ink-muted">Additional Breaches: </span>
                  <strong className="text-roseState-700">+{simulationResult.delta.additional_breaches} Cases</strong>
                </div>
                <div>
                  <span className="text-ink-muted">Additional Students Affected: </span>
                  <strong className="text-amber-800">+{simulationResult.delta.additional_students_at_risk.toLocaleString()} Seats</strong>
                </div>
                <div>
                  <span className="text-ink-muted">Overdue Surge: </span>
                  <strong className="text-rose-800">+{simulationResult.delta.overdue_rate_increase}</strong>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Breached Applications Sample List */}
      {simulationResult && simulationResult.impact_projections.breached_applications_sample?.length > 0 && (
        <div className="bg-white rounded-xl border border-roseState-700/30 p-5 shadow-soft space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-roseState-700" />
              <h3 className="text-xs font-bold text-ink-strong uppercase tracking-wider">
                Simulated At-Risk Application Dockets
              </h3>
            </div>
            <span className="text-[10px] bg-slate-100 text-ink-muted px-2 py-0.5 rounded uppercase font-mono">
              {simulationResult.model_label || 'forecast from workload model'}
            </span>
          </div>

          <div className="space-y-2">
            {simulationResult.impact_projections.breached_applications_sample.map((app: any, idx: number) => (
              <div key={idx} className="p-3 bg-roseState-100/20 rounded-lg border border-roseState-700/20 flex flex-wrap items-center justify-between gap-2 text-xs">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-ink-strong">{app.application_no}</span>
                    <span className="text-[10px] font-bold bg-blossom-100 text-blossom-700 px-1.5 py-0.5 rounded">
                      {app.current_stage}
                    </span>
                  </div>
                  <div className="text-ink-muted text-[11px] mt-0.5">{app.institution_name}</div>
                </div>

                <div className="flex items-center gap-4 text-right">
                  <div>
                    <div className="text-[10px] text-ink-muted">Projected Completion:</div>
                    <div className="font-mono font-bold text-roseState-700">{app.projected_completion_date}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-ink-muted">SLA Deadline:</div>
                    <div className="font-mono text-ink-strong">{app.sla_deadline}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-ink-muted">P90 Band:</div>
                    <div className="font-mono text-roseState-700 font-semibold">{app.p90_date}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Assumptions & Mitigations */}
      {simulationResult && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-3">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-blossom-600" />
              <h3 className="text-xs font-bold text-ink-strong uppercase tracking-wider">
                Workload Queueing Model Assumptions
              </h3>
            </div>
            <ul className="text-xs text-ink space-y-1.5 list-disc list-inside">
              {simulationResult.assumptions?.map((asm: string, idx: number) => (
                <li key={idx} className="text-ink-muted leading-relaxed">
                  <span className="text-ink">{asm}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blossom-600" />
              <h3 className="text-xs font-bold text-ink-strong uppercase tracking-wider">
                Automated Capacity Mitigations (Advisory)
              </h3>
            </div>
            <div className="space-y-2">
              {simulationResult.mitigation_recommendations.map((m: string, idx: number) => (
                <div key={idx} className="p-2.5 bg-slate-50 rounded-lg border border-ink-line text-xs flex items-center gap-2">
                  <ArrowRight className="w-3.5 h-3.5 text-mint-700 shrink-0" />
                  <span className="text-ink">{m}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
