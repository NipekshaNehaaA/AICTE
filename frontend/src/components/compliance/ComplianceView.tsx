'use client';

import React, { useState, useEffect } from 'react';
import { useApp } from '@/lib/app-context';
import {
  ShieldCheck,
  FileText,
  AlertTriangle,
  Clock,
  CheckCircle2,
  Upload,
  Calendar,
  Layers,
  Flame,
  ArrowRight,
  X,
  FileCheck2,
  Building,
} from 'lucide-react';

export const ComplianceView: React.FC = () => {
  const { currentUser, currentRegion } = useApp();

  const [activeTab, setActiveTab] = useState<'DOCUMENTS' | 'UNDERTAKINGS' | 'REGISTRY' | 'DEPENDENCY_VIEW'>('DOCUMENTS');
  const [documents, setDocuments] = useState<any[]>([]);
  const [undertakings, setUndertakings] = useState<any[]>([]);
  const [docTypes, setDocTypes] = useState<any[]>([]);
  const [dependencyData, setDependencyData] = useState<any | null>(null);

  // Upload modal state
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadDocCode, setUploadDocCode] = useState('LEASE_DEED');
  const [uploadDocNo, setUploadDocNo] = useState('');
  const [uploadIssueDate, setUploadIssueDate] = useState('2026-01-01');
  const [uploadExpiryDate, setUploadExpiryDate] = useState('2056-01-01');
  const [uploadAuthority, setUploadAuthority] = useState('Sub-Registrar Bengaluru');

  const fetchComplianceData = async () => {
    try {
      // 1. Fetch documents
      const docRes = await fetch('http://127.0.0.1:8000/api/v1/compliance/documents', {
        headers: {
          'x-user-role': currentUser.role,
          'x-region-id': currentRegion.code === 'SWRO' ? 'swro-id' : '',
        },
      });
      if (docRes.ok) {
        const docData = await docRes.json();
        setDocuments(docData.documents || []);
      }

      // 2. Fetch undertakings
      const undRes = await fetch('http://127.0.0.1:8000/api/v1/compliance/undertakings');
      if (undRes.ok) {
        const undData = await undRes.json();
        setUndertakings(undData.undertakings || []);
      }

      // 3. Fetch registry
      const regRes = await fetch('http://127.0.0.1:8000/api/v1/compliance/doc-registry');
      if (regRes.ok) {
        const regData = await regRes.json();
        setDocTypes(regData.registry || []);
      }
    } catch (err) {
      console.error('Failed to fetch compliance data', err);
    }
  };

  const fetchDependencies = async (instId?: string) => {
    try {
      const targetId = instId && instId !== 'inst-01' ? instId : 'default';
      const res = await fetch(`http://127.0.0.1:8000/api/v1/compliance/obligation-dependencies/${targetId}`);
      if (!res.ok) {
        console.error('Failed to fetch dependencies', res.status);
        return;
      }
      const data = await res.json();
      if (data && !data.detail) {
        setDependencyData(data);
      }
    } catch (err) {
      console.error('Failed to fetch dependencies', err);
    }
  };

  useEffect(() => {
    fetchComplianceData();
    fetchDependencies();
  }, [currentUser, currentRegion]);

  // Officer verifies document
  const handleVerifyDoc = async (docId: string, isApproved: boolean) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/compliance/documents/${docId}/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-user-id': currentUser.id,
          'x-user-role': currentUser.role,
        },
        body: JSON.stringify({ is_approved: isApproved }),
      });
      const data = await res.json();
      if (res.ok) {
        alert(`Document verified and marked ${data.new_status}! Stamped in audit ledger.`);
        fetchComplianceData();
      } else {
        alert(`Verification Failed: ${data.detail}`);
      }
    } catch (err) {
      alert('Error verifying document.');
    }
  };

  // Upload document
  const handleUpload = async () => {
    try {
      const instId = documents.length > 0 ? documents[0].institution_id || 'inst-01' : 'inst-01';
      const res = await fetch('http://127.0.0.1:8000/api/v1/compliance/documents/upload', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-user-id': currentUser.id,
          'x-user-role': currentUser.role,
        },
        body: JSON.stringify({
          institution_id: instId,
          doc_type_code: uploadDocCode,
          document_number: uploadDocNo || `DOC-${Date.now().toString().slice(-6)}`,
          file_content_mock: `Mock binary payload for ${uploadDocCode} at ${Date.now()}`,
          issue_date: uploadIssueDate,
          expiry_date: uploadExpiryDate,
          issuing_authority: uploadAuthority,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        if (data.anomaly_flag) {
          alert(`⚠️ Fraud Warning: Identical SHA-256 hash detected across institutions! Flagged for officer investigation.`);
        } else {
          alert('Document uploaded with SHA-256 hash computed and OCR metadata extracted!');
        }
        setShowUploadModal(false);
        fetchComplianceData();
      } else {
        alert(`Upload Failed: ${data.detail}`);
      }
    } catch (err) {
      alert('Error uploading document.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-ink-line p-4 shadow-soft flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-ink-strong">
              Document Registry & Institutional Compliance
            </h1>
            <span className="badge-sample-value">Sample offsets, configurable</span>
          </div>
          <p className="text-xs text-ink-muted mt-0.5">
            Registered land leases, safety NOCs, time-bound undertakings, and automated expiry alerts.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowUploadModal(true)}
            className="btn-primary !text-xs"
          >
            <Upload className="w-4 h-4" /> Upload Regulatory Document
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-ink-line pb-2">
        {[
          { id: 'DOCUMENTS', label: `Documents Watch (${documents.length})` },
          { id: 'UNDERTAKINGS', label: `Time-Bound Undertakings (${undertakings.length})` },
          { id: 'DEPENDENCY_VIEW', label: 'Obligation Dependency Graph' },
          { id: 'REGISTRY', label: 'Document Type Registry' },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => {
              setActiveTab(t.id as any);
              if (t.id === 'DEPENDENCY_VIEW') {
                fetchDependencies();
              }
            }}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === t.id
                ? 'bg-blossom-100 text-ink-strong border border-blossom-300'
                : 'text-ink-muted hover:bg-slate-100'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* TAB 1: DOCUMENTS TABLE */}
      {activeTab === 'DOCUMENTS' && (
        <div className="bg-white rounded-xl border border-ink-line shadow-soft overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-blossom-100/60 text-ink-strong border-b border-ink-line">
                  <th className="py-2.5 px-3 font-semibold">Document & Institute</th>
                  <th className="py-2.5 px-3 font-semibold">SHA-256 Hash</th>
                  <th className="py-2.5 px-3 font-semibold">Expiry Date & Offset</th>
                  <th className="py-2.5 px-3 font-semibold">Status</th>
                  <th className="py-2.5 px-3 font-semibold text-right">Officer Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-3">
                      <div className="font-bold text-ink-strong">{doc.document_name}</div>
                      <div className="text-[11px] text-ink">{doc.institution_name}</div>
                      <div className="text-[10px] text-ink-muted font-mono">{doc.document_number}</div>
                    </td>
                    <td className="py-3 px-3 font-mono text-[10px] text-ink-muted">
                      {doc.file_hash_sha256.slice(0, 16)}...
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-bold text-ink-strong">{doc.expiry_date}</div>
                      <div className="text-[11px] text-ink-muted">
                        {doc.days_until_expiry < 0 ? (
                          <span className="text-roseState-700 font-bold">
                            Expired {Math.abs(doc.days_until_expiry)} days ago
                          </span>
                        ) : (
                          <span>{doc.days_until_expiry} days remaining</span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      {doc.rag_status === 'EXPIRED' ? (
                        <span className="status-chip-overdue">
                          <AlertTriangle className="w-3 h-3" /> Expired (Block EoA)
                        </span>
                      ) : doc.rag_status === 'EXPIRING_SOON' ? (
                        <span className="status-chip-approaching">
                          <Clock className="w-3 h-3" /> Advance Alert (60d)
                        </span>
                      ) : (
                        <span className="status-chip-ontrack">
                          <CheckCircle2 className="w-3 h-3" /> Active & Verified
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-right">
                      {doc.status === 'PENDING_VERIFICATION' ? (
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleVerifyDoc(doc.id, true)}
                            className="btn-primary !text-[11px] !py-0.5 !px-2"
                          >
                            Verify
                          </button>
                          <button
                            onClick={() => handleVerifyDoc(doc.id, false)}
                            className="btn-secondary !text-[11px] !py-0.5 !px-2 text-roseState-700"
                          >
                            Reject
                          </button>
                        </div>
                      ) : (
                        <span className="text-[10px] text-ink-muted font-semibold">
                          Verified by Officer
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: TIME-BOUND UNDERTAKINGS */}
      {activeTab === 'UNDERTAKINGS' && (
        <div className="bg-white rounded-xl border border-ink-line shadow-soft divide-y divide-slate-100 overflow-hidden">
          {undertakings.map((u) => (
            <div key={u.id} className="p-4 hover:bg-slate-50 transition-colors flex items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-xs text-ink-strong">{u.condition_title}</span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                    u.status === 'DEFAULT_ESCALATED'
                      ? 'bg-roseState-100 text-roseState-700 border border-roseState-700/30'
                      : 'bg-blossom-100 text-blossom-700'
                  }`}>
                    {u.status.replace('_', ' ')}
                  </span>
                </div>
                <p className="text-xs text-ink leading-relaxed">{u.condition_details}</p>
                <div className="text-[11px] text-ink-muted flex items-center gap-3">
                  <span><strong>Institute:</strong> {u.institution_name}</span>
                  <span><strong>Statutory Due Date:</strong> {u.due_date} ({u.days_remaining}d)</span>
                  <span className="text-blossom-600 font-semibold">{u.aph_clause_ref}</span>
                </div>
              </div>

              <button
                onClick={() => alert('Fulfillment evidence upload portal.')}
                className="btn-secondary !text-xs !py-1 !px-3 shrink-0"
              >
                Upload Evidence →
              </button>
            </div>
          ))}
        </div>
      )}

      {/* TAB 3: OBLIGATION DEPENDENCY VIEW (SIGNATURE DIFFERENTIATOR 6) */}
      {activeTab === 'DEPENDENCY_VIEW' && (
        <div className="bg-white rounded-xl border border-ink-line p-6 shadow-soft space-y-5">
          <div>
            <h2 className="text-sm font-bold text-ink-strong flex items-center gap-2">
              <Layers className="w-4 h-4 text-blossom-600" />
              Obligation Dependency & Intake Impact Graph
            </h2>
            <p className="text-xs text-ink-muted mt-0.5">
              Demonstrates how an expired lease or unmet undertaking cascades into approval freezes and intake risk.
            </p>
          </div>

          {dependencyData && Array.isArray(dependencyData.blockers) ? (
            <div className="space-y-4">
              {/* Impact Banner */}
              <div className={`p-4 rounded-xl border text-xs flex items-center justify-between ${
                dependencyData.eoa_renewal_blocked
                  ? 'bg-roseState-100 border-roseState-700/30 text-roseState-700'
                  : 'bg-mint-100 border-mint-700/30 text-mint-700'
              }`}>
                <div>
                  <div className="font-bold text-sm">
                    {dependencyData.eoa_renewal_blocked
                      ? '⚠️ Extension of Approval (EoA) Blocked'
                      : '✅ Institutional Obligations Met'}
                  </div>
                  <div className="text-[11px] mt-0.5">
                    Institution: {dependencyData.institution_name || 'Technical Institute'} (PID: {dependencyData.permanent_id || '1-109283741'})
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[10px] uppercase font-bold">At-Risk Approved Intake</div>
                  <div className="text-xl font-bold font-mono">{dependencyData.at_risk_approved_intake ?? 0} Seats</div>
                </div>
              </div>

              {/* Cascade Blockers List */}
              <div className="space-y-2">
                <span className="text-xs font-bold text-ink-strong uppercase tracking-wider">
                  Active Statutory Blockers Causing Cascade
                </span>
                {dependencyData.blockers.length === 0 ? (
                  <div className="p-4 bg-slate-50 border border-ink-line rounded-lg text-xs text-ink-muted">
                    No active statutory blockers detected. Institutional documents and undertakings comply with statutory guidelines.
                  </div>
                ) : (
                  dependencyData.blockers.map((b: any, idx: number) => (
                    <div key={idx} className="p-3 bg-slate-50 rounded-lg border border-ink-line text-xs flex items-start gap-3">
                      <AlertTriangle className="w-4 h-4 text-roseState-700 shrink-0 mt-0.5" />
                      <div className="space-y-0.5">
                        <div className="font-bold text-ink-strong">{b.title}</div>
                        <p className="text-[11px] text-ink">{b.consequence}</p>
                        <span className="text-[10px] text-blossom-600 font-bold font-mono">{b.clause}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : (
            <div className="text-xs text-ink-muted text-center py-6">Loading dependency graph...</div>
          )}
        </div>
      )}

      {/* TAB 4: DOCUMENT TYPE REGISTRY */}
      {activeTab === 'REGISTRY' && (
        <div className="bg-white rounded-xl border border-ink-line shadow-soft overflow-hidden">
          <div className="p-3 bg-slate-50 border-b border-ink-line font-bold text-xs text-ink-strong">
            Configurable Regulatory Document Types (APH Standard)
          </div>
          <div className="divide-y divide-slate-100 text-xs">
            {docTypes.map((t) => (
              <div key={t.id} className="p-3 flex items-center justify-between">
                <div>
                  <div className="font-bold text-ink-strong">{t.name}</div>
                  <div className="text-[11px] text-ink-muted">Code: {t.code} • Category: {t.category}</div>
                </div>
                <div className="text-right">
                  <div className="font-semibold text-ink">Validity: {t.validity_years} Years</div>
                  <div className="text-[10px] text-blossom-600 font-bold">
                    Alert Offsets: {t.alert_offsets_days.join(', ')} days
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* UPLOAD MODAL */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-ink-strong/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-card border border-ink-line w-full max-w-md p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                <Upload className="w-4 h-4 text-blossom-600" /> Upload Regulatory Document
              </h3>
              <button onClick={() => setShowUploadModal(false)}><X className="w-4 h-4 text-ink-muted" /></button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-ink-strong block mb-1">Document Type</label>
                <select
                  value={uploadDocCode}
                  onChange={(e) => setUploadDocCode(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs"
                >
                  <option value="LEASE_DEED">Registered Land Lease Deed (30+ Years)</option>
                  <option value="FIRE_NOC">Fire and Life Safety Certificate (NOC)</option>
                  <option value="BUILDING_STABILITY">Building Stability Certificate</option>
                  <option value="UNIVERSITY_AFFILIATION">Affiliating University Approval</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-ink-strong block mb-1">Document Registration Number</label>
                <input
                  type="text"
                  value={uploadDocNo}
                  onChange={(e) => setUploadDocNo(e.target.value)}
                  placeholder="e.g. REG-LEASE-2026-KAR-891"
                  className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="font-semibold text-ink-strong block mb-1">Issue Date</label>
                  <input
                    type="date"
                    value={uploadIssueDate}
                    onChange={(e) => setUploadIssueDate(e.target.value)}
                    className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-ink-strong block mb-1">Expiry Date</label>
                  <input
                    type="date"
                    value={uploadExpiryDate}
                    onChange={(e) => setUploadExpiryDate(e.target.value)}
                    className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="font-semibold text-ink-strong block mb-1">Issuing Authority</label>
                <input
                  type="text"
                  value={uploadAuthority}
                  onChange={(e) => setUploadAuthority(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs"
                />
              </div>

              <div className="bg-blossom-100 p-2.5 rounded-lg border border-blossom-300 text-[11px] text-ink">
                <strong>Integrity Engine:</strong> SHA-256 hash will be computed at submission. Any hash collision with another institution will be immediately flagged in the Anomaly Center.
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button onClick={() => setShowUploadModal(false)} className="btn-secondary !text-xs">Cancel</button>
              <button onClick={handleUpload} className="btn-primary !text-xs">
                Upload & Verify Hash
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
