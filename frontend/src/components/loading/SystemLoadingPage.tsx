'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  ShieldCheck,
  Landmark,
  CheckCircle2,
  Cpu,
  Layers,
  ArrowRight,
  Database,
  Lock,
  Sparkles,
  Server,
  Activity,
} from 'lucide-react';

interface SystemLoadingPageProps {
  onComplete: () => void;
}

interface DiagnosticStep {
  id: string;
  label: string;
  detail: string;
  threshold: number;
  icon: React.ReactNode;
}

export const SystemLoadingPage: React.FC<SystemLoadingPageProps> = ({ onComplete }) => {
  const [progress, setProgress] = useState(0);
  const [currentStatusText, setCurrentStatusText] = useState('Connecting to National Gateway...');
  const completedRef = useRef(false);

  const diagnosticSteps: DiagnosticStep[] = [
    {
      id: 'step-1',
      label: 'National Data Gateway',
      detail: 'TLS 1.3 / DPDP Act 2023 Secure Enclave',
      threshold: 18,
      icon: <Lock className="w-4 h-4 text-blossom-600" />,
    },
    {
      id: 'step-2',
      label: 'APH 2024–27 Workflow Engine',
      detail: 'Compiling Table 2.3 statutory approval pipeline',
      threshold: 38,
      icon: <Layers className="w-4 h-4 text-blossom-700" />,
    },
    {
      id: 'step-3',
      label: '7 Regional Corridors Sync',
      detail: 'SWRO, SRO, WRO, NRO, ERO, CRO, NWRO',
      threshold: 58,
      icon: <Server className="w-4 h-4 text-blossom-600" />,
    },
    {
      id: 'step-4',
      label: 'Dynamic SLA & Expiry Timers',
      detail: 'Deficiency pause clock active (design choice, configurable)',
      threshold: 76,
      icon: <Activity className="w-4 h-4 text-amberState-700" />,
    },
    {
      id: 'step-5',
      label: 'SHA-256 Cryptographic Ledger',
      detail: 'Cryptographic hash chain continuous & tamper-evident',
      threshold: 90,
      icon: <Database className="w-4 h-4 text-blossom-700" />,
    },
    {
      id: 'step-6',
      label: 'AICTE Copilot & Weighted Risk Scoring',
      detail: 'APH clause RAG core & factor attribution',
      threshold: 99,
      icon: <Sparkles className="w-4 h-4 text-blossom-600" />,
    },
  ];

  // Progress animation
  useEffect(() => {
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          if (!completedRef.current) {
            completedRef.current = true;
            // Short delay to display 100% completion before advancing
            setTimeout(() => {
              onComplete();
            }, 350);
          }
          return 100;
        }

        const increment = prev < 30 ? 3 : prev < 70 ? 2 : prev < 90 ? 2 : 1;
        const next = Math.min(prev + increment, 100);

        if (next < 25) {
          setCurrentStatusText('Establishing Secure Handshake with National Gateway...');
        } else if (next < 50) {
          setCurrentStatusText('Compiling APH 2024–27 Statutory Rule Tables...');
        } else if (next < 75) {
          setCurrentStatusText('Synchronizing 7 Regional Offices & Live Workload Corridors...');
        } else if (next < 95) {
          setCurrentStatusText('Verifying Cryptographic Ledger Integrity & XAI Weights...');
        } else {
          setCurrentStatusText('Statutory Core Online • Gateway Fully Initialized');
        }

        return next;
      });
    }, 60);

    return () => clearInterval(interval);
  }, [onComplete]);

  const handleManualSkip = () => {
    if (!completedRef.current) {
      completedRef.current = true;
      onComplete();
    }
  };

  return (
    <div className="min-h-screen w-full bg-white text-ink flex flex-col justify-between p-4 sm:p-8 animate-fade-in">
      {/* Top Header */}
      <div className="max-w-4xl mx-auto w-full flex items-center justify-between border-b border-ink-line pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blossom-600 text-white flex items-center justify-center font-bold shadow-soft">
            <Landmark className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[11px] font-bold tracking-wider text-blossom-700 uppercase">
              Government of India • Ministry of Education
            </div>
            <div className="text-sm font-bold text-ink-strong">
              All India Council for Technical Education (AICTE)
            </div>
          </div>
        </div>

        {/* Portal Badge & Skip Button */}
        <div className="flex items-center gap-2">
          <span className="hidden sm:inline-block text-[10px] font-mono font-bold bg-blossom-100 text-blossom-700 px-2.5 py-1 rounded border border-blossom-300">
            National Portal • APH 2024–27
          </span>
          <button
            data-testid="skip-boot-button"
            onClick={handleManualSkip}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-blossom-600 hover:bg-blossom-700 text-white flex items-center gap-1.5 shadow-soft transition-all"
          >
            <span>Skip to Login</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Center Console in Cherry Blossom Palette */}
      <div className="max-w-2xl mx-auto w-full my-auto py-6 space-y-6">
        {/* Emblem & Title */}
        <div className="text-center space-y-3">
          <div className="relative inline-flex items-center justify-center">
            {/* Cherry Blossom Radiant Pulse Rings */}
            <div className="absolute w-24 h-24 rounded-full bg-blossom-300/40 animate-ping opacity-75" />
            <div className="absolute w-28 h-28 rounded-full bg-blossom-100/60 animate-pulse" />
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-tr from-blossom-100 via-white to-blossom-100 border-2 border-blossom-300 flex items-center justify-center shadow-card relative z-10">
              <ShieldCheck className="w-10 h-10 text-blossom-600" />
            </div>
          </div>

          <div>
            <div className="inline-block bg-blossom-100 text-blossom-700 text-[10px] font-bold px-2.5 py-0.5 rounded-full border border-blossom-300 mb-2">
              APH 2024–27 Statutory Lifecycle
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-ink-strong">
              Integrated Approval & Compliance Automation System
            </h1>
            <p className="text-xs sm:text-sm text-ink-muted mt-1 max-w-lg mx-auto">
              Automating institutional workflows, dynamic SLA monitoring, EVC scheduling, and tamper-evident compliance monitoring.
            </p>
          </div>
        </div>

        {/* Cherry Blossom Center Card */}
        <div className="bg-gradient-to-b from-white via-blossom-100/20 to-blossom-100/30 rounded-2xl border-2 border-blossom-300/80 p-6 shadow-card backdrop-blur-sm space-y-4">
          {/* Status Row */}
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-ink-strong font-semibold flex items-center gap-2">
              <Cpu className="w-4 h-4 text-blossom-600 animate-spin" style={{ animationDuration: '3s' }} />
              <span className="truncate">{currentStatusText}</span>
            </span>
            <span className="font-bold text-blossom-700 text-sm">
              {progress}%
            </span>
          </div>

          {/* Cherry Blossom Progress Bar */}
          <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden p-0.5 border border-blossom-300">
            <div
              className="h-full rounded-full bg-gradient-to-r from-blossom-300 via-blossom-600 to-blossom-700 transition-all duration-100 ease-out shadow-sm"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Diagnostic Steps Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-2">
            {diagnosticSteps.map((step) => {
              const isDone = progress >= step.threshold;
              return (
                <div
                  key={step.id}
                  className={`p-2.5 rounded-xl border text-xs transition-all flex items-center justify-between ${
                    isDone
                      ? 'bg-white border-blossom-300 text-ink-strong shadow-xs'
                      : 'bg-slate-50/80 border-slate-200 text-ink-muted opacity-60'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="shrink-0">{step.icon}</div>
                    <div className="truncate">
                      <div className="font-semibold text-ink-strong truncate">{step.label}</div>
                      <div className="text-[10px] text-ink-muted truncate">{step.detail}</div>
                    </div>
                  </div>

                  <div className="shrink-0 ml-2">
                    {isDone ? (
                      <CheckCircle2 className="w-4 h-4 text-mint-700 animate-fade-in" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border border-slate-300 animate-pulse" />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Footer */}
      <div className="max-w-4xl mx-auto w-full flex flex-wrap items-center justify-between gap-3 text-[11px] text-ink-muted border-t border-ink-line pt-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-mint-700 animate-pulse" />
          <span>Statutory Authority Reserved: AICTE Approval Process Handbook (APH 2024–27)</span>
        </div>
        <div className="flex items-center gap-4 font-mono font-medium">
          <span className="text-mint-700 font-bold">• Designed with DPDP principles in mind</span>
          <span>• SHA-256 Ledger Verified</span>
        </div>
      </div>
    </div>
  );
};
