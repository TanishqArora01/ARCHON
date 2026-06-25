import { Monolith } from './Monolith';
import { RepositoryGraph } from './RepositoryGraph';
import { IntelligenceCore } from './IntelligenceCore';
import { AmbientParticles } from './AmbientParticles';
import { CameraRig } from './CameraRig';
import { PostEffects } from './PostEffects';
import type { ScrollState } from '../scroll/useScrollProgress';
import { Environment } from '@react-three/drei';

interface CinematicSceneProps {
  scrollState: ScrollState;
}

/**
 * Master 3D scene containing all sub-scene objects, lighting, and post-processing.
 * This is the single persistent Three.js world that all scenes share.
 */
export function CinematicScene({ scrollState }: CinematicSceneProps) {
  return (
    <>
      {/* Camera controller */}
      <CameraRig scrollState={scrollState} />

      {/* Lighting */}
      <ambientLight intensity={0.15} color="#b8d4e3" />

      <directionalLight
        position={[5, 8, 5]}
        intensity={0.8}
        color="#c8dbe8"
        castShadow={false}
      />

      <directionalLight
        position={[-3, -2, 4]}
        intensity={0.2}
        color="#6ee7c0"
      />

      <pointLight
        position={[0, 0, 0]}
        intensity={0.5}
        color="#6ee7c0"
        distance={15}
        decay={2}
      />

      {/* Fog for depth */}
      <fog attach="fog" args={['#000000', 15, 45]} />

      {/* Environment for reflections */}
      <Environment preset="night" environmentIntensity={0.3} />

      {/* Scene objects */}
      <Monolith scrollState={scrollState} />
      <RepositoryGraph scrollState={scrollState} />
      <IntelligenceCore scrollState={scrollState} />

      {/* Ambient particles — always visible */}
      <AmbientParticles count={2500} radius={22} opacity={0.2} />

      {/* Post-processing */}
      <PostEffects />
    </>
  );
}
