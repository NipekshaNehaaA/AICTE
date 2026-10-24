'use client';

import React, { useState } from 'react';
import { useApp } from '@/lib/app-context';
import { apiFetch } from '@/lib/api';
import {
  Workflow,
  Sparkles,
  CheckCircle2,
  FileText,
  ShieldCheck,
  ArrowRight,
  BookOpen,
  Info,
} from 'lucide-react';

export const APHCompilerView: React.FC = () => {
  const { currentUser } = useApp();
  const [compiledDraft, setCompiledDraft] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [isActivated, setIsActivated] = useState(false);

  const handleRunCompiler = async () => {
    try {
      setLoading(true);
      const data = await apiFetch<any>('/api/v1/differentiators/aph-compiler', {
        method: 'POST',
        body: JSON.stringify({ aph_edition: '2024-25 to 2026-27' }),
      });
      setCompiledDraft(data);
    } catch (err: any) {
      alert(`Error running APH compiler: ${err?.message || 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveRuleset = async () => {
    if (!compiledDraft) return;
    try {
      const data = await apiFetch<any>(`/api/v1/differentiators/aph-compiler/${compiledDraft.draft_id}/approve`, {
        method: 'POST',
      });
      setIsActivated(true);
      alert('APH 2024-27 Ruleset officially approved and activated! The rules engine now operates on verified statutory clauses.');
    } catch (err: any) {
      alert(`Approval Failed: ${err?.message || 'Error approving compiled ruleset.'}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-ink-line p-4 shadow-soft flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Workflow className="w-5 h-5 text-blossom-600" />
            <h1 className="text-lg font-bold text-ink-strong">
              APH-to-Rules Compiler with Clause Provenance
            </h1>
            <span className="bg-blossom-100 text-blossom-700 text-[10px] font-bold px-2 py-0.5 rounded border border-blossom-300">
              Signature Differentiator 1
            </span>
          </div>
          <p className="text-xs text-ink-muted mt-0.5">
            Parses official APH handbook text into versioned rules. Every routing decision links to an exact clause and page.
          </p>
        </div>

        <button
          onClick={handleRunCompiler}
          disabled={loading}
          className="btn-primary !text-xs"
        >
          <Sparkles className="w-4 h-4" /> {loading ? 'Compiling Handbook...' : 'Run APH Compiler'}
        </button>
      </div>

      {/* Two Column Layout: Current Active Rules vs Newly Compiled Draft */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Current Active Ruleset */}
        <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <div>
              <h2 className="text-sm font-bold text-ink-strong">Active Ruleset in Production</h2>
              <div className="text-[11px] text-ink-muted">
                {isActivated ? 'Version: APH-2024-27-OFFICIAL-V1' : 'Version: APH-2024-27-SAMPLE-V1'}
              </div>
            </div>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
              isActivated ? 'bg-mint-100 text-mint-700' : 'bg-amberState-100 text-amberState-700'
            }`}>
              {isActivated ? 'Statutory Active' : 'Sample Configurable'}
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-lg border border-ink-line space-y-1">
              <div className="font-bold text-ink-strong">Pipeline Routing: Extension of Approval (EoA)</div>
              <div className="text-[11px] text-ink">Pipeline: <code>ONLY_SELF_DISCLOSURE</code></div>
              <div className="text-[10px] text-blossom-600 font-semibold font-mono">
                Chapter II, Clause 2.5 (Page 15)
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-ink-line space-y-1">
              <div className="font-bold text-ink-strong">Pipeline Routing: New Technical Institution</div>
              <div className="text-[11px] text-ink">Pipeline: <code>SCRUTINY_EVC</code></div>
              <div className="text-[10px] text-blossom-600 font-semibold font-mono">
                Chapter I, Clause 1.8 & 1.9 (Pages 7-8)
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-ink-line space-y-1">
              <div className="font-bold text-ink-strong">Land & Lease Validity Requirement</div>
              <div className="text-[11px] text-ink">Norm: Minimum 30-year live registered lease deed.</div>
              <div className="text-[10px] text-blossom-600 font-semibold font-mono">
                Chapter II Clause 2.1(e) & Chapter VI Clause 6.17(a) (Pages 12, 56)
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-ink-line space-y-1">
              <div className="font-bold text-ink-strong">Standing Appellate Committee (SAC) Appeal Window</div>
              <div className="text-[11px] text-ink">Norm: Mandatory 7-day appeal filing window.</div>
              <div className="text-[10px] text-blossom-600 font-semibold font-mono">
                Chapter I Clause 1.11(a) / Chapter II Clause 2.24(a) (Pages 9, 29)
              </div>
            </div>
          </div>
        </div>

        {/* Right: Compiled Draft with Diff & Human Gate */}
        <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <div>
              <h2 className="text-sm font-bold text-ink-strong flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-blossom-600" /> Compiled Draft (SUGGEST-ONLY)
              </h2>
              <div className="text-[11px] text-ink-muted">Extracted from AICTE APH 2024-27 Handbook</div>
            </div>
            {compiledDraft && (
              <span className="bg-mint-100 text-mint-700 text-[10px] font-bold px-2 py-0.5 rounded">
                Confidence: {Math.round(compiledDraft.confidence_score * 100)}%
              </span>
            )}
          </div>

          {compiledDraft ? (
            <div className="space-y-3 text-xs">
              {/* Extractor Engine Label Banner */}
              <div className={`p-2.5 rounded-lg border text-xs font-medium flex items-center justify-between ${
                compiledDraft.is_offline_extractor
                  ? 'bg-amberState-100/60 border-amberState-700/30 text-amberState-700'
                  : 'bg-blossom-100/60 border-blossom-300 text-blossom-700'
              }`}>
                <span>
                  Parser: <strong>{compiledDraft.is_offline_extractor ? 'OFFLINE DETERMINISTIC EXTRACTOR' : (compiledDraft.extractor_model || 'LLM Adapter')}</strong>
                  {compiledDraft.is_offline_extractor && ' (Regex over PDF; no external LLM key)'}
                </span>
                <span className="font-mono text-[10px] font-bold">
                  {compiledDraft.all_verified ? '100% VERIFIED' : 'CITATIONS AUDITED'}
                </span>
              </div>

              {/* Mandatory AI Draft Banner */}
              <div className="ai-draft-card p-3 text-xs space-y-1">
                <div className="font-bold text-blossom-700 flex items-center gap-1">
                  <ShieldCheck className="w-4 h-4 text-blossom-600" />
                  AI draft. Decision reserved for the competent authority.
                </div>
                <p className="text-[11px] text-ink">
                  A new APH cycle is a config change, not a code change. Review verified rules and YAML diff below before activation.
                </p>
              </div>

              {/* Verified Rule Citations List */}
              {compiledDraft.rules && compiledDraft.rules.length > 0 && (
                <div className="space-y-2 border border-ink-line rounded-lg p-3 bg-slate-50/50">
                  <div className="font-bold text-[11px] text-ink-strong flex items-center justify-between">
                    <span>Automatic Verifier Results (Verbatim Text Checks):</span>
                    <span className="text-[10px] font-mono text-ink-muted">
                      Pass Rate: {Math.round(compiledDraft.confidence_score * 100)}%
                    </span>
                  </div>
                  <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                    {compiledDraft.rules.map((rule: any, idx: number) => {
                      const isVer = rule.verification_status === 'VERIFIED';
                      return (
                        <div
                          key={idx}
                          className="p-2 rounded bg-white border border-ink-line flex items-start justify-between gap-2 text-[11px]"
                        >
                          <div className="space-y-0.5">
                            <div className="font-semibold text-ink-strong">
                              {rule.clause_id} <span className="text-ink-muted font-normal">(Page {rule.page_number})</span>
                            </div>
                            <div className="text-[10px] text-ink-muted italic line-clamp-1">
                              &ldquo;{rule.verbatim_quote}&rdquo;
                            </div>
                          </div>
                          <span
                            className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded whitespace-nowrap ${
                              isVer
                                ? 'bg-mint-100 text-mint-700 border border-mint-700/30'
                                : 'bg-roseState-100 text-roseState-700 border border-roseState-700/30'
                            }`}
                          >
                            {rule.verification_status || 'VERIFIED'}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* YAML Code Block */}
              <pre className="p-3 bg-slate-900 text-ink-ivory rounded-lg text-[11px] font-mono overflow-x-auto max-h-48">
                {compiledDraft.compiled_yaml}
              </pre>

              {/* Human Approval Gate */}
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[11px] text-ink-muted">Enforcing SoD: Requester != Approver</span>
                <button
                  onClick={handleApproveRuleset}
                  disabled={isActivated || !compiledDraft.all_verified}
                  className="btn-primary !text-xs !py-1.5"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {isActivated ? 'Ruleset Activated' : 'Approve & Activate Version'}
                </button>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center text-xs text-ink-muted border border-dashed border-ink-line rounded-lg">
              Click &quot;Run APH Compiler&quot; above to parse the official 2024-27 handbook and generate the versioned rules diff.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
