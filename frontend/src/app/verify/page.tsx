'use client';

import React, { useState, useEffect } from 'react';
import { apiFetch } from '@/lib/api';
import {
  ShieldCheck,
  ShieldAlert,
  Search,
  CheckCircle2,
  Lock,
  FileCheck2,
  ExternalLink,
  ArrowLeft,
  Calendar,
  Layers,
  Sparkles,
} from 'lucide-react';

export default function VerifyPage() {
  const [queryHash, setQueryHash] = useState('');
  const [chainHead, setChainHead] = useState('');
  const [verificationResult, setVerificationResult] = useState<any | null>(null);
  const [merkleRoots, setMerkleRoots] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  // Read URL query parameters on mount (e.g. /verify?hash=...&chain_head=...)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const h = params.get('hash') || '';
      const ch = params.get('chain_head') || '';
      if (h) setQueryHash(h);
      if (ch) setChainHead(ch);

      if (h || ch) {
        verifyHash(h, ch);
      }
      fetchMerkleRoots();
    }
  }, []);

  const fetchMerkleRoots = async () => {
    try {
      const data = await apiFetch<{ roots: any[] }>('/api/v1/audit/merkle-roots', { skipAuth: true });
      setMerkleRoots(data.roots || []);
    } catch (err) {
      console.error('Failed to load Merkle roots', err);
    }
  };

  const verifyHash = async (h?: string, ch?: string) => {
    const targetHash = h !== undefined ? h : queryHash;
    const targetChainHead = ch !== undefined ? ch : chainHead;

    if (!targetHash && !targetChainHead) return;

    try {
      setLoading(true);
      setSearched(true);
      const params = new URLSearchParams();
      if (targetHash) params.set('hash', targetHash.trim());
      if (targetChainHead) params.set('chain_head', targetChainHead.trim());

      const data = await apiFetch<any>(`/api/v1/audit/public-verify?${params.toString()}`, { skipAuth: true });
      setVerificationResult(data);
    } catch (err) {
      console.error('Verification error', err);
      setVerificationResult({
        is_verified: false,
        verification_status: 'CONNECTION_ERROR',
        message: 'Could not connect to AICTE Verification Service.',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FDFBFB] text-ink flex flex-col justify-between selection:bg-blossom-200">
      {/* Top Header */}
      <header className="border-b border-ink-line bg-white/90 backdrop-blur-md sticky top-0 z-40 shadow-soft">
        <div className="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blossom-500 to-blossom-700 flex items-center justify-center text-white font-bold shadow-soft">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm tracking-tight text-ink-strong">
                  AICTE Public Regulatory Verifier
                </span>
                <span className="bg-blossom-100 text-blossom-700 text-[10px] font-bold px-2 py-0.5 rounded border border-blossom-300">
                  Outsider-Verifiable Audit
                </span>
              </div>
              <p className="text-[11px] text-ink-muted">
                Statutory Non-Repudiation & Cryptographic SHA-256 Ledger Provenance
              </p>
            </div>
          </div>

          <a
            href="/"
            className="text-xs text-ink-muted hover:text-blossom-700 font-semibold flex items-center gap-1.5 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Dashboard
          </a>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-4xl mx-auto px-4 py-8 flex-1 space-y-8 w-full">
        {/* Verification Hero Banner */}
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold text-ink-strong">
            Verify AICTE Official Document Authenticity
          </h1>
          <p className="text-xs text-ink-muted max-w-xl mx-auto leading-relaxed">
            Verify any exported PDF report, Excel ledger, or regulatory decision hash against AICTE’s immutable Merkle-sealed audit trail. Confirms authenticity with <strong>zero disclosure of sensitive applicant data</strong>.
          </p>
        </div>

        {/* Input Card */}
        <div className="bg-white rounded-2xl border border-ink-line p-6 shadow-soft space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-bold text-ink-strong block">
              Report SHA-256 Hash or Transaction Hash
            </label>
            <div className="relative">
              <input
                type="text"
                value={queryHash}
                onChange={(e) => setQueryHash(e.target.value)}
                placeholder="e.g. 7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069"
                className="w-full pl-9 pr-4 py-2.5 text-xs font-mono bg-slate-50 border border-ink-line rounded-xl focus:outline-none focus:ring-2 focus:ring-blossom-400"
              />
              <Search className="w-4 h-4 text-ink-muted absolute left-3 top-3" />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-ink-muted block">
              Audit Chain Head Hash (Optional from Document Footer / QR)
            </label>
            <input
              type="text"
              value={chainHead}
              onChange={(e) => setChainHead(e.target.value)}
              placeholder="e.g. 9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca7"
              className="w-full px-4 py-2 text-xs font-mono bg-slate-50 border border-ink-line rounded-xl focus:outline-none focus:ring-2 focus:ring-blossom-400"
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <div className="text-[11px] text-ink-muted flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-mint-700" />
              <span>Zero-Knowledge: Applicant PII & confidential data are strictly protected.</span>
            </div>

            <button
              onClick={() => verifyHash()}
              disabled={loading || (!queryHash && !chainHead)}
              className="btn-primary !text-xs !py-2 !px-6 disabled:opacity-50"
            >
              {loading ? 'Verifying...' : 'Verify Cryptographic Proof'}
            </button>
          </div>
        </div>

        {/* Verification Result Card */}
        {searched && verificationResult && (
          <div
            className={`p-6 rounded-2xl border transition-all ${
              verificationResult.is_verified
                ? 'bg-mint-100/30 border-mint-700/40 shadow-soft'
                : 'bg-roseState-100/30 border-roseState-700/40 shadow-soft'
            }`}
          >
            <div className="flex items-start gap-4">
              <div
                className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 ${
                  verificationResult.is_verified
                    ? 'bg-mint-700 text-white'
                    : 'bg-roseState-700 text-white'
                }`}
              >
                {verificationResult.is_verified ? (
                  <ShieldCheck className="w-7 h-7" />
                ) : (
                  <ShieldAlert className="w-7 h-7" />
                )}
              </div>

              <div className="space-y-3 flex-1">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-ink-strong">
                      {verificationResult.is_verified
                        ? 'Cryptographically Verified Authentic'
                        : 'Verification Failed / Tampering Detected'}
                    </h2>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                        verificationResult.is_verified
                          ? 'bg-mint-100 text-mint-700 border-mint-700/30'
                          : 'bg-roseState-100 text-roseState-700 border-roseState-700/30'
                      }`}
                    >
                      {verificationResult.verification_status}
                    </span>
                  </div>
                  <p className="text-xs text-ink mt-1 leading-relaxed">
                    {verificationResult.message}
                  </p>
                </div>

                {/* Details Breakdown */}
                <div className="bg-white p-4 rounded-xl border border-ink-line text-xs space-y-2 font-mono">
                  <div className="flex flex-wrap items-center justify-between border-b border-slate-100 pb-1.5">
                    <span className="text-ink-muted">Document Type:</span>
                    <span className="font-bold text-ink-strong">{verificationResult.entity_type}</span>
                  </div>
                  <div className="flex flex-wrap items-center justify-between border-b border-slate-100 pb-1.5">
                    <span className="text-ink-muted">Verification Timestamp:</span>
                    <span className="text-ink">{verificationResult.verification_timestamp}</span>
                  </div>
                  <div className="space-y-0.5 border-b border-slate-100 pb-1.5">
                    <span className="text-ink-muted block">Query Hash (SHA-256):</span>
                    <span className="text-[11px] text-ink break-all font-bold">
                      {verificationResult.query_hash}
                    </span>
                  </div>
                  <div className="space-y-0.5 border-b border-slate-100 pb-1.5">
                    <span className="text-ink-muted block">Audit Chain Head:</span>
                    <span className="text-[11px] text-blossom-700 break-all font-bold">
                      {verificationResult.chain_head}
                    </span>
                  </div>
                  {verificationResult.daily_merkle_root && (
                    <div className="space-y-0.5 pt-0.5">
                      <span className="text-ink-muted block">Daily Merkle Root ({verificationResult.merkle_date}):</span>
                      <span className="text-[11px] text-mint-700 break-all font-bold">
                        {verificationResult.daily_merkle_root}
                      </span>
                    </div>
                  )}
                </div>

                {/* Statutory Privacy Statement */}
                <div className="text-[11px] text-ink-muted bg-white/70 p-3 rounded-lg border border-slate-200 leading-relaxed">
                  <strong>Statutory Guarantee:</strong> {verificationResult.privacy_guarantee}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Daily Merkle Roots Ledger Summary */}
        <div className="bg-white rounded-2xl border border-ink-line p-6 shadow-soft space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-blossom-600" />
              <h3 className="text-xs font-bold text-ink-strong uppercase tracking-wider">
                Public Daily Merkle Root Registry
              </h3>
            </div>
            <span className="text-[10px] bg-slate-100 text-ink-muted px-2 py-0.5 rounded font-mono">
              Sealed Daily
            </span>
          </div>

          <p className="text-xs text-ink-muted">
            Each day, AICTE cryptographically folds all regulatory transactions into a sealed Merkle root. Any past tampering irrevocably breaks this tree.
          </p>

          <div className="space-y-2">
            {merkleRoots.map((root, idx) => (
              <div
                key={root.id || idx}
                className="p-3 bg-slate-50 rounded-xl border border-ink-line text-xs flex flex-wrap items-center justify-between gap-2"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <Calendar className="w-3.5 h-3.5 text-blossom-600" />
                    <span className="font-bold text-ink-strong">{root.root_date}</span>
                    <span className="text-[10px] bg-white text-ink px-1.5 py-0.5 rounded border border-slate-200">
                      {root.total_entries} Entries
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-ink-muted mt-1 break-all">
                    Root: <strong className="text-ink">{root.merkle_root_hash}</strong>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-[10px] text-mint-700 font-bold bg-mint-100 px-2 py-0.5 rounded border border-mint-700/30">
                    SEALED & VERIFIED
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-ink-line bg-white py-4 text-center text-xs text-ink-muted">
        All India Council for Technical Education (AICTE) • Cryptographic Regulatory Audit Infrastructure
      </footer>
    </div>
  );
}
