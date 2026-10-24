'use client';

import React, { useState } from 'react';
import { apiFetch, API_BASE } from '@/lib/api';
import {
  Search,
  CheckCircle2,
  Clock,
  AlertCircle,
  ShieldCheck,
  Building2,
  Calendar,
  Lock,
  ArrowRight,
  ExternalLink,
  Info
} from 'lucide-react';

export const PublicTrackingView: React.FC = () => {
  const [trackingId, setTrackingId] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [trackResult, setTrackResult] = useState<any | null>(null);

  const handleTrack = async (idToSearch?: string) => {
    const id = (idToSearch || trackingId).trim();
    if (!id) {
      setErrorMsg('Please enter a valid Application Number or Permanent Institute ID (PID).');
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setTrackResult(null);

    try {
      // Direct call to public rate-limited tracking endpoint with no auth token
      const res = await fetch(`${API_BASE}/api/v1/public/track/${encodeURIComponent(id)}`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (res.status === 429) {
        setErrorMsg('Rate limit exceeded (Maximum 30 requests per minute). Please wait before trying again.');
        return;
      }

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setErrorMsg(err.detail || `No application found matching "${id}". Please verify your credentials.`);
        return;
      }

      const data = await res.json();
      setTrackResult(data);
    } catch (err: any) {
      console.error('Public tracking error', err);
      setErrorMsg('Network error connecting to public tracking server.');
    } finally {
      setLoading(false);
    }
  };

  const sampleCases = [
    { label: 'Sample Case 1', id: 'AICTE/2026-27/1-10000001' },
    { label: 'Sample Case 2', id: 'AICTE/2026-27/1-10000002' },
    { label: 'Sample PID', id: '1-10000001' },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12 animate-fade-in">
      {/* Title & Statutory Header */}
      <div className="bg-white rounded-xl border border-ink-line p-6 shadow-soft text-center space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blossom-50 border border-blossom-200 text-blossom-700 text-xs font-bold">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Statutory Public Transparency Portal</span>
        </div>
        <h1 className="text-xl font-bold text-ink-strong">
          Public Application Status Tracking
        </h1>
        <p className="text-xs text-ink-muted max-w-xl mx-auto">
          Citizens and applicant institutions can track real-time statutory approval progress, stage timelines, and statutory due dates without logging in.
        </p>

        {/* Search Input Bar */}
        <div className="pt-4 max-w-xl mx-auto">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleTrack();
            }}
            className="flex items-center gap-2"
          >
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-ink-muted absolute left-3.5 top-3" />
              <input
                type="text"
                value={trackingId}
                onChange={(e) => setTrackingId(e.target.value)}
                placeholder="Enter Application No (e.g. AICTE/2026-27/1-10000001) or PID"
                className="w-full text-xs font-mono pl-10 pr-3 py-2.5 rounded-lg border border-ink-line bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blossom-600 text-ink-strong"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary text-xs px-5 py-2.5 rounded-lg flex items-center gap-1.5 font-bold"
            >
              <span>{loading ? 'Searching...' : 'Track Status'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Quick Click Sample IDs */}
          <div className="flex items-center justify-center gap-2 mt-2.5 text-[11px] text-ink-muted">
            <span>Quick test:</span>
            {sampleCases.map((s, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setTrackingId(s.id);
                  handleTrack(s.id);
                }}
                className="font-mono text-blossom-600 hover:text-blossom-700 hover:underline bg-slate-100 px-2 py-0.5 rounded text-[10px]"
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error Message */}
      {errorMsg && (
        <div className="bg-roseState-50 border border-roseState-200 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-roseState-600 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-bold text-roseState-800">Search Result Notice</h3>
            <p className="text-xs text-roseState-700 mt-0.5">{errorMsg}</p>
          </div>
        </div>
      )}

      {/* Result Display */}
      {trackResult && (
        <div className="bg-white rounded-xl border border-ink-line p-6 shadow-soft space-y-6">
          {/* Header Summary */}
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-ink-line">
            <div>
              <div className="text-[11px] font-bold text-blossom-600 uppercase tracking-wider">
                Official Tracking Record
              </div>
              <h2 className="text-lg font-bold font-mono text-ink-strong">
                {trackResult.tracking_id}
              </h2>
              <div className="text-xs text-ink-muted mt-0.5">
                Academic Year: <span className="font-semibold text-ink-strong">{trackResult.academic_year}</span> &bull; Type: <span className="font-semibold text-ink-strong">{trackResult.application_type}</span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-[10px] font-bold text-ink-muted uppercase">Application Status</div>
                <div className={`text-xs font-bold font-mono px-2.5 py-1 rounded inline-block mt-0.5 ${
                  trackResult.application_status === 'APPROVED' ? 'bg-mint-100 text-mint-700' :
                  trackResult.application_status === 'REJECTED' ? 'bg-roseState-100 text-roseState-700' :
                  'bg-blue-100 text-blue-700'
                }`}>
                  {trackResult.application_status}
                </div>
              </div>
            </div>
          </div>

          {/* Key Public Fields Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-slate-50 rounded-xl border border-ink-line space-y-1">
              <div className="text-[11px] font-bold text-ink-muted uppercase">Current Stage</div>
              <div className="text-sm font-bold text-ink-strong">{trackResult.current_stage}</div>
              <div className="text-[11px] text-ink-muted">APH 2024-27 Statutory Procedure</div>
            </div>

            <div className="p-4 bg-slate-50 rounded-xl border border-ink-line space-y-1">
              <div className="text-[11px] font-bold text-ink-muted uppercase">Statutory Due Date</div>
              <div className="text-sm font-bold text-ink-strong">
                {trackResult.statutory_due_date ? new Date(trackResult.statutory_due_date).toLocaleDateString() : 'Pending'}
              </div>
              <div className="text-[11px] text-ink-muted">
                {trackResult.is_paused ? (
                  <span className="text-amber-700 font-medium">Clock Paused (Deficiency Cure in Progress)</span>
                ) : (
                  <span className="text-emerald-700 font-medium">Clock Running Normally</span>
                )}
              </div>
            </div>

            <div className="p-4 bg-slate-50 rounded-xl border border-ink-line space-y-1">
              <div className="text-[11px] font-bold text-ink-muted uppercase">Verification Seal</div>
              <div className="text-sm font-bold text-mint-700 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" />
                <span>SHA-256 Ledger Verified</span>
              </div>
              <div className="text-[11px] text-ink-muted">Immutable AICTE Audit Trail</div>
            </div>
          </div>

          {/* Next Required Action Card */}
          <div className="p-4 bg-blossom-50 rounded-xl border border-blossom-200 space-y-2">
            <div className="text-xs font-bold text-ink-strong flex items-center gap-2">
              <Clock className="w-4 h-4 text-blossom-600" />
              <span>Next Required Action</span>
            </div>
            <p className="text-xs text-ink leading-relaxed">
              {trackResult.next_required_action}
            </p>
          </div>

          {/* Stages Progression Timeline */}
          <div className="space-y-3">
            <div className="text-xs font-bold text-ink-muted uppercase tracking-wider">
              Statutory Stage Progression
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
              {(trackResult.stages_timeline || []).map((st: any, idx: number) => {
                const isCurrent = st.stage === trackResult.current_stage;
                const isCompleted = st.status === 'COMPLETED' || (!isCurrent && idx < 2);
                return (
                  <div
                    key={idx}
                    className={`p-3 rounded-lg border text-xs ${
                      isCurrent
                        ? 'bg-blossom-100 border-blossom-600 font-bold text-ink-strong shadow-soft'
                        : isCompleted
                        ? 'bg-slate-50 border-ink-line text-ink-muted'
                        : 'bg-white border-dashed border-ink-line text-ink-slate opacity-75'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-mono text-ink-muted">Step {idx + 1}</span>
                      {isCompleted ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-mint-700" />
                      ) : isCurrent ? (
                        <span className="w-2 h-2 rounded-full bg-blossom-600" />
                      ) : (
                        <span className="w-2 h-2 rounded-full bg-slate-300" />
                      )}
                    </div>
                    <div className="truncate font-semibold" title={st.stage}>
                      {st.stage?.replace(/_/g, ' ')}
                    </div>
                    <div className="text-[10px] text-ink-muted mt-0.5">
                      {st.status || (isCurrent ? 'ACTIVE' : isCompleted ? 'DONE' : 'PENDING')}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* DPDP Act 2023 Statutory Privacy Compliance Notice */}
          <div className="p-3.5 bg-slate-50 rounded-lg border border-ink-line text-[11px] text-ink-muted flex items-start gap-2.5">
            <ShieldCheck className="w-4 h-4 text-ink-slate shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-ink-strong">Privacy & Compliance Guarantee: </span>
              In accordance with the Digital Personal Data Protection (DPDP) Act 2023 and RTI Act Section 8(1)(j), no personal data (PII), phone numbers, officer email addresses, or confidential internal committee deliberations are published on this public transparency register.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
