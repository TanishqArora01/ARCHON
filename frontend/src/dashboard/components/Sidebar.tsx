import React from 'react';
import { NavLink } from 'react-router-dom';
import { Network, Search, Activity, Box, LogOut, User } from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';

const NAV_ITEMS = [
  { label: 'Repositories', icon: Box, path: '/dashboard/repositories' },
  { label: 'Analysis Runs', icon: Activity, path: '/dashboard/analysis' },
  { label: 'Graph Search', icon: Search, path: '/dashboard/search' },
  { label: 'Impact Analysis', icon: Network, path: '/dashboard/impact' },
];

export function Sidebar() {
  const { logout, user } = useAuth();

  return (
    <aside style={{
      width: '280px',
      height: '100vh',
      backgroundColor: 'rgba(10, 10, 10, 0.6)',
      backdropFilter: 'blur(20px)',
      borderRight: '1px solid rgba(255, 255, 255, 0.05)',
      display: 'flex',
      flexDirection: 'column',
      padding: '2rem 0',
      position: 'sticky',
      top: 0
    }}>
      <div style={{ padding: '0 2rem', marginBottom: '3rem' }}>
        <h2 style={{ 
          fontSize: '1.25rem', 
          fontWeight: 600, 
          letterSpacing: '0.05em',
          margin: 0,
          color: '#fff'
        }}>
          ARCHON
        </h2>
        <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
          Platform Workspace
        </span>
      </div>

      <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '0 1rem' }}>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '1rem',
              padding: '0.75rem 1rem',
              borderRadius: '8px',
              color: isActive ? '#fff' : 'rgba(255, 255, 255, 0.5)',
              backgroundColor: isActive ? 'rgba(255, 255, 255, 0.05)' : 'transparent',
              textDecoration: 'none',
              fontSize: '0.9rem',
              transition: 'all 0.2s ease'
            })}
            onMouseOver={(e) => {
              if (e.currentTarget.style.backgroundColor === 'transparent') {
                e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.02)';
                e.currentTarget.style.color = 'rgba(255, 255, 255, 0.8)';
              }
            }}
            onMouseOut={(e) => {
              // React Router handles active state style, so we don't reset if active.
              // A bit hacky with inline styles, but works for the demo.
              if (e.currentTarget.getAttribute('aria-current') !== 'page') {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = 'rgba(255, 255, 255, 0.5)';
              }
            }}
          >
            <item.icon size={18} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: '0 1rem', marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {user && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            padding: '1rem',
            marginBottom: '0.5rem',
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            borderRadius: '8px',
            border: '1px solid rgba(255, 255, 255, 0.05)'
          }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff'
            }}>
              <User size={16} />
            </div>
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <div style={{ 
                fontSize: '0.85rem', 
                fontWeight: 500, 
                color: '#fff',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {user.username}
              </div>
              <div style={{ 
                fontSize: '0.7rem', 
                color: 'rgba(255,255,255,0.4)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                {user.provider}
              </div>
            </div>
          </div>
        )}

        <button
          onClick={logout}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            color: 'rgba(255, 100, 100, 0.7)',
            backgroundColor: 'transparent',
            border: 'none',
            fontSize: '0.9rem',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            textAlign: 'left'
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.backgroundColor = 'rgba(255, 100, 100, 0.05)';
            e.currentTarget.style.color = 'rgba(255, 100, 100, 1)';
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = 'rgba(255, 100, 100, 0.7)';
          }}
        >
          <LogOut size={18} />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
