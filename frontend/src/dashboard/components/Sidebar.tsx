import React from 'react';
import { NavLink } from 'react-router-dom';
import { Network, Search, Activity, Box, LogOut, User, Bot, Sparkles } from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';

const NAV_ITEMS = [
  { label: 'Repositories',   icon: Box,      path: '/dashboard/repositories' },
  { label: 'Analysis Runs',  icon: Activity, path: '/dashboard/analysis' },
  { label: 'Graph Search',   icon: Search,   path: '/dashboard/search' },
  { label: 'Impact Analysis',icon: Network,  path: '/dashboard/impact' },
  { label: 'Agent System',   icon: Bot,      path: '/dashboard/agents' },
];

export function Sidebar() {
  const { logout, user } = useAuth();

  return (
    <aside style={{
      width: '260px',
      minWidth: '260px',
      height: '100vh',
      backgroundColor: 'rgba(8, 10, 12, 0.9)',
      backdropFilter: 'blur(20px)',
      borderRight: '1px solid rgba(255, 255, 255, 0.05)',
      display: 'flex',
      flexDirection: 'column',
      padding: '0',
      position: 'sticky',
      top: 0,
      overflowY: 'auto',
      overflowX: 'hidden',
    }}>

      {/* Logo / Brand */}
      <div style={{ padding: '1.75rem 1.5rem 1.5rem', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.25rem' }}>
          <div style={{
            width: '26px', height: '26px', borderRadius: '7px',
            background: 'linear-gradient(135deg, rgba(110,231,192,0.3), rgba(125,168,255,0.2))',
            border: '1px solid rgba(110,231,192,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Sparkles size={13} color="#6ee7c0" />
          </div>
          <h2 style={{
            fontSize: '1rem',
            fontWeight: 700,
            letterSpacing: '0.1em',
            margin: 0,
            color: '#fff',
          }}>
            ARCHON
          </h2>
        </div>
        <span style={{
          fontSize: '0.68rem',
          color: 'rgba(255,255,255,0.3)',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          paddingLeft: '0.1rem',
        }}>
          AI Staff Engineer · v1.0
        </span>
      </div>

      {/* Navigation */}
      <nav style={{
        flex: 1,
        padding: '1rem 0.75rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.25rem',
      }}>
        <p style={{
          fontSize: '0.65rem',
          color: 'rgba(255,255,255,0.25)',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          padding: '0.25rem 0.5rem 0.75rem',
          margin: 0,
        }}>
          Platform
        </p>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `sidebar-nav-link${isActive ? ' active' : ''}`}
          >
            <item.icon size={17} strokeWidth={1.8} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* User / Logout Footer */}
      <div style={{
        padding: '0.75rem',
        borderTop: '1px solid rgba(255,255,255,0.04)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.25rem',
      }}>
        {user && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '0.75rem',
            borderRadius: '8px',
            backgroundColor: 'rgba(255,255,255,0.03)',
            marginBottom: '0.25rem',
          }}>
            <div style={{
              width: '30px', height: '30px', borderRadius: '50%',
              background: 'linear-gradient(135deg, rgba(110,231,192,0.2), rgba(125,168,255,0.2))',
              border: '1px solid rgba(255,255,255,0.1)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'rgba(255,255,255,0.7)',
              flexShrink: 0,
            }}>
              <User size={14} />
            </div>
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <div style={{
                fontSize: '0.82rem',
                fontWeight: 500,
                color: '#fff',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}>
                {user.username}
              </div>
              <div style={{
                fontSize: '0.65rem',
                color: user.provider === 'demo'
                  ? 'rgba(110,231,192,0.6)'
                  : 'rgba(255,255,255,0.35)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}>
                {user.provider}
              </div>
            </div>
          </div>
        )}

        <button
          onClick={logout}
          className="sidebar-nav-link"
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgba(255,100,100,0.6)', width: '100%' }}
        >
          <LogOut size={16} strokeWidth={1.8} />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
