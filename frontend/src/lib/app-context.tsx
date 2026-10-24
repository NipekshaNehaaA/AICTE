'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiFetch, API_BASE } from '@/lib/api';

export type UserRole =
  | 'INSTITUTION_USER'
  | 'REGIONAL_OFFICER'
  | 'REGIONAL_DIRECTOR'
  | 'BUREAU_OFFICER'
  | 'BUREAU_HEAD'
  | 'SCRUTINY_MEMBER'
  | 'COMMITTEE_MEMBER'
  | 'SAC_SHC_MEMBER'
  | 'SUPER_ADMIN'
  | 'AUDITOR';

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  roleLabel: string;
  regionCode: string;
  institutionName?: string;
  institutionId?: string;
  token?: string;
}

export interface RegionInfo {
  code: string;
  name: string;
  city: string;
  activeCasesCount: number;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  category: 'SLA_ALERT' | 'EVC_SCHEDULE' | 'UNDERTAKING_DUE' | 'LEASE_EXPIRY' | 'ESCALATION';
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  timestamp: string;
  read: boolean;
  applicationId?: string;
  escalationLevel?: string;
}

export const SAMPLE_REGIONS: RegionInfo[] = [
  { code: 'SWRO', name: 'South-Western Regional Office', city: 'Bengaluru', activeCasesCount: 42 },
  { code: 'SRO', name: 'Southern Regional Office', city: 'Chennai', activeCasesCount: 38 },
  { code: 'WRO', name: 'Western Regional Office', city: 'Mumbai', activeCasesCount: 54 },
  { code: 'NRO', name: 'Northern Regional Office', city: 'Kanpur', activeCasesCount: 35 },
  { code: 'ERO', name: 'Eastern Regional Office', city: 'Kolkata', activeCasesCount: 22 },
  { code: 'CRO', name: 'Central Regional Office', city: 'Bhopal', activeCasesCount: 19 },
  { code: 'NWRO', name: 'North-Western Regional Office', city: 'Chandigarh', activeCasesCount: 28 },
  { code: 'HQ', name: 'AICTE Headquarters', city: 'New Delhi', activeCasesCount: 238 },
];

export const DEMO_USERS: Record<UserRole, UserProfile> = {
  INSTITUTION_USER: {
    id: 'usr-inst-01',
    name: 'Dr. Ramesh Kumar (Principal)',
    email: 'principal@rvce.edu.in',
    role: 'INSTITUTION_USER',
    roleLabel: 'Institution Admin',
    regionCode: 'SWRO',
    institutionName: 'R.V. College of Engineering (PID: 1-109283741)',
    institutionId: 'inst-01',
  },
  REGIONAL_OFFICER: {
    id: 'usr-ro-01',
    name: 'Dr. K. S. Venkatesh',
    email: 'ro.swro@aicte-india.org',
    role: 'REGIONAL_OFFICER',
    roleLabel: 'Regional Officer (SWRO)',
    regionCode: 'SWRO',
  },
  REGIONAL_DIRECTOR: {
    id: 'usr-rd-01',
    name: 'Dr. K. S. Sitaram',
    email: 'rd.swro@aicte-india.org',
    role: 'REGIONAL_DIRECTOR',
    roleLabel: 'Regional Director (Assumed Escalation)',
    regionCode: 'SWRO',
  },
  BUREAU_OFFICER: {
    id: 'usr-bo-01',
    name: 'Shri Anand K. Sharma',
    email: 'approval.bureau@aicte-india.org',
    role: 'BUREAU_OFFICER',
    roleLabel: 'Bureau Officer (HQ)',
    regionCode: 'HQ',
  },
  BUREAU_HEAD: {
    id: 'usr-bh-01',
    name: 'Dr. M. S. Jayaprakash',
    email: 'bureau.head@aicte-india.org',
    role: 'BUREAU_HEAD',
    roleLabel: 'Bureau Head (Assumed Escalation)',
    regionCode: 'HQ',
  },
  SCRUTINY_MEMBER: {
    id: 'usr-sm-01',
    name: 'Prof. N. Meenakshi',
    email: 'scrutiny.member@aicte-india.org',
    role: 'SCRUTINY_MEMBER',
    roleLabel: 'Scrutiny Committee Member',
    regionCode: 'SWRO',
  },
  COMMITTEE_MEMBER: {
    id: 'usr-cm-01',
    name: 'Prof. Meenakshi Sundaram',
    email: 'expert.visit@aicte-india.org',
    role: 'COMMITTEE_MEMBER',
    roleLabel: 'EVC Committee Expert',
    regionCode: 'SWRO',
  },
  SAC_SHC_MEMBER: {
    id: 'usr-sac-01',
    name: 'Justice (Retd.) K. V. Narayanan',
    email: 'sac.appellate@aicte-india.org',
    role: 'SAC_SHC_MEMBER',
    roleLabel: 'SAC/SHC Appellate Member',
    regionCode: 'HQ',
  },
  SUPER_ADMIN: {
    id: 'usr-sa-01',
    name: 'Dr. Arvind Ramanathan (Member Secretary)',
    email: 'member.secretary@aicte-india.org',
    role: 'SUPER_ADMIN',
    roleLabel: 'Member Secretary / Council Administration',
    regionCode: 'HQ',
  },
  AUDITOR: {
    id: 'usr-aud-01',
    name: 'Smt. Priya Balan',
    email: 'auditor.compliance@aicte-india.org',
    role: 'AUDITOR',
    roleLabel: 'Statutory Compliance Auditor',
    regionCode: 'HQ',
  },
};

