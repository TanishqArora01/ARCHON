import { useEffect, useRef } from 'react';
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
 * Capability list and final CTA.
 */
export function RevealOverlay({ scrollState }: RevealOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const hasAnimated = useRef(false);

  const scene7 = scrollState.sceneProgressArray[6];
  const visible = scene7 > 0.1;
  const fadeIn = smoothstep(0.1, 0.4, scene7);

  useEffect(() => {
    if (!containerRef.current || hasAnimated.current || scene7 < 0.15) return;
    hasAnimated.current = true;

    const ctx = gsap.context(() => {
      gsap.fromTo('.reveal-title', {
        y: 80,
        opacity: 0,
        scale: 0.9,
      }, {
        y: 0,
        opacity: 1,
        scale: 1,
        duration: 1.6,
        ease: 'power4.out',
      });

      gsap.fromTo('.reveal-subtitle', {
        y: 40,
        opacity: 0,
      }, {
        y: 0,
        opacity: 1,
        duration: 1.2,
        ease: 'power3.out',
        delay: 0.4,
      });

      gsap.fromTo('.capability-list li', {
        y: 20,
        opacity: 0,
      }, {
        y: 0,
        opacity: 1,
        duration: 0.8,
        ease: 'power3.out',
        stagger: 0.08,
        delay: 0.7,
      });

      gsap.fromTo('.reveal-cta', {
        y: 20,
        opacity: 0,
      }, {
        y: 0,
        opacity: 1,
        duration: 1,
        ease: 'power3.out',
        delay: 1.2,
      });
    }, containerRef.current);

    return () => ctx.revert();
  }, [scene7]);

  useEffect(() => {
    if (scene7 < 0.05) {
      hasAnimated.current = false;
    }
  }, [scene7]);

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

      <Link
        to="/login"
        className="cta-button reveal-cta"
        style={{ marginTop: 'var(--space-xl)' }}
      >
        Get Started
        <span className="arrow">→</span>
      </Link>
    </div>
  );
}
