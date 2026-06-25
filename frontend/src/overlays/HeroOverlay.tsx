import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Link } from 'react-router-dom';
import type { ScrollState } from '../scroll/useScrollProgress';

gsap.registerPlugin(ScrollTrigger);

interface HeroOverlayProps {
  scrollState: ScrollState;
}

/**
 * Scene 1 — Hero text overlay.
 * "UNDERSTAND SYSTEMS. NOT FILES."
 * Massive display typography with subtle entrance and scroll-driven fade.
 */
export function HeroOverlay({ scrollState }: HeroOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const ctx = gsap.context(() => {
      // Entrance animation
      gsap.fromTo(el.querySelectorAll('.hero-line'), {
        y: 60,
        opacity: 0,
      }, {
        y: 0,
        opacity: 1,
        duration: 1.4,
        ease: 'power3.out',
        stagger: 0.15,
        delay: 0.3,
      });

      gsap.fromTo(el.querySelector('.hero-subtitle'), {
        y: 30,
        opacity: 0,
      }, {
        y: 0,
        opacity: 1,
        duration: 1.2,
        ease: 'power3.out',
        delay: 0.8,
      });

      gsap.fromTo(el.querySelector('.hero-cta'), {
        y: 20,
        opacity: 0,
      }, {
        y: 0,
        opacity: 1,
        duration: 1,
        ease: 'power3.out',
        delay: 1.1,
      });

      gsap.fromTo(el.querySelector('.scroll-indicator'), {
        opacity: 0,
      }, {
        opacity: 1,
        duration: 1.5,
        delay: 2,
      });
    }, el);

    return () => ctx.revert();
  }, []);

  // Fade out as user scrolls into scene 2
  const scene1 = scrollState.sceneProgressArray[0];
  const fadeOut = Math.max(0, 1 - scene1 * 2.5);

  return (
    <div
      ref={containerRef}
      className="overlay-content"
      style={{
        opacity: fadeOut,
        transform: `translateY(${-scene1 * 60}px)`,
        transition: 'none',
        pointerEvents: fadeOut < 0.1 ? 'none' : 'auto',
      }}
    >
      <div style={{ overflow: 'hidden' }}>
        <h1 className="display-xl hero-line">UNDERSTAND</h1>
      </div>
      <div style={{ overflow: 'hidden' }}>
        <h1 className="display-xl hero-line">SYSTEMS.</h1>
      </div>
      <div style={{ overflow: 'hidden', marginTop: '-0.1em' }}>
        <p className="display-lg hero-line" style={{ color: 'var(--text-muted)' }}>
          NOT FILES.
        </p>
      </div>

      <p className="subtitle hero-subtitle" style={{ marginTop: 'var(--space-md)' }}>
        Repository Intelligence for Modern Engineering Teams.
      </p>

      <Link to="/login" className="cta-button hero-cta" style={{ marginTop: 'var(--space-sm)' }}>
        Explore Archon
        <span className="arrow">→</span>
      </Link>

      <div className="scroll-indicator">
        <span>Scroll</span>
        <div className="scroll-chevron" />
      </div>
    </div>
  );
}
