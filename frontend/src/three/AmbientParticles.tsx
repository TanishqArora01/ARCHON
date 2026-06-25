import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface AmbientParticlesProps {
  count?: number;
  radius?: number;
  opacity?: number;
}

/**
 * Persistent atmospheric particles drifting through the entire scene.
 * Uses Points geometry with slow brownian drift.
 * Very subtle — atmospheric, not distracting.
 */
export function AmbientParticles({
  count = 3000,
  radius = 25,
  opacity = 0.25,
}: AmbientParticlesProps) {
  const pointsRef = useRef<THREE.Points>(null);

  const { positions, velocities } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const velocities = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      // Distribute in a sphere
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = Math.cbrt(Math.random()) * radius;

      positions[i3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      positions[i3 + 2] = r * Math.cos(phi);

      // Slow drift velocities
      velocities[i3] = (Math.random() - 0.5) * 0.003;
      velocities[i3 + 1] = (Math.random() - 0.5) * 0.002;
      velocities[i3 + 2] = (Math.random() - 0.5) * 0.003;
    }

    return { positions, velocities };
  }, [count, radius]);

  const sizes = useMemo(() => {
    const arr = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      arr[i] = 0.5 + Math.random() * 1.5;
    }
    return arr;
  }, [count]);

  useFrame((_, delta) => {
    if (!pointsRef.current) return;
    const posAttr = pointsRef.current.geometry.getAttribute('position') as THREE.BufferAttribute;
    const posArr = posAttr.array as Float32Array;

    const clampedDelta = Math.min(delta, 0.05);

    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      posArr[i3] += velocities[i3] * clampedDelta * 60;
      posArr[i3 + 1] += velocities[i3 + 1] * clampedDelta * 60;
      posArr[i3 + 2] += velocities[i3 + 2] * clampedDelta * 60;

      // Wrap around sphere boundary
      const dist = Math.sqrt(
        posArr[i3] ** 2 + posArr[i3 + 1] ** 2 + posArr[i3 + 2] ** 2
      );
      if (dist > radius) {
        posArr[i3] *= -0.5;
        posArr[i3 + 1] *= -0.5;
        posArr[i3 + 2] *= -0.5;
      }
    }
    posAttr.needsUpdate = true;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
        <bufferAttribute
          attach="attributes-size"
          args={[sizes, 1]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={1.2}
        sizeAttenuation
        transparent
        opacity={opacity}
        color="#ffffff"
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}
