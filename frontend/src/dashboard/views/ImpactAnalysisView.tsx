import React, { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ShieldAlert, Info, ArrowLeft, Zap } from 'lucide-react';
import { getErrorMessage, getImpactAnalysis, type ImpactAnalysisResponse } from '../../api';

// ── Blast Radius Ring ─────────────────────────────────────────────────────

function BlastRadiusRing({ score }: { score: number }) {
  const pct = Math.min(Math.max(score, 0), 1);
  const RADIUS = 60;
  const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
  const offset = CIRCUMFERENCE * (1 - pct);
  const color = pct > 0.5 ? '#ef4444' : pct > 0.2 ? '#f59e0b' : '#4ade80';
  const label  = pct > 0.5 ? 'Critical' : pct > 0.2 ? 'Moderate' : 'Low';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
      <div style={{ position: 'relative', width: '160px', height: '160px' }}>
        <svg width="160" height="160" style={{ transform: 'rotate(-90deg)' }}>
          {/* Track */}
          <circle
            cx="80" cy="80" r={RADIUS}
            fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="10"
          />
          {/* Progress */}
          <circle
            cx="80" cy="80" r={RADIUS}
            fill="none" stroke={color} strokeWidth="10"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 1s ease, stroke 0.3s ease' }}
          />
        </svg>
        {/* Center label */}
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
        }}>
          <span style={{ fontSize: '1.6rem', fontWeight: 300, color, lineHeight: 1 }}>
            {(pct * 100).toFixed(0)}
            <span style={{ fontSize: '1rem', color: 'rgba(255,255,255,0.4)' }}>%</span>
          </span>
          <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.07em', marginTop: '0.15rem' }}>
            {label}
          </span>
        </div>
      </div>

      {/* Risk bar */}
      <div style={{ width: '160px' }}>
        <div style={{ height: '4px', borderRadius: '2px', background: 'rgba(255,255,255,0.07)', overflow: 'hidden' }}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${pct * 100}%` }}
            transition={{ duration: 1, ease: 'easeOut' }}
            style={{ height: '100%', background: color, borderRadius: '2px' }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem' }}>
          <span style={{ fontSize: '0.6rem', color: '#4ade80' }}>Low</span>
          <span style={{ fontSize: '0.6rem', color: '#f59e0b' }}>Moderate</span>
          <span style={{ fontSize: '0.6rem', color: '#ef4444' }}>Critical</span>
        </div>
      </div>
    </div>
  );
}

// ── Symbol badge ──────────────────────────────────────────────────────────

function symbolBadgeClass(type: string): string {
  const t = type.toLowerCase();
  if (['class', 'class_def'].includes(t))              return 'class';
  if (['function', 'function_def', 'def'].includes(t)) return 'function';
  if (['method'].includes(t))                          return 'method';
  if (['module', 'file'].includes(t))                  return 'module';
  if (['import', 'import_from'].includes(t))           return 'import';
  return 'default';
}

// ── Main Component ────────────────────────────────────────────────────────

export function ImpactAnalysisView() {
  const [searchParams] = useSearchParams();
  const snapshotId = searchParams.get('snapshot_id');
  const nodeId     = searchParams.get('node_id');

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [result, setResult]       = useState<ImpactAnalysisResponse | null>(null);

  const fetchImpact = useCallback(async (snapId: string, nId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getImpactAnalysis(snapId, nId);
      setResult(data);
    } catch (err: unknown) {
      console.error('Failed to fetch impact analysis', err);
      setError(getErrorMessage(err, 'Failed to calculate blast radius.'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (snapshotId && nodeId) fetchImpact(snapshotId, nodeId);
  }, [snapshotId, nodeId, fetchImpact]);

  // ── No target ────────────────────────────────────────────────────────────
  if (!snapshotId || !nodeId) {
    return (
      <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '5rem 2rem', textAlign: 'center' }}>
        <ShieldAlert size={48} style={{ color: 'rgba(255,255,255,0.15)', display: 'block', margin: '0 auto 1.5rem' }} />
        <h2 style={{ color: '#fff', fontWeight: 400, margin: '0 0 0.75rem' }}>No Target Selected</h2>
        <p style={{ color: 'rgba(255,255,255,0.45)', maxWidth: '360px', margin: '0 auto 2rem', fontSize: '0.9rem', lineHeight: 1.6 }}>
          Impact analysis requires a specific symbol node. Use Graph Search to find a symbol, then click "Analyze Impact".
        </p>
        <Link
          to="/dashboard/search"
          style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
            padding: '0.75rem 1.5rem',
            backgroundColor: '#fff', color: '#000',
            borderRadius: '6px', textDecoration: 'none', fontWeight: 600, fontSize: '0.9rem',
          }}
        >
          <ArrowLeft size={16} /> Go to Graph Search
        </Link>
      </div>
    );
  }

  const displayNodeName = decodeURIComponent(nodeId).split('::').slice(-2, -1)[0] || decodeURIComponent(nodeId);

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '2rem 0' }}>
      {/* Header */}
      <header style={{ marginBottom: '2.5rem' }}>
        <Link
          to="/dashboard/search"
          style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
            color: 'rgba(255,255,255,0.35)',
            textDecoration: 'none', fontSize: '0.82rem',
            marginBottom: '1rem',
            transition: 'color 0.15s',
          }}
          onMouseEnter={e => e.currentTarget.style.color = 'rgba(255,255,255,0.7)'}
          onMouseLeave={e => e.currentTarget.style.color = 'rgba(255,255,255,0.35)'}
        >
          <ArrowLeft size={13} /> Back to Graph Search
        </Link>
        <h1 className="dash-page-title">Impact Analysis</h1>
        <p style={{ color: 'rgba(255,255,255,0.4)', margin: '0.4rem 0 0', fontSize: '0.85rem', fontFamily: 'ui-monospace, monospace' }}>
          <Zap size={12} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '0.3rem', color: 'rgba(255,255,255,0.3)' }} />
          {displayNodeName}
        </p>
      </header>

      {/* Loading */}
      {isLoading && (
        <div style={{ textAlign: 'center', padding: '5rem 2rem', color: 'rgba(255,255,255,0.4)' }}>
          <div style={{
            width: '40px', height: '40px', borderRadius: '50%',
            border: '2px solid rgba(255,255,255,0.08)',
            borderTopColor: '#6ee7c0',
            animation: 'spin 0.9s linear infinite',
            margin: '0 auto 1.25rem',
          }} />
          Traversing dependency graph and calculating blast radius…
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <div style={{
          padding: '1.25rem 1.5rem',
          backgroundColor: 'rgba(255,50,50,0.08)',
          border: '1px solid rgba(248,113,113,0.25)',
          borderRadius: '8px', marginBottom: '2rem',
        }}>
          <h3 style={{ margin: '0 0 0.4rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#f87171', fontSize: '0.95rem' }}>
            <ShieldAlert size={16} /> Analysis Failed
          </h3>
          <p style={{ margin: 0, fontSize: '0.875rem', color: 'rgba(255,255,255,0.5)' }}>{error}</p>
        </div>
      )}

      {/* Results */}
      {!isLoading && !error && result && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: '2rem', alignItems: 'start' }}
        >
          {/* ── Left: Metrics Panel ─────────────────────────────── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>

            {/* Blast radius ring */}
            <div className="dash-card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '0.72rem', color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Blast Radius
              </h3>
              <BlastRadiusRing score={result.blast_radius_score} />
              <p style={{ margin: 0, fontSize: '0.78rem', color: 'rgba(255,255,255,0.35)', lineHeight: 1.5, textAlign: 'center' }}>
                % of graph nodes that depend on this symbol
              </p>
            </div>

            {/* Impacted count */}
            <div className="dash-card" style={{ padding: '1.25rem', textAlign: 'center' }}>
              <h3 style={{ margin: '0 0 0.5rem', fontSize: '0.72rem', color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Impacted Nodes
              </h3>
              <div style={{ fontSize: '2.5rem', fontWeight: 200, color: '#fff', lineHeight: 1 }}>
                {result.impacted_nodes.length}
              </div>
              <p style={{ margin: '0.4rem 0 0', fontSize: '0.75rem', color: 'rgba(255,255,255,0.3)' }}>
                symbols & modules affected
              </p>
            </div>

            {/* Risk interpretation */}
            <div className="dash-card" style={{ padding: '1.25rem' }}>
              <h3 style={{ margin: '0 0 0.75rem', fontSize: '0.72rem', color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Risk Level
              </h3>
              <div style={{
                padding: '0.5rem 0.875rem', borderRadius: '6px', textAlign: 'center',
                backgroundColor:
                  result.blast_radius_score > 0.5 ? 'rgba(239,68,68,0.12)' :
                  result.blast_radius_score > 0.2 ? 'rgba(245,158,11,0.12)' : 'rgba(74,222,128,0.1)',
                color:
                  result.blast_radius_score > 0.5 ? '#ef4444' :
                  result.blast_radius_score > 0.2 ? '#f59e0b' : '#4ade80',
                fontSize: '0.85rem', fontWeight: 600,
                border: `1px solid ${result.blast_radius_score > 0.5 ? 'rgba(239,68,68,0.2)' : result.blast_radius_score > 0.2 ? 'rgba(245,158,11,0.2)' : 'rgba(74,222,128,0.15)'}`,
              }}>
                {result.blast_radius_score > 0.5 ? '⚠ High Risk' :
                 result.blast_radius_score > 0.2 ? '◆ Moderate Risk' : '✓ Low Risk'}
              </div>
              <p style={{ margin: '0.75rem 0 0', fontSize: '0.76rem', color: 'rgba(255,255,255,0.35)', lineHeight: 1.5 }}>
                {result.blast_radius_score > 0.5
                  ? 'Requires architecture review and staged rollout.'
                  : result.blast_radius_score > 0.2
                    ? 'Careful testing of dependent modules advised.'
                    : 'Change can be made with low downstream risk.'}
              </p>
            </div>
          </div>

          {/* ── Right: Impacted Nodes List ───────────────────────── */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <h2 style={{ fontSize: '1rem', fontWeight: 500, color: '#fff', margin: 0 }}>
                Affected Symbols
              </h2>
              <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.3)' }}>
                {result.impacted_nodes.length} node{result.impacted_nodes.length !== 1 ? 's' : ''}
              </span>
            </div>

            {result.impacted_nodes.length === 0 ? (
              <div style={{
                padding: '4rem 2rem', textAlign: 'center',
                backgroundColor: 'rgba(255,255,255,0.02)',
                borderRadius: '10px', border: '1px dashed rgba(255,255,255,0.06)',
              }}>
                <Info size={32} style={{ color: 'rgba(255,255,255,0.15)', display: 'block', margin: '0 auto 1rem' }} />
                <p style={{ color: 'rgba(255,255,255,0.5)', margin: 0, fontSize: '0.9rem' }}>
                  No dependent nodes found. This symbol is isolated.
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                {result.impacted_nodes.map((node, idx) => (
                  <motion.div
                    key={node.id}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.03 }}
                    className="dash-card"
                    style={{
                      display: 'flex', alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '0.75rem 1rem',
                      gap: '1rem',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', overflow: 'hidden', flex: 1 }}>
                      <span className={`symbol-badge ${symbolBadgeClass(node.symbol_type)}`}>
                        {node.symbol_type.replace('_def', '').replace('_', ' ')}
                      </span>
                      <div style={{ overflow: 'hidden' }}>
                        <div style={{
                          color: '#fff', fontWeight: 500, fontSize: '0.875rem',
                          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                        }}>
                          {node.symbol_name}
                        </div>
                        <div style={{
                          fontSize: '0.72rem', color: 'rgba(255,255,255,0.3)',
                          fontFamily: 'ui-monospace, monospace',
                          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                        }}>
                          {node.file_path}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
}
