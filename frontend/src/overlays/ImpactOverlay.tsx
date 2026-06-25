import type { ScrollState } from '../scroll/useScrollProgress';
import { smoothstep } from '../scroll/useScrollProgress';

interface ImpactOverlayProps {
  scrollState: ScrollState;
}

/**
 * Scene 4 — Impact Analysis text overlay.
 * "SEE WHAT CHANGES BEFORE YOU SHIP THEM."
 */
export function ImpactOverlay({ scrollState }: ImpactOverlayProps) {
  const scene4 = scrollState.sceneProgressArray[3];
  const visible = scene4 > 0.05 && scene4 < 0.95;
  const fadeIn = smoothstep(0.05, 0.3, scene4);
  const fadeOut = 1 - smoothstep(0.75, 1, scene4);
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
      <p className="label">Impact Analysis</p>
      <h2 className="display-lg" style={{ maxWidth: '700px' }}>
        SEE WHAT CHANGES BEFORE YOU SHIP THEM.
      </h2>
      <p className="subtitle">
        Understand blast radius, dependency chains, and architectural impact
        before code reaches production.
      </p>
    </div>
  );
}
