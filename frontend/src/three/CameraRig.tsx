import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useRef } from 'react';
import type { ScrollState } from '../scroll/useScrollProgress';

interface CameraRigProps {
  scrollState: ScrollState;
}

/**
 * Camera path keyframes for each scene.
 * [x, y, z] camera position at each scene boundary.
 */
const CAMERA_POSITIONS: [number, number, number][] = [
  [0, 0.5, 10],    // Scene 1: Monolith — distant, centered
  [0, 0.8, 7],     // Scene 2: Awakening — moving closer
  [-1, 2, 9],      // Scene 3: Universe — elevated, slight offset
  [2, 1, 7],       // Scene 4: Impact — shifted right to see ripple
  [0, 3.5, 8],     // Scene 5: Architecture — elevated, layers visible
  [0, 0.5, 5],     // Scene 6: Intelligence Core — intimate
  [0, 0, 4],       // Scene 7: Reveal — close, centered
  [0, 0, 3],       // End position
];

const CAMERA_LOOK_AT: [number, number, number][] = [
  [0, 0, 0],
  [0, 0, 0],
  [0, 0, 0],
  [0, 0, 0],
  [0, 0, 0],
  [0, 0, 0],
  [0, 0, 0],
  [0, 0, 0],
];

const FOV_KEYFRAMES = [44, 44, 50, 48, 52, 38, 32, 30];

/**
 * Scroll-driven camera controller.
 * Smoothly interpolates position, lookAt, and FOV along a predefined path.
 */
export function CameraRig({ scrollState }: CameraRigProps) {
  const { camera } = useThree();
  const lookAtTarget = useRef(new THREE.Vector3());

  useFrame(() => {
    const progress = scrollState.globalProgress;

    // Map progress to keyframe indices
    const totalSegments = CAMERA_POSITIONS.length - 1;
    const rawIndex = progress * totalSegments;
    const index = Math.min(Math.floor(rawIndex), totalSegments - 1);
    const t = rawIndex - index;

    // Smooth interpolation with ease
    const eased = t * t * (3 - 2 * t); // smoothstep

    // Interpolate position
    const posA = CAMERA_POSITIONS[index];
    const posB = CAMERA_POSITIONS[index + 1];
    const targetX = THREE.MathUtils.lerp(posA[0], posB[0], eased);
    const targetY = THREE.MathUtils.lerp(posA[1], posB[1], eased);
    const targetZ = THREE.MathUtils.lerp(posA[2], posB[2], eased);

    // Smooth damping toward target
    camera.position.x += (targetX - camera.position.x) * 0.08;
    camera.position.y += (targetY - camera.position.y) * 0.08;
    camera.position.z += (targetZ - camera.position.z) * 0.08;

    // Interpolate lookAt
    const lookA = CAMERA_LOOK_AT[index];
    const lookB = CAMERA_LOOK_AT[index + 1];
    lookAtTarget.current.set(
      THREE.MathUtils.lerp(lookA[0], lookB[0], eased),
      THREE.MathUtils.lerp(lookA[1], lookB[1], eased),
      THREE.MathUtils.lerp(lookA[2], lookB[2], eased)
    );
    camera.lookAt(lookAtTarget.current);

    // Interpolate FOV
    const fovA = FOV_KEYFRAMES[index];
    const fovB = FOV_KEYFRAMES[index + 1];
    const targetFov = THREE.MathUtils.lerp(fovA, fovB, eased);
    if (camera instanceof THREE.PerspectiveCamera) {
      camera.fov += (targetFov - camera.fov) * 0.08;
      camera.updateProjectionMatrix();
    }
  });

  return null;
}
