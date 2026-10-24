'use client';

import React, { useState } from 'react';
import {
  Zap,
  Play,
  RotateCcw,
  FastForward,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ShieldCheck,
  FileText,
  Calendar,
  Layers,
  ChevronRight,
  ChevronDown,
  Sparkles,
  Lock,
  X,
  ExternalLink,
  Cpu,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { useApp } from '@/lib/app-context';
import { apiFetch } from '@/lib/api';

export interface ScenarioStepData {
  step_id: number;
  step_key: string;
  title: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  timestamp?: string;
  details?: Record<string, any>;
  description: string;
  aphCitation: string;
}

const INITIAL_STEPS: ScenarioStepData[] = [
  {
    step_id: 1,
    step_key: 'aph_upload',
    title: '1. APH Upload & Ingestion',
    status: 'PENDING',
    description: 'Ingest Approval Process Handbook amendment and parse regulatory clauses into draft specifications.',
    aphCitation: 'Chapter I & II Regulatory Gazette Standards',
  },
  {
    step_id: 2,
    step_key: 'rules_update',
    title: '2. Rules Update & Versioned AST Activation',
    status: 'PENDING',
    description: 'Compile natural language clauses into deterministic AST bytecode and activate new immutable RuleVersion.',
    aphCitation: 'Chapter II Clause 2.1(e) Land Lease Norms',
  },
  {
    step_id: 3,
    step_key: 'auto_route',
    title: '3. Application Ingestion & Table 2.3 Auto-Routing',
    status: 'PENDING',
    description: 'Submit institutional application and resolve regulatory pipeline, required stages, and SLA targets.',
    aphCitation: 'Table 2.3 & Chapter I Institutional Routes',
  },
  {
    step_id: 4,
    step_key: 'evc_scheduled',
    title: '4. Conflict-Free EVC Inspection Panel Dispatch',
    status: 'PENDING',
    description: 'Algorithmically allocate zero-conflict committee experts and generate immutable inspection panel.',
    aphCitation: 'Chapter I Clause 1.8 & Annexure-16 EVC Norms',
  },
  {
    step_id: 5,
    step_key: 'time_jump',
    title: '5. Time-Travel Fast-Forward (+15 Days)',
    status: 'PENDING',
    description: 'Advance virtual simulation clock past scrutiny SLA threshold to trigger overdue breach.',
    aphCitation: 'APH SLA Timeline Matrix',
  },
  {
    step_id: 6,
    step_key: 'alert_escalates',
    title: '6. Multi-Tier Alert & Escalation Cascade',
    status: 'PENDING',
    description: 'Fire multi-channel notifications and cascade breach from L1 Officer to L2 Director to L3 Bureau Head.',
    aphCitation: 'Chapter I Clause 1.10 Multi-Tier Escalations',
  },
  {
    step_id: 7,
    step_key: 'anomaly_flag',
    title: '7. Anti-Fraud Document Anomaly Detection',
    status: 'PENDING',
    description: 'Detect duplicate SHA-256 document hash across institutions and raise human-in-the-loop audit flag.',
    aphCitation: 'Chapter I Institutional Authentication Standards',
  },
  {
    step_id: 8,
    step_key: 'audit_chain_verifies',
    title: '8. Cryptographic SHA-256 Audit Continuity Proof',
    status: 'PENDING',
    description: 'Recompute and verify unbroken cryptographic hash chain across all ledger entries from genesis to head block.',
    aphCitation: 'Immutable Tamper-Evident Ledger Integrity',
  },
];

interface ScriptedScenarioModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ScriptedScenarioModal: React.FC<ScriptedScenarioModalProps> = ({ isOpen, onClose }) => {
  const { virtualDate, virtualDaysOffset, advanceVirtualDays, resetVirtualTime } = useApp();
  const [steps, setSteps] = useState<ScenarioStepData[]>(INITIAL_STEPS);
  const [isRunningScenario, setIsRunningScenario] = useState<boolean>(false);
  const [expandedStepId, setExpandedStepId] = useState<number | null>(null);
  const [scenarioSummary, setScenarioSummary] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  if (!isOpen) return null;

  const runSingleStep = async (stepId: number) => {
    const step = steps.find((s) => s.step_id === stepId);
    if (!step) return;

    setSteps((prev) =>
      prev.map((s) => (s.step_id === stepId ? { ...s, status: 'RUNNING' } : s))
    );
    setApiError(null);

    const endpoints: Record<number, string> = {
      1: '/api/v1/demo/scenario/step/1-aph-upload',
      2: '/api/v1/demo/scenario/step/2-rules-update',
      3: '/api/v1/demo/scenario/step/3-auto-route',
      4: '/api/v1/demo/scenario/step/4-evc-scheduled',
      5: '/api/v1/demo/scenario/step/5-time-jump',
      6: '/api/v1/demo/scenario/step/6-alert-escalates',
      7: '/api/v1/demo/scenario/step/7-anomaly-flag',
      8: '/api/v1/demo/scenario/step/8-audit-chain-verifies',
    };

    try {
      const data = await apiFetch<any>(endpoints[stepId], {
        method: 'POST',
      });

      setSteps((prev) =>
        prev.map((s) =>
          s.step_id === stepId
            ? {
                ...s,
                status: 'COMPLETED',
                timestamp: data.timestamp || new Date().toLocaleTimeString(),
                details: data.details || data,
              }
            : s
        )
      );
      setExpandedStepId(stepId);

      // If Step 5 time jump was triggered, advance frontend virtual days offset by 15
      if (stepId === 5) {
        advanceVirtualDays(15);
      }
    } catch (err: any) {
      setSteps((prev) =>
        prev.map((s) => (s.step_id === stepId ? { ...s, status: 'FAILED' } : s))
      );
      setApiError(err.message || 'Error executing step');
    }
  };

  const runFullScriptedScenario = async () => {
    setIsRunningScenario(true);
    setApiError(null);
    setScenarioSummary(null);

    // Reset steps state to running
    setSteps(INITIAL_STEPS.map((s) => ({ ...s, status: 'PENDING' })));

    try {
      const data = await apiFetch<any>('/api/v1/demo/scenario/run', {
        method: 'POST',
      });

      // Update all steps with returned payload
      const returnedSteps = data.steps || [];
      setSteps((prev) =>
        prev.map((s, idx) => {
          const ret = returnedSteps[idx];
          return {
            ...s,
            status: 'COMPLETED',
            timestamp: ret?.timestamp || new Date().toLocaleTimeString(),
            details: ret?.details || ret,
          };
        })
      );

      setScenarioSummary(data.summary);
      setExpandedStepId(8); // Auto-expand audit proof
      advanceVirtualDays(15);
    } catch (err: any) {
      setApiError(err.message || 'Failed to execute scripted scenario');
    } finally {
      setIsRunningScenario(false);
    }
  };

  const handleReset = () => {
    setSteps(INITIAL_STEPS);
    setExpandedStepId(null);
    setScenarioSummary(null);
    setApiError(null);
    resetVirtualTime();
  };

  const completedCount = steps.filter((s) => s.status === 'COMPLETED').length;
  const progressPercent = Math.round((completedCount / steps.length) * 100);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl border border-ink-line max-w-5xl w-full max-h-[92vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-rose-500 flex items-center justify-center font-bold shadow-md">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold tracking-tight">
                  AICTE Evaluator Demo & Time-Travel Command Console
                </h2>
                <span className="bg-amber-400/20 text-amber-300 text-[10px] font-bold px-2 py-0.5 rounded border border-amber-400/30 uppercase tracking-wider">
                  DEMO_MODE Sandbox
                </span>
              </div>
              <p className="text-xs text-slate-300">
                1-Click Scripted Scenario • APH Ingestion → Table 2.3 Auto-Route → SLA Escalation → Cryptographic Continuity
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Time Travel Bar */}
        <div className="px-6 py-3 bg-slate-50 border-b border-ink-line flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-blossom-600" />
            <span className="text-xs font-bold text-ink">Simulated System Clock:</span>
            <span className="text-xs font-mono bg-white px-2.5 py-1 rounded-md border border-ink-line text-ink-strong font-bold">
              {virtualDate.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
            </span>
            {virtualDaysOffset > 0 && (
              <span className="text-[11px] font-bold px-2 py-0.5 bg-rose-100 text-rose-700 rounded-full border border-rose-200">
                +{virtualDaysOffset} Days Warped
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold text-ink-muted">Fast Forward:</span>
            <button
              onClick={() => advanceVirtualDays(1)}
              className="px-2.5 py-1 bg-white hover:bg-slate-100 border border-ink-line rounded text-xs font-bold text-ink transition-colors flex items-center gap-1 shadow-sm"
            >
              <FastForward className="w-3 h-3 text-blossom-600" /> +1d
            </button>
            <button
              onClick={() => advanceVirtualDays(7)}
              className="px-2.5 py-1 bg-white hover:bg-slate-100 border border-ink-line rounded text-xs font-bold text-ink transition-colors flex items-center gap-1 shadow-sm"
            >
              <FastForward className="w-3 h-3 text-blossom-600" /> +7d
            </button>
            <button
              onClick={() => advanceVirtualDays(15)}
              className="px-2.5 py-1 bg-white hover:bg-rose-50 border border-rose-200 rounded text-xs font-bold text-rose-700 transition-colors flex items-center gap-1 shadow-sm"
              title="Fast forward past SLA scrutiny deadline"
            >
              <FastForward className="w-3 h-3 text-rose-600" /> +15d (SLA Warp)
            </button>
            <button
              onClick={() => advanceVirtualDays(30)}
              className="px-2.5 py-1 bg-white hover:bg-rose-50 border border-rose-200 rounded text-xs font-bold text-rose-700 transition-colors flex items-center gap-1 shadow-sm"
            >
              <FastForward className="w-3 h-3 text-rose-600" /> +30d
            </button>
            <button
              onClick={handleReset}
              className="px-2.5 py-1 bg-white hover:bg-slate-100 border border-ink-line rounded text-xs font-semibold text-ink-muted transition-colors flex items-center gap-1 shadow-sm"
              title="Reset Virtual Clock and Scenario"
            >
              <RotateCcw className="w-3 h-3" /> Reset
            </button>
          </div>
        </div>

        {/* Primary Action Button & Progress */}
        <div className="px-6 py-4 bg-gradient-to-r from-blue-50 via-slate-50 to-indigo-50 border-b border-ink-line flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-ink-strong">Scenario Execution Progress:</span>
              <span className="text-xs font-bold text-blossom-700">{completedCount} of 8 Steps Completed ({progressPercent}%)</span>
            </div>
            <div className="w-64 bg-slate-200 rounded-full h-2 mt-1.5 overflow-hidden">
              <div
                className="bg-gradient-to-r from-blue-600 to-indigo-600 h-2 rounded-full transition-all duration-500"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={runFullScriptedScenario}
              disabled={isRunningScenario}
              className="px-5 py-2.5 bg-gradient-to-r from-indigo-600 via-blue-600 to-blossom-600 hover:from-indigo-700 hover:to-blossom-700 text-white rounded-xl text-xs font-bold shadow-md hover:shadow-lg transition-all flex items-center gap-2 disabled:opacity-50"
            >
              {isRunningScenario ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Running Scenario...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 text-amber-300" />
                  ⚡ Run One-Click Scripted Scenario (Full Tour)
                </>
              )}
            </button>
          </div>
        </div>

        {/* Error / Summary Banners */}
        {apiError && (
          <div className="px-6 py-2.5 bg-rose-50 border-b border-rose-200 text-rose-800 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{apiError}</span>
          </div>
        )}

        {scenarioSummary && (
          <div className="px-6 py-3 bg-emerald-50 border-b border-emerald-200 text-emerald-900 text-xs flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <strong className="font-bold">Scenario Completed Successfully: </strong>
              <span>{scenarioSummary}</span>
            </div>
          </div>
        )}

        {/* 8-Step Timeline List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          {steps.map((step) => {
            const isExpanded = expandedStepId === step.step_id;
            return (
              <div
                key={step.step_id}
                className={`rounded-xl border transition-all ${
                  step.status === 'COMPLETED'
                    ? 'border-emerald-200 bg-emerald-50/20'
                    : step.status === 'RUNNING'
                    ? 'border-blue-300 bg-blue-50/30 ring-2 ring-blue-100'
                    : step.status === 'FAILED'
                    ? 'border-rose-200 bg-rose-50/30'
                    : 'border-ink-line bg-white hover:border-slate-300'
                }`}
              >
                <div className="p-4 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 ${
                        step.status === 'COMPLETED'
                          ? 'bg-emerald-600 text-white'
                          : step.status === 'RUNNING'
                          ? 'bg-blue-600 text-white animate-pulse'
                          : step.status === 'FAILED'
                          ? 'bg-rose-600 text-white'
                          : 'bg-slate-100 text-slate-600 border border-slate-200'
                      }`}
                    >
                      {step.status === 'COMPLETED' ? (
                        <CheckCircle2 className="w-4 h-4" />
                      ) : step.status === 'RUNNING' ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        step.step_id
                      )}
                    </div>

                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="text-xs font-bold text-ink-strong truncate">{step.title}</h3>
                        <span className="text-[10px] font-semibold px-2 py-0.5 bg-slate-100 text-ink-muted rounded-full">
                          {step.aphCitation}
                        </span>
                      </div>
                      <p className="text-[11px] text-ink-muted mt-0.5">{step.description}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {step.status === 'COMPLETED' && (
                      <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-md border border-emerald-200 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        Done {step.timestamp && `@ ${step.timestamp}`}
                      </span>
                    )}

                    {step.status === 'PENDING' && (
                      <button
                        onClick={() => runSingleStep(step.step_id)}
                        disabled={isRunningScenario}
                        className="px-2.5 py-1 bg-white hover:bg-slate-100 border border-ink-line rounded-lg text-[11px] font-bold text-ink flex items-center gap-1 shadow-sm transition-colors disabled:opacity-50"
                      >
                        <Play className="w-3 h-3 text-blossom-600" /> Run Step
                      </button>
                    )}

                    {step.status === 'COMPLETED' && (
                      <button
                        onClick={() => setExpandedStepId(isExpanded ? null : step.step_id)}
                        className="p-1 rounded text-ink-muted hover:text-ink hover:bg-slate-100 transition-colors"
                        title="Toggle payload details"
                      >
                        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      </button>
                    )}
                  </div>
                </div>

                {/* Expanded Details Drawer */}
                {isExpanded && step.details && (
                  <div className="px-4 pb-4 pt-1 border-t border-slate-100 text-xs">
                    <div className="bg-slate-900 text-slate-100 rounded-lg p-3 font-mono text-[11px] overflow-x-auto shadow-inner max-h-48">
                      <pre>{JSON.stringify(step.details, null, 2)}</pre>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-ink-line flex items-center justify-between text-xs text-ink-muted">
          <span>AICTE Approval & Regulatory Compliance Decision Support System • APH Cycle 2024–27</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-200 hover:bg-slate-300 rounded-lg font-semibold text-ink text-xs transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
