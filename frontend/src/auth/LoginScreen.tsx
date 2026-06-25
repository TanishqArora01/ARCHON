import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { demoLogin } from '../api';
import { Code2, GitMerge } from 'lucide-react';

export function LoginScreen() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [isConnecting, setIsConnecting] = useState(false);

  // If already logged in, redirect to dashboard
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleLogin = async (provider: string) => {
    if (provider === 'demo') {
      setIsConnecting(true);
      try {
        const { token } = await demoLogin();
        login(token);
        navigate('/dashboard', { replace: true });
      } catch (err) {
        console.error('Demo login failed', err);
        // Fallback for when backend isn't running
        login('demo-token-12345');
        navigate('/dashboard', { replace: true });
      } finally {
        setIsConnecting(false);
      }
    } else {
      // Redirect to the FastAPI backend to start the OAuth flow
      const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      window.location.href = `${backendUrl}/api/v1/oauth/${provider}/start`;
    }
  };

  return (
    <div className="login-container" style={{
      width: '100vw',
      height: '100vh',
      backgroundColor: '#000',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      position: 'relative',
      overflow: 'hidden',
      color: '#fff'
    }}>
      {/* Subtle background ambient glow */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: '600px',
        height: '600px',
        background: 'radial-gradient(circle, rgba(20,40,30,0.1) 0%, rgba(0,0,0,0) 70%)',
        pointerEvents: 'none'
      }} />

      <div style={{
        zIndex: 10,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '4rem',
        maxWidth: '400px',
        width: '100%',
        padding: '0 2rem'
      }}>
        <div style={{ textAlign: 'center' }}>
          <h1 style={{ 
            fontSize: '3rem', 
            fontWeight: 400, 
            letterSpacing: '-0.02em',
            margin: 0,
            marginBottom: '1rem'
          }}>
            ARCHON
          </h1>
          <p style={{
            fontSize: '1rem',
            color: 'rgba(255,255,255,0.4)',
            letterSpacing: '0.05em',
            margin: 0
          }}>
            THE AI STAFF ENGINEER
          </p>
        </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%' }}>
            <button 
              onClick={() => handleLogin('github')}
              style={{
                width: '100%',
                padding: '1rem',
                backgroundColor: '#fff',
                color: '#000',
                border: 'none',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.75rem',
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseOver={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
              onMouseOut={(e) => e.currentTarget.style.transform = 'translateY(0)'}
            >
              <Code2 size={20} />
              Continue with GitHub
            </button>
            
            <button 
              onClick={() => handleLogin('gitlab')}
              style={{
                width: '100%',
                padding: '1rem',
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                color: '#fff',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.75rem',
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                e.currentTarget.style.transform = 'translateY(-2px)';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.05)';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              <GitMerge size={20} />
              Continue with GitLab
            </button>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', margin: '2rem 0', gap: '1rem', width: '100%' }}>
            <div style={{ flex: 1, height: '1px', backgroundColor: 'rgba(255, 255, 255, 0.1)' }}></div>
            <span style={{ color: 'rgba(255, 255, 255, 0.3)', fontSize: '0.8rem', letterSpacing: '1px' }}>OR</span>
            <div style={{ flex: 1, height: '1px', backgroundColor: 'rgba(255, 255, 255, 0.1)' }}></div>
          </div>
          
          <button 
            onClick={() => handleLogin('demo')}
            disabled={isConnecting}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '100%',
              padding: '1rem',
              backgroundColor: 'rgba(200, 255, 220, 0.1)',
              border: '1px solid rgba(200, 255, 220, 0.2)',
              borderRadius: '8px',
              color: 'rgb(200, 255, 220)',
              fontSize: '1rem',
              cursor: isConnecting ? 'wait' : 'pointer',
              transition: 'all 0.2s ease',
              opacity: isConnecting ? 0.7 : 1
            }}
            onMouseOver={(e) => { if(!isConnecting) e.currentTarget.style.backgroundColor = 'rgba(200, 255, 220, 0.15)'}}
            onMouseOut={(e) => { if(!isConnecting) e.currentTarget.style.backgroundColor = 'rgba(200, 255, 220, 0.1)'}}
          >
            {isConnecting ? 'Authenticating...' : 'Developer Demo Login'}
          </button>
      </div>
    </div>
  );
}
