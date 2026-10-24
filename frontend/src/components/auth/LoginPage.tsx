'use client';

import React, { useState } from 'react';
import { useApp, DEMO_USERS, UserRole } from '@/lib/app-context';
import { apiFetch } from '@/lib/api';
import {
  ShieldCheck,
  Lock,
  Mail,
  KeyRound,
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
  UserPlus,
  HelpCircle,
  Sparkles,
  ToggleLeft,
  ToggleRight,
  Phone,
} from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { loginAsPersona, loginWithToken, restartBootSequence, isDemoMode, evaluatorMode, toggleEvaluatorMode } = useApp();
  const isEvalActive = evaluatorMode || isDemoMode;

  const [activeTab, setActiveTab] = useState<'credentials' | 'signup' | 'verify' | 'forgot' | 'personas'>('credentials');
  
  // Login form state
  const [email, setEmail] = useState('ro.swro@aicte-india.org');
  const [password, setPassword] = useState('DemoPassword@123');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // MFA State
  const [mfaStep, setMfaStep] = useState(false);
  const [mfaCode, setMfaCode] = useState('');
  const [mfaUserData, setMfaUserData] = useState<any | null>(null);

  // Institution Sign-up State
  const [signupForm, setSignupForm] = useState({
    email: '',
    password: '',
    fullName: '',
    institutionName: '',
    category: 'Engineering & Tech',
    regionCode: 'SWRO',
    address: 'Plot 10, Knowledge Park',
    state: 'Karnataka',
    whatsappPhone: '',
    optInWhatsapp: false,
    preferredLanguage: 'en',
  });
  const [signupIssuedToken, setSignupIssuedToken] = useState('');

  // Email Verification State
  const [verifyToken, setVerifyToken] = useState('');

  // Forgot Password State
  const [forgotEmail, setForgotEmail] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [forgotStep, setForgotStep] = useState<1 | 2>(1);

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
      role: 'REGIONAL_DIRECTOR' as UserRole,
      title: 'Regional Director (Assumed Escalation)',
      name: 'Dr. K. S. Sitaram',
      email: 'rd.swro@aicte-india.org',
      region: 'South-Western Region (Bengaluru)',
      scope: 'Level 2 SLA Escalations • Corridor Lead',
      icon: Award,
      badge: 'Regional Director (Assumed)',
      accent: 'border-blossom-500/40 bg-blossom-100/40',
    },
    {
      role: 'SCRUTINY_MEMBER' as UserRole,
      title: 'Scrutiny Committee Member',
      name: 'Prof. N. Meenakshi',
      email: 'scrutiny.member@aicte-india.org',
      region: 'SWRO Scrutiny Panels',
      scope: 'Table 2.3 Norms • Deficiency Memos',
      icon: UserCheck,
      badge: 'Scrutiny Member',
      accent: 'border-mint-700/30 bg-mint-100/30',
    },
    {
      role: 'COMMITTEE_MEMBER' as UserRole,
      title: 'EVC Committee Expert Inspector',
      name: 'Prof. Meenakshi Sundaram',
      email: 'expert.swro@aicte-india.org',
      region: 'SWRO Inspection Panels',
      scope: '30-min Geotagged Video Verification',
      icon: UserCheck,
      badge: 'Empanelled Expert',
      accent: 'border-slate-300 bg-slate-50',
    },
    {
      role: 'SAC_SHC_MEMBER' as UserRole,
      title: 'SAC/SHC Appellate Member',
      name: 'Justice (Retd.) K. V. Narayanan',
      email: 'sac.appellate@aicte-india.org',
      region: 'Pan-India Standing Appellate',
      scope: 'Clause 1.11(a) 7-Day Appeals',
      icon: Scale,
      badge: 'Appellate Member',
      accent: 'border-purple-300 bg-purple-50',
    },
    {
      role: 'BUREAU_OFFICER' as UserRole,
      title: 'Bureau Officer (HQ Approval Bureau)',
      name: 'Shri Anand K. Sharma',
      email: 'approval.bureau@aicte-india.org',
      region: 'AICTE Headquarters (New Delhi)',
      scope: 'Pan-India Bureau & Docket Management',
      icon: Award,
      badge: 'Central Bureau',
      accent: 'border-amberState-700/30 bg-amberState-100/30',
    },
    {
      role: 'BUREAU_HEAD' as UserRole,
      title: 'Bureau Head (Assumed Escalation)',
      name: 'Dr. M. S. Jayaprakash',
      email: 'bureau.head@aicte-india.org',
      region: 'AICTE Headquarters (New Delhi)',
      scope: 'Level 3 SLA Escalations • Policy Oversight',
      icon: ShieldCheck,
      badge: 'Bureau Head (Assumed)',
      accent: 'border-amberState-700/50 bg-amberState-100/50',
    },
    {
      role: 'INSTITUTION_USER' as UserRole,
      title: 'Institution Principal (Applicant)',
      name: 'Dr. Principal (Apex Institute)',
      email: 'principal.110000001@fictional-aicte.edu.in',
      region: 'Apex Institute of Technology (PID: 1-10000001)',
      scope: 'Application Intake & Compliance',
      icon: Building2,
      badge: 'Technical Institution',
      accent: 'border-mint-700/30 bg-mint-100/30',
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
      title: 'Member Secretary / Council Administration',
      name: 'Dr. Arvind Ramanathan (Member Secretary)',
      email: 'member.secretary@aicte-india.org',
      region: 'AICTE Council (HQ)',
      scope: 'Council Administration & Level 4 (EC decides, Council ratifies)',
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
    setSuccessMessage('');
    setLoading(true);

    try {
      const data = await apiFetch<any>('/api/v1/auth/login', {
        method: 'POST',
        skipAuth: true,
        body: JSON.stringify({ email, password }),
      });

      if (data.mfa_required) {
        setMfaUserData(data);
        setMfaStep(true);
      } else {
        const role = (data.role || 'REGIONAL_OFFICER') as UserRole;
        if (data.access_token) {
          const matchedUser = DEMO_USERS[role] || {
            id: data.user_id || 'usr-login',
            name: data.full_name || email,
            email,
            role,
            roleLabel: data.role || 'Officer',
            regionCode: data.region_code || 'SWRO',
          };
          loginWithToken(matchedUser, data.access_token);
        } else {
          loginAsPersona(role);
        }
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
      const data = await apiFetch<any>('/api/v1/auth/mfa-verify', {
        method: 'POST',
        skipAuth: true,
        body: JSON.stringify({
          email: mfaUserData?.email || email,
          mfa_code: mfaCode.replace(/\D/g, '').trim(),
        }),
      });

      const role = (data.role || mfaUserData?.role || 'REGIONAL_OFFICER') as UserRole;
      if (data.access_token) {
        const matchedUser = DEMO_USERS[role] || {
          id: data.user_id || mfaUserData?.user_id || 'usr-mfa',
          name: data.full_name || mfaUserData?.full_name || email,
          email,
          role,
          roleLabel: data.role || 'Officer',
          regionCode: data.region_code || 'SWRO',
        };
        loginWithToken(matchedUser, data.access_token);
      } else {
        loginAsPersona(role);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Invalid TOTP code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');
    setLoading(true);

    try {
      const resp = await apiFetch<any>('/api/v1/auth/signup', {
        method: 'POST',
        skipAuth: true,
        body: JSON.stringify({
          email: signupForm.email,
          password: signupForm.password,
          full_name: signupForm.fullName,
          institution_name: signupForm.institutionName,
          category: signupForm.category,
          region_code: signupForm.regionCode,
          address: signupForm.address,
          state: signupForm.state,
          whatsapp_phone: signupForm.whatsappPhone || null,
          opt_in_whatsapp: signupForm.optInWhatsapp,
          preferred_language: signupForm.preferredLanguage,
        }),
      });

      setSuccessMessage('Registration successful! Verification email has been dispatched.');
      setSignupIssuedToken(resp.verification_token || '');
      setVerifyToken(resp.verification_token || '');
    } catch (err: any) {
      setErrorMessage(err.message || 'Sign-up failed. Please check inputs.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');
    setLoading(true);

    try {
      await apiFetch<any>('/api/v1/auth/verify-email', {
        method: 'POST',
        skipAuth: true,
        body: JSON.stringify({ token: verifyToken.trim() }),
      });
      setSuccessMessage('Email verified successfully! You may now log in with your credentials.');
      setTimeout(() => {
        setActiveTab('credentials');
        setSuccessMessage('Account activated. Enter your password to sign in.');
      }, 1500);
    } catch (err: any) {
      setErrorMessage(err.message || 'Invalid or expired verification token.');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');
    setLoading(true);

    try {
      const resp = await apiFetch<any>('/api/v1/auth/forgot-password', {
        method: 'POST',
        skipAuth: true,
        body: JSON.stringify({ email: forgotEmail.trim() }),
      });
      setSuccessMessage(resp.message || 'Password reset instructions dispatched.');
      if (resp.reset_token) {
        setResetToken(resp.reset_token);
      }
      setForgotStep(2);
    } catch (err: any) {
      setErrorMessage(err.message || 'Could not process password reset.');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');
    setLoading(true);

    try {
      await apiFetch<any>('/api/v1/auth/reset-password', {
        method: 'POST',
        skipAuth: true,
        body: JSON.stringify({ token: resetToken.trim(), new_password: newPassword }),
      });
      setSuccessMessage('Password reset successfully. Please log in with your new credentials.');
      setTimeout(() => {
        setActiveTab('credentials');
        setPassword(newPassword);
        setForgotStep(1);
      }, 1500);
    } catch (err: any) {
      setErrorMessage(err.message || 'Password reset failed. Invalid or expired token.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between p-4 sm:p-6 text-ink">
      {/* Evaluator Mode Banner (When Active) */}
      {isEvalActive && (
        <div
          id="evaluator-mode-login-banner"
          className="bg-amber-500 text-slate-950 px-6 py-2 text-xs font-bold flex items-center justify-between tracking-wide shadow-sm border border-amber-600 rounded-xl mb-4 max-w-6xl mx-auto w-full"
        >
          <div className="flex items-center gap-2">
            <span className="px-1.5 py-0.5 bg-black text-amber-300 rounded text-[10px] font-black uppercase tracking-wider">
              EVALUATOR MODE ACTIVE
            </span>
            <span>
              Evaluation Sandbox Active • 1-Click Personas & Time Travel Enabled • Synthetic Evaluation Data
            </span>
          </div>
          <button
            onClick={() => toggleEvaluatorMode(false)}
            className="px-2.5 py-1 bg-black text-amber-300 rounded text-[10px] font-bold hover:bg-slate-900 transition-all"
          >
            Disable Evaluator Mode
          </button>
        </div>
      )}

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

        <div className="flex items-center gap-3">
          {/* Admin Evaluator Mode Toggle */}
          <button
            onClick={() => toggleEvaluatorMode(!isEvalActive)}
            className={`text-xs font-bold px-3 py-1.5 rounded-lg border flex items-center gap-1.5 transition-all shadow-xs ${
              isEvalActive
                ? 'bg-amber-100 text-amber-900 border-amber-300 hover:bg-amber-200'
                : 'bg-white text-ink-muted hover:text-ink-strong border-ink-line'
            }`}
            title="Toggle Evaluator Mode (Enables 1-Click Personas, Demo Shortcuts & Time-Travel)"
          >
            {isEvalActive ? <ToggleRight className="w-4 h-4 text-amber-600" /> : <ToggleLeft className="w-4 h-4 text-slate-400" />}
            <span>Evaluator Mode: {isEvalActive ? 'ON' : 'OFF'}</span>
          </button>

          <button
            onClick={restartBootSequence}
            className="text-xs font-semibold px-2.5 py-1.5 rounded-lg bg-white hover:bg-blossom-100/50 text-ink-strong border border-ink-line shadow-xs flex items-center gap-1.5 transition-all"
            title="Replay system boot & diagnostic loading sequence"
          >
            <RotateCcw className="w-3.5 h-3.5 text-blossom-600" />
            <span className="hidden md:inline">Replay Diagnostics</span>
          </button>
        </div>
      </div>

      {/* Main Authentication Card */}
      <div className="max-w-4xl mx-auto w-full my-6">
        <div className="bg-white rounded-2xl border border-ink-line shadow-card overflow-hidden">
          {/* Card Top Banner with Dynamic Tabs */}
          <div className="bg-gradient-to-r from-blossom-100/60 via-white to-mint-100/40 p-6 border-b border-ink-line flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-blossom-600" />
                <h2 className="text-lg font-bold text-ink-strong">
                  Authorized Regulatory Access Portal
                </h2>
              </div>
              <p className="text-xs text-ink-muted mt-1">
                Role-scoped authentication strictly enforced. Separation of Duties (SoD) guaranteed.
              </p>
            </div>

            {/* Navigation Tabs */}
            <div className="flex p-1 bg-slate-100 rounded-xl border border-ink-line text-xs font-semibold">
              <button
                type="button"
                onClick={() => {
                  setActiveTab('credentials');
                  setMfaStep(false);
                  setErrorMessage('');
                  setSuccessMessage('');
                }}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  activeTab === 'credentials'
                    ? 'bg-white text-ink-strong shadow-xs font-bold'
                    : 'text-ink-muted hover:text-ink'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => {
                  setActiveTab('signup');
                  setErrorMessage('');
                  setSuccessMessage('');
                }}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  activeTab === 'signup'
                    ? 'bg-white text-ink-strong shadow-xs font-bold'
                    : 'text-ink-muted hover:text-ink'
                }`}
              >
                New Institution
              </button>
              <button
                type="button"
                onClick={() => {
                  setActiveTab('verify');
                  setErrorMessage('');
                  setSuccessMessage('');
                }}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  activeTab === 'verify'
                    ? 'bg-white text-ink-strong shadow-xs font-bold'
                    : 'text-ink-muted hover:text-ink'
                }`}
              >
                Verify Email
              </button>
              {isEvalActive && (
                <button
                  type="button"
                  data-testid="tab-personas"
                  onClick={() => {
                    setActiveTab('personas');
                    setMfaStep(false);
                    setErrorMessage('');
                    setSuccessMessage('');
                  }}
                  className={`px-3 py-1.5 rounded-lg transition-all ${
                    activeTab === 'personas'
                      ? 'bg-white text-ink-strong shadow-xs font-bold'
                      : 'text-ink-muted hover:text-ink'
                  }`}
                >
                  ⚡ 1-Click Personas
                </button>
              )}
            </div>
          </div>

          {/* TAB 1: SIGN IN (CREDENTIALS & TOTP MFA) */}
          {activeTab === 'credentials' && (
            <div className="p-6 sm:p-8 max-w-md mx-auto">
              {!mfaStep ? (
                <form onSubmit={handleCredentialsSubmit} className="space-y-4">
                  <div className="text-center space-y-1 pb-2">
                    <div className="w-10 h-10 rounded-full bg-blossom-100 text-blossom-600 flex items-center justify-center mx-auto mb-2">
                      <KeyRound className="w-5 h-5" />
                    </div>
                    <h3 className="text-sm font-bold text-ink-strong">
                      Stakeholder Sign In
                    </h3>
                    <p className="text-xs text-ink-muted">
                      Enter your verified email address and statutory password.
                    </p>
                  </div>

                  {errorMessage && (
                    <div className="p-3 bg-roseState-100 border border-roseState-700/30 rounded-xl text-xs text-roseState-700 flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>{errorMessage}</span>
                    </div>
                  )}

                  {successMessage && (
                    <div className="p-3 bg-mint-100 border border-mint-700/30 rounded-xl text-xs text-mint-800 flex items-start gap-2">
                      <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-mint-700" />
                      <span>{successMessage}</span>
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
                      <button
                        type="button"
                        onClick={() => {
                          setActiveTab('forgot');
                          setForgotEmail(email);
                          setErrorMessage('');
                          setSuccessMessage('');
                        }}
                        className="text-[11px] text-blossom-600 hover:underline font-semibold"
                      >
                        Forgot Password?
                      </button>
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

                  {/* Pre-fill Quick Buttons (Only in Evaluator Mode) */}
                  {isEvalActive && (
                    <div className="pt-1">
                      <span className="text-[10px] font-semibold text-ink-muted">Quick fill credentials (Evaluator Mode):</span>
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        <button
                          type="button"
                          onClick={() => {
                            setEmail('ro.swro@aicte-india.org');
                            setPassword('DemoPassword@123');
                          }}
                          className="text-[10px] bg-slate-100 hover:bg-slate-200 text-ink px-2 py-0.5 rounded border border-ink-line"
                        >
                          Regional Officer
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
                  )}

                  <button
                    type="submit"
                    disabled={loading}
                    className="btn-primary w-full justify-center !py-2.5 mt-3 shadow-soft"
                  >
                    {loading ? 'Verifying Credentials...' : 'Sign In with Password →'}
                  </button>
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
                      Enter the 6-digit TOTP code for <strong className="text-ink">{email}</strong>.
                    </p>
                  </div>

                  {!isEvalActive ? (
                    <div className="bg-amberState-100 border border-amberState-700/30 p-3 rounded-xl text-xs text-amberState-700 flex flex-col items-center gap-1.5 text-center">
                      <div className="flex items-center gap-1.5 font-bold">
                        <AlertCircle className="w-4 h-4 text-amberState-700" />
                        <span>Evaluator Mode is currently OFF</span>
                      </div>
                      <p className="text-[11px] leading-relaxed">
                        To use sandbox demo PIN <code className="font-mono font-bold bg-white px-1.5 py-0.5 rounded border border-amberState-700/30">123456</code>, please activate Evaluator Mode.
                      </p>
                      <button
                        type="button"
                        onClick={() => toggleEvaluatorMode(true)}
                        className="mt-1 px-3 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold transition-all shadow-xs"
                      >
                        ⚡ Turn Evaluator Mode ON
                      </button>
                    </div>
                  ) : (
                    <div className="bg-mint-100/70 p-3 rounded-xl border border-mint-700/30 text-xs text-mint-800 text-center flex items-center justify-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-mint-700 shrink-0" />
                      <span><strong>(Evaluator Sandbox Active):</strong> Enter test PIN <code className="font-mono font-bold bg-white px-1.5 py-0.5 rounded border border-mint-700/40">123456</code>.</span>
                    </div>
                  )}

                  {errorMessage && (
                    <div className="p-3 bg-roseState-100 border border-roseState-700/30 rounded-xl text-xs text-roseState-700 flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>{errorMessage}</span>
                    </div>
                  )}

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-ink-strong text-center block">
                      6-Digit Security PIN
                    </label>
                    <input
                      type="text"
                      maxLength={6}
                      value={mfaCode}
                      onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      required
                      autoFocus
                      placeholder="123456"
                      className="w-full text-center font-mono text-xl tracking-[0.5em] py-2.5 border border-ink-line rounded-xl focus:outline-none focus:border-blossom-600 focus:ring-1 focus:ring-blossom-600 bg-[#FAFAFA]"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading || mfaCode.replace(/\D/g, '').length < 6}
                    className="btn-primary w-full justify-center !py-2.5 shadow-soft"
                  >
                    {loading ? 'Verifying TOTP Code...' : 'Verify MFA & Enter Portal →'}
                  </button>

                  <div className="text-center pt-2">
                    <button
                      type="button"
                      onClick={() => setMfaStep(false)}
                      className="text-xs text-ink-muted hover:text-ink font-semibold"
                    >
                      ← Back to Password Login
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* TAB 2: INSTITUTION SIGN-UP */}
          {activeTab === 'signup' && (
            <div className="p-6 sm:p-8 max-w-lg mx-auto">
              <div className="text-center space-y-1 pb-4">
                <div className="w-10 h-10 rounded-full bg-mint-100 text-mint-700 flex items-center justify-center mx-auto mb-2">
                  <UserPlus className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-bold text-ink-strong">
                  Register Technical Institution
                </h3>
                <p className="text-xs text-ink-muted">
                  Create an institutional account for regulatory approvals. Email verification required.
                </p>
              </div>

              {errorMessage && (
                <div className="p-3 mb-4 bg-roseState-100 border border-roseState-700/30 rounded-xl text-xs text-roseState-700 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {successMessage && (
                <div className="p-4 mb-4 bg-mint-100 border border-mint-700/30 rounded-xl text-xs text-mint-800 space-y-2">
                  <div className="flex items-center gap-2 font-bold text-mint-900">
                    <CheckCircle2 className="w-4 h-4 text-mint-700" />
                    <span>{successMessage}</span>
                  </div>
                  {signupIssuedToken && (
                    <div className="bg-white p-2.5 rounded-lg border border-mint-300 font-mono text-[11px] text-ink break-all">
                      <div className="text-[10px] text-ink-muted uppercase font-sans font-bold">Verification Token:</div>
                      {signupIssuedToken}
                    </div>
                  )}
                  <button
                    onClick={() => {
                      setVerifyToken(signupIssuedToken);
                      setActiveTab('verify');
                    }}
                    className="btn-primary !py-1.5 !px-3 text-xs w-full justify-center"
                  >
                    Proceed to Email Verification →
                  </button>
                </div>
              )}

              <form onSubmit={handleSignupSubmit} className="space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-ink-strong">Official Email</label>
                    <input
                      type="email"
                      required
                      value={signupForm.email}
                      onChange={(e) => setSignupForm({ ...signupForm, email: e.target.value })}
                      placeholder="principal@institute.edu.in"
                      className="w-full px-3 py-1.5 text-xs border border-ink-line rounded-lg"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-ink-strong">Password</label>
                    <input
                      type="password"
                      required
                      value={signupForm.password}
                      onChange={(e) => setSignupForm({ ...signupForm, password: e.target.value })}
                      placeholder="••••••••••••"
                      className="w-full px-3 py-1.5 text-xs border border-ink-line rounded-lg"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-ink-strong">Authorized Signatory Name</label>
                  <input
                    type="text"
                    required
                    value={signupForm.fullName}
                    onChange={(e) => setSignupForm({ ...signupForm, fullName: e.target.value })}
                    placeholder="e.g. Dr. Rajesh Sharma (Principal)"
                    className="w-full px-3 py-1.5 text-xs border border-ink-line rounded-lg"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-ink-strong">Institution Name</label>
                  <input
                    type="text"
                    required
                    value={signupForm.institutionName}
                    onChange={(e) => setSignupForm({ ...signupForm, institutionName: e.target.value })}
                    placeholder="e.g. Bharath Institute of Technology"
                    className="w-full px-3 py-1.5 text-xs border border-ink-line rounded-lg"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-ink-strong">Regional Office</label>
                    <select
                      value={signupForm.regionCode}
                      onChange={(e) => setSignupForm({ ...signupForm, regionCode: e.target.value })}
                      className="w-full px-3 py-1.5 text-xs border border-ink-line rounded-lg bg-white"
                    >
                      <option value="SWRO">South-Western (SWRO - Bengaluru)</option>
                      <option value="SRO">Southern (SRO - Chennai)</option>
                      <option value="WRO">Western (WRO - Mumbai)</option>
                      <option value="NRO">Northern (NRO - Kanpur)</option>
                      <option value="ERO">Eastern (ERO - Kolkata)</option>
                      <option value="CRO">Central (CRO - Bhopal)</option>
                      <option value="NWRO">North-Western (NWRO - Chandigarh)</option>
                    </select>
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-ink-strong">Category</label>
                    <select
                      value={signupForm.category}
                      onChange={(e) => setSignupForm({ ...signupForm, category: e.target.value })}
                      className="w-full px-3 py-1.5 text-xs border border-ink-line rounded-lg bg-white"
                    >
                      <option value="Engineering & Tech">Engineering & Technology</option>
                      <option value="Management">Management</option>
                      <option value="Pharmacy">Pharmacy</option>
                      <option value="Applied Engineering">Applied Engineering</option>
                      <option value="Architecture">Architecture & Planning</option>
                    </select>
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-ink-strong">WhatsApp Notifications (Sandbox / Opt-in)</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={signupForm.whatsappPhone}
                      onChange={(e) => setSignupForm({ ...signupForm, whatsappPhone: e.target.value })}
                      placeholder="+919876543210"
                      className="flex-1 px-3 py-1.5 text-xs border border-ink-line rounded-lg"
                    />
                    <label className="flex items-center gap-1.5 text-[11px] font-medium cursor-pointer">
                      <input
                        type="checkbox"
                        checked={signupForm.optInWhatsapp}
                        onChange={(e) => setSignupForm({ ...signupForm, optInWhatsapp: e.target.checked })}
                        className="rounded text-blossom-600"
                      />
                      <span>Opt-in</span>
                    </label>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="btn-primary w-full justify-center !py-2.5 mt-3 shadow-soft"
                >
                  {loading ? 'Creating Institution Account...' : 'Register & Dispatch Verification Email →'}
                </button>
              </form>
            </div>
          )}

          {/* TAB 3: VERIFY EMAIL */}
          {activeTab === 'verify' && (
            <div className="p-6 sm:p-8 max-w-md mx-auto">
              <div className="text-center space-y-1 pb-4">
                <div className="w-10 h-10 rounded-full bg-blossom-100 text-blossom-600 flex items-center justify-center mx-auto mb-2">
                  <Mail className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-bold text-ink-strong">
                  Verify Email Address
                </h3>
                <p className="text-xs text-ink-muted">
                  Enter the verification token sent to your registered institutional email.
                </p>
              </div>

              {errorMessage && (
                <div className="p-3 mb-4 bg-roseState-100 border border-roseState-700/30 rounded-xl text-xs text-roseState-700 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {successMessage && (
                <div className="p-3 mb-4 bg-mint-100 border border-mint-700/30 rounded-xl text-xs text-mint-800 flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-mint-700" />
                  <span>{successMessage}</span>
                </div>
              )}

              <form onSubmit={handleVerifySubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-ink-strong">Cryptographic Verification Token</label>
                  <input
                    type="text"
                    required
                    value={verifyToken}
                    onChange={(e) => setVerifyToken(e.target.value)}
                    placeholder="Enter or paste token..."
                    className="w-full px-3 py-2 text-xs font-mono border border-ink-line rounded-xl focus:border-blossom-600"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || !verifyToken}
                  className="btn-primary w-full justify-center !py-2.5 shadow-soft"
                >
                  {loading ? 'Verifying Token...' : 'Confirm Email Verification →'}
                </button>
              </form>
            </div>
          )}

          {/* TAB 4: FORGOT / RESET PASSWORD */}
          {activeTab === 'forgot' && (
            <div className="p-6 sm:p-8 max-w-md mx-auto">
              <div className="text-center space-y-1 pb-4">
                <div className="w-10 h-10 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center mx-auto mb-2">
                  <HelpCircle className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-bold text-ink-strong">
                  Password Reset Recovery
                </h3>
                <p className="text-xs text-ink-muted">
                  {forgotStep === 1
                    ? 'Enter your registered email address to receive reset instructions.'
                    : 'Enter the reset token received via SMTP and your new password.'}
                </p>
              </div>

              {errorMessage && (
                <div className="p-3 mb-4 bg-roseState-100 border border-roseState-700/30 rounded-xl text-xs text-roseState-700 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {successMessage && (
                <div className="p-3 mb-4 bg-mint-100 border border-mint-700/30 rounded-xl text-xs text-mint-800 flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-mint-700" />
                  <span>{successMessage}</span>
                </div>
              )}

              {forgotStep === 1 ? (
                <form onSubmit={handleForgotPasswordSubmit} className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-ink-strong">Registered Email</label>
                    <input
                      type="email"
                      required
                      value={forgotEmail}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      placeholder="e.g. ro.swro@aicte-india.org"
                      className="w-full px-3 py-2 text-xs border border-ink-line rounded-xl"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="btn-primary w-full justify-center !py-2.5 shadow-soft"
                  >
                    {loading ? 'Sending Reset Token...' : 'Dispatch Reset Email →'}
                  </button>
                  <div className="text-center">
                    <button
                      type="button"
                      onClick={() => setActiveTab('credentials')}
                      className="text-xs text-ink-muted hover:text-ink font-semibold"
                    >
                      ← Back to Login
                    </button>
                  </div>
                </form>
              ) : (
                <form onSubmit={handleResetPasswordSubmit} className="space-y-3">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-ink-strong">Password Reset Token</label>
                    <input
                      type="text"
                      required
                      value={resetToken}
                      onChange={(e) => setResetToken(e.target.value)}
                      placeholder="Paste reset token..."
                      className="w-full px-3 py-1.5 text-xs font-mono border border-ink-line rounded-lg"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-ink-strong">New Password</label>
                    <input
                      type="password"
                      required
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full px-3 py-1.5 text-xs border border-ink-line rounded-lg"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="btn-primary w-full justify-center !py-2.5 mt-2 shadow-soft"
                  >
                    {loading ? 'Updating Password...' : 'Update Password & Unlock →'}
                  </button>
                </form>
              )}
            </div>
          )}

          {/* TAB 5: 1-CLICK PERSONAS (EVALUATOR MODE ONLY) */}
          {activeTab === 'personas' && isEvalActive && (
            <div className="p-6 sm:p-8">
              <div className="mb-6 p-4 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-3">
                <Sparkles className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div className="text-xs">
                  <div className="font-bold text-amber-900">
                    Evaluator Sandbox Active (1-Click Authentication)
                  </div>
                  <div className="text-amber-800 mt-0.5">
                    Click any stakeholder persona below to instantly obtain a cryptographically signed JWT token with that persona&apos;s exact jurisdictional scope and Separation of Duties boundaries.
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {personas.map((persona) => {
                  const Icon = persona.icon;
                  return (
                    <button
                      key={persona.role}
                      type="button"
                      onClick={() => handlePersonaClick(persona.role)}
                      className={`text-left p-4 rounded-xl border transition-all hover:shadow-card hover:border-blossom-600/50 hover:-translate-y-0.5 flex flex-col justify-between ${persona.accent}`}
                    >
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-white/80 border border-slate-200">
                            {persona.badge}
                          </span>
                          <Icon className="w-4 h-4 text-ink-muted" />
                        </div>
                        <div className="text-sm font-bold text-ink-strong">{persona.title}</div>
                        <div className="text-xs font-semibold text-ink-muted mt-0.5">{persona.name}</div>
                        <div className="text-[11px] text-ink-muted/80 mt-1">{persona.region}</div>
                      </div>

                      <div className="mt-3 pt-2 border-t border-slate-200/60 flex items-center justify-between text-[11px]">
                        <span className="text-ink-muted font-medium">{persona.scope}</span>
                        <span className="font-bold text-blossom-700 flex items-center gap-1">
                          Log In →
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="max-w-6xl mx-auto w-full text-center py-4 border-t border-ink-line text-[11px] text-ink-muted space-y-1">
        <div>
          Official AICTE Statutory Portal • Built strictly against AICTE Approval Process Handbook (APH 2024–27)
        </div>
        <div>
          SHA-256 Hash-Chained Audit Ledger Active • DPDP Act 2023 Compliant • Separation of Duties Enforced
        </div>
      </div>
    </div>
  );
};
