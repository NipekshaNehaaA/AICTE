'use client';

import React, { useState, useEffect } from 'react';
import { apiFetch } from '@/lib/api';
import {
  History,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Lock,
  Search,
  ExternalLink,
  QrCode,
  RefreshCw,
  FolderOpen,
} from 'lucide-react';
import { useApp } from '@/lib/app-context';

export const AuditLedgerView: React.FC = () => {
  const { evaluatorMode, isDemoMode } = useApp();
  const isEvalActive = evaluatorMode || isDemoMode;
  const [entries, setEntries] = useState<any[]>([]);
  const [verificationResult, setVerificationResult] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAuditTrail = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiFetch<any>('/api/v1/audit/trail?limit=40');
      setEntries(data?.entries || []);
    } catch (err: any) {
      console.error('Failed to fetch audit trail', err);
      setError(err.message || 'Failed to retrieve immutable audit ledger.');
    } finally {
      setLoading(false);
    }
  };

  const verifyChain = async () => {
    try {
      const data = await apiFetch<any>('/api/v1/audit/verify-chain', { method: 'POST' });
      setVerificationResult(data);
    } catch (err: any) {
      console.error('Error verifying audit chain', err);
    }
  };

  const simulateTampering = async () => {
    try {
      await apiFetch('/api/v1/audit/simulate-tampering', { method: 'POST' });
      alert('Tampering simulated: A historical hash was modified. Click "Verify Chain Integrity" to see detection.');
      fetchAuditTrail();
      verifyChain();
    } catch (err: any) {
      alert(`Error simulating tampering: ${err.message}`);
    }
  };

  const restoreChain = async () => {
    try {
      await apiFetch('/api/v1/audit/restore-chain', { method: 'POST' });
      alert('Audit hash chain restored to valid state.');
      fetchAuditTrail();
      verifyChain();
    } catch (err: any) {
      alert(`Error restoring chain: ${err.message}`);
    }
  };

  useEffect(() => {
    fetchAuditTrail();
    verifyChain();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-ink-line p-4 shadow-soft flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-blossom-600" />
            <h1 className="text-lg font-bold text-ink-strong">
              Immutable Cryptographic Audit Trail (SHA-256)
            </h1>
            <span className="bg-mint-100 text-mint-700 text-[10px] font-bold px-2 py-0.5 rounded border border-mint-700/20">
              Append-Only Ledger
            </span>
          </div>
          <p className="text-xs text-ink-muted mt-0.5">
            Non-repudiable audit chain linking every stage advance, revert, document verification, and AI draft approval.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={verifyChain}
            className="btn-primary !text-xs"
          >
            <ShieldCheck className="w-4 h-4" /> Verify Chain Integrity
          </button>
          {isEvalActive && (
            <>
              <button
                onClick={simulateTampering}
                className="btn-secondary !text-xs text-roseState-700 border-roseState-700/30 hover:bg-roseState-100"
                title="Demo Feature: Deliberately corrupts a past hash to show instant detection"
              >
                <AlertTriangle className="w-4 h-4" /> Simulate Tampering
              </button>
              {verificationResult?.status === 'TAMPERING_DETECTED' && (
                <button
                  onClick={restoreChain}
                  className="btn-secondary !text-xs text-mint-700 border-mint-700/30"
                >
                  <RotateCcw className="w-4 h-4" /> Restore Chain
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Verification Status Banner */}
      {verificationResult && (
        <div
          className={`p-4 rounded-xl border text-xs flex items-center justify-between shadow-soft ${
            verificationResult.is_valid
              ? 'bg-mint-100 border-mint-700/30 text-mint-700'
              : 'bg-roseState-100 border-roseState-700/40 text-roseState-700'
          }`}
        >
          <div className="flex items-center gap-3">
            {verificationResult.is_valid ? (
              <CheckCircle2 className="w-6 h-6 text-mint-700 shrink-0" />
            ) : (
              <AlertTriangle className="w-6 h-6 text-roseState-700 shrink-0" />
            )}
            <div>
              <div className="font-bold text-sm">
                {verificationResult.is_valid
                  ? 'Cryptographic Hash Continuity Verified Unbroken'
                  : 'CRITICAL SECURITY BREACH: Hash Chain Tampering Detected!'}
              </div>
              <div className="text-[11px] mt-0.5">
                {verificationResult.message || verificationResult.security_alert}
              </div>
            </div>
          </div>

          <div className="text-right text-[11px] font-mono font-bold">
            Verified {verificationResult.total_entries_verified} Entries
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="p-8 bg-white rounded-xl border border-ink-line text-center shadow-soft">
          <RefreshCw className="w-7 h-7 text-blossom-600 animate-spin mx-auto mb-2" />
          <h3 className="text-xs font-bold text-ink-strong">Synchronizing Cryptographic Audit Trail...</h3>
          <p className="text-[11px] text-ink-muted mt-0.5">Fetching SHA-256 chained transaction blocks.</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="p-4 bg-rose-50 rounded-xl border border-rose-200 text-center shadow-soft">
          <AlertTriangle className="w-6 h-6 text-rose-600 mx-auto mb-1.5" />
          <h3 className="text-xs font-bold text-rose-900">Failed to Retrieve Audit Ledger</h3>
          <p className="text-[11px] text-rose-700 max-w-md mx-auto mt-0.5 mb-3">{error}</p>
          <button
            onClick={fetchAuditTrail}
            className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-lg shadow-sm inline-flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && entries.length === 0 && (
        <div className="p-8 bg-white rounded-xl border border-ink-line text-center shadow-soft">
          <FolderOpen className="w-8 h-8 text-slate-400 mx-auto mb-2" />
          <h3 className="text-xs font-bold text-ink-strong">No Audit Records Found</h3>
          <p className="text-[11px] text-ink-muted mt-0.5">No logged transactions found within current scope.</p>
        </div>
      )}

      {/* Audit Entries Table */}
      {!loading && !error && entries.length > 0 && (
        <div className="bg-white rounded-xl border border-ink-line shadow-soft overflow-hidden">
          <div className="p-3 bg-slate-50 border-b border-ink-line font-bold text-xs text-ink-strong flex items-center justify-between">
            <span>Audit Ledger Entries ({entries.length})</span>
            <span className="text-[10px] text-ink-muted">SHA-256 Chained</span>
          </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="bg-blossom-100/50 text-ink-strong border-b border-ink-line">
                <th className="py-2.5 px-3 font-semibold font-sans">#</th>
                <th className="py-2.5 px-3 font-semibold font-sans">Action & Actor</th>
                <th className="py-2.5 px-3 font-semibold font-sans">Entity</th>
                <th className="py-2.5 px-3 font-semibold font-sans">Previous Hash</th>
                <th className="py-2.5 px-3 font-semibold font-sans">Current Hash</th>
                <th className="py-2.5 px-3 font-semibold font-sans text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-[11px]">
              {entries.map((e) => (
                <tr key={e.id} className="hover:bg-slate-50 transition-colors">
                  <td className="py-2.5 px-3 font-bold text-ink-strong">#{e.id}</td>
                  <td className="py-2.5 px-3 font-sans">
                    <div className="font-bold text-ink-strong">{e.action_type}</div>
                    <div className="text-[10px] text-ink-muted">
                      {e.actor_role} ({e.actor_id ? e.actor_id.slice(0, 12) : 'SYSTEM'})
                    </div>
                  </td>
                  <td className="py-2.5 px-3 font-sans">
                    <span className="bg-slate-100 text-ink px-1.5 py-0.5 rounded text-[10px] font-semibold">
                      {e.entity_type}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-[10px] text-ink-muted truncate max-w-[140px]" title={e.prev_entry_hash}>
                    {e.prev_entry_hash.slice(0, 16)}...
                  </td>
                  <td className="py-2.5 px-3 text-[10px] text-blossom-700 font-bold truncate max-w-[140px]" title={e.curr_entry_hash}>
                    {e.curr_entry_hash.slice(0, 16)}...
                  </td>
                  <td className="py-2.5 px-3 text-right text-[10px] text-ink-muted font-sans whitespace-nowrap">
                    {e.timestamp}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      )}
    </div>
  );
};
