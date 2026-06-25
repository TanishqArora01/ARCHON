import type { ScrollState } from '../scroll/useScrollProgress';
import { smoothstep } from '../scroll/useScrollProgress';

interface ArchitectureOverlayProps {
  scrollState: ScrollState;
}

/**
 * Scene 5 — Architectural Reasoning text overlay.
 * "ARCHITECTURE IS A LIVING SYSTEM."
 */
export function ArchitectureOverlay({ scrollState }: ArchitectureOverlayProps) {
  const scene5 = scrollState.sceneProgressArray[4];
  const visible = scene5 > 0.05 && scene5 < 0.95;
  const fadeIn = smoothstep(0.05, 0.3, scene5);
  const fadeOut = 1 - smoothstep(0.75, 1, scene5);
  const opacity = fadeIn * fadeOut;

  if (!visible) return null;

  return (
    <div
      className="overlay-content align-left"
      style={{
        opacity,
        transform: `translateY(${(1 - fadeIn) * 40}px)`,
        pointerEvents: 'none',
      }}
    >
      <p className="label">Architecture Intelligence</p>
      <h2 className="display-lg" style={{ maxWidth: '750px' }}>
        ARCHITECTURE IS A LIVING SYSTEM.
      </h2>
      <p className="subtitle">
        Detect drift, violations, complexity growth, and technical debt
        before they become operational risk.
      </p>
    </div>
  );
}
