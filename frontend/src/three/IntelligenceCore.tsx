import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { ScrollState } from '../scroll/useScrollProgress';
import { smoothstep } from '../scroll/useScrollProgress';

interface IntelligenceCoreProps {
  scrollState: ScrollState;
}

/**
 * Scene 6 — The Intelligence Core.
 * Graph collapses inward. A precision-engineered glass core forms.
 * Information streams flow through it. Feels expensive and minimal.
 */
export function IntelligenceCore({ scrollState }: IntelligenceCoreProps) {
  const groupRef = useRef<THREE.Group>(null);
  const coreRef = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Mesh>(null);
  const streamsRef = useRef<THREE.LineSegments>(null);

  const scene6 = scrollState.sceneProgressArray[5];
  const scene7 = scrollState.sceneProgressArray[6];

  const coreVisible = scene6 > 0.2;
  const coreScale = smoothstep(0.2, 0.7, scene6);
  const revealFade = smoothstep(0, 0.5, scene7);

  // Information stream lines flowing inward
  const streamCount = 48;
  const streamPositions = useMemo(() => {
    const arr = new Float32Array(streamCount * 6);
    for (let i = 0; i < streamCount; i++) {
      const angle = (i / streamCount) * Math.PI * 2;
      const r = 6 + Math.random() * 3;
      const y = (Math.random() - 0.5) * 4;
      const i6 = i * 6;
      // Outer point
      arr[i6]     = Math.cos(angle) * r;
      arr[i6 + 1] = y;
      arr[i6 + 2] = Math.sin(angle) * r;
      // Inner point (converges to center)
      arr[i6 + 3] = 0;
      arr[i6 + 4] = 0;
      arr[i6 + 5] = 0;
    }
    return arr;
  }, []);

  useFrame((_, delta) => {
    if (!groupRef.current) return;

    // Slow rotation
    groupRef.current.rotation.y += delta * 0.08;

    // Scale entrance
    groupRef.current.scale.setScalar(coreScale * (1 - revealFade * 0.3));

    // Floating bob
    groupRef.current.position.y = Math.sin(Date.now() * 0.0003) * 0.1;

    // Animate stream convergence
    if (streamsRef.current) {
      const posAttr = streamsRef.current.geometry.getAttribute('position') as THREE.BufferAttribute;
      const arr = posAttr.array as Float32Array;
      const convergence = smoothstep(0.3, 0.8, scene6);

      for (let i = 0; i < streamCount; i++) {
        const i6 = i * 6;
        const angle = (i / streamCount) * Math.PI * 2 + Date.now() * 0.00005;
        const r = (1 - convergence) * (6 + Math.sin(i * 1.3) * 2) + 0.3;
        const y = Math.sin(i * 0.8 + Date.now() * 0.0002) * (1 - convergence) * 3;

        arr[i6]     = Math.cos(angle) * r;
        arr[i6 + 1] = y;
        arr[i6 + 2] = Math.sin(angle) * r;
      }
      posAttr.needsUpdate = true;
    }

    // Glow pulse
    if (glowRef.current) {
      const mat = glowRef.current.material as THREE.MeshBasicMaterial;
      mat.opacity = (0.08 + Math.sin(Date.now() * 0.001) * 0.04) * coreScale;
    }
  });

  if (!coreVisible) return null;

  return (
    <group ref={groupRef}>
      {/* Core icosahedron — black glass */}
      <mesh ref={coreRef}>
        <icosahedronGeometry args={[1.2, 2]} />
        <meshPhysicalMaterial
          color="#080810"
          metalness={0.98}
          roughness={0.04}
          clearcoat={1}
          clearcoatRoughness={0.02}
          reflectivity={1}
          envMapIntensity={1.2}
          emissive="#0a1520"
          emissiveIntensity={0.5}
          transparent
          opacity={coreScale}
        />
      </mesh>

      {/* Inner glow sphere */}
      <mesh ref={glowRef} scale={[1.8, 1.8, 1.8]}>
        <sphereGeometry args={[1, 24, 24]} />
        <meshBasicMaterial
          color="#6ee7c0"
          transparent
          opacity={0.08}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Information streams */}
      <lineSegments ref={streamsRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[streamPositions, 3]}
          />
        </bufferGeometry>
        <lineBasicMaterial
          color="#6ee7c0"
          transparent
          opacity={0.15 * coreScale}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </lineSegments>
    </group>
  );
}
