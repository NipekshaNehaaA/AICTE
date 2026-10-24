'use client';

import React, { useState, useEffect } from 'react';
import { useApp } from '@/lib/app-context';
import { apiFetch, apiFetchResponse } from '@/lib/api';
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
  Zap,
  Plus,
  RefreshCw,
  FileSignature,
  Key,
  Shield,
  Check,
  Download,
  History,
  FileUp,
  Loader2,
} from 'lucide-react';

type ComplianceTab = 'DOCUMENTS' | 'UNDERTAKINGS' | 'REGISTRY' | 'DEPENDENCY_VIEW' | 'LEASE_OCR' | 'CONNECTORS';

export const ComplianceView: React.FC = () => {
  const { currentUser, currentRegion } = useApp();

  const [activeTab, setActiveTab] = useState<ComplianceTab>('DOCUMENTS');
  const [documents, setDocuments] = useState<any[]>([]);
  const [undertakings, setUndertakings] = useState<any[]>([]);
  const [docTypes, setDocTypes] = useState<any[]>([]);
  const [dependencyData, setDependencyData] = useState<any | null>(null);

  // Real File Upload & Version History state
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadDocCode, setUploadDocCode] = useState('LEASE_DEED');
  const [uploadDocNo, setUploadDocNo] = useState('');
  const [uploadIssueDate, setUploadIssueDate] = useState('2026-01-01');
  const [uploadExpiryDate, setUploadExpiryDate] = useState('2056-01-01');
  const [uploadAuthority, setUploadAuthority] = useState('Sub-Registrar Bengaluru');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [replacesDocId, setReplacesDocId] = useState<string>('');
  const [downloadingDocId, setDownloadingDocId] = useState<string | null>(null);

  // Version History Modal state
  const [showVersionModal, setShowVersionModal] = useState(false);
  const [versionHistoryData, setVersionHistoryData] = useState<any | null>(null);
  const [versionLoading, setVersionLoading] = useState(false);

  // Lease OCR State
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrData, setOcrData] = useState<any | null>(null);
  const [ocrVerifyLoading, setOcrVerifyLoading] = useState(false);
  const [ocrVerifiedDate, setOcrVerifiedDate] = useState('2045-05-31');
  const [ocrRemarks, setOcrRemarks] = useState('Verified against Sub-Registrar lease registry');
  const [ocrSuccessMsg, setOcrSuccessMsg] = useState<string | null>(null);
  const [isLowQualityScan, setIsLowQualityScan] = useState(false);

  // External Connectors State
  const [digiLoading, setDigiLoading] = useState(false);
  const [digiResult, setDigiResult] = useState<any | null>(null);
  const [esignOtp, setEsignOtp] = useState('123456');
  const [esignLoading, setEsignLoading] = useState(false);
  const [esignResult, setEsignResult] = useState<any | null>(null);

  // New Doc Type Modal State
  const [showNewTypeModal, setShowNewTypeModal] = useState(false);
  const [newTypeName, setNewTypeName] = useState('');
  const [newTypeCode, setNewTypeCode] = useState('');
  const [newTypeCategory, setNewTypeCategory] = useState('LAND_AND_BUILDING');
  const [newTypeValidity, setNewTypeValidity] = useState(5);
  const [newTypeOffsets, setNewTypeOffsets] = useState('90,60,30,7');

  const getAuthHeaders = () => {
    const token = currentUser.token || (typeof window !== 'undefined' ? localStorage.getItem('aicte_auth_token') : '') || '';
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  };

  const fetchComplianceData = async () => {
    try {
      // 1. Fetch documents
      const docData = await apiFetch<any>('/api/v1/compliance/documents').catch(() => null);
      if (docData?.documents) {
        setDocuments(docData.documents);
      }

      // 2. Fetch undertakings
      const undData = await apiFetch<any>('/api/v1/compliance/undertakings').catch(() => null);
      if (undData?.undertakings) {
        setUndertakings(undData.undertakings);
      }

      // 3. Fetch registry
      const regData = await apiFetch<any>('/api/v1/compliance/doc-registry').catch(() => null);
      if (regData?.registry) {
        setDocTypes(regData.registry);
      }
    } catch (err) {
      console.error('Failed to fetch compliance data', err);
    }
  };

  const fetchDependencies = async (instId?: string) => {
    try {
      const targetId = instId && instId !== 'inst-01' ? instId : 'default';
      const data = await apiFetch<any>(`/api/v1/compliance/obligation-dependencies/${targetId}`).catch(() => null);
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

  // Document verification
  const handleVerifyDoc = async (docId: string, isApproved: boolean) => {
    try {
      const data = await apiFetch<any>(`/api/v1/compliance/documents/${docId}/verify`, {
        method: 'POST',
        body: JSON.stringify({ is_approved: isApproved, remarks: 'Verified by Officer' }),
      });
      alert(`Document verified and marked ${data.new_status}! Stamped in audit ledger.`);
      fetchComplianceData();
    } catch (err: any) {
      alert(`Verification Failed: ${err?.message || 'Error verifying document.'}`);
    }
  };

  // File validation & drag-and-drop handlers
  const validateAndSetFile = (file: File) => {
    setUploadError(null);
    const validExts = ['.pdf', '.jpg', '.jpeg', '.png'];
    const lowerName = file.name.toLowerCase();
    const hasValidExt = validExts.some((ext) => lowerName.endsWith(ext));
    if (!hasValidExt) {
      setUploadError('Invalid file type. Only PDF, JPG, and PNG documents are accepted.');
      return;
    }
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      setUploadError(`File size exceeds 10 MB limit (${(file.size / (1024 * 1024)).toFixed(2)} MB).`);
      return;
    }
    setSelectedFile(file);
    if (!uploadDocNo) {
      setUploadDocNo(`DOC-${Date.now().toString().slice(-6)}`);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  // Real Multipart Upload
  const handleRealUpload = async () => {
    if (!selectedFile) {
      setUploadError('Please select or drop a valid file (PDF, JPG, or PNG).');
      return;
    }
    setUploadLoading(true);
    setUploadError(null);
    setUploadProgress(25);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('doc_type_code', uploadDocCode);
      formData.append('document_number', uploadDocNo || `DOC-${Date.now().toString().slice(-6)}`);
      formData.append('issue_date', uploadIssueDate);
      formData.append('expiry_date', uploadExpiryDate);
      formData.append('issuing_authority', uploadAuthority);
      if (replacesDocId) {
        formData.append('replaces_document_id', replacesDocId);
      }

      setUploadProgress(65);
      const data = await apiFetch<any>('/api/v1/compliance/documents/upload-file', {
        method: 'POST',
        body: formData,
      });
      setUploadProgress(100);

      if (data.anomaly_flag) {
        alert('⚠️ Cryptographic Cross-Check Flag: Identical SHA-256 hash detected across institutions! Flagged in audit ledger for scrutiny.');
      } else {
        alert(`Document "${data.original_filename}" (v${data.version}) uploaded successfully! SHA-256 stamped in audit ledger.`);
      }

      setShowUploadModal(false);
      setSelectedFile(null);
      setUploadProgress(0);
      setReplacesDocId('');
      fetchComplianceData();
    } catch (err: any) {
      setUploadError(err?.message || 'Error uploading file.');
    } finally {
      setUploadLoading(false);
    }
  };

  // Authenticated Scoped Download with Cryptographic Tamper Detection
  const handleDownloadDoc = async (doc: any) => {
    setDownloadingDocId(doc.id);
    try {
      const res = await apiFetchResponse(`/api/v1/compliance/documents/${doc.id}/download`);
      if (!res.ok) {
        if (res.status === 409) {
          throw new Error('CRITICAL INTEGRITY FAILURE: Server detected on-disk byte alteration! Cryptographic hash does not match immutable SHA-256 ledger.');
        } else if (res.status === 403) {
          throw new Error('ACCESS DENIED: ScopedDAL jurisdictional barrier. You are not authorized to download records outside your region or institution.');
        } else {
          const errData = await res.json().catch(() => null);
          throw new Error(errData?.detail || `Download failed with HTTP ${res.status}`);
        }
      }

      const blob = await res.blob();
      const filename = doc.original_filename || `${doc.document_number || 'document'}.pdf`;
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Download Error: ${err?.message}`);
    } finally {
      setDownloadingDocId(null);
    }
  };

  // Version History Modal Opener
  const handleOpenVersions = async (docId: string) => {
    setShowVersionModal(true);
    setVersionLoading(true);
    setVersionHistoryData(null);
    try {
      const data = await apiFetch<any>(`/api/v1/compliance/documents/${docId}/versions`);
      setVersionHistoryData(data);
    } catch (err: any) {
      alert(`Failed to load version history: ${err?.message}`);
    } finally {
      setVersionLoading(false);
    }
  };

  // OCR Extraction Handler
  const handleExtractLeaseOCR = async () => {
    setOcrLoading(true);
    setOcrSuccessMsg(null);
    try {
      const data = await apiFetch<any>('/api/v1/compliance/ocr/extract-lease', {
        method: 'POST',
        body: JSON.stringify({
          longest_course_duration_years: 4,
          is_low_quality_scan: isLowQualityScan,
        }),
      });
      setOcrData(data);
      if (data.fields?.lease_end_date?.value) {
        setOcrVerifiedDate(data.fields.lease_end_date.value);
      } else if (data.requires_manual_entry) {
        setOcrVerifiedDate('2045-05-31'); // default prefill for manual officer correction
      }
    } catch (e: any) {
      console.error(e);
      alert(`OCR extraction failed: ${e?.message || 'Error'}`);
    } finally {
      setOcrLoading(false);
    }
  };

  // OCR Officer Verification Handler
  const handleVerifyLeaseOCR = async (isApproved: boolean) => {
    if (!ocrData?.draft_id) return;
    setOcrVerifyLoading(true);
    try {
      await apiFetch<any>('/api/v1/compliance/ocr/verify-lease', {
        method: 'POST',
        body: JSON.stringify({
          draft_id: ocrData.draft_id,
          is_approved: isApproved,
          verified_start_date: ocrData.fields?.lease_start_date?.value || '2015-06-01',
          verified_end_date: ocrVerifiedDate,
          verified_course_duration_years: ocrData.fields?.course_duration_years?.value || 4,
          officer_remarks: ocrRemarks,
        }),
      });
      setOcrSuccessMsg(`Officer verification recorded! Stamped into non-repudiable audit ledger.`);
    } catch (e: any) {
      console.error(e);
      alert(`Verification failed: ${e?.message || 'Error'}`);
    } finally {
      setOcrVerifyLoading(false);
    }
  };

  // DigiLocker Fetch Handler
  const handleDigiLockerFetch = async (docType: string) => {
    setDigiLoading(true);
    try {
      const data = await apiFetch<any>('/api/v1/adapters/digilocker/fetch', {
        method: 'POST',
        body: JSON.stringify({ doc_type: docType }),
      });
      setDigiResult(data);
    } catch (e: any) {
      console.error(e);
      alert(`DigiLocker fetch failed: ${e?.message || 'Error'}`);
    } finally {
      setDigiLoading(false);
    }
  };

  // Aadhaar e-Sign Handler
  const handleESign = async () => {
    setEsignLoading(true);
    try {
      const data = await apiFetch<any>('/api/v1/adapters/esign/sign', {
        method: 'POST',
        body: JSON.stringify({
          document_id: digiResult?.document_number || 'DOC-REG-2026-991',
          otp: esignOtp,
        }),
      });
      setEsignResult(data);
    } catch (e: any) {
      console.error(e);
      alert(`e-Sign failed: ${e?.message || 'Error'}`);
    } finally {
      setEsignLoading(false);
    }
  };

  // Create Doc Type Handler
  const handleCreateDocType = async () => {
    if (!newTypeName || !newTypeCode) return;
    try {
      await apiFetch<any>('/api/v1/compliance/document-types', {
        method: 'POST',
        body: JSON.stringify({
          name: newTypeName,
          code: newTypeCode.toUpperCase(),
          category: newTypeCategory,
          validity_years: Number(newTypeValidity),
          alert_offsets_days: newTypeOffsets,
          is_mandatory: true,
        }),
      });
      setShowNewTypeModal(false);
      fetchComplianceData();
    } catch (e: any) {
      console.error(e);
      alert(e?.message || 'Failed to create document type');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-ink-line p-4 shadow-soft flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-ink-strong">
              Document Registry, OCR & Institutional Compliance
            </h1>
            <span className="badge-sample-value">APH 2024–27 Norms</span>
          </div>
          <p className="text-xs text-ink-muted mt-0.5">
            Registered land leases, safety NOCs, time-bound undertakings, OCR extraction, and DigiLocker connectors.
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
      <div className="flex items-center gap-2 border-b border-ink-line pb-2 overflow-x-auto">
        {[
          { id: 'DOCUMENTS', label: `Documents Watch (${documents.length})` },
          { id: 'LEASE_OCR', label: '⚡ Lease OCR & Verification' },
          { id: 'CONNECTORS', label: '🏛️ DigiLocker & e-Sign Connectors' },
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
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shrink-0 ${
              activeTab === t.id
                ? 'bg-blossom-100 text-ink-strong border border-blossom-300 font-bold'
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
                  <th className="py-2.5 px-3 font-semibold">Document & Version</th>
                  <th className="py-2.5 px-3 font-semibold">SHA-256 Hash</th>
                  <th className="py-2.5 px-3 font-semibold">Expiry Date & Offset</th>
                  <th className="py-2.5 px-3 font-semibold">Status</th>
                  <th className="py-2.5 px-3 font-semibold">Storage & Downloads</th>
                  <th className="py-2.5 px-3 font-semibold text-right">Officer Gate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="font-bold text-ink-strong">{d.document_name}</span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 border border-slate-200 text-slate-700">
                          v{d.version || 1}
                        </span>
                        {d.is_latest_version && (
                          <span className="text-[9px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">
                            LATEST
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-ink-muted">
                        {d.institution_name} • No: {d.document_number}
                      </div>
                      {d.original_filename && (
                        <div className="text-[10px] text-indigo-600 font-mono flex items-center gap-1 mt-0.5">
                          <FileText className="w-3 h-3 shrink-0" />
                          <span className="truncate max-w-[200px]" title={d.original_filename}>{d.original_filename}</span>
                        </div>
                      )}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[10px] text-ink-muted">
                      {d.file_hash_sha256 ? `${d.file_hash_sha256.slice(0, 12)}...${d.file_hash_sha256.slice(-8)}` : 'N/A'}
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="font-mono">{d.expiry_date}</div>
                      <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                        d.days_until_expiry < 0
                          ? 'bg-rose-100 text-rose-700'
                          : d.days_until_expiry <= 30
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-emerald-100 text-emerald-700'
                      }`}>
                        {d.days_until_expiry < 0 ? `${Math.abs(d.days_until_expiry)}d EXPIRED` : `${d.days_until_expiry}d remaining`}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="text-[11px] font-semibold text-ink-strong">{d.status}</span>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleDownloadDoc(d)}
                          disabled={downloadingDocId === d.id}
                          title="Download document with SHA-256 cryptographic recheck"
                          className="px-2 py-1 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded border border-blue-200 font-semibold text-[11px] flex items-center gap-1 transition-colors disabled:opacity-50"
                        >
                          {downloadingDocId === d.id ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Download className="w-3 h-3" />
                          )}
                          Download
                        </button>
                        <button
                          onClick={() => handleOpenVersions(d.id)}
                          title="View document renewal history"
                          className="px-2 py-1 bg-slate-50 hover:bg-slate-100 text-slate-700 rounded border border-slate-200 font-semibold text-[11px] flex items-center gap-1 transition-colors"
                        >
                          <History className="w-3 h-3" />
                          History
                        </button>
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {d.verified_by ? (
                        <span className="text-[10px] text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                          ✓ Verified by {d.verified_by}
                        </span>
                      ) : (
                        <button
                          onClick={() => handleVerifyDoc(d.id, true)}
                          className="px-2.5 py-1 bg-white hover:bg-slate-100 border border-ink-line rounded text-[11px] font-semibold text-ink transition-colors shadow-sm"
                        >
                          Verify (Officer Gate)
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: LEASE OCR & OFFICER VERIFICATION (ITEM 5.3) */}
      {activeTab === 'LEASE_OCR' && (
        <div className="space-y-5">
          <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-500" />
                  Land Lease Deed OCR Extraction & Confidence Score Engine
                  <span className="text-[10px] font-bold px-2 py-0.5 bg-slate-100 text-slate-700 rounded border border-slate-200">
                    simulated extraction on synthetic text
                  </span>
                </h3>
                <p className="text-xs text-ink-muted mt-0.5">
                  Automated field parsing per Chapter II Clause 2.1(e) with confidence metrics and human officer verification.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1.5 text-xs text-slate-700 font-medium cursor-pointer bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-200">
                  <input
                    type="checkbox"
                    checked={isLowQualityScan}
                    onChange={(e) => setIsLowQualityScan(e.target.checked)}
                    className="rounded border-slate-300 text-rose-600 focus:ring-rose-500"
                  />
                  <span>Simulate Low-Quality Scan (Confidence &lt; 75%)</span>
                </label>
                <button
                  onClick={handleExtractLeaseOCR}
                  disabled={ocrLoading}
                  className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg text-xs font-bold shadow-sm hover:shadow transition-all flex items-center gap-1.5 disabled:opacity-50"
                >
                  {ocrLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5 text-amber-300" />}
                  <span>{isLowQualityScan ? 'Run Degraded Scan Extraction' : 'Run High-Confidence OCR Extraction'}</span>
                </button>
              </div>
            </div>

            {ocrData ? (
              <div className="mt-5 space-y-5">
                {/* Low Quality Alert Banner if confidence < 75% */}
                {ocrData.requires_manual_entry && (
                  <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl space-y-1.5">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                      <strong className="text-xs font-bold text-rose-900">
                        Low-Quality Scan Alert — Automatic Extraction Withheld
                      </strong>
                      <span className="text-[10px] font-bold px-2 py-0.5 bg-rose-100 text-rose-800 rounded">
                        Confidence {Math.round((ocrData.average_confidence || 0.52) * 100)}% &lt; 75% Threshold
                      </span>
                    </div>
                    <p className="text-xs text-rose-800">
                      Document text was smudged or degraded below the 75% regulatory threshold. The system has withheld automatic field extraction. Human officer manual entry and verification are mandatory under Chapter II Clause 2.1(e).
                    </p>
                  </div>
                )}

                {/* Field-level confidence scores */}
                <div>
                  <h4 className="text-xs font-bold text-ink-strong uppercase tracking-wider mb-2">
                    Extracted Deed Parameters (Field Confidence Metrics)
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    {Object.entries(ocrData.fields || {}).map(([key, val]: any) => {
                      const confPercent = Math.round((val.confidence || 0.9) * 100);
                      return (
                        <div key={key} className="p-3 bg-slate-50 rounded-xl border border-ink-line">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold text-ink-muted uppercase">{key.replace(/_/g, ' ')}</span>
                            <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                              confPercent >= 90 ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                            }`}>
                              {confPercent}% Conf
                            </span>
                          </div>
                          <div className="mt-1.5 font-bold font-mono text-xs text-ink-strong">
                            {val.value ? String(val.value) : (val.raw_snippet || 'Manual Entry Required')}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Deterministic Rule Evaluation Card */}
                {ocrData.rule_evaluation && (
                  <div className="p-4 bg-blue-50/50 rounded-xl border border-blue-200 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-blue-900">
                        Chapter II Clause 2.1(e) Deterministic Compliance Evaluation
                      </span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                        ocrData.rule_evaluation.is_eoa_blocked
                          ? 'bg-rose-100 text-rose-800 border-rose-300'
                          : ocrData.rule_evaluation.evaluation_status === 'WITHHELD_DUE_TO_LOW_CONFIDENCE'
                          ? 'bg-amber-100 text-amber-800 border-amber-300'
                          : 'bg-emerald-100 text-emerald-800 border-emerald-300'
                      }`}>
                        {ocrData.rule_evaluation.evaluation_status === 'WITHHELD_DUE_TO_LOW_CONFIDENCE'
                          ? 'PENDING MANUAL ENTRY'
                          : ocrData.rule_evaluation.is_eoa_blocked ? 'EOA BLOCKED' : 'COMPLIANT WITH LIVE LEASE NORMS'}
                      </span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs pt-1">
                      <div>
                        <span className="text-ink-muted block text-[11px]">Live Lease Remaining:</span>
                        <strong className="text-ink-strong">{ocrData.rule_evaluation.years_remaining ? `${ocrData.rule_evaluation.years_remaining} Years` : 'Pending Entry'}</strong>
                      </div>
                      <div>
                        <span className="text-ink-muted block text-[11px]">EoA Cutoff Block Date:</span>
                        <strong className="text-ink-strong font-mono">{ocrData.rule_evaluation.eoa_block_date || 'Pending Verification'}</strong>
                      </div>
                      <div>
                        <span className="text-ink-muted block text-[11px]">APH Requirement:</span>
                        <span className="text-ink-strong">{ocrData.rule_evaluation.threshold_note || 'Clause 2.1(e) minimum course duration live lease'}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Officer Verification Gate */}
                <div className="p-4 bg-slate-900 text-white rounded-xl space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      <span className="text-xs font-bold">Human Officer Verification Gate (Separation of Duties)</span>
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono">Draft ID: {ocrData.draft_id}</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div>
                      <label className="text-[11px] text-slate-300 block mb-1">Confirmed Lease Expiry Date:</label>
                      <input
                        type="date"
                        value={ocrVerifiedDate}
                        onChange={(e) => setOcrVerifiedDate(e.target.value)}
                        className="w-full p-2 bg-slate-800 border border-slate-700 rounded-lg text-xs font-mono text-white"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] text-slate-300 block mb-1">Officer Verification Remarks:</label>
                      <input
                        type="text"
                        value={ocrRemarks}
                        onChange={(e) => setOcrRemarks(e.target.value)}
                        className="w-full p-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white"
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <span className="text-[11px] text-slate-400">
                      Enforces pairwise SoD: Submitter ≠ Verifier.
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleVerifyLeaseOCR(false)}
                        disabled={ocrVerifyLoading}
                        className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold transition-colors disabled:opacity-50"
                      >
                        Reject
                      </button>
                      <button
                        onClick={() => handleVerifyLeaseOCR(true)}
                        disabled={ocrVerifyLoading}
                        className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-colors shadow-sm disabled:opacity-50 flex items-center gap-1"
                      >
                        {ocrVerifyLoading && <RefreshCw className="w-3 h-3 animate-spin" />}
                        <span>Approve & Stamped Verification</span>
                      </button>
                    </div>
                  </div>

                  {ocrSuccessMsg && (
                    <div className="p-2.5 bg-emerald-900/60 border border-emerald-500 rounded-lg text-xs text-emerald-200 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>{ocrSuccessMsg}</span>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-xs text-ink-muted">
                Click "Run High-Confidence OCR Extraction" to parse lease parameters and evaluate Chapter II Clause 2.1(e).
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: DIGILOCKER & E-SIGN CONNECTORS (ITEM 5.5) */}
      {activeTab === 'CONNECTORS' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* DigiLocker Connector Card */}
          <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-4">
            <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
              <div>
                <h3 className="text-xs font-bold text-ink-strong flex items-center gap-2">
                  <Shield className="w-4 h-4 text-blossom-600" />
                  National DigiLocker Ingestion (Simulated Connector)
                </h3>
                <p className="text-[11px] text-ink-muted mt-0.5">
                  Direct digital fetch of authentic land lease and fire certificates via simulated government repository connector.
                </p>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 bg-blue-100 text-blue-800 rounded">
                Simulated Connector
              </span>
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => handleDigiLockerFetch('LAND_LEASE')}
                disabled={digiLoading}
                className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 border border-ink-line rounded-lg text-xs font-semibold text-ink flex items-center gap-1.5 transition-colors shadow-sm disabled:opacity-50"
              >
                <FileText className="w-3.5 h-3.5 text-blossom-600" />
                Fetch Land Lease Deed (30-Yr)
              </button>
              <button
                onClick={() => handleDigiLockerFetch('FIRE_NOC')}
                disabled={digiLoading}
                className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 border border-ink-line rounded-lg text-xs font-semibold text-ink flex items-center gap-1.5 transition-colors shadow-sm disabled:opacity-50"
              >
                <Flame className="w-3.5 h-3.5 text-rose-600" />
                Fetch Fire Safety NOC
              </button>
            </div>

            {digiResult && (
              <div className="p-3 bg-slate-50 rounded-xl border border-ink-line text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <strong className="text-ink-strong">{digiResult.title}</strong>
                  <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    ✓ Cryptographically Verified
                  </span>
                </div>
                <div className="space-y-1 text-[11px] text-ink-muted">
                  <div><strong>Issuer:</strong> {digiResult.issuing_authority}</div>
                  <div><strong>Doc No:</strong> {digiResult.document_number} • <strong>Expiry:</strong> {digiResult.expiry_date}</div>
                  <div className="font-mono text-[10px]"><strong>URI:</strong> {digiResult.digilocker_uri}</div>
                  <div className="font-mono text-[10px] truncate"><strong>SHA-256:</strong> {digiResult.file_hash_sha256}</div>
                </div>
              </div>
            )}
          </div>

          {/* e-Sign Connector Card */}
          <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-4">
            <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
              <div>
                <h3 className="text-xs font-bold text-ink-strong flex items-center gap-2">
                  <FileSignature className="w-4 h-4 text-indigo-600" />
                  Digital e-Sign PKCS#7 Stamping (Simulated Connector)
                </h3>
                <p className="text-[11px] text-ink-muted mt-0.5">
                  PKCS#7 cryptographic signature envelope application for institutional declarations and compliance affidavits (simulated connector; no Aadhaar data stored).
                </p>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 bg-indigo-100 text-indigo-800 rounded">
                Simulated Connector
              </span>
            </div>

            <div className="flex items-center gap-2 text-xs">
              <label className="text-[11px] font-semibold text-ink-muted shrink-0">e-Sign Verification Code:</label>
              <input
                type="text"
                value={esignOtp}
                onChange={(e) => setEsignOtp(e.target.value)}
                className="w-28 p-1.5 bg-slate-50 border border-ink-line rounded-lg text-xs font-mono font-bold text-center"
              />
              <button
                onClick={handleESign}
                disabled={esignLoading}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold shadow-sm transition-colors disabled:opacity-50 flex items-center gap-1"
              >
                {esignLoading && <RefreshCw className="w-3 h-3 animate-spin" />}
                <span>Stamp Digital e-Sign</span>
              </button>
            </div>

            {esignResult && (
              <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-200 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <strong className="text-indigo-950 font-bold">{esignResult.transaction_id}</strong>
                  <span className="text-[10px] font-bold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded border border-emerald-300">
                    ✓ Valid e-Sign
                  </span>
                </div>
                <div className="text-[11px] text-indigo-900 space-y-1">
                  <div><strong>Certifying Authority:</strong> {esignResult.cert_authority}</div>
                  <div className="font-mono text-[10px]"><strong>Envelope:</strong> {esignResult.signature_envelope_token}</div>
                  <div><strong>Timestamp:</strong> {esignResult.timestamp}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: UNDERTAKINGS TABLE */}
      {activeTab === 'UNDERTAKINGS' && (
        <div className="bg-white rounded-xl border border-ink-line shadow-soft overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-blossom-100/60 text-ink-strong border-b border-ink-line">
                  <th className="py-2.5 px-3 font-semibold">Undertaking Condition</th>
                  <th className="py-2.5 px-3 font-semibold">APH Clause</th>
                  <th className="py-2.5 px-3 font-semibold">Due Date</th>
                  <th className="py-2.5 px-3 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {undertakings.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-3">
                      <div className="font-bold text-ink-strong">{u.condition_title}</div>
                      <div className="text-[11px] text-ink-muted">{u.institution_name}</div>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-blossom-600 font-semibold">
                      {u.aph_clause_ref}
                    </td>
                    <td className="py-2.5 px-3 font-mono">{u.due_date}</td>
                    <td className="py-2.5 px-3">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-ink-strong">
                        {u.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 5: OBLIGATION DEPENDENCY VIEW */}
      {activeTab === 'DEPENDENCY_VIEW' && (
        <div className="bg-white rounded-xl border border-ink-line p-5 shadow-soft space-y-4">
          <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-ink-strong">
                Institutional Obligation Dependency Graph
              </h3>
              <p className="text-[11px] text-ink-muted mt-0.5">
                Deterministic mapping of statutory approval prerequisites to institutional compliance state.
              </p>
            </div>
            {dependencyData && (
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                dependencyData.eoa_renewal_blocked
                  ? 'bg-rose-100 text-rose-800 border-rose-300'
                  : 'bg-emerald-100 text-emerald-800 border-emerald-300'
              }`}>
                {dependencyData.eoa_renewal_blocked ? 'EOA RENEWAL BLOCKED' : 'ALL PREREQUISITES SATISFIED'}
              </span>
            )}
          </div>

          {dependencyData ? (
            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-3 bg-slate-50 rounded-xl border border-ink-line">
                  <span className="text-[10px] font-bold text-ink-muted uppercase">Monitored Institution</span>
                  <div className="font-bold text-ink-strong mt-0.5">{dependencyData.institution_name}</div>
                  <span className="text-[10px] text-ink-muted font-mono">{dependencyData.permanent_id}</span>
                </div>
                <div className="p-3 bg-slate-50 rounded-xl border border-ink-line">
                  <span className="text-[10px] font-bold text-ink-muted uppercase">Compliance Health Score</span>
                  <div className="font-bold text-emerald-700 text-base mt-0.5">{dependencyData.overall_health_score}%</div>
                </div>
                <div className="p-3 bg-slate-50 rounded-xl border border-ink-line">
                  <span className="text-[10px] font-bold text-ink-muted uppercase">Sanctioned Intake at Risk</span>
                  <div className="font-bold text-rose-700 text-base mt-0.5">{dependencyData.at_risk_approved_intake} Seats</div>
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="text-[11px] font-bold text-ink-strong uppercase">Identified Statutory Blockers</h4>
                {dependencyData.blockers?.length === 0 ? (
                  <div className="text-xs text-mint-700 bg-mint-50 p-3 rounded-lg border border-mint-200">
                    No active regulatory blockers. Institution is fully compliant with APH 2024–27 requirements.
                  </div>
                ) : (
                  dependencyData.blockers?.map((b: any, i: number) => (
                    <div key={i} className="p-3 rounded-lg border border-rose-200 bg-rose-50/50 flex items-start justify-between">
                      <div>
                        <div className="font-bold text-rose-900">{b.title}</div>
                        <div className="text-[11px] text-rose-700 mt-0.5">{b.consequence}</div>
                      </div>
                      <span className="text-[10px] text-blossom-600 font-bold font-mono">{b.clause}</span>
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

      {/* TAB 6: DOCUMENT TYPE REGISTRY (ITEM 5.2) */}
      {activeTab === 'REGISTRY' && (
        <div className="bg-white rounded-xl border border-ink-line shadow-soft overflow-hidden">
          <div className="p-4 bg-slate-50 border-b border-ink-line flex items-center justify-between">
            <div>
              <div className="font-bold text-xs text-ink-strong">
                Configurable Regulatory Document Types (APH Standard)
              </div>
              <p className="text-[11px] text-ink-muted mt-0.5">
                Statutory document definitions, validity periods, and multi-tier alert offset horizons.
              </p>
            </div>
            <button
              onClick={() => setShowNewTypeModal(true)}
              className="px-3 py-1.5 bg-blossom-600 hover:bg-blossom-700 text-white rounded-lg text-xs font-bold shadow-sm transition-colors flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" /> Register Document Type
            </button>
          </div>
          <div className="divide-y divide-slate-100 text-xs">
            {docTypes.map((t) => (
              <div key={t.id} className="p-3 flex items-center justify-between hover:bg-slate-50 transition-colors">
                <div>
                  <div className="font-bold text-ink-strong">{t.name}</div>
                  <div className="text-[11px] text-ink-muted">Code: {t.code} • Category: {t.category}</div>
                </div>
                <div className="text-right">
                  <div className="font-semibold text-ink">Validity: {t.validity_years} Years</div>
                  <div className="text-[10px] text-blossom-600 font-bold">
                    Alert Offsets: {Array.isArray(t.alert_offsets_days) ? t.alert_offsets_days.join(', ') : t.alert_offsets_days} days
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MODAL: REGISTER DOCUMENT TYPE */}
      {showNewTypeModal && (
        <div className="fixed inset-0 bg-ink-strong/40 flex items-center justify-center z-50 p-4 animate-fade-in">
          <div className="bg-white rounded-xl shadow-card border border-ink-line w-full max-w-md p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                <Plus className="w-4 h-4 text-blossom-600" /> Register Statutory Document Type
              </h3>
              <button onClick={() => setShowNewTypeModal(false)}><X className="w-4 h-4 text-ink-muted" /></button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-ink-strong block mb-1">Document Type Name</label>
                <input
                  type="text"
                  value={newTypeName}
                  onChange={(e) => setNewTypeName(e.target.value)}
                  placeholder="e.g. Master Plan Approval"
                  className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs"
                />
              </div>

              <div>
                <label className="font-semibold text-ink-strong block mb-1">Code</label>
                <input
                  type="text"
                  value={newTypeCode}
                  onChange={(e) => setNewTypeCode(e.target.value)}
                  placeholder="e.g. MASTER_PLAN"
                  className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="font-semibold text-ink-strong block mb-1">Validity (Years)</label>
                  <input
                    type="number"
                    value={newTypeValidity}
                    onChange={(e) => setNewTypeValidity(Number(e.target.value))}
                    className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-ink-strong block mb-1">Alert Offsets (Days)</label>
                  <input
                    type="text"
                    value={newTypeOffsets}
                    onChange={(e) => setNewTypeOffsets(e.target.value)}
                    placeholder="90,60,30,7"
                    className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs font-mono"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button onClick={() => setShowNewTypeModal(false)} className="btn-secondary !text-xs">Cancel</button>
              <button onClick={handleCreateDocType} className="btn-primary !text-xs">
                Save to Registry
              </button>
            </div>
          </div>
        </div>
      )}

      {/* REAL MULTIPART UPLOAD MODAL */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-ink-strong/50 backdrop-blur-xs flex items-center justify-center z-50 p-4 animate-fade-in">
          <div className="bg-white rounded-2xl shadow-xl border border-ink-line w-full max-w-lg p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                <FileUp className="w-4 h-4 text-blossom-600" />
                Upload Regulatory Document (Real Byte Storage)
              </h3>
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setSelectedFile(null);
                  setUploadError(null);
                }}
                className="p-1 hover:bg-slate-100 rounded-lg text-ink-muted transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {uploadError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-2 text-xs text-rose-800">
                <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{uploadError}</span>
              </div>
            )}

            <div className="space-y-4 text-xs">
              {/* Drag and Drop Zone */}
              <div>
                <label className="font-semibold text-ink-strong block mb-1">
                  Document Binary File <span className="text-rose-500">*</span>
                </label>
                <div
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => document.getElementById('compliance-file-input')?.click()}
                  className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all ${
                    dragActive
                      ? 'border-blossom-500 bg-blossom-50/60'
                      : selectedFile
                      ? 'border-emerald-400 bg-emerald-50/40'
                      : 'border-slate-300 hover:border-slate-400 bg-slate-50'
                  }`}
                >
                  <input
                    id="compliance-file-input"
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        validateAndSetFile(e.target.files[0]);
                      }
                    }}
                  />
                  {selectedFile ? (
                    <div className="space-y-1">
                      <div className="flex items-center justify-center gap-2 text-emerald-700 font-bold">
                        <CheckCircle2 className="w-5 h-5" />
                        <span className="text-xs break-all">{selectedFile.name}</span>
                      </div>
                      <p className="text-[11px] text-ink-muted">
                        {(selectedFile.size / 1024).toFixed(1)} KB • {selectedFile.type || 'Binary Document'}
                      </p>
                      <span className="text-[10px] text-blossom-600 underline font-semibold">
                        Click or drag to change file
                      </span>
                    </div>
                  ) : (
                    <div className="space-y-1">
                      <Upload className="w-7 h-7 mx-auto text-slate-400" />
                      <p className="text-xs font-semibold text-ink-strong">
                        Drag & drop your document here, or <span className="text-blossom-600 underline">browse files</span>
                      </p>
                      <p className="text-[10px] text-ink-muted">
                        PDF, JPG, PNG accepted (up to 10 MB). Validated via magic bytes and SHA-256 integrity hash.
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Renewal / Versioning Option */}
              <div>
                <label className="font-semibold text-ink-strong block mb-1">
                  Document Renewal / Amendment (Versioning)
                </label>
                <select
                  value={replacesDocId}
                  onChange={(e) => setReplacesDocId(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs"
                >
                  <option value="">-- New Document (Version 1) --</option>
                  {documents.map((d) => (
                    <option key={d.id} value={d.id}>
                      Renew: {d.document_name} ({d.document_number}) — current v{d.version || 1}
                    </option>
                  ))}
                </select>
                <p className="text-[10px] text-ink-muted mt-1">
                  Renewals automatically increment version number and preserve previous versions for authorized officers.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-ink-strong block mb-1">Document Category</label>
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
                  <label className="font-semibold text-ink-strong block mb-1">Registration / Deed No.</label>
                  <input
                    type="text"
                    value={uploadDocNo}
                    onChange={(e) => setUploadDocNo(e.target.value)}
                    placeholder="e.g. REG-LEASE-2026-KAR-891"
                    className="w-full p-2 bg-slate-50 border border-ink-line rounded-lg text-xs font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
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

              {/* Upload Progress Bar */}
              {uploadLoading && (
                <div className="space-y-1.5 pt-1">
                  <div className="flex justify-between text-[11px] font-semibold text-ink-muted">
                    <span className="flex items-center gap-1.5">
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-blossom-600" />
                      Storing file bytes & computing SHA-256 hash...
                    </span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
                    <div
                      className="bg-gradient-to-r from-blossom-500 to-indigo-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              <div className="bg-blossom-50/60 p-3 rounded-xl border border-blossom-200 text-[11px] text-ink space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-ink-strong">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  Statutory Non-Repudiation Engine:
                </div>
                <p className="text-ink-muted">
                  Uploaded bytes are cryptographically digested via SHA-256 and stamped to the Merkle audit ledger. Future downloads dynamically re-verify byte fidelity to prevent on-disk tampering.
                </p>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setSelectedFile(null);
                  setUploadError(null);
                }}
                disabled={uploadLoading}
                className="btn-secondary !text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleRealUpload}
                disabled={uploadLoading || !selectedFile}
                className="btn-primary !text-xs disabled:opacity-50"
              >
                {uploadLoading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="w-3.5 h-3.5" /> Submit & Store File
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* VERSION HISTORY MODAL */}
      {showVersionModal && (
        <div className="fixed inset-0 bg-ink-strong/50 backdrop-blur-xs flex items-center justify-center z-50 p-4 animate-fade-in">
          <div className="bg-white rounded-2xl shadow-xl border border-ink-line w-full max-w-xl p-6 space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                  <History className="w-4 h-4 text-indigo-600" />
                  Document Version History
                </h3>
                <p className="text-[11px] text-ink-muted mt-0.5">
                  Immutable record of past submissions and renewals per Chapter II Clause 2.1
                </p>
              </div>
              <button
                onClick={() => setShowVersionModal(false)}
                className="p-1 hover:bg-slate-100 rounded-lg text-ink-muted transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {versionLoading ? (
              <div className="py-12 flex flex-col items-center justify-center gap-2 text-ink-muted text-xs">
                <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
                <span>Loading version chain from audit ledger...</span>
              </div>
            ) : versionHistoryData ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs bg-slate-50 p-3 rounded-xl border border-ink-line">
                  <div>
                    <span className="text-ink-muted">Registration: </span>
                    <span className="font-mono font-bold text-ink-strong">{versionHistoryData.document_number}</span>
                  </div>
                  <div className="text-[11px] font-semibold text-ink-muted">
                    Total Versions: <span className="text-ink-strong font-bold">{versionHistoryData.total_versions}</span>
                  </div>
                </div>

                <div className="space-y-2">
                  {versionHistoryData.versions?.map((ver: any) => (
                    <div
                      key={ver.id}
                      className={`p-3.5 rounded-xl border transition-all ${
                        ver.is_latest_version
                          ? 'border-indigo-300 bg-indigo-50/30'
                          : 'border-ink-line bg-white hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-slate-900 text-white">
                            v{ver.version}
                          </span>
                          {ver.is_latest_version && (
                            <span className="text-[10px] font-bold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded border border-emerald-300">
                              ACTIVE (LATEST)
                            </span>
                          )}
                          <span className="text-xs font-bold text-ink-strong">
                            {ver.original_filename || ver.document_name}
                          </span>
                        </div>
                        <button
                          onClick={() => handleDownloadDoc(ver)}
                          disabled={downloadingDocId === ver.id}
                          className="px-2.5 py-1 bg-white hover:bg-slate-100 text-blue-700 rounded-lg border border-blue-200 font-semibold text-[11px] flex items-center gap-1 shadow-xs transition-colors disabled:opacity-50"
                        >
                          {downloadingDocId === ver.id ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Download className="w-3 h-3" />
                          )}
                          Download v{ver.version}
                        </button>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-2 pt-2 border-t border-slate-100 text-[10px] text-ink-muted">
                        <div>
                          <span>Size: </span>
                          <strong className="text-ink-strong">
                            {ver.size_bytes ? `${(ver.size_bytes / 1024).toFixed(1)} KB` : 'N/A'}
                          </strong>
                        </div>
                        <div>
                          <span>Uploaded: </span>
                          <strong className="text-ink-strong">
                            {ver.created_at ? new Date(ver.created_at).toLocaleDateString() : 'N/A'}
                          </strong>
                        </div>
                        <div>
                          <span>Status: </span>
                          <strong className="text-ink-strong">{ver.status}</strong>
                        </div>
                      </div>

                      <div className="mt-1 text-[10px] font-mono text-ink-muted truncate" title={ver.file_hash_sha256}>
                        SHA-256: {ver.file_hash_sha256 || 'N/A'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-xs text-ink-muted text-center py-6">No version history records found.</div>
            )}

            <div className="flex justify-end pt-2 border-t border-slate-100">
              <button onClick={() => setShowVersionModal(false)} className="btn-secondary !text-xs">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
