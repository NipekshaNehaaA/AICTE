'use client';

import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  ShieldCheck,
  FileText,
  Lock,
  CheckCircle2,
  X,
  ExternalLink,
} from 'lucide-react';

export const SecurityAnomaliesView: React.FC = () => {
  const [anomalies, setAnomalies] = useState<any[]>([]);

  const fetchAnomalies = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/differentiators/anomalies');
      const data = await res.json();
      setAnomalies(data.anomalies || []);
    } catch (err) {
      console.error('Failed to fetch anomalies', err);
    }
  };

  useEffect(() => {
    fetchAnomalies();
  }, []);

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
      </div>

      {/* Anomalies List */}
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
    </div>
  );
};
