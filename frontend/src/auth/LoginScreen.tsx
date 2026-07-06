import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { demoLogin } from '../api';
import { Code2, GitMerge, Loader2, AlertCircle, Server } from 'lucide-react';

type LoginStage = 'idle' | 'waking' | 'connecting' | 'error';

export function LoginScreen() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [stage, setStage] = useState<LoginStage>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [wakeSeconds, setWakeSeconds] = useState(0);

  // If already logged in, redirect to dashboard
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // Wake-up timer shown while waiting for backend cold start
  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    if (stage === 'waking' || stage === 'connecting') {
      timer = setInterval(() => setWakeSeconds((s) => s + 1), 1000);
    } else {
      setWakeSeconds(0);
    }
    return () => clearInterval(timer);
  }, [stage]);

  const handleLogin = async (provider: string) => {
    setErrorMsg('');
    if (provider === 'demo') {
      setStage('waking');
      try {
        // Attempt backend demo login — backend may cold-start (Render free tier)
        const { token } = await demoLogin();
        setStage('connecting');
        login(token);
        navigate('/dashboard', { replace: true });
      } catch (err: unknown) {
        // Do NOT silently log users in with a fake token.
        // Show a clear, honest error explaining what happened.
        const msg =
          err instanceof Error ? err.message : 'Unknown error';
        if (
          msg.toLowerCase().includes('failed to fetch') ||
          msg.toLowerCase().includes('network') ||
          msg.toLowerCase().includes('500') ||
          msg.toLowerCase().includes('503')
        ) {
          setErrorMsg(
            'Backend is waking up (free tier cold start). Please wait 20–30 seconds and try again.'
          );
        } else {
          setErrorMsg(`Login failed: ${msg}`);
        }
        setStage('error');
      }
    } else {
      // Redirect to the FastAPI backend to start the OAuth flow
      const backendUrl =
        import.meta.env.VITE_API_URL || 'https://archon-ixrh.onrender.com';
      window.location.href = `${backendUrl}/api/v1/oauth/${provider}/start`;
    }
  };

  const isLoading = stage === 'waking' || stage === 'connecting';

  return (
    <div
      className="login-container"
      style={{
        width: '100vw',
        height: '100vh',
        backgroundColor: '#000',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        overflow: 'hidden',
        color: '#fff',
      }}
    >
      {/* Ambient background glow */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '600px',
          height: '600px',
          background:
            'radial-gradient(circle, rgba(34,197,94,0.05) 0%, rgba(0,0,0,0) 70%)',
          pointerEvents: 'none',
        }}
      />

      <div
        style={{
          zIndex: 10,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '2.5rem',
          maxWidth: '420px',
          width: '100%',
          padding: '0 2rem',
        }}
      >
        {/* Logo */}
        <div style={{ textAlign: 'center' }}>
          <h1
            style={{
              fontSize: '3rem',
              fontWeight: 400,
              letterSpacing: '-0.02em',
              margin: 0,
              marginBottom: '0.5rem',
              fontFamily: '"Space Grotesk", sans-serif',
            }}
          >
            ARCHON
          </h1>
          <p
            style={{
              fontSize: '0.875rem',
              color: 'rgba(255,255,255,0.4)',
              letterSpacing: '0.1em',
              margin: 0,
              textTransform: 'uppercase',
            }}
          >
            The AI Staff Engineer
          </p>
        </div>

        {/* Auth buttons */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%' }}>
          {/* GitHub */}
          <button
            onClick={() => handleLogin('github')}
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '0.9rem 1.25rem',
              backgroundColor: isLoading ? 'rgba(255,255,255,0.7)' : '#fff',
              color: '#000',
              border: 'none',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.75rem',
              fontWeight: 500,
              fontSize: '0.95rem',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
              fontFamily: '"Inter", sans-serif',
            }}
            onMouseOver={(e) => {
              if (!isLoading) e.currentTarget.style.transform = 'translateY(-2px)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <Code2 size={20} />
            Continue with GitHub
          </button>

          {/* GitLab */}
          <button
            onClick={() => handleLogin('gitlab')}
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '0.9rem 1.25rem',
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              color: '#fff',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.75rem',
              fontWeight: 500,
              fontSize: '0.95rem',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
              fontFamily: '"Inter", sans-serif',
            }}
            onMouseOver={(e) => {
              if (!isLoading) {
                e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                e.currentTarget.style.transform = 'translateY(-2px)';
              }
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.05)';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <GitMerge size={20} />
            Continue with GitLab
          </button>

          {/* Divider */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '1rem',
              padding: '0.25rem 0',
            }}
          >
            <div style={{ flex: 1, height: '1px', backgroundColor: 'rgba(255,255,255,0.08)' }} />
            <span
              style={{
                color: 'rgba(255,255,255,0.25)',
                fontSize: '0.75rem',
                letterSpacing: '1px',
              }}
            >
              OR
            </span>
            <div style={{ flex: 1, height: '1px', backgroundColor: 'rgba(255,255,255,0.08)' }} />
          </div>

          {/* Demo login */}
          <button
            onClick={() => handleLogin('demo')}
            disabled={isLoading}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.6rem',
              width: '100%',
              padding: '0.9rem 1.25rem',
              backgroundColor: 'rgba(34, 197, 94, 0.08)',
              border: '1px solid rgba(34, 197, 94, 0.25)',
              borderRadius: '8px',
              color: 'rgb(134, 239, 172)',
              fontSize: '0.95rem',
              fontFamily: '"Inter", sans-serif',
              cursor: isLoading ? 'wait' : 'pointer',
              transition: 'all 0.2s ease',
              opacity: isLoading ? 0.7 : 1,
            }}
            onMouseOver={(e) => {
              if (!isLoading)
                e.currentTarget.style.backgroundColor = 'rgba(34, 197, 94, 0.14)';
            }}
            onMouseOut={(e) => {
              if (!isLoading)
                e.currentTarget.style.backgroundColor = 'rgba(34, 197, 94, 0.08)';
            }}
          >
            {isLoading ? (
              <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
            ) : (
              <Server size={18} />
            )}
            {stage === 'waking'
              ? `Waking up backend… ${wakeSeconds > 5 ? `(${wakeSeconds}s)` : ''}`
              : stage === 'connecting'
              ? 'Authenticating…'
              : 'Developer Demo Login'}
          </button>
        </div>

        {/* Cold start warning — shown while waking */}
        {stage === 'waking' && wakeSeconds > 8 && (
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.5rem',
              padding: '0.75rem 1rem',
              backgroundColor: 'rgba(251, 191, 36, 0.07)',
              border: '1px solid rgba(251, 191, 36, 0.2)',
              borderRadius: '8px',
              width: '100%',
              boxSizing: 'border-box',
            }}
          >
            <AlertCircle size={16} style={{ color: '#fbbf24', flexShrink: 0, marginTop: '2px' }} />
            <p
              style={{
                margin: 0,
                fontSize: '0.8rem',
                color: 'rgba(251, 191, 36, 0.8)',
                lineHeight: 1.5,
              }}
            >
              The backend is on a free tier and takes 20–40 seconds to wake from sleep. Hang tight.
            </p>
          </div>
        )}

        {/* Error state */}
        {stage === 'error' && errorMsg && (
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.5rem',
              padding: '0.75rem 1rem',
              backgroundColor: 'rgba(239, 68, 68, 0.07)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              borderRadius: '8px',
              width: '100%',
              boxSizing: 'border-box',
            }}
          >
            <AlertCircle size={16} style={{ color: '#ef4444', flexShrink: 0, marginTop: '2px' }} />
            <p style={{ margin: 0, fontSize: '0.8rem', color: 'rgba(239,68,68,0.9)', lineHeight: 1.5 }}>
              {errorMsg}
            </p>
          </div>
        )}


      </div>
    </div>
  );
}
