import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

/**
 * Persistent top navigation bar for the Archon marketing site.
 * Transparent at top, gets a subtle frosted glass effect on scroll.
 */
export function MarketingNav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <nav
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        padding: '0 2rem',
        height: '56px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        transition: 'background 0.3s ease, border-color 0.3s ease',
        background: scrolled ? 'rgba(0,0,0,0.75)' : 'transparent',
        borderBottom: scrolled
          ? '1px solid rgba(255,255,255,0.06)'
          : '1px solid transparent',
        backdropFilter: scrolled ? 'blur(12px)' : 'none',
        WebkitBackdropFilter: scrolled ? 'blur(12px)' : 'none',
      }}
    >
      {/* Logo */}
      <Link
        to="/"
        style={{
          textDecoration: 'none',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}
      >
        <svg
          width="22"
          height="22"
          viewBox="0 0 32 32"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <polygon
            points="16,4 26,9.5 26,22.5 16,28 6,22.5 6,9.5"
            stroke="#22c55e"
            strokeWidth="1.5"
            fill="none"
            opacity="0.7"
          />
          <path
            d="M11 23 L16 9 L21 23"
            stroke="#ffffff"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
          <path d="M12.8 18 L19.2 18" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <span
          style={{
            color: '#fff',
            fontFamily: '"Space Grotesk", sans-serif',
            fontWeight: 600,
            fontSize: '1rem',
            letterSpacing: '-0.01em',
          }}
        >
          Archon
        </span>
      </Link>

      {/* Nav links — center */}
      <div
        style={{
          display: 'flex',
          gap: '2rem',
          alignItems: 'center',
        }}
      >
        <NavLink href="https://github.com/TanishqArora01/ARCHON" external>
          GitHub
        </NavLink>
        <NavLink href="https://github.com/TanishqArora01/ARCHON#readme" external>
          Docs
        </NavLink>
      </div>

      {/* CTA */}
      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
        <Link
          to="/login"
          style={{
            color: 'rgba(255,255,255,0.55)',
            fontSize: '0.875rem',
            fontWeight: 400,
            textDecoration: 'none',
            fontFamily: '"Inter", sans-serif',
            transition: 'color 0.2s',
          }}
          onMouseOver={(e) => (e.currentTarget.style.color = '#fff')}
          onMouseOut={(e) => (e.currentTarget.style.color = 'rgba(255,255,255,0.55)')}
        >
          Sign in
        </Link>
        <Link
          to="/login"
          style={{
            padding: '0.45rem 1rem',
            backgroundColor: '#fff',
            color: '#000',
            borderRadius: '6px',
            fontSize: '0.875rem',
            fontWeight: 500,
            textDecoration: 'none',
            fontFamily: '"Inter", sans-serif',
            transition: 'transform 0.2s, opacity 0.2s',
          }}
          onMouseOver={(e) => (e.currentTarget.style.opacity = '0.9')}
          onMouseOut={(e) => (e.currentTarget.style.opacity = '1')}
        >
          Get Started
        </Link>
      </div>
    </nav>
  );
}

function NavLink({
  href,
  children,
  external,
}: {
  href: string;
  children: React.ReactNode;
  external: boolean;
}) {
  const style: React.CSSProperties = {
    color: 'rgba(255,255,255,0.45)',
    fontSize: '0.875rem',
    fontWeight: 400,
    textDecoration: 'none',
    fontFamily: '"Inter", sans-serif',
    transition: 'color 0.2s',
    cursor: 'pointer',
  };

  const handleOver = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.currentTarget.style.color = '#fff';
  };
  const handleOut = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.currentTarget.style.color = 'rgba(255,255,255,0.45)';
  };

  if (external) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        style={style}
        onMouseOver={handleOver}
        onMouseOut={handleOut}
      >
        {children}
      </a>
    );
  }
  return (
    <a href={href} style={style} onMouseOver={handleOver} onMouseOut={handleOut}>
      {children}
    </a>
  );
}
