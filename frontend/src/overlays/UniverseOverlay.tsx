import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import type { ScrollState } from '../scroll/useScrollProgress';
import { smoothstep } from '../scroll/useScrollProgress';

interface UniverseOverlayProps {
  scrollState: ScrollState;
}

const METRICS = [
  { value: '10K+', label: 'Symbols Extracted' },
  { value: '250K+', label: 'Relationships Mapped' },
  { value: '100%', label: 'Architecture Boundaries' },
  { value: '∞', label: 'Repository Memory' },
];

/**
 * Scene 3 — Repository Universe metrics.
 * Floating glass metric cards that count up on entrance.
 */
export function UniverseOverlay({ scrollState }: UniverseOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const hasAnimated = useRef(false);

  const scene3 = scrollState.sceneProgressArray[2];
  const visible = scene3 > 0.1 && scene3 < 0.95;
  const fadeIn = smoothstep(0.1, 0.4, scene3);
  const fadeOut = 1 - smoothstep(0.8, 1, scene3);
  const opacity = fadeIn * fadeOut;

  useEffect(() => {
    if (!containerRef.current || hasAnimated.current || scene3 < 0.15) return;

    hasAnimated.current = true;

    const cards = containerRef.current.querySelectorAll('.metric-card');
    gsap.fromTo(cards, {
      y: 40,
      opacity: 0,
      scale: 0.9,
    }, {
      y: 0,
      opacity: 1,
      scale: 1,
      duration: 0.8,
      ease: 'power3.out',
      stagger: 0.1,
    });
  }, [scene3]);

  // Reset animation state when scrolling back
  useEffect(() => {
    if (scene3 < 0.05) {
      hasAnimated.current = false;
    }
  }, [scene3]);

  if (!visible) return null;

  return (
    <div
      ref={containerRef}
      className="overlay-content"
      style={{
        opacity,
        pointerEvents: 'none',
      }}
    >
      <p className="label" style={{ marginBottom: 'var(--space-xs)' }}>Repository Intelligence</p>
      <h2 className="display-md" style={{ marginBottom: 'var(--space-lg)' }}>
        A living map of your entire system.
      </h2>

      <div className="metrics-grid">
        {METRICS.map((metric) => (
          <div key={metric.label} className="metric-card glass-card">
            <div className="metric-value">{metric.value}</div>
            <div className="metric-label">{metric.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
