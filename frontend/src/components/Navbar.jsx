import React, { useState, useEffect } from 'react';
import { Bell, Activity, Shield, User, LogOut, CheckCheck, RefreshCw } from 'lucide-react';
import { api } from '../services/api';

export default function Navbar({
  currentUser,
  currentRole,
  onRoleChange,
  activeTab,
  setActiveTab,
  onOpenAudit,
}) {
  const [notifications, setNotifications] = useState([]);
  const [showNotifs, setShowNotifs] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchNotifs = async () => {
    try {
      const data = await api.getNotifications();
      if (Array.isArray(data)) {
        setNotifications(data);
        setUnreadCount(data.filter((n) => !n.read).length);
      }
    } catch {
      // Offline or unauthenticated
    }
  };

  useEffect(() => {
    fetchNotifs();
    const interval = setInterval(fetchNotifs, 8000);
    return () => clearInterval(interval);
  }, [currentUser]);

  const handleMarkAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      fetchNotifs();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <header style={{
      background: 'var(--bg-surface)',
      borderBottom: '1px solid var(--border-default)',
      padding: '10px 20px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      {/* Brand & Mission Identifier */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            background: 'var(--accent-blue)',
            color: '#fff',
            fontWeight: '700',
            fontSize: '14px',
            padding: '3px 7px',
            borderRadius: 'var(--radius-sm)',
            fontFamily: 'var(--font-mono)'
          }}>
            MEDREA
          </div>
          <div>
            <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)', lineHeight: 1.2 }}>
              Clinical Reconciliation Command Center
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Decision Support & Alert System v0.1
            </div>
          </div>
        </div>

        {/* Portal View Tabs */}
        <div style={{ display: 'flex', gap: '4px', marginLeft: '12px', background: 'var(--bg-surface-elevated)', padding: '3px', borderRadius: '6px', border: '1px solid var(--border-default)' }}>
          <button
            onClick={() => {
              if (onRoleChange && currentRole !== 'DOCTOR') onRoleChange('DOCTOR');
              if (setActiveTab) setActiveTab('doctor');
            }}
            style={{
              background: activeTab === 'doctor' ? 'var(--accent-blue)' : 'transparent',
              color: activeTab === 'doctor' ? '#fff' : 'var(--text-secondary)',
              border: 'none',
              borderRadius: '4px',
              padding: '4px 10px',
              fontSize: '11px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Doctor View
          </button>
          <button
            onClick={() => {
              if (onRoleChange && currentRole !== 'PATIENT') onRoleChange('PATIENT');
              if (setActiveTab) setActiveTab('patient');
            }}
            style={{
              background: activeTab === 'patient' ? 'var(--accent-blue)' : 'transparent',
              color: activeTab === 'patient' ? '#fff' : 'var(--text-secondary)',
              border: 'none',
              borderRadius: '4px',
              padding: '4px 10px',
              fontSize: '11px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Patient View
          </button>
          <button
            onClick={() => {
              if (onRoleChange && currentRole !== 'GUARDIAN') onRoleChange('GUARDIAN');
              if (setActiveTab) setActiveTab('guardian');
            }}
            style={{
              background: activeTab === 'guardian' ? 'var(--accent-blue)' : 'transparent',
              color: activeTab === 'guardian' ? '#fff' : 'var(--text-secondary)',
              border: 'none',
              borderRadius: '4px',
              padding: '4px 10px',
              fontSize: '11px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Guardian View
          </button>
        </div>

        {/* Hardware Status Indicator */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          padding: '2px 8px',
          borderRadius: '12px',
          fontSize: '11px',
          color: 'var(--success-green)',
        }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--success-green)' }}></span>
          <span>ESP32 Pager: COM5 (Online)</span>
        </div>
      </div>

      {/* User Controls & Persona Switcher */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {/* Quick Role Switcher for Demo Ease */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-secondary)' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Role:</span>
          <button
            onClick={() => onRoleChange && onRoleChange('DOCTOR')}
            className={`btn btn-sm ${currentRole === 'DOCTOR' ? 'btn-primary' : 'btn-secondary'}`}
          >
            Dr. Sharma (Doctor)
          </button>
          <button
            onClick={() => onRoleChange && onRoleChange('PATIENT')}
            className={`btn btn-sm ${currentRole === 'PATIENT' ? 'btn-primary' : 'btn-secondary'}`}
          >
            Rahul (Patient)
          </button>
          <button
            onClick={() => onRoleChange && onRoleChange('GUARDIAN')}
            className={`btn btn-sm ${currentRole === 'GUARDIAN' ? 'btn-primary' : 'btn-secondary'}`}
          >
            Sunita (Guardian)
          </button>
        </div>

        {/* Global Audit Trail Button */}
        <button
          onClick={onOpenAudit}
          className="btn btn-secondary btn-sm"
          title="Open Clinical Audit Trail"
          style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
        >
          <Shield size={14} />
          <span>Audit Log</span>
        </button>

        {/* Notification Bell */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setShowNotifs(!showNotifs)}
            style={{
              background: 'transparent',
              border: '1px solid var(--border-default)',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              alignItems: 'center',
              position: 'relative',
            }}
            title="In-app Notifications"
          >
            <Bell size={16} />
            {unreadCount > 0 && (
              <span style={{
                position: 'absolute',
                top: '-4px',
                right: '-4px',
                background: 'var(--high-red)',
                color: '#fff',
                fontSize: '9px',
                fontWeight: '700',
                padding: '1px 5px',
                borderRadius: '8px',
              }}>
                {unreadCount}
              </span>
            )}
          </button>

          {/* Notifications Dropdown */}
          {showNotifs && (
            <div style={{
              position: 'absolute',
              right: 0,
              top: '36px',
              width: '320px',
              background: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-md)',
              boxShadow: '0 10px 15px -3px rgba(0,0,0,0.5)',
              zIndex: 200,
              maxHeight: '400px',
              overflowY: 'auto',
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 12px',
                borderBottom: '1px solid var(--border-default)',
                fontSize: '12px',
                fontWeight: '600',
              }}>
                <span>Inbox Notifications ({notifications.length})</span>
                {unreadCount > 0 && (
                  <button
                    onClick={handleMarkAllRead}
                    style={{ background: 'none', border: 'none', color: 'var(--accent-blue)', cursor: 'pointer', fontSize: '11px' }}
                  >
                    Mark all read
                  </button>
                )}
              </div>

              {notifications.length === 0 ? (
                <div style={{ padding: '20px', textAlign: 'center', fontSize: '12px', color: 'var(--text-muted)' }}>
                  No new notifications.
                </div>
              ) : (
                notifications.map((n) => (
                  <div
                    key={n.id}
                    style={{
                      padding: '10px 12px',
                      borderBottom: '1px solid var(--border-subtle)',
                      background: n.read ? 'transparent' : 'rgba(59, 130, 246, 0.05)',
                      fontSize: '12px',
                    }}
                  >
                    <div style={{ fontWeight: '600', color: 'var(--text-primary)', marginBottom: '2px' }}>
                      {n.title}
                    </div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '11px', lineHeight: 1.4 }}>
                      {n.message}
                    </div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '10px', marginTop: '4px' }}>
                      {new Date(n.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Current User Pill */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '4px 10px',
          background: 'var(--bg-surface-elevated)',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--border-default)',
        }}>
          <User size={14} color="var(--text-secondary)" />
          <div>
            <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)' }}>
              {currentUser?.name || currentUser?.full_name || 'User'}
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              {currentUser?.role}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
