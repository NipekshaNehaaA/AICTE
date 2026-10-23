'use client';

import React, { useState } from 'react';
import { useApp, DEMO_USERS, UserRole } from '@/lib/app-context';
import {
  ShieldCheck,
  Lock,
  Mail,
  KeyRound,
  ArrowRight,
  Sparkles,
  Building2,
  CheckCircle2,
  UserCheck,
  AlertCircle,
  Eye,
  EyeOff,
  Landmark,
  Scale,
  Award,
  RotateCcw,
  Users,
} from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { loginAsPersona, loginWithToken, restartBootSequence } = useApp();

  const [activeTab, setActiveTab] = useState<'credentials' | 'personas'>('credentials');
  const [email, setEmail] = useState('ro.swro@aicte-india.org');
  const [password, setPassword] = useState('DemoPassword@123');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // MFA State
  const [mfaStep, setMfaStep] = useState(false);
  const [mfaCode, setMfaCode] = useState('');
  const [mfaUserData, setMfaUserData] = useState<any | null>(null);

  const personas = [
    {
      role: 'REGIONAL_OFFICER' as UserRole,
      title: 'Regional Officer (SWRO)',
      name: 'Dr. K. S. Venkatesh',
      email: 'ro.swro@aicte-india.org',
      region: 'South-Western Region (Bengaluru)',
      scope: '42 Active Cases • Scrutiny & EVC',
      icon: Landmark,
      badge: 'Regional Authority',
      accent: 'border-blossom-300 bg-blossom-100/30',
    },
    {
      role: 'INSTITUTION_USER' as UserRole,
      title: 'Institution Principal (Applicant)',
      name: 'Dr. Ramesh Kumar (Principal)',
      email: 'principal@rvce.edu.in',
      region: 'R.V. College of Engg (PID: 1-109283741)',
      scope: 'Application Intake & Compliance',
      icon: Building2,
      badge: 'Technical Institution',
      accent: 'border-mint-700/30 bg-mint-100/30',
    },
    {
      role: 'BUREAU_OFFICER' as UserRole,
      title: 'Bureau Officer (HQ Approval Bureau)',
      name: 'Shri Anand Sharma',
      email: 'approval.bureau@aicte-india.org',
      region: 'AICTE Headquarters (New Delhi)',
      scope: 'Pan-India Bureau & Escalation L3',
      icon: Award,
      badge: 'Central Bureau',
      accent: 'border-amberState-700/30 bg-amberState-100/30',
    },
    {
      role: 'COMMITTEE_MEMBER' as UserRole,
      title: 'EVC Committee Expert Inspector',
      name: 'Prof. Meenakshi Sundaram',
      email: 'expert.visit@aicte-india.org',
      region: 'SWRO Inspection Panels',
      scope: 'On-Site / Virtual Report Verification',
      icon: UserCheck,
      badge: 'Empanelled Expert',
      accent: 'border-slate-300 bg-slate-50',
    },
    {
      role: 'AUDITOR' as UserRole,
      title: 'Statutory Compliance Auditor',
      name: 'Smt. Priya Balan',
      email: 'auditor.compliance@aicte-india.org',
      region: 'National Audit & Vigilance',
      scope: 'Read-Only Everywhere • Hash Ledger',
      icon: Scale,
      badge: 'Read-Only Auditor',
      accent: 'border-ink-line bg-white',
    },
    {
      role: 'SUPER_ADMIN' as UserRole,
      title: 'Member Secretary / Approving Authority',
      name: 'Prof. Rajive Kumar',
      email: 'member.secretary@aicte-india.org',
      region: 'AICTE Council (HQ)',
      scope: 'Final Council Approvals & Level 4',
      icon: ShieldCheck,
      badge: 'Council Authority',
      accent: 'border-blossom-600/40 bg-blossom-100/50',
    },
  ];

  const handlePersonaClick = (role: UserRole) => {
    loginAsPersona(role);
  };

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setLoading(true);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Authentication failed');
      }

      if (data.mfa_required) {
        setMfaUserData(data);
        setMfaStep(true);
      } else {
        // Direct Login
        const role = (data.role || 'REGIONAL_OFFICER') as UserRole;
        loginAsPersona(role);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Invalid credentials. Please verify your email and password.');
    } finally {
      setLoading(false);
    }
  };

  const handleMfaVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setLoading(true);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/auth/mfa-verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: mfaUserData?.email || email,
          mfa_code: mfaCode.trim(),
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Invalid MFA code');
      }

      const role = (data.role || mfaUserData?.role || 'REGIONAL_OFFICER') as UserRole;
      loginAsPersona(role);
    } catch (err: any) {
      setErrorMessage(err.message || 'MFA verification failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col justify-between p-4 sm:p-6 lg:p-8">
      {/* Top Header */}
      <div className="max-w-6xl mx-auto w-full flex items-center justify-between border-b border-ink-line pb-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-blossom-600 text-white flex items-center justify-center font-bold text-xl shadow-soft">
            <Landmark className="w-6 h-6" />
          </div>
          <div>
            <div className="text-[11px] font-bold tracking-wider uppercase text-blossom-700">
              अखिल भारतीय तकनीकी शिक्षा परिषद • भारत सरकार
            </div>
            <h1 className="text-base sm:text-lg font-bold text-ink-strong leading-tight">
              All India Council for Technical Education
            </h1>
            <p className="text-[11px] text-ink-muted">
              Integrated Approval Workflow Automation, Compliance Monitoring & Alert Management System
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={restartBootSequence}
            className="text-xs font-semibold px-2.5 py-1.5 rounded-lg bg-white hover:bg-blossom-100/50 text-ink-strong border border-ink-line shadow-xs flex items-center gap-1.5 transition-all"
            title="Replay system boot & diagnostic loading sequence"
          >
            <RotateCcw className="w-3.5 h-3.5 text-blossom-600" />
            <span className="hidden md:inline">Replay Boot Sequence</span>
          </button>
          <span className="hidden sm:inline-block bg-blossom-100 text-blossom-700 font-mono text-[10px] font-bold px-2.5 py-1 rounded border border-blossom-300">
            APH 2024–27 Aligned
          </span>
          <span className="hidden sm:inline-block bg-mint-100 text-mint-700 text-[10px] font-bold px-2.5 py-1 rounded border border-mint-700/30">
            Govt Cloud Ready
          </span>
        </div>
      </div>

      {/* Main Authentication Card */}
      <div className="max-w-4xl mx-auto w-full my-6">
        <div className="bg-white rounded-2xl border border-ink-line shadow-card overflow-hidden">
          {/* Card Top Banner */}
          <div className="bg-gradient-to-r from-blossom-100/60 via-white to-mint-100/40 p-6 border-b border-ink-line flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-blossom-600" />
                <h2 className="text-lg font-bold text-ink-strong">
                  Authorized Stakeholder Single Sign-On (SSO)
                </h2>
              </div>
              <p className="text-xs text-ink-muted mt-1">
                Access is restricted to authorized institutional representatives, regional officers, empanelled experts, and AICTE officials.
              </p>
            </div>

            {/* Tab Switcher */}
            <div className="flex p-1 bg-slate-100 rounded-xl border border-ink-line text-xs font-semibold">
              <button
                type="button"
                onClick={() => {
                  setActiveTab('credentials');
                  setMfaStep(false);
                }}
                className={`px-4 py-1.5 rounded-lg transition-all ${
                  activeTab === 'credentials'
                    ? 'bg-white text-ink-strong shadow-xs font-bold'
                    : 'text-ink-muted hover:text-ink'
                }`}
              >
                Standard Credentials
              </button>
              <button
                type="button"
                onClick={() => {
                  setActiveTab('personas');
                  setMfaStep(false);
                }}
                className={`px-4 py-1.5 rounded-lg transition-all ${
                  activeTab === 'personas'
                    ? 'bg-white text-ink-strong shadow-xs font-bold'
                    : 'text-ink-muted hover:text-ink'
                }`}
              >
                1-Click Demo Personas
              </button>
            </div>
          </div>

          {/* TAB 1: CREDENTIALS & TOTP MFA */}
          {activeTab === 'credentials' && (
            <div className="p-6 sm:p-8 max-w-md mx-auto">
              {!mfaStep ? (
                /* Step 1: Username & Password */
                <form onSubmit={handleCredentialsSubmit} className="space-y-4">
                  <div className="text-center space-y-1 pb-2">
                    <div className="w-10 h-10 rounded-full bg-blossom-100 text-blossom-600 flex items-center justify-center mx-auto mb-2">
                      <KeyRound className="w-5 h-5" />
                    </div>
                    <h3 className="text-sm font-bold text-ink-strong">
                      AICTE Official Login Portal
                    </h3>
                    <p className="text-xs text-ink-muted">
                      Enter your registered government email address and password.
                    </p>
                  </div>

                  {errorMessage && (
                    <div className="p-3 bg-roseState-100 border border-roseState-700/30 rounded-xl text-xs text-roseState-700 flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>{errorMessage}</span>
                    </div>
                  )}

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-ink-strong">Email Address</label>
                    <div className="relative">
                      <Mail className="w-4 h-4 text-ink-muted absolute left-3 top-1/2 -translate-y-1/2" />
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        className="w-full pl-9 pr-3 py-2 text-xs border border-ink-line rounded-xl focus:outline-none focus:border-blossom-600 focus:ring-1 focus:ring-blossom-600 bg-[#FAFAFA]"
                        placeholder="e.g. ro.swro@aicte-india.org"
                      />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-semibold text-ink-strong">Password</label>
                      <span className="text-[10px] text-ink-muted">Demo: DemoPassword@123</span>
                    </div>
                    <div className="relative">
                      <Lock className="w-4 h-4 text-ink-muted absolute left-3 top-1/2 -translate-y-1/2" />
                      <input
                        type={showPassword ? 'text' : 'password'}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        className="w-full pl-9 pr-9 py-2 text-xs border border-ink-line rounded-xl focus:outline-none focus:border-blossom-600 focus:ring-1 focus:ring-blossom-600 bg-[#FAFAFA]"
                        placeholder="••••••••••••"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-muted hover:text-ink"
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {/* Pre-fill Quick Buttons */}
                  <div className="pt-1">
                    <span className="text-[10px] font-semibold text-ink-muted">Quick fill credentials:</span>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      <button
                        type="button"
                        onClick={() => {
                          setEmail('ro.swro@aicte-india.org');
                          setPassword('DemoPassword@123');
                        }}
                        className="text-[10px] bg-slate-100 hover:bg-slate-200 text-ink px-2 py-0.5 rounded border border-ink-line"
                      >
                        SWRO Officer
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setEmail('principal.110000001@fictional-aicte.edu.in');
                          setPassword('DemoPassword@123');
                        }}
                        className="text-[10px] bg-slate-100 hover:bg-slate-200 text-ink px-2 py-0.5 rounded border border-ink-line"
                      >
                        Institution
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setEmail('member.secretary@aicte-india.org');
                          setPassword('DemoPassword@123');
                        }}
                        className="text-[10px] bg-slate-100 hover:bg-slate-200 text-ink px-2 py-0.5 rounded border border-ink-line"
                      >
                        Member Secretary
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="btn-primary w-full justify-center !py-2.5 mt-3 shadow-soft"
                  >
                    {loading ? 'Verifying Credentials...' : 'Sign In with Password →'}
                  </button>

                  <div className="pt-3 border-t border-ink-line text-center">
                    <button
                      type="button"
                      onClick={() => {
                        setActiveTab('personas');
                        setMfaStep(false);
                      }}
                      className="text-xs text-blossom-700 hover:text-blossom-800 font-semibold inline-flex items-center gap-1.5 transition-colors"
                    >
                      <Users className="w-3.5 h-3.5" />
                      <span>Or evaluate with 1-Click Demo Personas →</span>
                    </button>
                  </div>
                </form>
              ) : (
                /* Step 2: Interactive TOTP MFA Verification */
                <form onSubmit={handleMfaVerify} className="space-y-4 animate-scale-up">
                  <div className="text-center space-y-1 pb-2">
                    <div className="w-10 h-10 rounded-full bg-mint-100 text-mint-700 flex items-center justify-center mx-auto mb-2">
                      <ShieldCheck className="w-5 h-5" />
                    </div>
                    <h3 className="text-sm font-bold text-ink-strong">
                      Two-Factor Authentication (TOTP MFA)
                    </h3>
                    <p className="text-xs text-ink-muted">
                      A 6-digit authentication code has been generated for{' '}
                      <strong className="text-ink">{email}</strong>.
                    </p>
                  </div>

                  <div className="bg-amberState-100/60 p-3 rounded-xl border border-amberState-700/20 text-xs text-amberState-700 text-center">
                    <strong>Demo Evaluation Notice:</strong> Enter test code <code className="font-mono font-bold bg-white px-1.5 py-0.5 rounded border border-amberState-700/30">123456</code> to proceed.
                  </div>

                  {errorMessage && (
                    <div className="p-3 bg-roseState-100 border border-roseState-700/30 rounded-xl text-xs text-roseState-700 flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>{errorMessage}</span>
                    </div>
                  )}

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-ink-strong text-center block">
                      Enter 6-Digit TOTP Code
                    </label>
                    <input
                      type="text"
                      maxLength={6}
                      value={mfaCode}
                      onChange={(e) => setMfaCode(e.target.value)}
                      required
                      autoFocus
                      placeholder="123456"
                      className="w-full text-center font-mono text-xl tracking-[0.5em] py-2.5 border border-ink-line rounded-xl focus:outline-none focus:border-blossom-600 focus:ring-1 focus:ring-blossom-600 bg-[#FAFAFA]"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading || mfaCode.length < 6}
                    className="btn-primary w-full justify-center !py-2.5 shadow-soft"
                  >
                    {loading ? 'Verifying TOTP Code...' : 'Verify MFA & Enter Portal →'}
                  </button>

                  <div className="text-center pt-2">
                    <button
                      type="button"
                      onClick={() => setMfaStep(false)}
                      className="text-xs text-ink-muted hover:text-ink underline"
                    >
                      ← Back to Password Login
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* TAB 2: ONE-CLICK DEMO PERSONAS */}
          {activeTab === 'personas' && (
            <div className="p-6 sm:p-8 space-y-5">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-ink-strong uppercase tracking-wider">
                    Select a Stakeholder Persona for Evaluation
                  </h3>
                  <p className="text-xs text-ink-muted">
                    Click any role below to instantly authenticate with strict RBAC and regional row-level security scopes.
                  </p>
                </div>
                <span className="text-[10px] font-bold bg-blossom-100 text-blossom-700 px-2 py-0.5 rounded border border-blossom-300">
                  Statutory Simulation Mode
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {personas.map((p) => {
                  const Icon = p.icon;
                  return (
                    <button
                      key={p.role}
                      type="button"
                      onClick={() => handlePersonaClick(p.role)}
                      className={`text-left p-4 rounded-xl border transition-all hover:scale-[1.02] hover:shadow-soft flex flex-col justify-between ${p.accent}`}
                    >
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="w-8 h-8 rounded-lg bg-white border border-ink-line flex items-center justify-center text-blossom-600 shadow-xs">
                            <Icon className="w-4 h-4" />
                          </div>
                          <span className="text-[9px] font-bold uppercase tracking-wider bg-white/80 px-2 py-0.5 rounded border border-slate-200 text-ink-muted">
                            {p.badge}
                          </span>
                        </div>

                        <div>
                          <div className="text-xs font-bold text-ink-strong">
                            {p.title}
                          </div>
                          <div className="text-[11px] text-ink font-semibold mt-0.5">
                            {p.name}
                          </div>
                          <div className="text-[10px] text-ink-muted">
                            {p.region}
                          </div>
                        </div>
                      </div>

                      <div className="pt-3 mt-3 border-t border-slate-200/60 flex items-center justify-between text-[11px]">
                        <span className="text-[10px] text-ink-muted italic truncate max-w-[170px]">
                          {p.scope}
                        </span>
                        <div className="flex items-center gap-1 font-bold text-blossom-700 shrink-0">
                          <span>Enter</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>

              <div className="pt-3 border-t border-ink-line flex flex-wrap items-center justify-between gap-2 text-xs text-ink-muted">
                <span>Prefer official email and password authentication?</span>
                <button
                  type="button"
                  onClick={() => {
                    setActiveTab('credentials');
                    setMfaStep(false);
                  }}
                  className="font-semibold text-blossom-700 hover:text-blossom-800 inline-flex items-center gap-1 transition-colors"
                >
                  <KeyRound className="w-3.5 h-3.5" />
                  <span>Switch to Standard Credentials →</span>
                </button>
              </div>
            </div>
          )}

          {/* Footer Security Strip */}
          <div className="bg-[#FAFAFA] p-4 border-t border-ink-line flex flex-wrap items-center justify-between gap-3 text-[11px] text-ink-muted">
            <div className="flex items-center gap-4">
              <span>• 256-Bit TLS Encryption</span>
              <span>• Pairwise SoD Enforced</span>
              <span>• DPDP Act 2023 Aligned</span>
            </div>
            <div className="text-blossom-700 font-semibold">
              Statutory reserve: Automation supports, authorized humans decide.
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="max-w-6xl mx-auto w-full text-center text-xs text-ink-muted pt-2 border-t border-ink-line">
        © 2026 All India Council for Technical Education (AICTE), Ministry of Education, Government of India.
      </div>
    </div>
  );
};
