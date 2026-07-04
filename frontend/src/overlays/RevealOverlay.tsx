import { useEffect, useRef, useState } from 'react';
import gsap from 'gsap';
import { Link } from 'react-router-dom';
import type { ScrollState } from '../scroll/useScrollProgress';
import { smoothstep } from '../scroll/useScrollProgress';

interface RevealOverlayProps {
  scrollState: ScrollState;
}

const CAPABILITIES = [
  'Repository Intelligence',
  'Architecture Intelligence',
  'Impact Intelligence',
  'Engineering Reasoning',
];

/**
 * Scene 7 — The Reveal.
 * "ARCHON" in massive typography.
 * "The AI Staff Engineer" subtitle.
 * Email waitlist + Get Started CTA.
 */
export function RevealOverlay({ scrollState }: RevealOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const hasAnimated = useRef(false);
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const scene7 = scrollState.sceneProgressArray[6];
  const visible = scene7 > 0.1;
  const fadeIn = smoothstep(0.1, 0.4, scene7);

  useEffect(() => {
    if (!containerRef.current || hasAnimated.current || scene7 < 0.15) return;
    hasAnimated.current = true;

    const ctx = gsap.context(() => {
      gsap.fromTo('.reveal-title', {
        y: 80, opacity: 0, scale: 0.9,
      }, {
        y: 0, opacity: 1, scale: 1,
        duration: 1.6, ease: 'power4.out',
      });

      gsap.fromTo('.reveal-subtitle', {
        y: 40, opacity: 0,
      }, {
        y: 0, opacity: 1,
        duration: 1.2, ease: 'power3.out', delay: 0.4,
      });

      gsap.fromTo('.capability-list li', {
        y: 20, opacity: 0,
      }, {
        y: 0, opacity: 1,
        duration: 0.8, ease: 'power3.out', stagger: 0.08, delay: 0.7,
      });

      gsap.fromTo('.reveal-cta-area', {
        y: 20, opacity: 0,
      }, {
        y: 0, opacity: 1,
        duration: 1, ease: 'power3.out', delay: 1.2,
      });

      gsap.fromTo('.reveal-social-proof', {
        y: 16, opacity: 0,
      }, {
        y: 0, opacity: 1,
        duration: 0.8, ease: 'power3.out', delay: 1.6,
      });
    }, containerRef.current);

    return () => ctx.revert();
  }, [scene7]);

  useEffect(() => {
    if (scene7 < 0.05) {
      hasAnimated.current = false;
    }
  }, [scene7]);

  const handleWaitlist = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    // Open mailto — works without a backend. Can be replaced with a Resend/Mailchimp form.
    const subject = encodeURIComponent('Archon Early Access Request');
    const body = encodeURIComponent(
      `Hi,\n\nI'd like early access to Archon.\n\nEmail: ${email}`
    );
    window.open(`mailto:archon@example.com?subject=${subject}&body=${body}`);
    setSubmitted(true);
  };

  if (!visible) return null;

  return (
    <div
      ref={containerRef}
      className="overlay-content"
      style={{
        opacity: fadeIn,
        pointerEvents: fadeIn > 0.5 ? 'auto' : 'none',
      }}
    >
      <h1
        className="display-xl reveal-title"
        style={{
          fontSize: 'clamp(64px, 12vw, 180px)',
          letterSpacing: '-0.04em',
          fontWeight: 700,
        }}
      >
        ARCHON
      </h1>

      <p
        className="subtitle reveal-subtitle"
        style={{
          fontSize: 'clamp(18px, 2.2vw, 28px)',
          color: 'var(--text-muted)',
          marginTop: 'var(--space-sm)',
          fontWeight: 400,
        }}
      >
        The AI Staff Engineer
      </p>

      <ul className="capability-list" style={{ marginTop: 'var(--space-xl)' }}>
        {CAPABILITIES.map((cap) => (
          <li key={cap}>{cap}</li>
        ))}
      </ul>

      {/* CTA area — primary button + waitlist */}
      <div
        className="reveal-cta-area"
        style={{
          marginTop: 'var(--space-xl)',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          alignItems: 'flex-start',
        }}
      >
        <Link to="/login" className="cta-button reveal-cta">
          Get Started Free
          <span className="arrow">→</span>
        </Link>

        {/* Email waitlist */}
        {!submitted ? (
          <form
            onSubmit={handleWaitlist}
            style={{
              display: 'flex',
              gap: '0.5rem',
              width: '100%',
              maxWidth: '380px',
            }}
          >
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
              style={{
                flex: 1,
                padding: '0.55rem 0.9rem',
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: '6px',
                color: '#fff',
                fontSize: '0.875rem',
                fontFamily: '"Inter", sans-serif',
                outline: 'none',
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = 'rgba(34,197,94,0.4)';
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)';
              }}
            />
            <button
              type="submit"
              style={{
                padding: '0.55rem 1rem',
                background: 'rgba(34,197,94,0.15)',
                border: '1px solid rgba(34,197,94,0.35)',
                borderRadius: '6px',
                color: 'rgb(134, 239, 172)',
                fontSize: '0.875rem',
                fontFamily: '"Inter", sans-serif',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'background 0.2s',
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.background = 'rgba(34,197,94,0.25)';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.background = 'rgba(34,197,94,0.15)';
              }}
            >
              Join waitlist
            </button>
          </form>
        ) : (
          <p
            style={{
              fontSize: '0.875rem',
              color: 'rgb(134, 239, 172)',
              margin: 0,
              fontFamily: '"Inter", sans-serif',
            }}
          >
            ✓ You're on the list. We'll reach out soon.
          </p>
        )}
      </div>

      {/* Social proof */}
      <div
        className="reveal-social-proof"
        style={{
          marginTop: '2.5rem',
          display: 'flex',
          gap: '1.5rem',
          alignItems: 'center',
          flexWrap: 'wrap',
        }}
      >
        <a
          href="https://github.com/TanishqArora01/ARCHON"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            color: 'rgba(255,255,255,0.35)',
            fontSize: '0.8rem',
            textDecoration: 'none',
            fontFamily: '"Inter", sans-serif',
            transition: 'color 0.2s',
          }}
          onMouseOver={(e) => (e.currentTarget.style.color = 'rgba(255,255,255,0.7)')}
          onMouseOut={(e) => (e.currentTarget.style.color = 'rgba(255,255,255,0.35)')}
        >
          <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
          </svg>
          Open source on GitHub
        </a>

        <span style={{ color: 'rgba(255,255,255,0.1)', fontSize: '0.8rem' }}>·</span>

        <span
          style={{
            color: 'rgba(255,255,255,0.35)',
            fontSize: '0.8rem',
            fontFamily: '"Inter", sans-serif',
          }}
        >
          🐳 Self-hostable · Docker Compose
        </span>

        <span style={{ color: 'rgba(255,255,255,0.1)', fontSize: '0.8rem' }}>·</span>

        <span
          style={{
            color: 'rgba(255,255,255,0.35)',
            fontSize: '0.8rem',
            fontFamily: '"Inter", sans-serif',
          }}
        >
          🦙 Works with Ollama · NVIDIA · OpenAI
        </span>
      </div>
    </div>
  );
}
