'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiFetch, API_BASE, WorkspaceType, getActiveWorkspace, setActiveWorkspace } from '@/lib/api';

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
  institutionPid?: string;
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
    institutionName: 'Apex Institute of Technology',
    institutionPid: '1-10000001',
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

export const getDefaultTabForRole = (role: UserRole): string => {
  switch (role) {
    case 'INSTITUTION_USER':
      return 'dashboard';
    case 'REGIONAL_OFFICER':
    case 'REGIONAL_DIRECTOR':
    case 'SCRUTINY_MEMBER':
    case 'COMMITTEE_MEMBER':
    case 'SAC_SHC_MEMBER':
    case 'BUREAU_OFFICER':
      return 'applications';
    case 'AUDITOR':
      return 'audit';
    case 'SUPER_ADMIN':
    case 'BUREAU_HEAD':
    default:
      return 'dashboard';
  }
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
  fetchNotifications: () => Promise<void>;
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
  loginWithToken: (user: UserProfile, token: string, ws?: WorkspaceType) => void;
  logout: () => void;
  workspace: WorkspaceType;
  setWorkspace: (ws: WorkspaceType) => void;
  sandboxOverride: { override_email?: string | null; override_whatsapp?: string | null };
  updateSandboxOverride: (email?: string, whatsapp?: string) => Promise<void>;
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
  const [workspace, setWorkspaceState] = useState<WorkspaceType>('sandbox');
  const [isDemoMode, setIsDemoMode] = useState<boolean>(true);
  const [evaluatorMode, setEvaluatorMode] = useState<boolean>(true);
  const [currentUser, setCurrentUser] = useState<UserProfile>(DEMO_USERS.REGIONAL_OFFICER);
  const [currentRegion, setCurrentRegion] = useState<RegionInfo>(SAMPLE_REGIONS[0]); // Default: SWRO Bengaluru
  const [virtualDaysOffset, setVirtualDaysOffset] = useState<number>(0);
  const [baseDate] = useState<Date>(new Date('2026-10-22T09:00:00Z'));
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeNavTab, setActiveNavTab] = useState<string>('dashboard');
  const [selectedApplicationId, setSelectedApplicationId] = useState<string | null>(null);
  const [sandboxOverride, setSandboxOverride] = useState<{ override_email?: string | null; override_whatsapp?: string | null }>({
    override_email: null,
    override_whatsapp: null,
  });

  const openCaseDocket = (id: string) => {
    setSelectedApplicationId(id);
    setActiveNavTab('case');
  };

  const fetchSandboxOverride = async () => {
    try {
      const data = await apiFetch<any>('/api/v1/demo/sandbox-override', { skipAuth: true });
      if (data) {
        setSandboxOverride(data);
      }
    } catch {
      // Endpoint returns 404 in Live workspace or if backend offline
    }
  };

  const updateSandboxOverride = async (email?: string, whatsapp?: string) => {
    try {
      const data = await apiFetch<any>('/api/v1/demo/sandbox-override', {
        method: 'POST',
        body: JSON.stringify({ override_email: email, override_whatsapp: whatsapp }),
        skipAuth: true,
      });
      if (data?.overrides) {
        setSandboxOverride(data.overrides);
      }
    } catch (err) {
      console.error('Failed to update sandbox override recipient:', err);
    }
  };

  const setWorkspace = (newWs: WorkspaceType) => {
    setActiveWorkspace(newWs);
    setWorkspaceState(newWs);
    const isSandbox = newWs === 'sandbox';
    setIsDemoMode(isSandbox);
    setEvaluatorMode(isSandbox);

    if (typeof window !== 'undefined') {
      const savedToken = localStorage.getItem(`aicte_auth_token_${newWs}`);
      const savedUserStr = localStorage.getItem(`aicte_user_${newWs}`);
      if (savedToken && savedUserStr) {
        try {
          const userObj = JSON.parse(savedUserStr);
          setCurrentUser({ ...userObj, token: savedToken });
          setIsAuthenticated(true);
          return;
        } catch {
          // parse failed
        }
      }
      setIsAuthenticated(false);
    }

    if (isSandbox) {
      fetchSandboxOverride();
    }
  };

  useEffect(() => {
    const initialWs = getActiveWorkspace();
    setWorkspaceState(initialWs);
    const isSandbox = initialWs === 'sandbox';
    setIsDemoMode(isSandbox);
    setEvaluatorMode(isSandbox);

    if (typeof window !== 'undefined') {
      const savedToken = localStorage.getItem(`aicte_auth_token_${initialWs}`) || localStorage.getItem('aicte_auth_token');
      const savedUserStr = localStorage.getItem(`aicte_user_${initialWs}`) || localStorage.getItem('aicte_user');
      if (savedToken && savedUserStr) {
        try {
          const userObj = JSON.parse(savedUserStr);
          setCurrentUser({ ...userObj, token: savedToken });
          setIsAuthenticated(true);
        } catch {}
      }
    }

    if (isSandbox) {
      fetchSandboxOverride();
    }
  }, []);

  const toggleEvaluatorMode = async (enabled: boolean) => {
    setWorkspace(enabled ? 'sandbox' : 'live');
  };

  const restartBootSequence = () => {
    setIsAuthenticated(false);
    setIsSystemLoading(true);
  };

  const loginAsPersona = async (role: UserRole) => {
    if (workspace !== 'sandbox') {
      console.warn('One-click personas are strictly restricted to Sandbox workspace.');
      return;
    }
    const user = DEMO_USERS[role];
    const targetTab = getDefaultTabForRole(role);
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
            localStorage.setItem('aicte_auth_token_sandbox', data.access_token);
            localStorage.setItem('aicte_auth_token', data.access_token);
            localStorage.setItem('aicte_user_sandbox', JSON.stringify(userWithToken));
          }
          const reg = SAMPLE_REGIONS.find((r) => r.code === user.regionCode) || SAMPLE_REGIONS[0];
          setCurrentRegion(reg);
          setIsAuthenticated(true);
          setActiveNavTab(targetTab);
          return;
        }
      } catch (e) {
        console.warn('Demo token endpoint unreachable, using local demo user', e);
      }
      setCurrentUser(user);
      const reg = SAMPLE_REGIONS.find((r) => r.code === user.regionCode) || SAMPLE_REGIONS[0];
      setCurrentRegion(reg);
      setIsAuthenticated(true);
      setActiveNavTab(targetTab);
    }
  };

  const loginWithToken = (user: UserProfile, token: string, ws: WorkspaceType = workspace) => {
    const userWithToken = { ...user, token };
    const targetTab = getDefaultTabForRole(user.role);
    setCurrentUser(userWithToken);
    if (typeof window !== 'undefined') {
      localStorage.setItem(`aicte_auth_token_${ws}`, token);
      localStorage.setItem(`aicte_user_${ws}`, JSON.stringify(user));
      localStorage.setItem('aicte_auth_token', token);
      localStorage.setItem('aicte_user', JSON.stringify(user));
    }
    const reg = SAMPLE_REGIONS.find((r) => r.code === user.regionCode) || SAMPLE_REGIONS[0];
    setCurrentRegion(reg);
    setIsAuthenticated(true);
    setActiveNavTab(targetTab);
  };

  const logout = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(`aicte_auth_token_${workspace}`);
      localStorage.removeItem(`aicte_user_${workspace}`);
      localStorage.removeItem('aicte_auth_token');
      localStorage.removeItem('aicte_user');
    }
    setIsAuthenticated(false);
  };

  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  const fetchNotifications = async () => {
    try {
      const data = await apiFetch<any>('/api/v1/alerts/notifications');
      if (data && Array.isArray(data.notifications)) {
        const mapped: NotificationItem[] = data.notifications.map((n: any) => ({
          id: n.id,
          title: n.title,
          message: n.message,
          category: n.category || 'SLA_ALERT',
          severity: n.severity || 'INFO',
          timestamp: n.timestamp,
          read: Boolean(n.is_read),
          applicationId: n.application_id,
          escalationLevel: n.escalation_level,
        }));
        setNotifications(mapped);
      }
    } catch {
      // Unauthenticated or network issue
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchNotifications();
      const interval = setInterval(fetchNotifications, 5000);
      return () => clearInterval(interval);
    }
  }, [isAuthenticated, currentUser.id]);

  const virtualDate = new Date(baseDate.getTime() + virtualDaysOffset * 24 * 60 * 60 * 1000);

  const switchRole = async (role: UserRole) => {
    const targetTab = getDefaultTabForRole(role);
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
        setActiveNavTab(targetTab);
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
    setActiveNavTab(targetTab);
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
      fetchNotifications();
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
      fetchNotifications();
    } catch (e: any) {
      console.error('Time travel reset error', e);
    }
  };

  const markNotificationAsRead = async (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
    try {
      await apiFetch(`/api/v1/alerts/notifications/${id}/read`, { method: 'POST' });
    } catch {}
  };

  const markAllNotificationsAsRead = async () => {
    const unread = notifications.filter((n) => !n.read);
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    for (const n of unread) {
      try {
        await apiFetch(`/api/v1/alerts/notifications/${n.id}/read`, { method: 'POST' });
      } catch {}
    }
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
        fetchNotifications,
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
        workspace,
        setWorkspace,
        sandboxOverride,
        updateSandboxOverride,
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
