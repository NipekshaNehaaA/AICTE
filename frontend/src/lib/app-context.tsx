'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

export type UserRole =
  | 'INSTITUTION_USER'
  | 'REGIONAL_OFFICER'
  | 'BUREAU_OFFICER'
  | 'COMMITTEE_MEMBER'
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
  BUREAU_OFFICER: {
    id: 'usr-bo-01',
    name: 'Shri Anand Sharma',
    email: 'approval.bureau@aicte-india.org',
    role: 'BUREAU_OFFICER',
    roleLabel: 'Bureau Officer (HQ)',
    regionCode: 'HQ',
  },
  COMMITTEE_MEMBER: {
    id: 'usr-cm-01',
    name: 'Prof. Meenakshi Sundaram',
    email: 'expert.visit@aicte-india.org',
    role: 'COMMITTEE_MEMBER',
    roleLabel: 'EVC Committee Expert',
    regionCode: 'SWRO',
  },
  SUPER_ADMIN: {
    id: 'usr-sa-01',
    name: 'Prof. Rajive Kumar (Member Secretary)',
    email: 'member.secretary@aicte-india.org',
    role: 'SUPER_ADMIN',
    roleLabel: 'Member Secretary / Approving Authority',
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
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isSystemLoading, setIsSystemLoading] = useState<boolean>(true);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [currentUser, setCurrentUser] = useState<UserProfile>(DEMO_USERS.REGIONAL_OFFICER);
  const [currentRegion, setCurrentRegion] = useState<RegionInfo>(SAMPLE_REGIONS[0]); // Default: SWRO Bengaluru
  const [virtualDaysOffset, setVirtualDaysOffset] = useState<number>(0);
  const [baseDate] = useState<Date>(new Date('2026-10-22T09:00:00Z'));
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeNavTab, setActiveNavTab] = useState<string>('dashboard');

  const restartBootSequence = () => {
    setIsAuthenticated(false);
    setIsSystemLoading(true);
  };

  const loginAsPersona = (role: UserRole) => {
    const user = DEMO_USERS[role];
    if (user) {
      setCurrentUser(user);
      const reg = SAMPLE_REGIONS.find((r) => r.code === user.regionCode) || SAMPLE_REGIONS[0];
      setCurrentRegion(reg);
      setIsAuthenticated(true);
      setActiveNavTab('dashboard');
    }
  };

  const loginWithToken = (user: UserProfile, token: string) => {
    setCurrentUser(user);
    const reg = SAMPLE_REGIONS.find((r) => r.code === user.regionCode) || SAMPLE_REGIONS[0];
    setCurrentRegion(reg);
    setIsAuthenticated(true);
    setActiveNavTab('dashboard');
  };

  const logout = () => {
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

  const switchRole = (role: UserRole) => {
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
      const res = await fetch('http://127.0.0.1:8000/api/v1/demo/time-travel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days_to_advance: days }),
      });
      const data = await res.json();
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
    } catch (e) {
      console.error('Time travel API call error', e);
      setVirtualDaysOffset((prev) => prev + days);
    }
  };

  const resetVirtualTime = async () => {
    try {
      await fetch('http://127.0.0.1:8000/api/v1/demo/time-travel/reset', { method: 'POST' });
    } catch (e) {}
    setVirtualDaysOffset(0);
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
