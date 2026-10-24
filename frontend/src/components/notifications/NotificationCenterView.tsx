'use client';

import React, { useState, useEffect } from 'react';
import { useApp } from '@/lib/app-context';
import { apiFetch } from '@/lib/api';
import {
  Bell,
  Mail,
  MessageSquare,
  Smartphone,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Send,
  Settings,
  Filter,
  Check,
  Zap,
  Loader2,
  Globe,
  ShieldCheck,
  ExternalLink,
} from 'lucide-react';

export const NotificationCenterView: React.FC = () => {
  const { currentUser } = useApp();

  const [notifications, setNotifications] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterChannel, setFilterChannel] = useState<string>('ALL');
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [resendingId, setResendingId] = useState<string | null>(null);
  const [runningScheduler, setRunningScheduler] = useState(false);
  const [schedulerStatus, setSchedulerStatus] = useState<any | null>(null);

  // User & Institution Preferences state
  const [showPreferences, setShowPreferences] = useState(false);
  const [prefLang, setPrefLang] = useState('en');
  const [prefChannels, setPrefChannels] = useState<string[]>(['IN_APP', 'EMAIL']);
  const [whatsappPhone, setWhatsappPhone] = useState('+91-9876543210');
  const [optInWhatsapp, setOptInWhatsapp] = useState(false);
  const [savingPrefs, setSavingPrefs] = useState(false);
  const [prefSuccess, setPrefSuccess] = useState(false);

  const fetchNotificationsAndScheduler = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<any>('/api/v1/alerts/notifications').catch(() => null);
      if (data?.notifications) {
        setNotifications(data.notifications);
      }
      const statusData = await apiFetch<any>('/api/v1/scheduler/status').catch(() => null);
      if (statusData) {
        setSchedulerStatus(statusData);
      }
      const prefData = await apiFetch<any>('/api/v1/alerts/preferences').catch(() => null);
      if (prefData) {
        setPrefLang(prefData.preferred_language || 'en');
        if (prefData.preferred_channels) {
          setPrefChannels(prefData.preferred_channels.split(','));
        }
        if (prefData.whatsapp_phone) {
          setWhatsappPhone(prefData.whatsapp_phone);
        }
        setOptInWhatsapp(Boolean(prefData.opt_in_whatsapp));
      }
    } catch (err) {
      console.error('Failed to load notification center data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotificationsAndScheduler();
  }, []);

  const handleResend = async (notifId: string) => {
    setResendingId(notifId);
    try {
      const res = await apiFetch<any>(`/api/v1/alerts/notifications/${notifId}/resend`, {
        method: 'POST',
      });
      alert(`Alert resent successfully! New status: ${res.delivery_status}. Stamped in audit ledger.`);
      fetchNotificationsAndScheduler();
    } catch (err: any) {
      alert(`Resend failed: ${err?.message || 'Error'}`);
    } finally {
      setResendingId(null);
    }
  };

  const handleTriggerScheduler = async () => {
    setRunningScheduler(true);
    try {
      const data = await apiFetch<any>('/api/v1/scheduler/run-now', {
        method: 'POST',
      });
      alert(
        `Real-clock evaluation cycle executed!\n` +
        `• Doc Expiry Alerts: ${data.stats?.doc_expiry_alerts || 0}\n` +
        `• Undertaking Alerts: ${data.stats?.undertaking_alerts || 0}\n` +
        `• EVC Alerts: ${data.stats?.evc_alerts || 0}\n` +
        `• SLA Breach Alerts: ${data.stats?.sla_breach_alerts || 0}\n` +
        `• Skipped Idempotent: ${data.stats?.skipped_idempotent || 0}`
      );
      fetchNotificationsAndScheduler();
    } catch (err: any) {
      alert(`Evaluation trigger failed: ${err?.message || 'Error'}`);
    } finally {
      setRunningScheduler(false);
    }
  };

  const handleSavePreferences = async () => {
    setSavingPrefs(true);
    setPrefSuccess(false);
    try {
      await apiFetch<any>('/api/v1/alerts/preferences', {
        method: 'PUT',
        body: JSON.stringify({
          preferred_language: prefLang,
          preferred_channels: prefChannels.join(','),
          whatsapp_phone: whatsappPhone,
          opt_in_whatsapp: optInWhatsapp,
        }),
      });
      setPrefSuccess(true);
      setTimeout(() => setPrefSuccess(false), 3000);
    } catch (err: any) {
      alert(`Failed to save preferences: ${err?.message || 'Error'}`);
    } finally {
      setSavingPrefs(false);
    }
  };

  const filteredNotifs = notifications.filter((n) => {
    if (filterChannel !== 'ALL') {
      if (filterChannel === 'EMAIL' && !n.delivery_channel?.includes('EMAIL')) return false;
      if (filterChannel === 'WHATSAPP' && !n.delivery_channel?.includes('WHATSAPP')) return false;
      if (filterChannel === 'SMS' && !n.delivery_channel?.includes('SMS')) return false;
      if (filterChannel === 'IN_APP' && n.delivery_channel !== 'IN_APP') return false;
    }
    if (filterStatus !== 'ALL') {
      if (n.delivery_status !== filterStatus) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-ink-line p-5 shadow-soft flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-ink-strong flex items-center gap-2">
              <Bell className="w-5 h-5 text-blossom-600" />
              Statutory Notification & Alert Dispatch Centre
            </h1>
            <span className="badge-sample-value">Task 2 Real Engine</span>
          </div>
          <p className="text-xs text-ink-muted mt-1">
            Real APScheduler clock, multi-channel dispatch (Real SMTP, Twilio WhatsApp sandbox, In-App), static reviewed multilingual templates, and idempotency protection.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setShowPreferences(true)}
            className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 border border-ink-line text-ink-strong rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <Settings className="w-3.5 h-3.5 text-slate-600" /> Channels & Languages
          </button>
          <button
            onClick={handleTriggerScheduler}
            disabled={runningScheduler}
            className="px-3.5 py-1.5 bg-gradient-to-r from-blossom-600 to-indigo-600 hover:from-blossom-700 hover:to-indigo-700 text-white rounded-xl text-xs font-bold shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-50"
          >
            {runningScheduler ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Zap className="w-3.5 h-3.5 text-amber-300" />
            )}
            Run Real-Clock Evaluation
          </button>
        </div>
      </div>

      {/* Scheduler Status & KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 bg-white rounded-xl border border-ink-line shadow-soft">
          <div className="flex items-center justify-between text-xs text-ink-muted">
            <span className="font-semibold">APScheduler Status</span>
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          </div>
          <div className="text-base font-bold text-ink-strong mt-1">
            {schedulerStatus?.is_running ? 'Active & Watching' : 'Initialized (On-Demand)'}
          </div>
          <p className="text-[11px] text-ink-muted mt-0.5">
            Startup catch-up: {schedulerStatus?.catchup_completed ? 'Completed ✓' : 'Ready'}
          </p>
        </div>

        <div className="p-4 bg-white rounded-xl border border-ink-line shadow-soft">
          <div className="flex items-center justify-between text-xs text-ink-muted">
            <span className="font-semibold">Real SMTP Channel</span>
            <Mail className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-base font-bold text-emerald-700 mt-1">
            {notifications.filter((n) => n.delivery_channel?.includes('EMAIL') && n.delivery_status === 'DELIVERED').length} Delivered
          </div>
          <p className="text-[11px] text-ink-muted mt-0.5">Mailpit (Dev) / SMTP with backoff</p>
        </div>

        <div className="p-4 bg-white rounded-xl border border-ink-line shadow-soft">
          <div className="flex items-center justify-between text-xs text-ink-muted">
            <span className="font-semibold">WhatsApp Sandbox</span>
            <MessageSquare className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-base font-bold text-ink-strong mt-1">
            {notifications.filter((n) => n.delivery_channel?.includes('WHATSAPP')).length} Messages
          </div>
          <p className="text-[11px] text-ink-muted mt-0.5">Twilio Sandbox Adapter (Opt-in)</p>
        </div>

        <div className="p-4 bg-white rounded-xl border border-ink-line shadow-soft">
          <div className="flex items-center justify-between text-xs text-ink-muted">
            <span className="font-semibold">Failed / Deferred</span>
            <AlertTriangle className="w-4 h-4 text-rose-600" />
          </div>
          <div className="text-base font-bold text-rose-700 mt-1">
            {notifications.filter((n) => n.delivery_status === 'FAILED' || n.delivery_status === 'DEFERRED_QUIET_HOURS').length} Alerts
          </div>
          <p className="text-[11px] text-ink-muted mt-0.5">Quiet hours & retries tracked</p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white rounded-xl border border-ink-line p-3 shadow-soft flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-ink-muted" />
          <span className="text-xs font-bold text-ink-strong">Filter Channel:</span>
          {['ALL', 'EMAIL', 'WHATSAPP', 'IN_APP', 'SMS'].map((ch) => (
            <button
              key={ch}
              onClick={() => setFilterChannel(ch)}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                filterChannel === ch
                  ? 'bg-blossom-100 text-blossom-700 font-bold border border-blossom-300'
                  : 'text-ink-muted hover:bg-slate-100'
              }`}
            >
              {ch}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-ink-strong">Status:</span>
          {['ALL', 'DELIVERED', 'FAILED', 'DEFERRED_QUIET_HOURS', 'SIMULATED'].map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                filterStatus === st
                  ? 'bg-slate-900 text-white font-bold'
                  : 'text-ink-muted hover:bg-slate-100'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Notifications Table */}
      <div className="bg-white rounded-2xl border border-ink-line shadow-soft overflow-hidden">
        <div className="p-4 bg-slate-50 border-b border-ink-line flex items-center justify-between">
          <div className="font-bold text-xs text-ink-strong">
            Notification Audit Ledger & Delivery Log ({filteredNotifs.length})
          </div>
          <button
            onClick={fetchNotificationsAndScheduler}
            className="text-xs font-semibold text-blossom-600 hover:underline flex items-center gap-1"
          >
            <RotateCcw className="w-3 h-3" /> Refresh Logs
          </button>
        </div>

        {loading ? (
          <div className="py-16 text-center text-xs text-ink-muted flex flex-col items-center justify-center gap-2">
            <Loader2 className="w-6 h-6 animate-spin text-blossom-600" />
            <span>Fetching alert delivery records...</span>
          </div>
        ) : filteredNotifs.length === 0 ? (
          <div className="py-12 text-center text-xs text-ink-muted">
            No notification records match the selected filter.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-100/70 text-ink-strong border-b border-ink-line">
                  <th className="py-2.5 px-3 font-semibold">Timestamp & Category</th>
                  <th className="py-2.5 px-3 font-semibold">Alert Subject & Content</th>
                  <th className="py-2.5 px-3 font-semibold">Recipient & Lang</th>
                  <th className="py-2.5 px-3 font-semibold">Channel</th>
                  <th className="py-2.5 px-3 font-semibold">Delivery Status</th>
                  <th className="py-2.5 px-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredNotifs.map((n) => (
                  <tr key={n.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <div className="font-mono text-[11px] text-ink-strong">{n.timestamp}</div>
                      <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded uppercase ${
                        n.severity === 'CRITICAL'
                          ? 'bg-rose-100 text-rose-700'
                          : 'bg-slate-200 text-slate-700'
                      }`}>
                        {n.category}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 max-w-sm">
                      <div className="font-bold text-ink-strong">{n.title}</div>
                      <p className="text-[11px] text-ink-muted line-clamp-2 mt-0.5">{n.message}</p>
                      {n.receipt_id && (
                        <span className="text-[9px] font-mono text-slate-400 block truncate mt-0.5" title={n.receipt_id}>
                          Receipt: {n.receipt_id}
                        </span>
                      )}
                      {n.error_message && (
                        <span className="text-[10px] text-rose-600 font-semibold block mt-0.5">
                          Error: {n.error_message}
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-ink">{n.recipient_contact || 'Registered Officer'}</div>
                      <span className="text-[10px] font-mono font-bold text-indigo-600 uppercase">
                        [{n.language || 'en'}]
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                        n.delivery_channel === 'EMAIL'
                          ? 'bg-blue-50 text-blue-800 border-blue-200'
                          : n.delivery_channel?.includes('WHATSAPP')
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                          : n.delivery_channel === 'SMS_SIMULATED'
                          ? 'bg-slate-100 text-slate-700 border-slate-200'
                          : 'bg-purple-50 text-purple-800 border-purple-200'
                      }`}>
                        {n.delivery_channel}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        n.delivery_status === 'DELIVERED'
                          ? 'bg-emerald-100 text-emerald-800'
                          : n.delivery_status === 'FAILED'
                          ? 'bg-rose-100 text-rose-800'
                          : n.delivery_status === 'DEFERRED_QUIET_HOURS'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-slate-100 text-slate-700'
                      }`}>
                        {n.delivery_status}
                      </span>
                      {n.retry_count > 0 && (
                        <span className="text-[9px] text-ink-muted block mt-0.5">
                          Retries: {n.retry_count}
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {(n.delivery_status === 'FAILED' || n.delivery_status === 'DEFERRED_QUIET_HOURS') && (
                        <button
                          onClick={() => handleResend(n.id)}
                          disabled={resendingId === n.id}
                          className="px-2 py-1 bg-white hover:bg-slate-100 border border-slate-300 rounded text-[11px] font-semibold text-ink-strong shadow-xs transition-colors flex items-center gap-1 ml-auto disabled:opacity-50"
                        >
                          {resendingId === n.id ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <RotateCcw className="w-3 h-3 text-blossom-600" />
                          )}
                          Resend
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* PREFERENCES MODAL */}
      {showPreferences && (
        <div className="fixed inset-0 bg-ink-strong/50 backdrop-blur-xs flex items-center justify-center z-50 p-4 animate-fade-in">
          <div className="bg-white rounded-2xl shadow-xl border border-ink-line w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-ink-strong flex items-center gap-2">
                <Settings className="w-4 h-4 text-blossom-600" />
                Notification Channel & Language Preferences
              </h3>
              <button
                onClick={() => setShowPreferences(false)}
                className="p-1 hover:bg-slate-100 rounded-lg text-ink-muted transition-colors"
              >
                ✕
              </button>
            </div>

            {prefSuccess && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-2 text-xs text-emerald-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Preferences updated successfully and recorded in audit ledger.</span>
              </div>
            )}

            <div className="space-y-4 text-xs">
              {/* Language Selection */}
              <div>
                <label className="font-semibold text-ink-strong block mb-1">
                  Preferred Alert Language (Static Reviewed Templates)
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { code: 'en', label: 'English' },
                    { code: 'hi', label: 'हिन्दी (Hindi)' },
                    { code: 'ta', label: 'தமிழ் (Tamil)' },
                  ].map((l) => (
                    <button
                      key={l.code}
                      type="button"
                      onClick={() => setPrefLang(l.code)}
                      className={`p-2 rounded-xl border text-center font-bold text-xs transition-all ${
                        prefLang === l.code
                          ? 'border-blossom-500 bg-blossom-50 text-blossom-800'
                          : 'border-slate-200 bg-slate-50 text-ink-muted hover:border-slate-300'
                      }`}
                    >
                      {l.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Channels */}
              <div>
                <label className="font-semibold text-ink-strong block mb-1">
                  Enabled Delivery Channels
                </label>
                <div className="space-y-2">
                  {[
                    { id: 'IN_APP', label: 'In-App Portal Notifications', desc: 'Real-time dashboard notifications' },
                    { id: 'EMAIL', label: 'Email Notifications (Real SMTP)', desc: 'Sent to registered official mailbox' },
                    { id: 'WHATSAPP_SANDBOX', label: 'WhatsApp Notifications (Twilio Sandbox)', desc: 'Official sandbox alerts' },
                  ].map((ch) => {
                    const isChecked = prefChannels.includes(ch.id);
                    return (
                      <label
                        key={ch.id}
                        className="flex items-start gap-2.5 p-2 bg-slate-50 rounded-xl border border-slate-200 cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setPrefChannels([...prefChannels, ch.id]);
                            } else {
                              setPrefChannels(prefChannels.filter((c) => c !== ch.id));
                            }
                          }}
                          className="mt-0.5 rounded border-slate-300 text-blossom-600 focus:ring-blossom-500"
                        />
                        <div>
                          <div className="font-bold text-ink-strong">{ch.label}</div>
                          <div className="text-[10px] text-ink-muted">{ch.desc}</div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* WhatsApp Opt-In */}
              <div className="p-3 bg-emerald-50/60 rounded-xl border border-emerald-200 space-y-2">
                <label className="font-bold text-emerald-900 block">
                  WhatsApp Sandbox Opt-In
                </label>
                <input
                  type="text"
                  value={whatsappPhone}
                  onChange={(e) => setWhatsappPhone(e.target.value)}
                  placeholder="+91-9876543210"
                  className="w-full p-2 bg-white border border-emerald-300 rounded-lg text-xs font-mono"
                />
                <label className="flex items-center gap-2 cursor-pointer pt-1">
                  <input
                    type="checkbox"
                    checked={optInWhatsapp}
                    onChange={(e) => setOptInWhatsapp(e.target.checked)}
                    className="rounded border-emerald-400 text-emerald-600 focus:ring-emerald-500"
                  />
                  <span className="text-[11px] text-emerald-800 font-medium">
                    I opt in to receive statutory AICTE regulatory alerts via WhatsApp Sandbox.
                  </span>
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                onClick={() => setShowPreferences(false)}
                className="btn-secondary !text-xs"
              >
                Close
              </button>
              <button
                onClick={handleSavePreferences}
                disabled={savingPrefs}
                className="btn-primary !text-xs flex items-center gap-1"
              >
                {savingPrefs ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                Save Preferences
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
