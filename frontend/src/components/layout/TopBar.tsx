'use client';

import React, { useState } from 'react';
import { useApp, SAMPLE_REGIONS, DEMO_USERS, UserRole } from '@/lib/app-context';
import {
  Search,
  Bell,
  Clock,
  FastForward,
  RotateCcw,
  CheckCheck,
  User,
  ChevronDown,
  MapPin,
  Calendar,
  AlertCircle,
  FileClock,
  LogOut,
} from 'lucide-react';

export const TopBar: React.FC = () => {
  const {
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
    logout,
    restartBootSequence,
  } = useApp();

  const [showRoleMenu, setShowRoleMenu] = useState(false);
  const [showRegionMenu, setShowRegionMenu] = useState(false);
  const [showNotifMenu, setShowNotifMenu] = useState(false);

  const formattedDate = virtualDate.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  return (
    <header className="h-16 bg-white border-b border-ink-line px-6 flex items-center justify-between sticky top-0 z-20 shadow-soft">
      {/* Search Input */}
      <div className="flex items-center gap-3 w-80">
        <div className="relative w-full">
          <Search className="w-4 h-4 text-ink-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search PID, App No, or ask plain English..."
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-ink-line rounded-lg text-ink focus:bg-white focus:border-blossom-600 transition-all placeholder:text-ink-muted"
          />
        </div>
      </div>

      {/* Middle & Right Controls: Region, Time Travel, Alerts, Role Switcher */}
      <div className="flex items-center gap-3">
        {/* Configurable AICTE Region Selector */}
        <div className="relative">
          <button
            onClick={() => {
              setShowRegionMenu(!showRegionMenu);
              setShowRoleMenu(false);
              setShowNotifMenu(false);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 hover:bg-slate-100 border border-ink-line rounded-lg text-xs font-semibold text-ink transition-all"
            title="Switch Regional Office Scope"
          >
            <MapPin className="w-3.5 h-3.5 text-blossom-600" />
            <span className="truncate max-w-[140px]">{currentRegion.code} ({currentRegion.city})</span>
            <ChevronDown className="w-3.5 h-3.5 text-ink-muted" />
          </button>

          {showRegionMenu && (
            <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-card border border-ink-line p-2 z-50">
              <div className="text-[11px] font-bold text-ink-muted uppercase tracking-wider px-2 py-1 border-b border-slate-100">
                AICTE Regional Offices (Configurable)
              </div>
              <div className="max-h-60 overflow-y-auto mt-1 space-y-0.5">
                {SAMPLE_REGIONS.map((region) => (
                  <button
                    key={region.code}
                    onClick={() => {
                      setRegionByCode(region.code);
                      setShowRegionMenu(false);
                    }}
                    className={`w-full text-left px-2 py-2 rounded-lg text-xs flex items-center justify-between transition-colors ${
                      currentRegion.code === region.code
                        ? 'bg-blossom-100 font-bold text-ink-strong'
                        : 'hover:bg-slate-50 text-ink'
                    }`}
                  >
                    <div>
                      <div className="font-semibold">{region.name}</div>
                      <div className="text-[10px] text-ink-muted">{region.city}</div>
                    </div>
                    <span className="text-[10px] font-bold px-1.5 py-0.5 bg-slate-100 rounded text-ink-muted">
                      {region.activeCasesCount} cases
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* TIME-TRAVEL SIMULATOR (MANDATORY DEMO FEATURE) */}
        <div className="flex items-center bg-slate-100/80 rounded-lg p-1 border border-ink-line/80 gap-1">
          <div className="flex items-center gap-1 px-2 text-xs font-bold text-ink-strong">
            <Calendar className="w-3.5 h-3.5 text-blossom-600" />
            <span>{formattedDate}</span>
            {virtualDaysOffset > 0 && (
              <span className="bg-roseState-100 text-roseState-700 text-[10px] px-1.5 py-0.2 rounded-full font-bold ml-1">
                +{virtualDaysOffset}d
              </span>
            )}
          </div>
          <button
            onClick={() => advanceVirtualDays(1)}
            className="px-2 py-1 bg-white hover:bg-blossom-100 border border-ink-line rounded text-[11px] font-semibold text-ink transition-colors flex items-center gap-0.5 shadow-sm"
            title="Advance clock by 1 day"
          >
            <FastForward className="w-3 h-3 text-blossom-600" /> +1d
          </button>
          <button
            onClick={() => advanceVirtualDays(7)}
            className="px-2 py-1 bg-white hover:bg-blossom-100 border border-ink-line rounded text-[11px] font-semibold text-ink transition-colors flex items-center gap-0.5 shadow-sm"
            title="Advance clock by 7 days to trigger SLA & EVC reminders"
          >
            <FastForward className="w-3 h-3 text-blossom-600" /> +7d
          </button>
          <button
            onClick={() => advanceVirtualDays(30)}
            className="px-2 py-1 bg-white hover:bg-roseState-100 border border-ink-line rounded text-[11px] font-semibold text-ink transition-colors flex items-center gap-0.5 shadow-sm"
            title="Advance clock by 30 days to trigger document expiry and level-3 escalations"
          >
            <FastForward className="w-3 h-3 text-roseState-700" /> +30d
          </button>
          {virtualDaysOffset > 0 && (
            <button
              onClick={resetVirtualTime}
              className="px-1.5 py-1 text-ink-muted hover:text-ink-strong transition-colors"
              title="Reset to Real-Time Clock"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* NOTIFICATION BELL & POPUP */}
        <div className="relative">
          <button
            onClick={() => {
              setShowNotifMenu(!showNotifMenu);
              setShowRoleMenu(false);
              setShowRegionMenu(false);
            }}
            className="relative p-2 rounded-lg hover:bg-slate-100 text-ink transition-colors border border-transparent hover:border-ink-line"
            aria-label="View notifications"
          >
            <Bell className="w-4 h-4" />
            {unreadNotificationsCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 bg-roseState-700 text-white text-[9px] font-bold rounded-full flex items-center justify-center">
                {unreadNotificationsCount}
              </span>
            )}
          </button>

          {showNotifMenu && (
            <div className="absolute right-0 mt-2 w-96 bg-white rounded-xl shadow-card border border-ink-line p-3 z-50">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <div className="text-xs font-bold text-ink-strong flex items-center gap-1.5">
                  <Bell className="w-3.5 h-3.5 text-blossom-600" /> Notifications & Escalation Alerts
                </div>
                {unreadNotificationsCount > 0 && (
                  <button
                    onClick={markAllNotificationsAsRead}
                    className="text-[11px] text-blossom-600 hover:underline font-semibold flex items-center gap-1"
                  >
                    <CheckCheck className="w-3 h-3" /> Mark all read
                  </button>
                )}
              </div>
              <div className="max-h-72 overflow-y-auto mt-2 space-y-2">
                {notifications.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => markNotificationAsRead(item.id)}
                    className={`p-2.5 rounded-lg border text-xs cursor-pointer transition-colors ${
                      item.read
                        ? 'bg-slate-50 border-ink-line/60 opacity-80'
                        : item.severity === 'CRITICAL'
                        ? 'bg-roseState-100 border-roseState-700/30'
                        : 'bg-amberState-100 border-amberState-700/30'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-ink-strong flex items-center gap-1">
                        {item.severity === 'CRITICAL' && (
                          <AlertCircle className="w-3.5 h-3.5 text-roseState-700 shrink-0" />
                        )}
                        {item.title}
                      </span>
                      <span className="text-[10px] text-ink-muted">{item.timestamp}</span>
                    </div>
                    <p className="text-[11px] text-ink leading-relaxed">{item.message}</p>
                    {item.escalationLevel && (
                      <span className="mt-1 inline-block text-[9px] font-bold px-1.5 py-0.5 rounded bg-roseState-700 text-white">
                        Escalated to: {item.escalationLevel}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* DEMO ROLE SWITCHER (ONE-CLICK SWITCHER) */}
        <div className="relative">
          <button
            onClick={() => {
              setShowRoleMenu(!showRoleMenu);
              setShowRegionMenu(false);
              setShowNotifMenu(false);
            }}
            className="flex items-center gap-2 pl-2 pr-3 py-1.5 bg-blossom-100 hover:bg-blossom-300/40 border border-blossom-300 rounded-lg text-xs font-semibold text-ink-strong transition-all shadow-soft"
          >
            <div className="w-6 h-6 rounded-md bg-blossom-600 text-white flex items-center justify-center font-bold text-xs">
              {currentUser.name.charAt(0)}
            </div>
            <div className="text-left">
              <div className="leading-none text-[11px] font-bold text-blossom-700">Role: {currentUser.roleLabel}</div>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-ink-muted" />
          </button>

          {showRoleMenu && (
            <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-card border border-ink-line p-2 z-50">
              <div className="text-[11px] font-bold text-ink-muted uppercase tracking-wider px-2 py-1 border-b border-slate-100">
                Demo Role Switcher (RBAC)
              </div>
              <div className="space-y-1 mt-1">
                {(Object.keys(DEMO_USERS) as UserRole[]).map((roleKey) => {
                  const u = DEMO_USERS[roleKey];
                  const isSelected = currentUser.role === u.role;
                  return (
                    <button
                      key={roleKey}
                      onClick={() => {
                        switchRole(roleKey);
                        setShowRoleMenu(false);
                      }}
                      className={`w-full text-left px-2.5 py-2 rounded-lg text-xs flex items-center justify-between transition-colors ${
                        isSelected
                          ? 'bg-blossom-100 font-bold text-ink-strong border-l-4 border-blossom-600'
                          : 'hover:bg-slate-50 text-ink'
                      }`}
                    >
                      <div>
                        <div className="font-bold text-ink-strong">{u.roleLabel}</div>
                        <div className="text-[10px] text-ink-muted">{u.name}</div>
                      </div>
                      <span className="text-[9px] px-1.5 py-0.5 bg-slate-100 rounded text-ink-muted font-bold">
                        {u.regionCode}
                      </span>
                    </button>
                  );
                })}
              </div>
              <div className="pt-1 mt-1 border-t border-slate-100 space-y-0.5">
                <button
                  onClick={() => {
                    setShowRoleMenu(false);
                    restartBootSequence();
                  }}
                  className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink hover:bg-slate-50 font-medium flex items-center gap-1.5 transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-blossom-600" />
                  <span>Reboot System Diagnostics</span>
                </button>
                <button
                  onClick={() => {
                    setShowRoleMenu(false);
                    logout();
                  }}
                  className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs text-roseState-700 hover:bg-roseState-100/50 font-bold flex items-center gap-1.5 transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Sign Out of Session</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Dedicated Sign Out Button */}
        <button
          onClick={logout}
          className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-50 hover:bg-roseState-100/50 hover:text-roseState-700 border border-ink-line rounded-lg text-xs font-semibold text-ink-muted transition-all"
          title="Sign out and return to Login Screen"
        >
          <LogOut className="w-3.5 h-3.5 text-roseState-700" />
          <span className="hidden sm:inline">Sign Out</span>
        </button>
      </div>
    </header>
  );
};
