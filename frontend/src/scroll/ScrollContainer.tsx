import React from 'react';

interface ScrollContainerProps {
  children: React.ReactNode;
}

/**
 * The scrollable HTML layer that sits on top of the fixed Three.js canvas.
 * Total height = 700vh (7 scenes × 100vh each).
 * Contains all text overlays positioned at their corresponding scroll offsets.
 */
export function ScrollContainer({ children }: ScrollContainerProps) {
  return (
    <div className="scroll-container" style={{ height: '700vh' }}>
      {children}
    </div>
  );
}

interface SceneSectionProps {
  id: string;
  /** Which scene number (1-7), determines vertical offset */
  index: number;
  children: React.ReactNode;
}

/**
 * A single 100vh scene section positioned at its scroll offset.
 */
export function SceneSection({ id, index, children }: SceneSectionProps) {
  return (
    <section
      id={id}
      className="scene-section"
      style={{
        position: 'absolute',
        top: `${index * 100}vh`,
        left: 0,
        right: 0,
        height: '100vh',
      }}
    >
      {children}
    </section>
  );
}