interface AppContextType {
  currentUser: UserProfile;
  switchRole: (role: UserRole) => void;
  currentRegion: RegionInfo;
  setRegionByCode: (code: string) => void;
  virtualDate: Date;
  virtualDaysOffset: number;
  advanceVirtualDays: (days: number) => void;
  resetVirtualTime: () => void;
  notifications: NotificationItem[];
  unreadNotificationsCount: number;
  markNotificationAsRead: (id: string) => void;
  markAllNotificationsAsRead: () => void;
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  activeNavTab: string;
  setActiveNavTab: (tab: string) => void;
  isAuthenticated: boolean;
  isSystemLoading: boolean;
  setIsSystemLoading: (loading: boolean) => void;
  restartBootSequence: () => void;
  loginAsPersona: (role: UserRole) => void;
  loginWithToken: (user: UserProfile, token: string) => void;
  logout: () => void;
  isDemoMode: boolean;
  setIsDemoMode: (val: boolean) => void;
  evaluatorMode: boolean;
  setEvaluatorMode: (val: boolean) => void;
  toggleEvaluatorMode: (enabled: boolean) => Promise<void>;
  selectedApplicationId: string | null;
  setSelectedApplicationId: (id: string | null) => void;
  openCaseDocket: (id: string) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isSystemLoading, setIsSystemLoading] = useState<boolean>(true);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);
  const [evaluatorMode, setEvaluatorMode] = useState<boolean>(false);
  const [currentUser, setCurrentUser] = useState<UserProfile>(DEMO_USERS.REGIONAL_OFFICER);
  const [currentRegion, setCurrentRegion] = useState<RegionInfo>(SAMPLE_REGIONS[0]); // Default: SWRO Bengaluru
  const [virtualDaysOffset, setVirtualDaysOffset] = useState<number>(0);
  const [baseDate] = useState<Date>(new Date('2026-10-22T09:00:00Z'));
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeNavTab, setActiveNavTab] = useState<string>('dashboard');
  const [selectedApplicationId, setSelectedApplicationId] = useState<string | null>(null);

  const openCaseDocket = (id: string) => {
    setSelectedApplicationId(id);
    setActiveNavTab('case');
  };

  useEffect(() => {
    apiFetch<any>('/api/v1/system/mode', { skipAuth: true })
      .then((data) => {
        if (data) {
          const mode = Boolean(data.evaluator_mode ?? data.demo_mode ?? false);
          setIsDemoMode(mode);
          setEvaluatorMode(mode);
        }
      })
      .catch((err) => {
        console.warn('Could not fetch system execution mode:', err);
      });
  }, []);

  const toggleEvaluatorMode = async (enabled: boolean) => {
    try {
      const data = await apiFetch<any>('/api/v1/system/evaluator-mode', {
        method: 'POST',
        skipAuth: true,
        body: JSON.stringify({ enabled }),
      });
      const active = Boolean(data.evaluator_mode ?? enabled);
      setIsDemoMode(active);
      setEvaluatorMode(active);
    } catch (err) {
      console.error('Failed to toggle Evaluator Mode:', err);
      setIsDemoMode(enabled);
      setEvaluatorMode(enabled);
    }
  };

  const restartBootSequence = () => {
    setIsAuthenticated(false);
    setIsSystemLoading(true);
  };

  const loginAsPersona = async (role: UserRole) => {
    const user = DEMO_USERS[role];
    if (user) {
      try {
        const data = await apiFetch<any>(`/api/v1/auth/demo-token/${role}`, {
          method: 'POST',
          skipAuth: true,
        });
        if (data && data.access_token) {
          const userWithToken = { ...user, token: data.access_token };
          setCurrentUser(userWithToken);
          if (typeof window !== 'undefined') {
            localStorage.setItem('aicte_auth_token', data.access_token);
          }
          const reg = SAMPLE_REGIONS.find((r) => r.code === user.regionCode) || SAMPLE_REGIONS[0];
          setCurrentRegion(reg);
          setIsAuthenticated(true);
          setActiveNavTab('dashboard');
          return;
        }
      } catch (e) {
        console.warn('Demo token endpoint unreachable, using local demo user', e);
      }
      setCurrentUser(user);
      const reg = SAMPLE_REGIONS.find((r) => r.code === user.regionCode) || SAMPLE_REGIONS[0];
      setCurrentRegion(reg);
      setIsAuthenticated(true);
      setActiveNavTab('dashboard');
    }
  };

  const loginWithToken = (user: UserProfile, token: string) => {
    const userWithToken = { ...user, token };
    setCurrentUser(userWithToken);
    if (typeof window !== 'undefined') {
      localStorage.setItem('aicte_auth_token', token);
    }
    const reg = SAMPLE_REGIONS.find((r) => r.code === user.regionCode) || SAMPLE_REGIONS[0];
    setCurrentRegion(reg);
    setIsAuthenticated(true);
    setActiveNavTab('dashboard');
  };

  const logout = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('aicte_auth_token');
    }
    setIsAuthenticated(false);
  };

  const [notifications, setNotifications] = useState<NotificationItem[]>([
    {
      id: 'notif-1',
      title: 'Approaching SLA: Scrutiny Stage',
      message: 'Application AICTE/2026-27/1-10928 has 2 days remaining before scrutiny deadline.',
      category: 'SLA_ALERT',
      severity: 'WARNING',
      timestamp: '2026-10-22 09:30 AM',
      read: false,
      applicationId: 'app-01',
    },
    {
      id: 'notif-2',
      title: 'EVC Visit Required',
      message: 'New Institution application for BMS Institute of Technology queued for EVC panel allocation.',
      category: 'EVC_SCHEDULE',
      severity: 'INFO',
      timestamp: '2026-10-21 04:15 PM',
      read: false,
      applicationId: 'app-03',
    },
    {
      id: 'notif-3',
      title: 'Lease Deed Expiry Warning (60-Day Offset)',
      message: 'Land lease deed for Oxford Engineering College expires in 58 days. Renewal required.',
      category: 'LEASE_EXPIRY',
      severity: 'WARNING',
      timestamp: '2026-10-20 11:00 AM',
      read: false,
    },
    {
      id: 'notif-4',
      title: 'Overdue Undertaking Escalation (Level 2)',
      message: 'Fire Safety Certificate compliance overdue by 5 days. Escalated to Regional Officer.',
      category: 'ESCALATION',
      severity: 'CRITICAL',
      timestamp: '2026-10-19 02:00 PM',
      read: true,
      escalationLevel: 'L2_REGIONAL_HEAD',
    },
  ]);

  const virtualDate = new Date(baseDate.getTime() + virtualDaysOffset * 24 * 60 * 60 * 1000);

  const switchRole = async (role: UserRole) => {
    try {
      const data = await apiFetch<any>(`/api/v1/auth/demo-token/${role}`, {
        method: 'POST',
        skipAuth: true,
      });
      if (data && data.access_token) {
        const updatedUser: UserProfile = {
          ...DEMO_USERS[role],
          token: data.access_token,
        };
        setCurrentUser(updatedUser);
        if (typeof window !== 'undefined') {
          localStorage.setItem('aicte_auth_token', data.access_token);
        }
        return;
      }
    } catch (e: any) {
      if (e?.status === 403) {
        console.warn('Role switching is disabled in production (DEMO_MODE=False).');
        return;
      }
      console.warn('Demo token endpoint unreachable, using local demo user', e);
    }
    setCurrentUser(DEMO_USERS[role]);
  };

  const setRegionByCode = (code: string) => {
    const found = SAMPLE_REGIONS.find((r) => r.code === code);
    if (found) {
      setCurrentRegion(found);
    }
  };

  const advanceVirtualDays = async (days: number) => {
    try {
      const data = await apiFetch<any>('/api/v1/demo/time-travel', {
        method: 'POST',
        body: JSON.stringify({ days_to_advance: days }),
      });
      // CRITICAL: Update displayed virtual date ONLY AFTER backend call succeeds!
      setVirtualDaysOffset((prev) => prev + days);

      // Add live escalation notification from backend response
      const newNotif: NotificationItem = {
        id: `notif-warp-${Date.now()}`,
        title: `Time-Travel Alert: +${days} Days Fast-Forwarded`,
        message: `System clock reached ${data.new_simulated_date}. Triggered ${data.eval_summary.escalations_triggered} live escalations (${data.eval_summary.overdue_cases} overdue cases).`,
        category: 'ESCALATION',
        severity: 'CRITICAL',
        timestamp: new Date().toLocaleTimeString(),
        read: false,
      };
      setNotifications((curr) => [newNotif, ...curr]);
    } catch (e: any) {
      console.error('Time travel API call error', e);
      // DO NOT update virtual date on failure
    }
  };

  const resetVirtualTime = async () => {
    try {
      await apiFetch('/api/v1/demo/time-travel/reset', { method: 'POST' });
      // Update displayed date ONLY AFTER backend call succeeds!
      setVirtualDaysOffset(0);
    } catch (e: any) {
      console.error('Time travel reset error', e);
    }
  };

  const markNotificationAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  };

  const markAllNotificationsAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const unreadNotificationsCount = notifications.filter((n) => !n.read).length;

  return (
    <AppContext.Provider
      value={{
        currentUser,
        switchRole,
        currentRegion,
        setRegionByCode,
        virtualDate,
        virtualDaysOffset,
        advanceVirtualDays,
        resetVirtualTime,
        notifications,
        unreadNotificationsCount,
        markNotificationAsRead,
        markAllNotificationsAsRead,
        searchQuery,
        setSearchQuery,
        activeNavTab,
        setActiveNavTab,
        isAuthenticated,
        isSystemLoading,
        setIsSystemLoading,
        restartBootSequence,
        loginAsPersona,
        loginWithToken,
        logout,
        isDemoMode,
        setIsDemoMode,
        evaluatorMode,
        setEvaluatorMode,
        toggleEvaluatorMode,
        selectedApplicationId,
        setSelectedApplicationId,
        openCaseDocket,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
