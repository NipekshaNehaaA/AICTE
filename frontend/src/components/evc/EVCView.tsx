'use client';

import React, { useState, useEffect } from 'react';
import { useApp } from '@/lib/app-context';
import { apiFetch, API_BASE } from '@/lib/api';
import {
  CalendarCheck,
  MapPin,
  Clock,
  UserCheck,
  CheckCircle2,
  AlertTriangle,
  Building,
  Sparkles,
  ShieldCheck,
  Video,
  FileCheck2,
  X,
  Calendar,
  ShieldAlert,
} from 'lucide-react';

export const EVCView: React.FC = () => {
  const { currentUser, currentRegion } = useApp();

  const [queue, setQueue] = useState<any[]>([]);
  const [selectedCase, setSelectedCase] = useState<any | null>(null);
  const [smartProposal, setSmartProposal] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  // Report modal state
  const [showReportModal, setShowReportModal] = useState(false);
  const [recommendation, setRecommendation] = useState('RECOMMENDED');
  const [summaryText, setSummaryText] = useState('All laboratories, instructional areas, and faculty appointments verified in accordance with Chapter VI norms.');
  const [geoLat, setGeoLat] = useState(12.9716);
  const [geoLng, setGeoLng] = useState(77.5946);

  const getAuthHeaders = () => {
    const token = currentUser.token || (typeof window !== 'undefined' ? localStorage.getItem('aicte_auth_token') : '') || '';
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  };

  const fetchQueue = async () => {
    try {
      setLoading(true);
      const data = await apiFetch<any>(`/api/v1/evc/queue?region_code=${currentRegion.code}`);
      setQueue(data.queue || []);
      if (data.queue && data.queue.length > 0 && !selectedCase) {
        setSelectedCase(data.queue[0]);
      }
    } catch (err) {
      console.error('Failed to fetch EVC queue', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchSmartProposal = async (appId: string) => {
    try {
      const data = await apiFetch<any>('/api/v1/evc/suggest-panel', {
        method: 'POST',
        body: JSON.stringify({ application_id: appId, proposed_date: '2026-10-30', mode: 'ON_SITE' }),
      });
      setSmartProposal(data);
    } catch (err) {
      console.error('Failed to fetch smart proposal', err);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [currentRegion]);

  useEffect(() => {
    if (selectedCase) {
      fetchSmartProposal(selectedCase.application_id);
    }
  }, [selectedCase]);

  // Confirm EVC Schedule
  const handleConfirmSchedule = async () => {
    if (!selectedCase) return;
    try {
      const data = await apiFetch<any>(`/api/v1/evc/${selectedCase.application_id}/confirm`, {
        method: 'POST',
        body: JSON.stringify({ selected_member_ids: ['exp-01', 'exp-02', 'exp-03'] }),
      });
      alert(`EVC Panel officially confirmed for ${data.scheduled_date}! Stamped in audit ledger.`);
      fetchQueue();
    } catch (err: any) {
      alert(`Confirmation Failed: ${err?.message || 'Error confirming EVC schedule.'}`);
    }
  };

  // Submit EVC Report
  const handleSubmitReport = async () => {
    if (!selectedCase) return;
    try {
      const data = await apiFetch<any>(`/api/v1/evc/reports/${selectedCase.application_id}/submit`, {
        method: 'POST',
        body: JSON.stringify({
          recommendation,
          inspection_summary: summaryText,
          deficiencies: [],
          geo_lat: geoLat,
          geo_lng: geoLng,
        }),
      });
      alert(`Geotagged EVC Report submitted with verdict [${data.recommendation}]! Advanced to Executive Committee.`);
      setShowReportModal(false);
      fetchQueue();
    } catch (err: any) {
      alert(`Report submission failed: ${err?.message || 'Error submitting report.'}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-ink-line p-4 shadow-soft flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-ink-strong">
              Expert Visit Committee (EVC) Inspection Hub
            </h1>
            <span className="bg-blossom-100 text-blossom-700 text-[11px] font-bold px-2 py-0.5 rounded border border-blossom-300">
              Clause 1.9 & Annexure-16 Compliant
            </span>
          </div>
          <p className="text-xs text-ink-muted mt-0.5">
            Smart conflict-free panel allocation, 30-min geotagged video verification, and statutory inspection reports.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-ink font-semibold">
            Region: <strong className="text-blossom-700">{currentRegion.name}</strong>
          </span>
        </div>
      </div>

      {/* Grid: Left EVC Queue (1 Col), Right Panel Inspector & Scheduler (2 Cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Col: Inspection Queue */}
        <div className="lg:col-span-1 bg-white rounded-xl border border-ink-line shadow-soft flex flex-col h-[650px] overflow-hidden">
          <div className="p-3 bg-slate-50 border-b border-ink-line font-bold text-xs text-ink-strong flex items-center justify-between">
            <span>Inspection Queue ({queue.length})</span>
            <span className="text-[10px] text-ink-muted">15-Day SLA</span>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
            {queue.map((item) => {
              const isSelected = selectedCase?.application_id === item.application_id;
              return (
                <div
                  key={item.application_id}
                  onClick={() => setSelectedCase(item)}
                  className={`p-3 cursor-pointer transition-all ${
                    isSelected ? 'bg-blossom-100/70 border-l-4 border-blossom-600' : 'hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs text-ink-strong font-mono">{item.application_no}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                      item.panel_status === 'CONFIRMED'
                        ? 'bg-mint-100 text-mint-700'
                        : 'bg-amberState-100 text-amberState-700'
                    }`}>
                      {item.panel_status.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="text-xs text-ink font-semibold truncate">{item.institution_name}</div>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-ink-muted">
                    <span>{item.application_type.replace('_', ' ')}</span>
                    <span className="font-mono text-blossom-600 font-semibold">{item.sla_deadline}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right 2 Cols: Smart Panel Proposal & Actions */}
        <div className="lg:col-span-2 space-y-6">
          {selectedCase && smartProposal ? (
            <>
              {/* Selected Case Overview */}
              <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-base font-bold text-ink-strong">
                        {selectedCase.institution_name}
                      </h2>
                      <span className="text-xs bg-slate-100 text-ink px-2 py-0.5 rounded font-mono">
                        {selectedCase.application_no}
                      </span>
                    </div>
                    <div className="text-xs text-ink mt-1 flex items-center gap-3">
                      <span><strong>Type:</strong> {selectedCase.application_type}</span>
                      <span><strong>Stage:</strong> {selectedCase.current_stage}</span>
                      <span><strong>Region:</strong> {selectedCase.region}</span>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-[10px] font-bold text-ink-muted uppercase block">Inspection Mode</span>
                    <span className="text-xs font-bold text-blossom-700 bg-blossom-100 px-2.5 py-0.5 rounded border border-blossom-300">
                      Physical On-Site (30-Min Video)
                    </span>
                  </div>
                </div>

                {/* SMART PANEL PROPOSAL (SUGGEST-ONLY) */}
                <div className="ai-draft-card p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-blossom-600" />
                      <h3 className="text-xs font-bold text-ink-strong uppercase tracking-wider">
                        Smart Expert Panel Proposal (Annexure-16 Clause 16.5)
                      </h3>
                    </div>
                    <span className="bg-blossom-100 text-blossom-700 text-[10px] font-bold px-2 py-0.5 rounded border border-blossom-300">
                      SUGGEST-ONLY
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {smartProposal.suggested_panel.map((exp: any) => (
                      <div key={exp.id} className="p-3 bg-slate-50 rounded-lg border border-ink-line text-xs space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-ink-strong">{exp.name}</span>
                          <span className="text-[10px] font-bold bg-white text-ink px-1.5 py-0.5 rounded border border-slate-200">
                            {exp.state}
                          </span>
                        </div>
                        <div className="text-[10px] text-blossom-600 font-semibold">{exp.role_in_panel}</div>
                        <div className="text-[11px] text-ink-muted">{exp.expertise}</div>
                        {exp.inclusion_rationale && (
                          <div className="text-[10px] text-ink-muted bg-white p-1.5 rounded border border-slate-200 italic leading-snug">
                            {exp.inclusion_rationale}
                          </div>
                        )}
                        <div className="mt-1 pt-1 border-t border-slate-200 text-[10px] text-mint-700 font-bold flex items-center justify-between">
                          <span className="flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" /> No Conflict
                          </span>
                          <span className="text-ink-muted font-normal font-mono">
                            Load: {exp.workload_active_visits || 0} visits
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Excluded Candidates Strip */}
                  {smartProposal.excluded_candidates && smartProposal.excluded_candidates.length > 0 && (
                    <div className="p-3 bg-roseState-100/20 rounded-lg border border-roseState-700/20 text-xs space-y-2">
                      <div className="flex items-center gap-1.5 font-bold text-roseState-700">
                        <ShieldAlert className="w-3.5 h-3.5" />
                        <span>Excluded Candidates (Conflict Prevention & Cooling Enforcement):</span>
                      </div>
                      <div className="space-y-1">
                        {smartProposal.excluded_candidates.map((exc: any, ei: number) => (
                          <div key={ei} className="flex flex-wrap items-center justify-between gap-2 text-[11px] bg-white p-2 rounded border border-roseState-700/10">
                            <span className="font-semibold text-ink-strong">{exc.name}</span>
                            <span className="text-roseState-700 font-mono text-[10px] bg-roseState-100/50 px-1.5 py-0.5 rounded">
                              {exc.reason}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="text-[10px] text-ink-muted bg-white p-2 rounded border border-slate-200 flex items-center gap-2">
                    <ShieldCheck className="w-3.5 h-3.5 text-mint-700 shrink-0" />
                    <span>Statutory Rule: Panel composition verified against Annexure-16 Clause 16.5 (Academician + Industry Expert + Registered Architect).</span>
                  </div>
                </div>

                {/* Actions Bar */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={handleConfirmSchedule}
                      className="btn-primary !text-xs !py-1.5"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" /> Confirm Panel & Schedule (HUMAN-ONLY)
                    </button>
                    {selectedCase.panel_id && (
                      <a
                        href={`${API_BASE}/api/v1/evc/schedule/${selectedCase.panel_id}/ics`}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-secondary !text-xs !py-1.5 text-ink border-ink-line hover:bg-slate-100 flex items-center gap-1.5"
                      >
                        <Calendar className="w-3.5 h-3.5 text-blossom-600" /> Export .ics Calendar Invite
                      </a>
                    )}
                    <button
                      onClick={() => setShowReportModal(true)}
                      className="btn-secondary !text-xs !py-1.5 text-blossom-600 border-blossom-300 hover:bg-blossom-100"
                    >
                      <FileCheck2 className="w-3.5 h-3.5" /> Submit Geotagged Report
                    </button>
                  </div>

                  <span className="text-[11px] text-ink-muted">
                    Clause 1.9(g): 30-min recording link to be verified
                  </span>
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white rounded-xl border border-ink-line p-12 text-center text-xs text-ink-muted shadow-soft">
              Select an application from the queue to view inspection details.
            </div>
          )}
        </div>
      </div>

      {/* REPORT SUBMISSION MODAL */}
      {showReportModal && (
        <div className="fixed inset-0 bg-ink-strong/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-card border border-ink-line w-full max-w-lg p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                <FileCheck2 className="w-4 h-4 text-blossom-600" /> Submit Official EVC Inspection Report
              </h3>
              <button onClick={() => setShowReportModal(false)}><X className="w-4 h-4 text-ink-muted" /></button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-ink-strong block mb-1">Inspection Recommendation</label>
                <select
                  value={recommendation}
                  onChange={(e) => setRecommendation(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs"
                >
                  <option value="RECOMMENDED">RECOMMENDED (Nil Deficiency - Proceed to LoA/EoA)</option>
                  <option value="CONDITIONAL">CONDITIONAL (Subject to Time-Bound Undertaking)</option>
                  <option value="NOT_RECOMMENDED">NOT RECOMMENDED (Deficiencies Noted - Issue LoD/LoR)</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-ink-strong block mb-1">Inspection Findings & Summary</label>
                <textarea
                  rows={4}
                  value={summaryText}
                  onChange={(e) => setSummaryText(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-2 bg-slate-50 p-3 rounded-lg border border-ink-line">
                <div>
                  <label className="text-[10px] font-bold text-ink-muted uppercase block">GPS Latitude (Geotag)</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={geoLat}
                    onChange={(e) => setGeoLat(parseFloat(e.target.value))}
                    className="w-full p-1.5 bg-white border border-ink-line rounded text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-ink-muted uppercase block">GPS Longitude (Geotag)</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={geoLng}
                    onChange={(e) => setGeoLng(parseFloat(e.target.value))}
                    className="w-full p-1.5 bg-white border border-ink-line rounded text-xs font-mono"
                  />
                </div>
              </div>

              <div className="bg-blossom-100 p-2.5 rounded-lg border border-blossom-300 text-[11px] text-ink">
                <strong>Non-Repudiation:</strong> EVC reports submitted with geotags and timestamped signatures are permanently chained in the immutable audit ledger.
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button onClick={() => setShowReportModal(false)} className="btn-secondary !text-xs">Cancel</button>
              <button onClick={handleSubmitReport} className="btn-primary !text-xs">
                Submit & Sign Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
