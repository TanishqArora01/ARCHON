import { useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { AdaptiveDpr } from '@react-three/drei';

import { CinematicScene } from './three/CinematicScene';
import { ScrollContainer, SceneSection } from './scroll/ScrollContainer';
import { useScrollProgress } from './scroll/useScrollProgress';

import { HeroOverlay } from './overlays/HeroOverlay';
import { UniverseOverlay } from './overlays/UniverseOverlay';
import { ImpactOverlay } from './overlays/ImpactOverlay';
import { ArchitectureOverlay } from './overlays/ArchitectureOverlay';
import { ReasoningOverlay } from './overlays/ReasoningOverlay';
import { RevealOverlay } from './overlays/RevealOverlay';

/**
 * Archon — Cinematic Marketing Website
 *
 * Architecture:
 * - Fixed full-viewport Three.js Canvas (z-index: 1)
 * - Scrollable HTML overlay container (z-index: 2)
 * - Single scroll progress state drives everything
 * - All 7 scenes share one persistent 3D world
 */
export default function MarketingSite() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const scrollState = useScrollProgress(scrollRef);

  return (
    <>
      {/* Fixed 3D Canvas — fills entire viewport, behind scroll layer */}
      <div className="canvas-container">
        <Canvas
          camera={{ position: [0, 0.5, 10], fov: 44, near: 0.1, far: 100 }}
          dpr={[1, 2]}
          gl={{
            antialias: true,
            alpha: false,
            powerPreference: 'high-performance',
            stencil: false,
            depth: true,
          }}
          style={{ background: '#000000' }}
        >
          <AdaptiveDpr pixelated />
          <color attach="background" args={['#000000']} />
          <CinematicScene scrollState={scrollState} />
        </Canvas>
      </div>

      {/* Scrollable overlay layer — HTML text on top of 3D */}
      <div ref={scrollRef}>
        <ScrollContainer>
          {/* Scene 1: The Monolith — Hero */}
          <SceneSection id="scene-hero" index={0}>
            <HeroOverlay scrollState={scrollState} />
          </SceneSection>

          {/* Scene 2: Repository Awakening — transition scene, no text overlay */}
          <SceneSection id="scene-awakening" index={1}>
            <></>
          </SceneSection>

          {/* Scene 3: Repository Universe — metrics */}
          <SceneSection id="scene-universe" index={2}>
            <UniverseOverlay scrollState={scrollState} />
          </SceneSection>

          {/* Scene 4: Impact Analysis */}
          <SceneSection id="scene-impact" index={3}>
            <ImpactOverlay scrollState={scrollState} />
          </SceneSection>

          {/* Scene 5: Architectural Reasoning */}
          <SceneSection id="scene-architecture" index={4}>
            <ArchitectureOverlay scrollState={scrollState} />
          </SceneSection>

          {/* Scene 6: Intelligence Core */}
          <SceneSection id="scene-reasoning" index={5}>
            <ReasoningOverlay scrollState={scrollState} />
          </SceneSection>

          {/* Scene 7: The Reveal */}
          <SceneSection id="scene-reveal" index={6}>
            <RevealOverlay scrollState={scrollState} />
          </SceneSection>
        </ScrollContainer>
      </div>
    </>
  );
}
