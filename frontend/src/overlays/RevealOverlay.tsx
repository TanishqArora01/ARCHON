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

    </div>
  );
}
