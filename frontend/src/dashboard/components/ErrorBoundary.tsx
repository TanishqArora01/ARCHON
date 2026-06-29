import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface State { hasError: boolean; error: Error | null; }

export class ErrorBoundary extends React.Component<React.PropsWithChildren, State> {
  constructor(props: React.PropsWithChildren) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[Archon ErrorBoundary]', error, info.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        minHeight: '50vh', padding: '3rem', textAlign: 'center',
        color: '#fff',
      }}>
        <div style={{
          width: '64px', height: '64px', borderRadius: '16px',
          backgroundColor: 'rgba(248,113,113,0.1)',
          border: '1px solid rgba(248,113,113,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginBottom: '1.5rem',
        }}>
          <AlertTriangle size={28} color="#f87171" />
        </div>

        <h2 style={{ margin: '0 0 0.5rem', fontWeight: 400, fontSize: '1.25rem' }}>
          Something went wrong
        </h2>
        <p style={{ margin: '0 0 0.5rem', color: 'rgba(255,255,255,0.5)', maxWidth: '380px', lineHeight: 1.6, fontSize: '0.9rem' }}>
          An unexpected error occurred in this view. The error has been logged.
        </p>
        {this.state.error && (
          <code style={{
            display: 'block',
            margin: '0.75rem 0 1.5rem',
            padding: '0.75rem 1rem',
            backgroundColor: 'rgba(248,113,113,0.07)',
            border: '1px solid rgba(248,113,113,0.15)',
            borderRadius: '6px',
            color: '#f87171', fontSize: '0.75rem',
            maxWidth: '500px', wordBreak: 'break-word',
            fontFamily: 'ui-monospace, monospace',
            textAlign: 'left',
          }}>
            {this.state.error.message}
          </code>
        )}
        <button
          onClick={() => this.setState({ hasError: false, error: null })}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
            padding: '0.65rem 1.25rem',
            backgroundColor: 'rgba(255,255,255,0.08)',
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: '6px', color: '#fff',
            fontSize: '0.875rem', fontWeight: 500, cursor: 'pointer',
          }}
        >
          <RefreshCw size={14} /> Try again
        </button>
      </div>
    );
  }
}
