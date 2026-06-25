import type { ScrollState } from '../scroll/useScrollProgress';
import { smoothstep } from '../scroll/useScrollProgress';

interface ReasoningOverlayProps {
  scrollState: ScrollState;
}

/**
 * Scene 6 — Reasoning / Intelligence Core text overlay.
 * "REASONING BUILT ON EVIDENCE."
 */
export function ReasoningOverlay({ scrollState }: ReasoningOverlayProps) {
  const scene6 = scrollState.sceneProgressArray[5];
  const visible = scene6 > 0.15 && scene6 < 0.95;
  const fadeIn = smoothstep(0.15, 0.4, scene6);
  const fadeOut = 1 - smoothstep(0.75, 1, scene6);
  const opacity = fadeIn * fadeOut;

  if (!visible) return null;

  return (
    <div
      className="overlay-content"
      style={{
        opacity,
        transform: `translateY(${(1 - fadeIn) * 40}px)`,
        pointerEvents: 'none',
      }}
    >
      <p className="label">Engineering Reasoning</p>
      <h2 className="display-lg" style={{ maxWidth: '700px' }}>
        REASONING BUILT ON EVIDENCE.
      </h2>
      <p className="subtitle">
        Every recommendation is backed by repository intelligence,
        architecture context, and graph evidence.
      </p>
    </div>
  );
}
