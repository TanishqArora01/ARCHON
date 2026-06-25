import { useEffect, useRef, useState, useCallback } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const SCENE_COUNT = 7;

export interface ScrollState {
  /** Overall progress 0 → 1 across the entire scroll journey */
  globalProgress: number;
  /** Current scene index 0-6 */
  sceneIndex: number;
  /** Progress within the current scene 0 → 1 */
  sceneProgress: number;
  /** Per-scene progress array [0→1, 0→1, ...] */
  sceneProgressArray: number[];
}

const INITIAL_STATE: ScrollState = {
  globalProgress: 0,
  sceneIndex: 0,
  sceneProgress: 0,
  sceneProgressArray: Array(SCENE_COUNT).fill(0),
};

/**
 * Master scroll progress hook.
 * Tracks global scroll position and decomposes into per-scene progress values.
 * Drives the entire cinematic experience.
 */
export function useScrollProgress(containerRef: React.RefObject<HTMLDivElement | null>): ScrollState {
  const [state, setState] = useState<ScrollState>(INITIAL_STATE);
  const stateRef = useRef<ScrollState>(INITIAL_STATE);

  const updateProgress = useCallback((self: ScrollTrigger) => {
    const progress = self.progress;
    const rawScene = progress * SCENE_COUNT;
    const sceneIndex = Math.min(Math.floor(rawScene), SCENE_COUNT - 1);
    const sceneProgress = rawScene - sceneIndex;

    const sceneProgressArray = Array(SCENE_COUNT).fill(0).map((_, i) => {
      if (i < sceneIndex) return 1;
      if (i === sceneIndex) return sceneProgress;
      return 0;
    });

    const next: ScrollState = {
      globalProgress: progress,
      sceneIndex,
      sceneProgress,
      sceneProgressArray,
    };

    stateRef.current = next;
    setState(next);
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const trigger = ScrollTrigger.create({
      trigger: container,
      start: 'top top',
      end: 'bottom bottom',
      scrub: 0.8,
      onUpdate: updateProgress,
    });

    return () => {
      trigger.kill();
    };
  }, [containerRef, updateProgress]);

  return state;
}

/**
 * Utility: get a smooth interpolated value that transitions
 * between 0→1 within a sub-range of a scene's progress.
 */
export function sceneRange(sceneProgress: number, start: number, end: number): number {
  if (sceneProgress <= start) return 0;
  if (sceneProgress >= end) return 1;
  return (sceneProgress - start) / (end - start);
}

/**
 * Utility: clamp a value between min and max.
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

/**
 * Utility: smooth step interpolation.
 */
export function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = clamp((x - edge0) / (edge1 - edge0), 0, 1);
  return t * t * (3 - 2 * t);
}
