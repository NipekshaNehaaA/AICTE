'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  AlertTriangle,
  ShieldCheck,
  FileText,
  Lock,
  CheckCircle2,
  X,
  ExternalLink,
  RefreshCw,
  FolderOpen,
} from 'lucide-react';
import { apiFetch } from '@/lib/api';

export const SecurityAnomaliesView: React.FC = () => {
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnomalies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<{ anomalies: any[] }>('/api/v1/differentiators/anomalies');
      setAnomalies(data.anomalies || []);
    } catch (err: any) {
      console.error('Failed to fetch anomalies', err);
      setError(err?.message || 'Failed to fetch security anomalies');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAnomalies();
  }, [fetchAnomalies]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-ink-line p-4 shadow-soft flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-roseState-700" />
            <h1 className="text-lg font-bold text-ink-strong">
              Document Integrity & Anomaly Detection Center
            </h1>
            <span className="bg-roseState-100 text-roseState-700 text-[10px] font-bold px-2 py-0.5 rounded border border-roseState-700/30">
              Signature Differentiator 2
            </span>
          </div>
          <p className="text-xs text-ink-muted mt-0.5">
            Cryptographic SHA-256 hash collision detection, metadata tamper flags, and fraudulent document inspection.
          </p>
        </div>
        <button
          onClick={fetchAnomalies}
          className="btn-secondary !text-xs"
          disabled={loading}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="p-8 bg-white rounded-xl border border-ink-line text-center shadow-soft">
          <RefreshCw className="w-7 h-7 text-blossom-600 animate-spin mx-auto mb-2" />
          <h3 className="text-xs font-bold text-ink-strong">Scanning Hash Collision Registry...</h3>
          <p className="text-[11px] text-ink-muted mt-0.5">Cross-referencing document SHA-256 hashes against known entities.</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="p-4 bg-rose-50 rounded-xl border border-rose-200 text-center shadow-soft">
          <AlertTriangle className="w-6 h-6 text-rose-600 mx-auto mb-1.5" />
          <h3 className="text-xs font-bold text-rose-900">Failed to Load Security Anomalies</h3>
          <p className="text-[11px] text-rose-700 max-w-md mx-auto mt-0.5 mb-3">{error}</p>
          <button
            onClick={fetchAnomalies}
            className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-lg shadow-sm inline-flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            Retry Scan
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && anomalies.length === 0 && (
        <div className="p-8 bg-white rounded-xl border border-ink-line text-center shadow-soft">
          <CheckCircle2 className="w-8 h-8 text-mint-600 mx-auto mb-2" />
          <h3 className="text-xs font-bold text-ink-strong">No Document Anomalies Detected</h3>
          <p className="text-[11px] text-ink-muted mt-0.5">All uploaded certificates and documents have unique, uncorrupted hashes.</p>
        </div>
      )}

      {/* Anomalies List */}
      {!loading && !error && anomalies.length > 0 && (
        <div className="space-y-4">
          {anomalies.map((a) => (
          <div key={a.id} className="p-5 rounded-xl border border-roseState-700/40 bg-roseState-100/30 shadow-card space-y-3">
            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-roseState-700/20 pb-3">
              <div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-roseState-700 text-white uppercase">
                  {a.anomaly_type.replace('_', ' ')} • {a.severity} SEVERITY
                </span>
                <h3 className="text-sm font-bold text-ink-strong mt-1">
                  Cross-Institution Document Reuse Detected
                </h3>
                <div className="text-xs text-ink">
                  Institution: <strong>{a.institution_name}</strong> • Document: {a.document_name} ({a.document_number})
                </div>
              </div>

              <div className="text-right text-[11px] text-ink-muted">
                Detected at: {a.created_at}
              </div>
            </div>

            <p className="text-xs text-ink leading-relaxed">
              {a.details}
            </p>

            <div className="bg-white p-3 rounded-lg border border-slate-200 text-xs font-mono space-y-1">
              <span className="text-[10px] font-bold text-ink-muted uppercase block">Matching SHA-256 Digest</span>
              <div className="text-blossom-700 font-bold truncate">{a.file_hash_sha256}</div>
            </div>

            <div className="flex items-center justify-between pt-1 text-xs">
              <span className="text-[11px] text-ink-muted">
                SUGGEST-ONLY flag: AI and hash checkers flag suspicion; an authorized human officer investigates.
              </span>
              <button
                onClick={() => alert('Detailed comparative forensic inspection opened.')}
                className="btn-primary !text-xs !py-1 !px-3"
              >
                Initiate Forensic Scrutiny
              </button>
            </div>
          </div>
        ))}
        </div>
      )}
    </div>
  );
};
