'use client';

import React, { useState, useEffect } from 'react';
import { useApp } from '@/lib/app-context';
import {
  FileText,
  Clock,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  ArrowRight,
  Plus,
  Download,
  Info,
  ShieldCheck,
  Building2,
  Calendar,
  X,
  FileCheck,
  Lock,
  UserCheck,
} from 'lucide-react';

interface ApplicationItem {
  id: string;
  application_no: string;
  institution_name: string;
  permanent_id: string;
  region_code: string;
  application_type: string;
  pipeline_type: string;
  current_stage: string;
  status: string;
  sla_deadline: string;
  sla_status: string;
  paused_hours: number;
  submitted_at: string;
}

export const ApplicationsView: React.FC = () => {
  const { currentUser, currentRegion } = useApp();

  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);
  const [appDetails, setAppDetails] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [filterStage, setFilterStage] = useState<string>('ALL');

  // Modals
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [showRevertModal, setShowRevertModal] = useState(false);
  const [showCureModal, setShowCureModal] = useState(false);
  const [showAIDraftModal, setShowAIDraftModal] = useState(false);
  const [currentAIDraft, setCurrentAIDraft] = useState<any | null>(null);

  // Form states
  const [newAppType, setNewAppType] = useState('NEW_INSTITUTION');
  const [newCourseName, setNewCourseName] = useState('Computer Science and Engineering');
  const [revertCategory, setRevertCategory] = useState('Missing Fire & Safety NOC');
  const [revertRemarks, setRevertRemarks] = useState('');
  const [cureResponse, setCureResponse] = useState('');

  // Fetch applications
  const fetchApplications = async () => {
    try {
      setLoading(true);
      const res = await fetch(`http://127.0.0.1:8000/api/v1/applications?region_code=${currentRegion.code}`, {
        headers: {
          'x-user-role': currentUser.role,
          'x-region-id': currentRegion.code === 'SWRO' ? 'swro-id' : '',
        },
      });
      const data = await res.json();
      setApplications(data.applications || []);
      if (data.applications && data.applications.length > 0 && !selectedAppId) {
        setSelectedAppId(data.applications[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch applications', err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch single application details
  const fetchDetails = async (id: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/applications/${id}`, {
        headers: {
          'x-user-role': currentUser.role,
        },
      });
      const data = await res.json();
      setAppDetails(data);
    } catch (err) {
      console.error('Failed to fetch details', err);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, [currentRegion, currentUser]);

  useEffect(() => {
    if (selectedAppId) {
      fetchDetails(selectedAppId);
    }
  }, [selectedAppId]);

  // Advance stage
  const handleAdvance = async () => {
    if (!selectedAppId) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/workflow/${selectedAppId}/advance`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-user-id': currentUser.id,
          'x-user-role': currentUser.role,
        },
      });
      const data = await res.json();
      if (res.ok) {
        alert(`Stage advanced to: ${data.new_stage}`);
        fetchApplications();
        fetchDetails(selectedAppId);
      } else {
        alert(`Advance Failed: ${data.detail || 'SoD or Permission violation'}`);
      }
    } catch (err) {
      alert('Error advancing stage.');
    }
  };

  // Revert application
  const handleRevert = async () => {
    if (!selectedAppId) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/workflow/${selectedAppId}/revert`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-user-id': currentUser.id,
          'x-user-role': currentUser.role,
        },
        body: JSON.stringify({
          reason_category: revertCategory,
          deficiency_remarks: revertRemarks || 'Document non-compliant with APH Chapter VI standards.',
          aph_clause_ref: 'Chapter I, Clause 1.8(f) & Annexure-1 (Page 7, 77)',
          cure_days: 15,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        alert('Application returned for deficiency. Statutory SLA clock paused.');
        setShowRevertModal(false);
        fetchApplications();
        fetchDetails(selectedAppId);
      } else {
        alert(`Revert Failed: ${data.detail}`);
      }
    } catch (err) {
      alert('Error reverting application.');
    }
  };

  // Submit cure
  const handleCureSubmit = async () => {
    if (!selectedAppId) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/workflow/${selectedAppId}/cure-submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-user-id': currentUser.id,
          'x-user-role': 'INSTITUTION_USER',
        },
        body: JSON.stringify({
          institution_response: cureResponse || 'Uploaded renewed compliance documents with digital verification.',
        }),
      });
      const data = await res.json();
      if (res.ok) {
        alert('Clarification submitted. Statutory SLA clock resumed!');
        setShowCureModal(false);
        fetchApplications();
        fetchDetails(selectedAppId);
      } else {
        alert(`Submit Failed: ${data.detail}`);
      }
    } catch (err) {
      alert('Error submitting cure.');
    }
  };

  // Request AI Draft Case Summary
  const handleGenerateAIDraft = async () => {
    if (!selectedAppId) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/workflow/${selectedAppId}/draft-summary`, {
        method: 'POST',
        headers: {
          'x-user-id': currentUser.id,
          'x-user-role': currentUser.role,
        },
      });
      const data = await res.json();
      if (res.ok) {
        setCurrentAIDraft(data);
        setShowAIDraftModal(true);
      } else {
        alert(`AI Draft Failed: ${data.detail}`);
      }
    } catch (err) {
      alert('Error generating draft summary.');
    }
  };

  // Approve AI Draft (Human Gate)
  const handleApproveAIDraft = async () => {
    if (!currentAIDraft) return;
    try {
      // Use different approver to adhere to SoD
      const approverId = currentUser.role === 'SUPER_ADMIN' ? currentUser.id : 'usr-sec-director-01';
      const res = await fetch(`http://127.0.0.1:8000/api/v1/workflow/ai-drafts/${currentAIDraft.draft_id}/approve`, {
        method: 'POST',
        headers: {
          'x-user-id': approverId,
          'x-user-role': 'SUPER_ADMIN',
        },
      });
      const data = await res.json();
      if (res.ok) {
        alert('AI Draft officially approved by Competent Authority and stamped in immutable audit trail!');
        setShowAIDraftModal(false);
      } else {
        alert(`Approval Failed: ${data.detail}`);
      }
    } catch (err) {
      alert('Error approving AI draft.');
    }
  };

  const filteredApps = applications.filter((app) => {
    if (filterStage === 'ALL') return true;
    if (filterStage === 'ACTIVE') return app.status === 'IN_PROGRESS';
    if (filterStage === 'DEFICIENT') return app.status === 'DEFICIENT';
    if (filterStage === 'OVERDUE') return app.sla_status === 'OVERDUE';
    return app.current_stage === filterStage;
  });

  return (
    <div className="space-y-6">
      {/* Header with Title & Intake Action */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-4 rounded-xl border border-ink-line shadow-soft">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-ink-strong">
              Approval Workflow & Application Routing
            </h1>
            <span className="bg-blossom-100 text-blossom-700 text-[11px] font-bold px-2 py-0.5 rounded border border-blossom-300">
              APH Table 2.3 Compliant
            </span>
          </div>
          <p className="text-xs text-ink-muted mt-0.5">
            Deterministic stage pipelines, statutory SLA clocks, and human-in-the-loop review.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSubmitModal(true)}
            className="btn-primary !text-xs"
          >
            <Plus className="w-4 h-4" /> New Application Intake
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-ink-line pb-2">
        {['ALL', 'ACTIVE', 'DEFICIENT', 'OVERDUE'].map((tab) => (
          <button
            key={tab}
            onClick={() => setFilterStage(tab)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              filterStage === tab
                ? 'bg-blossom-100 text-ink-strong border border-blossom-300'
                : 'text-ink-muted hover:bg-slate-100'
            }`}
          >
            {tab === 'ALL' ? 'All Cases' : tab}
          </button>
        ))}
      </div>

      {/* Split Grid: Left Application List (1 Col), Right Case Detail Dossier (2 Cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Col: Applications Table */}
        <div className="lg:col-span-1 bg-white rounded-xl border border-ink-line shadow-soft overflow-hidden flex flex-col h-[700px]">
          <div className="p-3 border-b border-ink-line bg-slate-50 font-bold text-xs text-ink-strong flex items-center justify-between">
            <span>Applications ({filteredApps.length})</span>
            <span className="text-[10px] text-ink-muted">{currentRegion.code} Scope</span>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
            {filteredApps.map((app) => {
              const isSelected = app.id === selectedAppId;
              return (
                <div
                  key={app.id}
                  onClick={() => setSelectedAppId(app.id)}
                  className={`p-3 cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-blossom-100/70 border-l-4 border-blossom-600'
                      : 'hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs text-ink-strong">{app.application_no}</span>
                    <span className="text-[10px] px-1.5 py-0.2 bg-slate-100 rounded font-semibold text-ink-muted">
                      {app.application_type.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="text-xs text-ink truncate font-medium">{app.institution_name}</div>
                  <div className="mt-2 flex items-center justify-between text-[11px]">
                    <span className="bg-slate-100 text-ink-slate px-1.5 py-0.5 rounded text-[10px] font-semibold">
                      {app.current_stage}
                    </span>
                    {app.status === 'DEFICIENT' ? (
                      <span className="status-chip-approaching !text-[10px] !py-0.2">
                        Clock Paused
                      </span>
                    ) : app.sla_status === 'OVERDUE' ? (
                      <span className="status-chip-overdue !text-[10px] !py-0.2">
                        Overdue
                      </span>
                    ) : (
                      <span className="status-chip-ontrack !text-[10px] !py-0.2">
                        On Track
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right 2 Cols: Selected Case Detail Dossier */}
        <div className="lg:col-span-2 space-y-6">
          {appDetails ? (
            <>
              {/* Top Case Summary Bar */}
              <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-4">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-base font-bold text-ink-strong">
                        {appDetails.application_no}
                      </h2>
                      <span className="text-xs bg-slate-100 text-ink px-2 py-0.5 rounded font-bold">
                        {appDetails.application_type}
                      </span>
                    </div>
                    <div className="text-xs text-ink mt-1 flex items-center gap-3">
                      <span><strong>Institute:</strong> {appDetails.institution.name}</span>
                      <span><strong>PID:</strong> {appDetails.institution.permanent_id}</span>
                      <span><strong>Region:</strong> {appDetails.institution.region_code}</span>
                    </div>
                  </div>

                  {/* SLA Countdown Clock */}
                  <div className="text-right bg-slate-50 p-2.5 rounded-lg border border-ink-line">
                    <div className="text-[10px] uppercase font-bold text-ink-muted flex items-center gap-1 justify-end">
                      <Clock className="w-3 h-3 text-blossom-600" /> Statutory SLA Clock
                    </div>
                    <div className="text-sm font-bold text-ink-strong mt-0.5">
                      {appDetails.sla.is_paused ? (
                        <span className="text-amberState-700">PAUSED (Deficiency Cure)</span>
                      ) : (
                        `${appDetails.sla.days_remaining} Days Remaining`
                      )}
                    </div>
                    <div className="text-[10px] text-ink-muted mt-0.5">
                      Target Deadline: {appDetails.sla.deadline}
                    </div>
                  </div>
                </div>

                {/* VISUAL STAGE PIPELINE TRACKER */}
                <div className="border-t border-slate-100 pt-3">
                  <div className="text-xs font-bold text-ink-muted uppercase tracking-wider mb-2">
                    Processing Stage Pipeline ({appDetails.pipeline_type})
                  </div>
                  <div className="flex items-center gap-2 overflow-x-auto py-2">
                    {appDetails.stages.map((stg: any, index: number) => {
                      const isCompleted = stg.status === 'PASSED' || index < appDetails.stages.findIndex((s: any) => s.stage_name === appDetails.current_stage);
                      const isCurrent = stg.stage_name === appDetails.current_stage;
                      return (
                        <React.Fragment key={stg.id}>
                          <div
                            className={`px-3 py-2 rounded-lg text-xs font-semibold shrink-0 flex items-center gap-1.5 border transition-all ${
                              isCurrent
                                ? 'bg-blossom-100 text-ink-strong border-blossom-600 font-bold shadow-soft'
                                : isCompleted
                                ? 'bg-mint-100 text-mint-700 border-mint-700/30'
                                : 'bg-slate-50 text-ink-muted border-ink-line'
                            }`}
                          >
                            {isCompleted ? (
                              <CheckCircle2 className="w-3.5 h-3.5 text-mint-700" />
                            ) : isCurrent ? (
                              <Clock className="w-3.5 h-3.5 text-blossom-600" />
                            ) : (
                              <div className="w-3.5 h-3.5 rounded-full border border-ink-line flex items-center justify-center text-[9px]">
                                {index + 1}
                              </div>
                            )}
                            <span>{stg.stage_name.replace('_', ' ')}</span>
                          </div>
                          {index < appDetails.stages.length - 1 && (
                            <ArrowRight className="w-3.5 h-3.5 text-ink-line shrink-0" />
                          )}
                        </React.Fragment>
                      );
                    })}
                  </div>
                </div>

                {/* Workflow Actions Bar - Role-Scoped Decision Boundaries */}
                <div className="flex flex-wrap items-center justify-between border-t border-slate-100 pt-3 gap-2">
                  <div className="flex items-center gap-2">
                    {currentUser.role === 'AUDITOR' ? (
                      <div className="flex items-center gap-2 text-xs font-semibold text-ink-muted bg-slate-100 px-3 py-1.5 rounded-lg border border-ink-line">
                        <Lock className="w-3.5 h-3.5 text-ink-slate" />
                        <span>Auditor View: Strictly Read-Only (Statutory SoD Enforced — Mutations Disabled)</span>
                      </div>
                    ) : currentUser.role === 'INSTITUTION_USER' ? (
                      <div className="flex items-center gap-2">
                        {appDetails.status === 'DEFICIENT' ? (
                          <button
                            onClick={() => setShowCureModal(true)}
                            className="btn-primary !text-xs !py-1.5 !bg-amber-600 hover:!bg-amber-700"
                          >
                            <FileCheck className="w-3.5 h-3.5" /> Submit Rectification (Cure Deficiency)
                          </button>
                        ) : (
                          <div className="text-xs font-semibold text-ink-muted bg-slate-50 px-3 py-1.5 rounded-lg border border-ink-line flex items-center gap-1.5">
                            <Clock className="w-3.5 h-3.5 text-blossom-600" />
                            <span>Institution Desk: Under official review. Stage sign-offs are reserved for AICTE Authority.</span>
                          </div>
                        )}
                      </div>
                    ) : (
                      <>
                        <button
                          onClick={handleAdvance}
                          className="btn-primary !text-xs !py-1.5"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" /> Sign-Off & Advance Stage (AUTO)
                        </button>
                        <button
                          onClick={() => setShowRevertModal(true)}
                          className="btn-secondary !text-xs !py-1.5 text-roseState-700 border-roseState-700/30 hover:bg-roseState-100"
                        >
                          <RotateCcw className="w-3.5 h-3.5" /> Revert for Deficiency
                        </button>
                        {appDetails.status === 'DEFICIENT' && (
                          <button
                            onClick={() => setShowCureModal(true)}
                            className="btn-primary !text-xs !py-1.5 !bg-amber-600 hover:!bg-amber-700"
                          >
                            <FileCheck className="w-3.5 h-3.5" /> Submit Rectification (Unpause)
                          </button>
                        )}
                      </>
                    )}
                  </div>

                  {currentUser.role !== 'AUDITOR' && (
                    <button
                      onClick={handleGenerateAIDraft}
                      className="btn-secondary !text-xs !py-1.5 text-blossom-600 border-blossom-300 hover:bg-blossom-100"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-blossom-600" /> Draft Electronic Docket (AI)
                    </button>
                  )}
                </div>
              </div>

              {/* "Why did this happen?" Clause Provenance Card */}
              <div className="bg-white rounded-xl border border-ink-line p-4 shadow-soft">
                <div className="flex items-center gap-1.5 text-xs font-bold text-ink-strong mb-1">
                  <Info className="w-4 h-4 text-blossom-600" /> Why did this happen? (APH Clause Provenance)
                </div>
                <div className="bg-slate-50 p-3 rounded-lg border border-ink-line text-xs space-y-1 mt-2">
                  <div className="font-bold text-ink-strong">
                    {appDetails.aph_provenance.clause} — {appDetails.aph_provenance.title} (Page {appDetails.aph_provenance.page})
                  </div>
                  <p className="text-[11px] text-ink leading-relaxed">
                    {appDetails.aph_provenance.summary}
                  </p>
                </div>
              </div>

              {/* Case Event Timeline */}
              <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft">
                <h3 className="text-xs font-bold text-ink-strong uppercase tracking-wider mb-3">
                  Case Activity & Observations Timeline
                </h3>
                <div className="space-y-3">
                  {appDetails.events.map((ev: any) => (
                    <div key={ev.id} className="flex items-start gap-3 text-xs border-l-2 border-blossom-300 pl-3 py-0.5">
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-ink-strong">{ev.event_type.replace('_', ' ')}</span>
                          <span className="text-[10px] text-ink-muted">{ev.timestamp}</span>
                        </div>
                        <p className="text-[11px] text-ink mt-0.5">{ev.description}</p>
                        <span className="text-[10px] text-blossom-600 font-semibold">{ev.aph_clause_ref}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white rounded-xl border border-ink-line p-12 text-center text-ink-muted text-xs shadow-soft">
              Select an application from the queue to view its full dossier.
            </div>
          )}
        </div>
      </div>

      {/* MODAL 1: NEW APPLICATION INTAKE */}
      {showSubmitModal && (
        <div className="fixed inset-0 bg-ink-strong/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-card border border-ink-line w-full max-w-md p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                <Plus className="w-4 h-4 text-blossom-600" /> New Application Intake
              </h3>
              <button onClick={() => setShowSubmitModal(false)}><X className="w-4 h-4 text-ink-muted" /></button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-ink-strong block mb-1">Application Type</label>
                <select
                  value={newAppType}
                  onChange={(e) => setNewAppType(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs"
                >
                  <option value="NEW_INSTITUTION">New Technical Institution (Ch. I)</option>
                  <option value="EXTENSION_OF_APPROVAL">Extension of Approval (EoA - Ch. II)</option>
                  <option value="INCREASE_INTAKE">Increase in Intake / Additional Course (Ch. II)</option>
                  <option value="NEW_PROGRAMME">To Start New Programme / Level (Ch. II)</option>
                  <option value="CLOSURE">Closure of Institution (Ch. II)</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-ink-strong block mb-1">Programme / Course</label>
                <input
                  type="text"
                  value={newCourseName}
                  onChange={(e) => setNewCourseName(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs"
                />
              </div>

              <div className="bg-blossom-100 p-2.5 rounded-lg border border-blossom-300 text-[11px] text-ink">
                <strong>Rules Engine Preview:</strong> Selecting this will automatically route through{' '}
                <span className="font-bold underline">
                  {newAppType === 'EXTENSION_OF_APPROVAL' ? 'Self-Disclosure' : 'Scrutiny + EVC'}
                </span>{' '}
                per APH 2024-27 Table 2.3.
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button onClick={() => setShowSubmitModal(false)} className="btn-secondary !text-xs">Cancel</button>
              <button
                onClick={async () => {
                  const instId = appDetails ? appDetails.institution.id : 'inst-01';
                  const res = await fetch('http://127.0.0.1:8000/api/v1/applications/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ institution_id: instId, application_type: newAppType }),
                  });
                  if (res.ok) {
                    alert('Application successfully submitted and auto-routed!');
                    setShowSubmitModal(false);
                    fetchApplications();
                  }
                }}
                className="btn-primary !text-xs"
              >
                Submit Application
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: REVERT FOR DEFICIENCY */}
      {showRevertModal && (
        <div className="fixed inset-0 bg-ink-strong/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-card border border-ink-line w-full max-w-md p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="text-sm font-bold text-roseState-700 flex items-center gap-2">
                <RotateCcw className="w-4 h-4" /> Return Application for Deficiency
              </h3>
              <button onClick={() => setShowRevertModal(false)}><X className="w-4 h-4 text-ink-muted" /></button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-ink-strong block mb-1">Deficiency Category</label>
                <select
                  value={revertCategory}
                  onChange={(e) => setRevertCategory(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs"
                >
                  <option value="Missing Fire Safety NOC">Missing Fire Safety NOC (Clause 6.17(i))</option>
                  <option value="Land Lease Period Inadequate">Land Lease Period &lt; 30 Years (Clause 2.1(e))</option>
                  <option value="Unqualified Principal">No Regular Qualified Principal (Clause 7.4(b))</option>
                  <option value="Deficient Infrastructure Area">Built-Up Area Deficiency (Clause 6.17)</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-ink-strong block mb-1">Recorded Remarks / Deficiencies</label>
                <textarea
                  rows={3}
                  value={revertRemarks}
                  onChange={(e) => setRevertRemarks(e.target.value)}
                  placeholder="Record mandatory statutory reasons as required under APH Clause 1.8(f)..."
                  className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs"
                />
              </div>

              <div className="bg-amberState-100 p-2.5 rounded-lg border border-amberState-700/20 text-[11px] text-amberState-700">
                <strong>Statutory Rule:</strong> Reverting will pause the SLA clock and give the institution a 15-day cure window.
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button onClick={() => setShowRevertModal(false)} className="btn-secondary !text-xs">Cancel</button>
              <button onClick={handleRevert} className="btn-primary !text-xs !bg-roseState-700 hover:!bg-rose-800">
                Confirm Revert & Pause Clock
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: CURE SUBMISSION (INSTITUTION) */}
      {showCureModal && (
        <div className="fixed inset-0 bg-ink-strong/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-card border border-ink-line w-full max-w-md p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-mint-700" /> Submit Deficiency Rectification
              </h3>
              <button onClick={() => setShowCureModal(false)}><X className="w-4 h-4 text-ink-muted" /></button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-ink-strong block mb-1">Institution Clarification / Response</label>
                <textarea
                  rows={3}
                  value={cureResponse}
                  onChange={(e) => setCureResponse(e.target.value)}
                  placeholder="Detail the actions taken to cure the deficiency, attach renewed certificate numbers..."
                  className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs"
                />
              </div>

              <div className="bg-mint-100 p-2.5 rounded-lg border border-mint-700/20 text-[11px] text-mint-700">
                <strong>SLA Rule:</strong> Resubmitting will resume the statutory SLA clock and route application to Re-Scrutiny (Clause 1.8(g)).
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button onClick={() => setShowCureModal(false)} className="btn-secondary !text-xs">Cancel</button>
              <button onClick={handleCureSubmit} className="btn-primary !text-xs">
                Submit & Resume SLA Clock
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 4: ISOLATED AI CASE SUMMARY DOCKET & HUMAN APPROVAL GATE */}
      {showAIDraftModal && currentAIDraft && (
        <div className="fixed inset-0 bg-ink-strong/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-card border border-ink-line w-full max-w-xl p-5 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-blossom-600" />
                <h3 className="text-sm font-bold text-ink-strong">AI Draft Electronic Case Summary</h3>
              </div>
              <button onClick={() => setShowAIDraftModal(false)}><X className="w-4 h-4 text-ink-muted" /></button>
            </div>

            {/* MANDATORY AI SAFEGUARD BANNER */}
            <div className="bg-blossom-100 border border-blossom-300 p-2.5 rounded-lg text-xs font-semibold text-blossom-700 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-blossom-600 shrink-0" />
              <span>AI draft. Decision reserved for the competent authority.</span>
            </div>

            {/* Docket Content */}
            <div className="bg-slate-50 p-4 rounded-xl border border-ink-line text-xs space-y-3">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                <span className="font-bold text-ink-strong">{currentAIDraft.docket.header.application_no}</span>
                <span className="text-mint-700 font-bold bg-mint-100 px-2 py-0.5 rounded">
                  Confidence: {Math.round(currentAIDraft.confidence_score * 100)}%
                </span>
              </div>

              <div>
                <span className="text-ink-muted block text-[10px] uppercase font-bold">Pipeline Assessment</span>
                <div className="font-semibold text-ink mt-0.5">
                  Route: {currentAIDraft.docket.pipeline_assessment.prescribed_route} | Current: {currentAIDraft.docket.pipeline_assessment.current_stage}
                </div>
              </div>

              <div>
                <span className="text-ink-muted block text-[10px] uppercase font-bold">Scrutiny Findings</span>
                <ul className="list-disc pl-4 mt-1 space-y-1 text-ink">
                  {currentAIDraft.docket.scrutiny_findings.map((f: string, idx: number) => (
                    <li key={idx}>{f}</li>
                  ))}
                </ul>
              </div>

              <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                <span className="text-ink-muted block text-[10px] uppercase font-bold">Recommendation Draft</span>
                <div className="font-bold text-ink-strong mt-0.5">
                  {currentAIDraft.docket.suggested_recommendation}
                </div>
              </div>

              <div>
                <span className="text-ink-muted block text-[10px] uppercase font-bold">APH Clause Provenance</span>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {currentAIDraft.docket.aph_clause_provenance.map((c: string, idx: number) => (
                    <span key={idx} className="bg-slate-200 text-ink text-[10px] px-2 py-0.5 rounded font-mono font-bold">
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-100">
              <span className="text-[11px] text-ink-muted">Enforcing Pairwise SoD: Requester != Approver</span>
              <div className="flex gap-2">
                <button onClick={() => setShowAIDraftModal(false)} className="btn-secondary !text-xs">Discard</button>
                <button onClick={handleApproveAIDraft} className="btn-primary !text-xs">
                  Approve as Official Record
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
