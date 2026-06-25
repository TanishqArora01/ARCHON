import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from './AuthContext';

/**
 * OAuthCallback
 *
 * This route handles the redirect from the FastAPI backend after a successful
 * OAuth flow. It reads the JWT token and provider from the query params,
 * stores the token via AuthContext, and redirects to the dashboard.
 *
 * URL pattern: /oauth/callback?token=...&provider=...
 */
export function OAuthCallback() {
  const [searchParams] = useSearchParams();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = searchParams.get('token');
    const provider = searchParams.get('provider');
    const oauthError = searchParams.get('error');

    if (oauthError) {
      setError(`Authentication failed with ${provider || 'provider'}: ${oauthError}`);
      return;
    }

    if (token) {
      login(token);
      // Small delay to let state propagate before navigation
      setTimeout(() => {
        navigate('/dashboard', { replace: true });
      }, 100);
    } else {
      setError(`Authentication failed. No token received from ${provider || 'provider'}.`);
    }
  }, [searchParams, login, navigate]);

  if (error) {
    return (
      <div style={{
        width: '100vw',
        height: '100vh',
        backgroundColor: '#000',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#fff',
        fontFamily: '"Inter", sans-serif',
        gap: '2rem'
      }}>
        <h2 style={{ fontWeight: 300, color: '#ff6b6b' }}>Authentication Error</h2>
        <p style={{ color: 'rgba(255,255,255,0.5)', maxWidth: '400px', textAlign: 'center' }}>{error}</p>
        <button
          onClick={() => navigate('/login', { replace: true })}
          style={{
            padding: '0.75rem 2rem',
            backgroundColor: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '8px',
            color: '#fff',
            cursor: 'pointer',
            fontSize: '0.9rem'
          }}
        >
          Back to Login
        </button>
      </div>
    );
  }

  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      backgroundColor: '#000',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#fff',
      fontFamily: '"Inter", sans-serif',
    }}>
      <div style={{ letterSpacing: '2px', fontSize: '0.8rem', opacity: 0.5 }}>
        AUTHENTICATING...
      </div>
    </div>
  );
}
