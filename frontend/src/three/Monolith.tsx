import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { ScrollState } from '../scroll/useScrollProgress';
import { smoothstep } from '../scroll/useScrollProgress';

interface MonolithProps {
  scrollState: ScrollState;
}

/**
 * Scene 1 — The Monolith.
 * A massive black glass object floating in darkness.
 * Rotates extremely slowly. Fractures and dissolves in Scene 2.
 */
export function Monolith({ scrollState }: MonolithProps) {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef = useRef<THREE.Mesh>(null);

  // Scene 1 progress: visible, rotating slowly
  // Scene 2 progress: scale down and dissolve
  const scene2 = scrollState.sceneProgressArray[1];

  // Visibility: fully visible in scene 0-1, fade during scene 2
  const dissolve = smoothstep(0, 0.7, scene2);
  const scale = 1 - dissolve * 0.8;
  const opacity = 1 - dissolve;

  // Monolith geometry parameters
  const geometry = useMemo(() => {
    return new THREE.BoxGeometry(1.6, 3.2, 0.8, 4, 8, 4);
  }, []);

  useFrame((_, delta) => {
    if (!groupRef.current || !meshRef.current) return;

    // Extremely slow rotation
    groupRef.current.rotation.y += delta * 0.05;
    groupRef.current.rotation.x = Math.sin(Date.now() * 0.0002) * 0.03;

    // Floating bob
    groupRef.current.position.y = Math.sin(Date.now() * 0.0004) * 0.15;

    // Scale driven by scroll
    groupRef.current.scale.setScalar(scale);

    // Update material opacity
    const mat = meshRef.current.material as THREE.MeshPhysicalMaterial;
    mat.opacity = opacity;

    // In scene 2, fragment outward
    if (scene2 > 0.01) {
      groupRef.current.position.z = -dissolve * 3;
    } else {
      groupRef.current.position.z = 0;
    }
  });

  // Only render if not fully dissolved
  if (opacity < 0.01) return null;

  return (
    <group ref={groupRef}>
      <mesh ref={meshRef} geometry={geometry}>
        <meshPhysicalMaterial
          color="#0a0a0f"
          metalness={0.95}
          roughness={0.08}
          clearcoat={1}
          clearcoatRoughness={0.05}
          reflectivity={1}
          envMapIntensity={0.8}
          transparent
          opacity={opacity}
        />
      </mesh>

      {/* Subtle edge glow */}
      <mesh geometry={geometry} scale={[1.005, 1.005, 1.005]}>
        <meshBasicMaterial
          color="#1a2a3a"
          transparent
          opacity={opacity * 0.15}
          side={THREE.BackSide}
        />
      </mesh>
    </group>
  );
}
