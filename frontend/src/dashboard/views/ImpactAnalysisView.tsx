import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ShieldAlert, Info, ArrowLeft } from 'lucide-react';
import { getErrorMessage, getImpactAnalysis, type ImpactAnalysisResponse } from '../../api';

export function ImpactAnalysisView() {
  const [searchParams] = useSearchParams();
  const snapshotId = searchParams.get('snapshot_id');
  const nodeId = searchParams.get('node_id');
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImpactAnalysisResponse | null>(null);

  useEffect(() => {
    if (snapshotId && nodeId) {
      fetchImpact(snapshotId, nodeId);
    }
  }, [snapshotId, nodeId]);

  const fetchImpact = async (snapId: string, nId: string) => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await getImpactAnalysis(snapId, nId);
      setResult(data);
    } catch (err: unknown) {
      console.error('Failed to fetch impact analysis', err);
      setError(getErrorMessage(err, 'Failed to calculate blast radius.'));
    } finally {
      setIsLoading(false);
    }
  };

  if (!snapshotId || !nodeId) {
    return (
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '4rem 2rem', textAlign: 'center' }}>
        <ShieldAlert size={48} style={{ color: 'rgba(255,255,255,0.2)', margin: '0 auto 1rem auto' }} />
        <h2 style={{ color: '#fff', fontWeight: 400 }}>No Target Selected</h2>
        <p style={{ color: 'rgba(255,255,255,0.5)', maxWidth: '400px', margin: '1rem auto 2rem auto' }}>
          Impact analysis requires a specific node to analyze. Please navigate to the Graph Search to find and analyze a symbol.
        </p>
        <Link to="/dashboard/search" style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.75rem 1.5rem',
          backgroundColor: '#fff',
          color: '#000',
          borderRadius: '4px',
          textDecoration: 'none',
          fontWeight: 600
        }}>
          <ArrowLeft size={16} /> Go to Graph Search
        </Link>
      </div>
    );
  }

  const displayNodeName = nodeId.split('::').slice(-2, -1)[0] || nodeId;

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem 0' }}>
      <header style={{ marginBottom: '3rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div>
          <Link to="/dashboard/search" style={{ color: 'rgba(255,255,255,0.4)', textDecoration: 'none', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <ArrowLeft size={14} /> Back to Search
          </Link>
        </div>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 300, margin: 0, letterSpacing: '-0.02em', color: '#fff' }}>Impact Analysis</h1>
          <p style={{ color: 'rgba(255,255,255,0.5)', margin: '0.5rem 0 0 0', fontSize: '0.9rem', fontFamily: 'monospace' }}>
            Target: {displayNodeName}
          </p>
        </div>
      </header>

      {isLoading && (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>
          <div style={{ 
            width: '40px', height: '40px', borderRadius: '50%', 
            border: '2px solid rgba(255,255,255,0.1)', 
            borderTopColor: '#fff', 
            animation: 'spin 1s linear infinite', 
            margin: '0 auto 1rem auto' 
          }} />
          Calculating blast radius and traversing dependency graph...
        </div>
      )}

      {error && (
        <div style={{ padding: '1.5rem', backgroundColor: 'rgba(255, 50, 50, 0.1)', border: '1px solid rgba(255, 50, 50, 0.2)', color: '#ff6b6b', borderRadius: '8px', marginBottom: '2rem' }}>
          <h3 style={{ margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldAlert size={18} /> Error
          </h3>
          <p style={{ margin: 0, fontSize: '0.9rem' }}>{error}</p>
        </div>
      )}

      {!isLoading && !error && result && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2.5fr', gap: '2rem' }}>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div style={{ 
              backgroundColor: 'rgba(20, 20, 20, 0.6)', 
              border: '1px solid rgba(255,255,255,0.05)', 
              borderRadius: '8px', 
              padding: '1.5rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem'
            }}>
              <h3 style={{ margin: 0, fontSize: '0.9rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Blast Radius Score
              </h3>
              <div style={{ fontSize: '3rem', fontWeight: 300, color: result.blast_radius_score > 0.5 ? '#ef4444' : result.blast_radius_score > 0.2 ? '#f59e0b' : '#4ade80' }}>
                {(result.blast_radius_score * 100).toFixed(1)}%
              </div>
              <p style={{ margin: 0, fontSize: '0.85rem', color: 'rgba(255,255,255,0.4)', lineHeight: 1.5 }}>
                Percentage of graph nodes that depend on this symbol. Higher values indicate greater change risk.
              </p>
            </div>

            <div style={{ 
              backgroundColor: 'rgba(20, 20, 20, 0.6)', 
              border: '1px solid rgba(255,255,255,0.05)', 
              borderRadius: '8px', 
              padding: '1.5rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem'
            }}>
              <h3 style={{ margin: 0, fontSize: '0.9rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Impacted Nodes
              </h3>
              <div style={{ fontSize: '2rem', fontWeight: 300, color: '#fff' }}>
                {result.impacted_nodes.length}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 400, color: '#fff', margin: '0 0 0.5rem 0' }}>Detailed Impact</h2>
            
            {result.impacted_nodes.length === 0 ? (
              <div style={{ padding: '3rem', textAlign: 'center', backgroundColor: 'rgba(20, 20, 20, 0.6)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                <Info size={32} style={{ color: 'rgba(255,255,255,0.2)', margin: '0 auto 1rem auto' }} />
                <p style={{ color: 'rgba(255,255,255,0.6)', margin: 0 }}>No dependent nodes found. This symbol appears to be isolated.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {result.impacted_nodes.map(node => (
                  <div key={node.id} style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '1rem',
                    backgroundColor: 'rgba(20, 20, 20, 0.6)',
                    border: '1px solid rgba(255,255,255,0.05)',
                    borderRadius: '8px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                      <div style={{ 
                        padding: '0.25rem 0.5rem', 
                        backgroundColor: 'rgba(255,255,255,0.1)', 
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        fontWeight: 'bold',
                        color: 'rgba(255,255,255,0.8)'
                      }}>
                        {node.symbol_type}
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span style={{ color: '#fff', fontWeight: 500 }}>{node.symbol_name}</span>
                        <span style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>{node.file_path}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      )}
      
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
