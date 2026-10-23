'use client';

import React, { useState, useEffect } from 'react';
import {
  Sliders,
  AlertTriangle,
  Users,
  Clock,
  TrendingDown,
  Sparkles,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';

export const WhatIfSimulatorView: React.FC = () => {
  const [inspectorShortage, setInspectorShortage] = useState(30);
  const [staffingLevel, setStaffingLevel] = useState(70);
  const [simulationResult, setSimulationResult] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  const runSimulation = async () => {
    try {
      setLoading(true);
      const res = await fetch('http://127.0.0.1:8000/api/v1/differentiators/what-if-simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          inspector_shortage_percent: inspectorShortage,
          staffing_level_percent: staffingLevel,
        }),
      });
      const data = await res.json();
      setSimulationResult(data);
    } catch (err) {
      console.error('Simulation error', err);
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
              Signature Differentiator 3
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

      {/* Projected Impact Cards */}
      {simulationResult && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-roseState-700/30 p-4 shadow-soft bg-roseState-100/20">
            <span className="text-[10px] uppercase font-bold text-roseState-700">Projected SLA Breaches</span>
            <div className="text-2xl font-bold font-mono text-roseState-700 mt-1">
              {simulationResult.impact_projections.predicted_sla_breaches} Cases
            </div>
            <div className="text-[11px] text-ink-muted mt-1">
              Projected Overdue Rate: <strong>{simulationResult.impact_projections.projected_overdue_rate}</strong>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-amberState-700/30 p-4 shadow-soft bg-amberState-100/20">
            <span className="text-[10px] uppercase font-bold text-amberState-700">At-Risk Student Seats</span>
            <div className="text-2xl font-bold font-mono text-amberState-700 mt-1">
              {simulationResult.impact_projections.at_risk_student_seats.toLocaleString()}
            </div>
            <div className="text-[11px] text-ink-muted mt-1">
              Delayed intake approvals directly impacting admissions
            </div>
          </div>

          <div className="bg-white rounded-xl border border-ink-line p-4 shadow-soft">
            <span className="text-[10px] uppercase font-bold text-ink-muted">Effective Delay Multiplier</span>
            <div className="text-2xl font-bold font-mono text-ink-strong mt-1">
              {simulationResult.simulation_parameters.effective_slowdown}
            </div>
            <div className="text-[11px] text-ink-muted mt-1">
              Total active workload: {simulationResult.impact_projections.total_active_workload} applications
            </div>
          </div>
        </div>
      )}

      {/* Recommended Mitigations */}
      {simulationResult && (
        <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blossom-600" />
            <h3 className="text-xs font-bold text-ink-strong uppercase tracking-wider">
              Automated Capacity Mitigations (Advisory)
            </h3>
          </div>
          <div className="space-y-2">
            {simulationResult.mitigation_recommendations.map((m: string, idx: number) => (
              <div key={idx} className="p-3 bg-slate-50 rounded-lg border border-ink-line text-xs flex items-center gap-2">
                <ArrowRight className="w-3.5 h-3.5 text-mint-700 shrink-0" />
                <span className="text-ink">{m}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
