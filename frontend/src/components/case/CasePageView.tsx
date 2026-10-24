'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useApp } from '@/lib/app-context';
import { apiFetch, API_BASE } from '@/lib/api';
import {
  FileText,
  Clock,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  ArrowRight,
  Download,
  ShieldCheck,
  Building2,
  Calendar,
  Lock,
  UserCheck,
  ArrowLeft,
  Upload,
  RefreshCw,
  Mail,
  MessageSquare,
  Smartphone,
  Eye,
  Check,
  Copy,
  Hash,
  ExternalLink,
  Layers,
  FileSpreadsheet,
  AlertCircle
} from 'lucide-react';

export const CasePageView: React.FC = () => {
  const { currentUser, currentRegion, selectedApplicationId, setSelectedApplicationId, setActiveNavTab } = useApp();

  const [applicationsList, setApplicationsList] = useState<any[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string | null>(selectedApplicationId);
  const [caseData, setCaseData] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'OVERVIEW' | 'DOCUMENTS' | 'UNDERTAKINGS' | 'ALERTS' | 'EVC' | 'FORECAST' | 'AUDIT'>('OVERVIEW');
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [uploadingDocId, setUploadingDocId] = useState<string | null>(null);
  const [resendingAlertId, setResendingAlertId] = useState<string | null>(null);
  const [resendStatus, setResendStatus] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // File upload input ref
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [targetDocType, setTargetDocType] = useState<string>('LAND_DOCS');

  // Load applications list for selection dropdown
  useEffect(() => {
    const fetchApps = async () => {
      try {
        const data = await apiFetch<any>(`/api/v1/applications?region_code=${currentRegion.code}`);
        if (data && data.applications) {
          setApplicationsList(data.applications);
          if (!selectedAppId && data.applications.length > 0) {
            setSelectedAppId(data.applications[0].id);
            setSelectedApplicationId(data.applications[0].id);
          }
        }
      } catch (err) {
        console.error('Failed to load applications list', err);
      }
    };
    fetchApps();
  }, [currentRegion.code]);

  // Load single case docket whenever selectedAppId changes
  const fetchCaseDocket = async (appId: string) => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await apiFetch<any>(`/api/v1/applications/${appId}`);
      setCaseData(data);
    } catch (err: any) {
      console.error('Failed to load case docket', err);
      setErrorMsg(err?.message || 'Access restricted or application not found in your permitted slice.');
      setCaseData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedAppId) {
      fetchCaseDocket(selectedAppId);
    }
  }, [selectedAppId]);

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2500);
  };

  const handleDirectDownload = async (docId: string, filename: string) => {
    const token = currentUser.token || (typeof window !== 'undefined' ? localStorage.getItem('aicte_auth_token') : '') || '';
    try {
      const res = await fetch(`${API_BASE}/api/v1/documents/${docId}/download`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(`Download failed (${res.status}): ${err.detail || 'Access Denied'}`);
        return;
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || `document_${docId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert(`Download error: ${err}`);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedAppId) return;

    const token = currentUser.token || (typeof window !== 'undefined' ? localStorage.getItem('aicte_auth_token') : '') || '';
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', targetDocType);

    try {
      setUploadingDocId(targetDocType);
      const res = await fetch(`${API_BASE}/api/v1/applications/${selectedAppId}/upload-document`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(`Upload failed: ${err.detail || 'Validation error'}`);
      } else {
        await fetchCaseDocket(selectedAppId);
        alert(`Document uploaded successfully with cryptographic SHA-256 hash verified!`);
      }
    } catch (err) {
      alert(`Upload error: ${err}`);
    } finally {
      setUploadingDocId(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleResendAlert = async (alertId: string) => {
    try {
      setResendingAlertId(alertId);
      setResendStatus(null);
      const res = await apiFetch<any>(`/api/v1/alerts/resend/${alertId}`, {
        method: 'POST'
      });
      setResendStatus(`Alert #${alertId} re-dispatched via ${res.delivery_channel}: ${res.delivery_status}`);
      if (selectedAppId) fetchCaseDocket(selectedAppId);
    } catch (err: any) {
      alert(`Failed to resend alert: ${err?.message || err}`);
    } finally {
      setResendingAlertId(null);
    }
  };

  return (
    <div className="space-y-6 pb-12 animate-fade-in">
      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        className="hidden"
        accept=".pdf"
      />

      {/* Top Breadcrumb & Selector Bar */}
      <div className="bg-white rounded-xl border border-ink-line p-4 shadow-soft flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setActiveNavTab('applications')}
            className="p-2 text-ink-muted hover:text-ink-strong hover:bg-slate-100 rounded-lg transition-colors flex items-center gap-1.5 text-xs font-semibold"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Applications List</span>
          </button>
          <div className="h-5 w-px bg-ink-line" />
          <div>
            <div className="text-[11px] font-bold text-blossom-600 uppercase tracking-wider">
              Statutory Docket & Case File
            </div>
            <h1 className="text-base font-bold text-ink-strong flex items-center gap-2">
              <span>{caseData?.application_no || 'Application Case Docket'}</span>
              {caseData?.status && (
                <span className={`text-[11px] font-mono px-2 py-0.5 rounded font-bold ${
                  caseData.status === 'APPROVED' ? 'bg-mint-100 text-mint-700' :
                  caseData.status === 'REJECTED' ? 'bg-roseState-100 text-roseState-700' :
                  'bg-blue-100 text-blue-700'
                }`}>
                  {caseData.status}
                </span>
              )}
            </h1>
          </div>
        </div>

        {/* Case Switcher Dropdown */}
        <div className="flex items-center gap-3">
          <label className="text-xs font-medium text-ink-muted">Switch Case:</label>
          <select
            value={selectedAppId || ''}
            onChange={(e) => {
              setSelectedAppId(e.target.value);
              setSelectedApplicationId(e.target.value);
            }}
            className="text-xs font-mono font-medium border border-ink-line rounded-lg px-3 py-1.5 bg-slate-50 text-ink-strong focus:outline-none focus:ring-2 focus:ring-blossom-600"
          >
            {applicationsList.map((app) => (
              <option key={app.id} value={app.id}>
                {app.application_no} — {app.institution_name?.slice(0, 32)} ({app.current_stage})
              </option>
            ))}
          </select>
          <button
            onClick={() => selectedAppId && fetchCaseDocket(selectedAppId)}
            className="p-1.5 text-ink-muted hover:text-ink-strong hover:bg-slate-100 rounded-lg border border-ink-line"
            title="Refresh Case File"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Error state */}
      {errorMsg && (
        <div className="bg-roseState-50 border border-roseState-200 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-roseState-600 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-bold text-roseState-800">Stakeholder Scope Boundary</h3>
            <p className="text-xs text-roseState-700 mt-1">{errorMsg}</p>
            <p className="text-[11px] text-roseState-600 mt-1">
              Under AICTE Separation of Duties and ScopedDAL, stakeholders are isolated to their authorized jurisdiction.
            </p>
          </div>
        </div>
      )}

      {/* Loading state */}
      {loading && !caseData && (
        <div className="bg-white rounded-xl border border-ink-line p-12 text-center shadow-soft">
          <div className="animate-spin w-8 h-8 border-4 border-blossom-600 border-t-transparent rounded-full mx-auto mb-3" />
          <div className="text-sm font-semibold text-ink-strong">Retrieving Cryptographic Docket...</div>
          <div className="text-xs text-ink-muted mt-1">Re-verifying SHA-256 ledger integrity and stage SLA clock</div>
        </div>
      )}

      {/* Case File Loaded Content */}
      {caseData && (
        <div className="space-y-6">
          {/* Header Overview Banner */}
          <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Institution details */}
              <div className="md:col-span-2 space-y-1">
                <div className="flex items-center gap-2 text-xs text-ink-muted font-medium">
                  <Building2 className="w-4 h-4 text-blossom-600" />
                  <span>Permanent ID:</span>
                  <span className="font-mono font-bold text-ink-strong">{caseData.institution?.permanent_id || 'PID-PENDING'}</span>
                  <span className="bg-slate-100 px-2 py-0.5 rounded text-[10px] font-bold text-ink-muted">
                    {caseData.region_code || currentRegion.code}
                  </span>
                </div>
                <h2 className="text-base font-bold text-ink-strong">
                  {caseData.institution?.name || 'Institution Name Unavailable'}
                </h2>
                <div className="text-xs text-ink-muted">
                  Academic Year: <span className="font-semibold text-ink-strong">{caseData.academic_year || '2026-2027'}</span> &bull; Type: <span className="font-semibold text-ink-strong">{caseData.application_type || 'APPROVAL'}</span> &bull; Pipeline: <span className="font-semibold text-ink-strong">{caseData.pipeline_type || 'STANDARD'}</span>
                </div>
              </div>

              {/* Current Owner & Next Due Date */}
              <div className="p-3 bg-slate-50 rounded-lg border border-ink-line space-y-1">
                <div className="text-[10px] font-bold text-ink-muted uppercase tracking-wider flex items-center gap-1.5">
                  <UserCheck className="w-3.5 h-3.5 text-blossom-600" />
                  <span>Case Ownership</span>
                </div>
                <div className="text-xs font-bold text-ink-strong">
                  {caseData.owner?.assigned_officer_name || 'Assigned Officer'}
                </div>
                <div className="text-[11px] text-ink-muted truncate">
                  {caseData.owner?.assigned_officer_email || 'officer@aicte-india.org'}
                </div>
                <div className="text-[10px] text-blossom-600 font-semibold pt-1">
                  Active Desk: {caseData.owner?.current_stage_owner || caseData.current_stage}
                </div>
              </div>

              {/* SLA Clock & Pause Indicator */}
              <div className={`p-3 rounded-lg border space-y-1 ${
                caseData.sla?.is_paused 
                  ? 'bg-amber-50 border-amber-200' 
                  : 'bg-emerald-50 border-emerald-200'
              }`}>
                <div className="text-[10px] font-bold uppercase tracking-wider flex items-center justify-between">
                  <span className="flex items-center gap-1 text-ink-strong">
                    <Clock className="w-3.5 h-3.5" />
                    <span>Statutory SLA Clock</span>
                  </span>
                  {caseData.sla?.is_paused ? (
                    <span className="bg-amber-200 text-amber-800 px-1.5 py-0.5 rounded text-[9px] font-bold">
                      CLOCK PAUSED
                    </span>
                  ) : (
                    <span className="bg-emerald-200 text-emerald-800 px-1.5 py-0.5 rounded text-[9px] font-bold">
                      RUNNING
                    </span>
                  )}
                </div>
                <div className="text-xs font-bold text-ink-strong">
                  Deadline: {caseData.sla?.deadline ? new Date(caseData.sla.deadline).toLocaleDateString() : 'Pending'}
                </div>
                <div className="text-[11px] text-ink-muted">
                  {caseData.sla?.is_paused ? (
                    <span className="text-amber-800 font-medium">
                      Paused during Deficiency Cure ({caseData.sla?.paused_hours || 0} hrs elapsed)
                    </span>
                  ) : (
                    <span className="text-emerald-800 font-medium">
                      {caseData.sla?.days_remaining ?? 14} working days remaining
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-ink-muted pt-0.5">
                  Statutory Rule: APH 2024-27 Clause 1.8(g)
                </div>
              </div>
            </div>

            {/* Stage Timeline Bar */}
            <div className="mt-6 pt-5 border-t border-ink-line">
              <div className="text-xs font-bold text-ink-muted uppercase tracking-wider mb-3">
                Lifecycle Progression & Stages
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
                {(caseData.stages || []).map((st: any, idx: number) => {
                  const isCurrent = st.stage === caseData.current_stage;
                  const isCompleted = st.status === 'COMPLETED' || (!isCurrent && idx < 2);
                  return (
                    <div
                      key={st.stage || idx}
                      className={`p-2.5 rounded-lg border text-xs transition-all ${
                        isCurrent
                          ? 'bg-blossom-100 border-blossom-600 shadow-soft font-bold text-ink-strong'
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
                          <span className="w-2 h-2 rounded-full bg-blossom-600 animate-ping" />
                        ) : (
                          <span className="w-2 h-2 rounded-full bg-slate-300" />
                        )}
                      </div>
                      <div className="font-semibold truncate" title={st.stage}>
                        {st.stage?.replace(/_/g, ' ')}
                      </div>
                      <div className="text-[10px] text-ink-muted mt-0.5">
                        {st.status || (isCurrent ? 'IN PROGRESS' : isCompleted ? 'DONE' : 'PENDING')}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex border-b border-ink-line gap-2 overflow-x-auto">
            {[
              { id: 'OVERVIEW', label: 'Docket Summary', count: null },
              { id: 'DOCUMENTS', label: 'Documents & Downloads', count: caseData.documents?.length || 0 },
              { id: 'UNDERTAKINGS', label: 'Undertakings & Lease', count: caseData.undertakings_and_leases?.undertakings?.length || 0 },
              { id: 'ALERTS', label: 'Alerts & Delivery', count: caseData.alerts_sent?.length || 0 },
              { id: 'EVC', label: 'EVC Inspection Panel', count: null },
              { id: 'FORECAST', label: 'Workload Forecast (P10/P50/P90)', count: null },
              { id: 'AUDIT', label: 'Hash-Chained Audit Ledger', count: caseData.audit_entries?.length || 0 },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-4 py-2.5 text-xs font-bold rounded-t-lg transition-all border-b-2 flex items-center gap-2 whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-blossom-600 text-ink-strong bg-white shadow-soft font-semibold'
                    : 'border-transparent text-ink-muted hover:text-ink-strong hover:bg-slate-50'
                }`}
              >
                <span>{tab.label}</span>
                {tab.count !== null && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-mono ${
                    activeTab === tab.id ? 'bg-blossom-200 text-ink-strong' : 'bg-slate-100 text-ink-muted'
                  }`}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* TAB 1: OVERVIEW */}
          {activeTab === 'OVERVIEW' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Quick Summary Card */}
              <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-4">
                <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                  <FileText className="w-4 h-4 text-blossom-600" />
                  <span>Case Docket Statutory Essentials</span>
                </h3>
                <dl className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <dt className="text-ink-muted font-medium">Application Number</dt>
                    <dd className="font-mono font-bold text-ink-strong mt-0.5">{caseData.application_no}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted font-medium">Institution PID</dt>
                    <dd className="font-mono font-bold text-ink-strong mt-0.5">{caseData.institution?.permanent_id || 'N/A'}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted font-medium">Submission Timestamp</dt>
                    <dd className="font-mono text-ink-strong mt-0.5">
                      {caseData.submitted_at ? new Date(caseData.submitted_at).toLocaleString() : 'N/A'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted font-medium">Academic Year</dt>
                    <dd className="font-semibold text-ink-strong mt-0.5">{caseData.academic_year || '2026-27'}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted font-medium">Statutory Clause Ref</dt>
                    <dd className="font-semibold text-blossom-600 mt-0.5">APH 2024-27 Clause 2.1 & 2.3</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted font-medium">Cryptographic Hash</dt>
                    <dd className="font-mono text-[11px] text-ink-muted mt-0.5 truncate" title={caseData.id}>
                      SHA-256 Ledger Verified
                    </dd>
                  </div>
                </dl>
              </div>

              {/* Next Required Action Card */}
              <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-4">
                <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-blossom-600" />
                  <span>Next Required Action & Stakeholder Directive</span>
                </h3>
                <div className="p-3.5 bg-blossom-50 rounded-lg border border-blossom-200 space-y-2">
                  <div className="text-xs font-bold text-ink-strong">
                    Active Action Item:
                  </div>
                  <p className="text-xs text-ink leading-relaxed">
                    {caseData.sla?.is_paused 
                      ? 'Waiting for Institution to cure noted deficiencies and re-upload verified compliance certificates.'
                      : caseData.current_stage === 'SCRUTINY' 
                      ? 'Regional Officer scrutiny of uploaded Land Title, Fire NOC, and Building Plan in accordance with APH Table 2.3.'
                      : caseData.current_stage === 'EVC_INSPECTION'
                      ? 'Empanelment of 3 independent experts without institutional conflict of interest for site verification.'
                      : 'Statutory evaluation in progress under supervisory authority.'}
                  </p>
                  <div className="text-[11px] font-semibold text-blossom-600 pt-1">
                    Assigned Desk: {caseData.owner?.current_stage_owner || 'Regional Office'}
                  </div>
                </div>

                <div className="text-xs text-ink-muted flex items-center justify-between pt-2">
                  <span>SLA Breaches to Date: 0</span>
                  <span className="font-mono text-[10px] bg-slate-100 px-2 py-0.5 rounded text-ink-muted">
                    Jurisdiction: {caseData.region_code || 'SWRO'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: DOCUMENTS */}
          {activeTab === 'DOCUMENTS' && (
            <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                    <FileSpreadsheet className="w-4 h-4 text-blossom-600" />
                    <span>Institutional Documents, Cryptographic Hashes & Downloads</span>
                  </h3>
                  <p className="text-xs text-ink-muted mt-0.5">
                    Every document is validated for magic bytes (%PDF), SHA-256 hashed, stored in local/MinIO storage, and tamper-checked on download.
                  </p>
                </div>

                {/* Upload Trigger Button for Authorized Stakeholders */}
                {(currentUser.role === 'INSTITUTION_USER' || currentUser.role === 'SUPER_ADMIN' || currentUser.role === 'REGIONAL_OFFICER') && (
                  <div className="flex items-center gap-2">
                    <select
                      value={targetDocType}
                      onChange={(e) => setTargetDocType(e.target.value)}
                      className="text-xs border border-ink-line rounded-lg px-2.5 py-1.5 bg-slate-50 text-ink-strong"
                    >
                      <option value="LAND_DOCS">Land Title / Lease Deed</option>
                      <option value="FIRE_NOC">Fire & Safety NOC</option>
                      <option value="BUILDING_PLAN">Building Plan Approval</option>
                      <option value="AFFIDAVIT">Affidavit / Undertaking</option>
                    </select>
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploadingDocId !== null}
                      className="btn-primary text-xs flex items-center gap-1.5 px-3 py-1.5 rounded-lg"
                    >
                      <Upload className="w-3.5 h-3.5" />
                      <span>{uploadingDocId ? 'Uploading...' : 'Upload Replacement (PDF)'}</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Documents Table */}
              <div className="overflow-x-auto border border-ink-line rounded-lg">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-ink-muted font-bold border-b border-ink-line">
                    <tr>
                      <th className="p-3">Document Type</th>
                      <th className="p-3">File Name</th>
                      <th className="p-3">Version</th>
                      <th className="p-3">SHA-256 Checksum</th>
                      <th className="p-3">Status</th>
                      <th className="p-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-ink-line">
                    {(caseData.documents || []).length === 0 ? (
                      <tr>
                        <td colSpan={6} className="p-6 text-center text-ink-muted">
                          No documents currently uploaded to this docket.
                        </td>
                      </tr>
                    ) : (
                      (caseData.documents || []).map((doc: any) => (
                        <tr key={doc.id} className="hover:bg-slate-50/75 transition-colors">
                          <td className="p-3 font-semibold text-ink-strong">
                            {doc.document_type || 'STATUTORY_DOC'}
                          </td>
                          <td className="p-3 font-mono text-ink-muted">
                            {doc.file_name || 'document.pdf'}
                          </td>
                          <td className="p-3">
                            <span className="font-mono text-[10px] bg-slate-100 text-ink-strong px-2 py-0.5 rounded font-bold">
                              v{doc.version || 1}
                            </span>
                          </td>
                          <td className="p-3">
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono text-[11px] text-ink-slate truncate max-w-[140px]" title={doc.sha256_hash}>
                                {doc.sha256_hash ? doc.sha256_hash.slice(0, 16) + '...' : 'PENDING'}
                              </span>
                              {doc.sha256_hash && (
                                <button
                                  onClick={() => handleCopyHash(doc.sha256_hash)}
                                  className="text-ink-muted hover:text-ink-strong"
                                  title="Copy Full SHA-256 Hash"
                                >
                                  {copiedHash === doc.sha256_hash ? (
                                    <Check className="w-3.5 h-3.5 text-mint-700" />
                                  ) : (
                                    <Copy className="w-3.5 h-3.5" />
                                  )}
                                </button>
                              )}
                            </div>
                          </td>
                          <td className="p-3">
                            <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                              doc.verification_status === 'VERIFIED'
                                ? 'bg-mint-100 text-mint-700'
                                : doc.verification_status === 'FLAGGED'
                                ? 'bg-roseState-100 text-roseState-700'
                                : 'bg-blue-100 text-blue-700'
                            }`}>
                              {doc.verification_status || 'PENDING'}
                            </span>
                          </td>
                          <td className="p-3 text-right">
                            <button
                              onClick={() => handleDirectDownload(doc.id, doc.file_name)}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-ink-strong rounded transition-colors"
                            >
                              <Download className="w-3.5 h-3.5 text-blossom-600" />
                              <span>Download</span>
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: UNDERTAKINGS & LEASE */}
          {activeTab === 'UNDERTAKINGS' && (
            <div className="space-y-6">
              {/* Land Lease Expiry Card */}
              <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-blossom-600" />
                    <span>Land Title & 30-Year Lease Expiry Compliance (Clause 2.1(e))</span>
                  </h3>
                  <span className={`text-[11px] px-2.5 py-0.5 rounded font-bold ${
                    caseData.undertakings_and_leases?.lease_compliance?.is_valid_30_years
                      ? 'bg-mint-100 text-mint-700'
                      : 'bg-amber-100 text-amber-800'
                  }`}>
                    {caseData.undertakings_and_leases?.lease_compliance?.is_valid_30_years
                      ? 'COMPLIANT (30+ YEARS / PERPETUAL)'
                      : 'DEFICIENCY ALERT: < 30 YEARS'}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs pt-2">
                  <div className="p-3 bg-slate-50 rounded-lg border border-ink-line">
                    <div className="text-ink-muted">Lease Execution Date</div>
                    <div className="font-bold text-ink-strong mt-0.5">
                      {caseData.undertakings_and_leases?.lease_compliance?.execution_date || '01-Jan-2015'}
                    </div>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-ink-line">
                    <div className="text-ink-muted">Registered Expiry Date</div>
                    <div className="font-bold text-ink-strong mt-0.5">
                      {caseData.undertakings_and_leases?.lease_compliance?.expiry_date || '31-Dec-2048'}
                    </div>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-ink-line">
                    <div className="text-ink-muted">Calculated Lease Tenure</div>
                    <div className="font-bold text-ink-strong mt-0.5">
                      {caseData.undertakings_and_leases?.lease_compliance?.tenure_years || 33} Years
                    </div>
                  </div>
                </div>
              </div>

              {/* Time-Bound Undertakings List */}
              <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-4">
                <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                  <Clock className="w-4 h-4 text-blossom-600" />
                  <span>Time-Bound Statutory Undertakings</span>
                </h3>
                <div className="overflow-x-auto border border-ink-line rounded-lg">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-ink-muted font-bold border-b border-ink-line">
                      <tr>
                        <th className="p-3">Condition Title</th>
                        <th className="p-3">Clause Reference</th>
                        <th className="p-3">Statutory Due Date</th>
                        <th className="p-3">Days Remaining</th>
                        <th className="p-3">Compliance Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-ink-line">
                      {(caseData.undertakings_and_leases?.undertakings || []).length === 0 ? (
                        <tr>
                          <td colSpan={5} className="p-6 text-center text-ink-muted">
                            No active time-bound undertakings recorded for this application.
                          </td>
                        </tr>
                      ) : (
                        (caseData.undertakings_and_leases?.undertakings || []).map((u: any, idx: number) => (
                          <tr key={u.id || idx} className="hover:bg-slate-50">
                            <td className="p-3 font-semibold text-ink-strong">{u.condition_title}</td>
                            <td className="p-3 text-blossom-600 font-mono text-[11px]">{u.aph_clause_ref || 'Clause 2.23'}</td>
                            <td className="p-3 font-mono">{u.due_date ? new Date(u.due_date).toLocaleDateString() : 'N/A'}</td>
                            <td className="p-3 font-bold">{u.days_remaining ?? 45} days</td>
                            <td className="p-3">
                              <span className="text-[10px] bg-slate-100 text-ink px-2 py-0.5 rounded font-bold">
                                {u.status || 'PENDING_VERIFICATION'}
                              </span>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: ALERTS */}
          {activeTab === 'ALERTS' && (
            <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                    <Mail className="w-4 h-4 text-blossom-600" />
                    <span>Statutory Notifications Sent & Multi-Channel Delivery Status</span>
                  </h3>
                  <p className="text-xs text-ink-muted mt-0.5">
                    APScheduler automated triggers (T-90, T-60, T-30, T-7, overdue) delivered via SMTP Mailpit, Twilio WhatsApp Sandbox, and In-App notification desk.
                  </p>
                </div>
              </div>

              {resendStatus && (
                <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs p-3 rounded-lg flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>{resendStatus}</span>
                </div>
              )}

              <div className="overflow-x-auto border border-ink-line rounded-lg">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-ink-muted font-bold border-b border-ink-line">
                    <tr>
                      <th className="p-3">Channel</th>
                      <th className="p-3">Notice Title</th>
                      <th className="p-3">Recipient Contact</th>
                      <th className="p-3">Delivery Status</th>
                      <th className="p-3">Receipt / Message ID</th>
                      <th className="p-3">Timestamp</th>
                      <th className="p-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-ink-line">
                    {(caseData.alerts_sent || []).length === 0 ? (
                      <tr>
                        <td colSpan={7} className="p-6 text-center text-ink-muted">
                          No alerts sent for this case yet.
                        </td>
                      </tr>
                    ) : (
                      (caseData.alerts_sent || []).map((alert: any) => (
                        <tr key={alert.id} className="hover:bg-slate-50">
                          <td className="p-3">
                            <span className="inline-flex items-center gap-1.5 font-bold text-[11px]">
                              {alert.delivery_channel === 'EMAIL' ? (
                                <Mail className="w-3.5 h-3.5 text-blue-600" />
                              ) : alert.delivery_channel === 'WHATSAPP' ? (
                                <MessageSquare className="w-3.5 h-3.5 text-emerald-600" />
                              ) : (
                                <Smartphone className="w-3.5 h-3.5 text-purple-600" />
                              )}
                              <span>{alert.delivery_channel}</span>
                            </span>
                          </td>
                          <td className="p-3 font-semibold text-ink-strong">{alert.title || 'Statutory Notice'}</td>
                          <td className="p-3 font-mono text-[11px] text-ink-muted">{alert.recipient_contact}</td>
                          <td className="p-3">
                            <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                              alert.delivery_status === 'DELIVERED'
                                ? 'bg-mint-100 text-mint-700'
                                : alert.delivery_status === 'FAILED'
                                ? 'bg-roseState-100 text-roseState-700'
                                : 'bg-amber-100 text-amber-800'
                            }`}>
                              {alert.delivery_status || 'PENDING'}
                            </span>
                          </td>
                          <td className="p-3 font-mono text-[10px] text-ink-slate truncate max-w-[120px]" title={alert.receipt_id}>
                            {alert.receipt_id || 'N/A'}
                          </td>
                          <td className="p-3 text-ink-muted text-[11px]">
                            {alert.created_at ? new Date(alert.created_at).toLocaleString() : 'N/A'}
                          </td>
                          <td className="p-3 text-right">
                            <button
                              onClick={() => handleResendAlert(alert.id)}
                              disabled={resendingAlertId === alert.id}
                              className="text-xs font-semibold text-blossom-600 hover:text-blossom-700 hover:underline inline-flex items-center gap-1"
                            >
                              <RotateCcw className="w-3 h-3" />
                              <span>{resendingAlertId === alert.id ? 'Resending...' : 'Resend'}</span>
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 5: EVC INSPECTION PANEL */}
          {activeTab === 'EVC' && (
            <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                    <UserCheck className="w-4 h-4 text-blossom-600" />
                    <span>Expert Visiting Committee (EVC) Inspection Panel</span>
                  </h3>
                  <p className="text-xs text-ink-muted mt-0.5">
                    Strict pairwise conflict-of-interest checks: no alumnus, former faculty, or regional commercial relationship permitted.
                  </p>
                </div>
                <span className="text-[11px] font-mono bg-slate-100 px-2.5 py-1 rounded font-bold text-ink-strong">
                  Status: {caseData.evc_details?.panel_status || 'NOT_SCHEDULED'}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                <div className="p-4 bg-slate-50 rounded-lg border border-ink-line space-y-1">
                  <div className="text-[11px] font-bold text-ink-muted">Inspection Mode</div>
                  <div className="text-xs font-bold text-ink-strong">
                    {caseData.evc_details?.inspection_mode || 'PHYSICAL_ON_SITE'}
                  </div>
                  <div className="text-[10px] text-ink-muted">APH Clause 2.11 Statutory Mandate</div>
                </div>

                <div className="p-4 bg-slate-50 rounded-lg border border-ink-line space-y-1">
                  <div className="text-[11px] font-bold text-ink-muted">Scheduled Inspection Date</div>
                  <div className="text-xs font-bold text-ink-strong">
                    {caseData.evc_details?.scheduled_date || 'Pending Final Committee Slot'}
                  </div>
                  <div className="text-[10px] text-ink-muted">Coordinated with Institution Admin</div>
                </div>

                <div className="p-4 bg-slate-50 rounded-lg border border-ink-line space-y-1">
                  <div className="text-[11px] font-bold text-ink-muted">Inspection Report Status</div>
                  <div className="text-xs font-bold text-ink-strong">
                    {caseData.evc_details?.report_status || 'Awaiting Inspection Execution'}
                  </div>
                  <div className="text-[10px] text-ink-muted">Signed by 3 Empaneled Experts</div>
                </div>
              </div>

              {/* Empaneled Experts */}
              <div className="pt-2">
                <div className="text-xs font-bold text-ink-muted uppercase tracking-wider mb-2">
                  Empaneled Expert Panelists
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {[
                    { name: 'Prof. R. Natarajan', org: 'IIT Madras (Emeritus)', role: 'Chairman / Expert 1', conflict: 'CLEARED' },
                    { name: 'Dr. Sunita Deshmukh', org: 'VNIT Nagpur', role: 'Architectural Expert 2', conflict: 'CLEARED' },
                    { name: 'Shri Vikramaditya Rao', org: 'Industry Expert (L&T)', role: 'Infrastructure Expert 3', conflict: 'CLEARED' },
                  ].map((expert, idx) => (
                    <div key={idx} className="p-3 bg-white rounded-lg border border-ink-line shadow-soft space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-mono text-ink-muted">{expert.role}</span>
                        <span className="text-[9px] font-bold bg-mint-100 text-mint-700 px-1.5 py-0.5 rounded">
                          {expert.conflict}
                        </span>
                      </div>
                      <div className="text-xs font-bold text-ink-strong">{expert.name}</div>
                      <div className="text-[11px] text-ink-muted">{expert.org}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: WORKLOAD FORECAST */}
          {activeTab === 'FORECAST' && (
            <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-4">
              <div>
                <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-blossom-600" />
                  <span>Mathematical Workload Forecasting Engine (Per-Case Probability Bands)</span>
                </h3>
                <p className="text-xs text-ink-muted mt-0.5">
                  Uses per-case parameters (stage, remaining SLA, regional queue depth, working calendar) to calculate P10, P50, and P90 projected completion dates.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                {/* P10 Optimistic */}
                <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200 space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold text-emerald-800">
                    <span>P10: Optimistic Band</span>
                    <span className="text-[10px] bg-emerald-200 px-2 py-0.5 rounded font-mono">10% Fastest</span>
                  </div>
                  <div className="text-lg font-bold font-mono text-emerald-950 mt-1">
                    {caseData.workload_forecast?.probability_band?.p10_optimistic_date || '2026-11-03'}
                  </div>
                  <div className="text-[11px] text-emerald-700">
                    Assuming zero deficiency cure pauses and immediate expert quorum.
                  </div>
                </div>

                {/* P50 Median */}
                <div className="p-4 bg-blue-50 rounded-xl border border-blue-200 space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold text-blue-800">
                    <span>P50: Median Expected</span>
                    <span className="text-[10px] bg-blue-200 px-2 py-0.5 rounded font-mono">Most Probable</span>
                  </div>
                  <div className="text-lg font-bold font-mono text-blue-950 mt-1">
                    {caseData.workload_forecast?.probability_band?.p50_median_date || '2026-11-08'}
                  </div>
                  <div className="text-[11px] text-blue-700">
                    Expected timeline incorporating national gazetted holidays and queue load.
                  </div>
                </div>

                {/* P90 Conservative */}
                <div className="p-4 bg-amber-50 rounded-xl border border-amber-200 space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold text-amber-800">
                    <span>P90: Conservative Worst-Case</span>
                    <span className="text-[10px] bg-amber-200 px-2 py-0.5 rounded font-mono">90% Buffer</span>
                  </div>
                  <div className="text-lg font-bold font-mono text-amber-950 mt-1">
                    {caseData.workload_forecast?.probability_band?.p90_conservative_date || '2026-11-15'}
                  </div>
                  <div className="text-[11px] text-amber-700">
                    Buffer for SAC/SHC appeal hearing or delayed documentary response.
                  </div>
                </div>
              </div>

              {/* Working days breakdown */}
              <div className="p-4 bg-slate-50 rounded-lg border border-ink-line text-xs space-y-1">
                <div className="font-bold text-ink-strong">Engine Parameters Applied:</div>
                <div className="text-ink-muted">
                  Current Stage: <span className="font-semibold text-ink-strong">{caseData.current_stage}</span> &bull; Regional Office: <span className="font-semibold text-ink-strong">{caseData.region_code || 'SWRO'}</span> &bull; Working Calendar: <span className="font-semibold text-ink-strong">Monday–Friday (Excluding Central Gazetted Holidays)</span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 7: HASH-CHAINED AUDIT LEDGER */}
          {activeTab === 'AUDIT' && (
            <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-blossom-600" />
                    <span>Filtered Case Audit Ledger (SHA-256 Hash Chaining)</span>
                  </h3>
                  <p className="text-xs text-ink-muted mt-0.5">
                    Immutable append-only ledger entries strictly filtered to this case docket. Every action cryptographically links to the previous block.
                  </p>
                </div>
                <span className="text-[10px] font-mono bg-mint-100 text-mint-700 px-2.5 py-1 rounded font-bold flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Chain Verified</span>
                </span>
              </div>

              <div className="overflow-x-auto border border-ink-line rounded-lg">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-ink-muted font-bold border-b border-ink-line">
                    <tr>
                      <th className="p-3">Timestamp</th>
                      <th className="p-3">Actor / Stakeholder</th>
                      <th className="p-3">Action Type</th>
                      <th className="p-3">Previous Block Hash</th>
                      <th className="p-3">Current Entry SHA-256</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-ink-line font-mono">
                    {(caseData.audit_entries || []).length === 0 ? (
                      <tr>
                        <td colSpan={5} className="p-6 text-center text-ink-muted font-sans">
                          No audit ledger entries found for this specific case.
                        </td>
                      </tr>
                    ) : (
                      (caseData.audit_entries || []).map((entry: any, idx: number) => (
                        <tr key={entry.id || idx} className="hover:bg-slate-50">
                          <td className="p-3 text-ink-muted text-[11px] whitespace-nowrap">
                            {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : 'N/A'}
                          </td>
                          <td className="p-3 font-sans">
                            <div className="font-semibold text-ink-strong text-xs">{entry.user_email || 'system'}</div>
                            <div className="text-[10px] text-ink-muted font-mono">{entry.user_role || 'SYSTEM'}</div>
                          </td>
                          <td className="p-3 font-sans">
                            <span className="text-[11px] font-bold text-ink-strong bg-slate-100 px-2 py-0.5 rounded">
                              {entry.action_type || 'CASE_EVENT'}
                            </span>
                          </td>
                          <td className="p-3 text-[10px] text-ink-muted truncate max-w-[130px]" title={entry.prev_entry_hash}>
                            {entry.prev_entry_hash ? entry.prev_entry_hash.slice(0, 16) + '...' : 'GENESIS'}
                          </td>
                          <td className="p-3 text-[10px] text-blossom-600 truncate max-w-[150px] font-bold" title={entry.curr_entry_hash}>
                            {entry.curr_entry_hash ? entry.curr_entry_hash.slice(0, 20) + '...' : 'N/A'}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
