import React from 'react';
import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        backgroundColor: '#000',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#fff',
        fontFamily: '"Inter", sans-serif',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Ambient glow */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '500px',
          height: '500px',
          background:
            'radial-gradient(circle, rgba(34,197,94,0.04) 0%, rgba(0,0,0,0) 70%)',
          pointerEvents: 'none',
        }}
      />

      <div
        style={{
          position: 'relative',
          zIndex: 1,
          textAlign: 'center',
          padding: '2rem',
        }}
      >
        {/* 404 display */}
        <p
          style={{
            fontSize: '0.75rem',
            letterSpacing: '0.3em',
            color: 'rgba(34,197,94,0.7)',
            textTransform: 'uppercase',
            margin: '0 0 1rem 0',
          }}
        >
          Error 404
        </p>
        <h1
          style={{
            fontSize: 'clamp(3rem, 10vw, 7rem)',
            fontWeight: 700,
            letterSpacing: '-0.04em',
            margin: '0 0 1rem 0',
            fontFamily: '"Space Grotesk", sans-serif',
            opacity: 0.15,
          }}
        >
          NOT FOUND
        </h1>

        <p
          style={{
            fontSize: '1rem',
            color: 'rgba(255,255,255,0.45)',
            margin: '0 0 2.5rem 0',
            maxWidth: '380px',
            lineHeight: 1.6,
          }}
        >
          This path doesn't exist in the repository graph. Let's get you back to
          something real.
        </p>

        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link
            to="/"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.75rem 1.5rem',
              backgroundColor: '#fff',
              color: '#000',
              borderRadius: '8px',
              fontWeight: 500,
              fontSize: '0.9rem',
              textDecoration: 'none',
              transition: 'transform 0.2s',
            }}
            onMouseOver={(e) => (e.currentTarget.style.transform = 'translateY(-2px)')}
            onMouseOut={(e) => (e.currentTarget.style.transform = 'translateY(0)')}
          >
            ← Back to Home
          </Link>

          <Link
            to="/login"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.75rem 1.5rem',
              backgroundColor: 'transparent',
              color: 'rgba(255,255,255,0.6)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: '8px',
              fontWeight: 400,
              fontSize: '0.9rem',
              textDecoration: 'none',
              transition: 'all 0.2s',
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.3)';
              e.currentTarget.style.color = '#fff';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)';
              e.currentTarget.style.color = 'rgba(255,255,255,0.6)';
            }}
          >
            Go to Dashboard
          </Link>
        </div>

        {/* Brand footer */}
        <p
          style={{
            marginTop: '4rem',
            fontSize: '0.7rem',
            color: 'rgba(255,255,255,0.12)',
            letterSpacing: '0.2em',
          }}
        >
          ARCHON — AI STAFF ENGINEER
        </p>
      </div>
    </div>
  );
}
