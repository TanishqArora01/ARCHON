import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { GitBranch, ArrowRight, Search, Loader2, Plus, Zap, Activity } from 'lucide-react';
import {
  listRepositories, listAnalysisRuns, triggerAnalysis,
  type Repository, type AnalysisRun,
} from '../../api';
import { ConnectRepoModal } from '../components/ConnectRepoModal';

// ── Provider icon ─────────────────────────────────────────────────────────

function ProviderIcon({ provider }: { provider: string }) {
  // Generic GitBranch for GitLab / GitHub / other
  return <GitBranch size={18} />;
}

// ── Repository Status from run history ───────────────────────────────────

function RepoStatus({ latestRun }: { latestRun: AnalysisRun | undefined }) {
  if (!latestRun) {
    return (
      <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.78rem', color: 'rgba(255,255,255,0.35)' }}>
        <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'rgba(255,255,255,0.2)', display: 'inline-block' }} />
        Not analyzed
      </span>
    );
  }
  const colorMap: Record<string, string> = {
    completed: '#4ade80',
    running:   '#60a5fa',
    failed:    '#f87171',
    pending:   '#f59e0b',
    queued:    '#a78bfa',
  };
  const color = colorMap[latestRun.status] ?? 'rgba(255,255,255,0.3)';
  const isRunning = latestRun.status === 'running' || latestRun.status === 'pending';
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.78rem', color }}>
      <span style={{
        width: '6px', height: '6px', borderRadius: '50%', background: color, display: 'inline-block',
        animation: isRunning ? 'pulse-dot 1.4s ease-in-out infinite' : 'none',
      }} />
      {latestRun.status.charAt(0).toUpperCase() + latestRun.status.slice(1)}
    </span>
  );
}

// ── Main Component ────────────────────────────────────────────────────────

export function RepositoriesView() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [repos, setRepos]             = useState<Repository[]>([]);
  const [runs,  setRuns]              = useState<AnalysisRun[]>([]);
  const [isLoading, setIsLoading]     = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const [reposData, runsData] = await Promise.all([listRepositories(), listAnalysisRuns()]);
      setRepos(reposData);
      setRuns(runsData);
    } catch (err) {
      console.error('Failed to fetch repositories', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  // Latest run per repository
  const latestRunByRepo = useMemo(() => {
    const map: Record<string, AnalysisRun> = {};
    for (const run of runs) {
      if (!run.repository_id) continue;
      if (!map[run.repository_id] || new Date(run.created_at ?? 0) > new Date(map[run.repository_id].created_at ?? 0)) {
        map[run.repository_id] = run;
      }
    }
    return map;
  }, [runs]);

  const filteredRepos = useMemo(() =>
    repos.filter(r =>
      r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.owner.toLowerCase().includes(searchQuery.toLowerCase())
    ), [repos, searchQuery]);

  const handleAnalyze = async (e: React.MouseEvent, repoId: string) => {
    e.stopPropagation();
    try {
      setAnalyzingId(repoId);
      await triggerAnalysis(repoId);
      // Refresh after a short delay so the new run shows
      setTimeout(fetchData, 1500);
    } catch (err) {
      console.error('Failed to trigger analysis', err);
    } finally {
      setAnalyzingId(null);
    }
  };

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '2rem 0' }}>
      {/* Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
        <div>
          <h1 className="dash-page-title">Repositories</h1>
          <p className="dash-page-subtitle">
            Connect and analyze your engineering systems with the multi-agent pipeline.
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.5rem',
            padding: '0.65rem 1.2rem',
            backgroundColor: '#fff', color: '#000',
            border: 'none', borderRadius: '6px',
            fontWeight: 600, fontSize: '0.875rem',
            cursor: 'pointer', transition: 'opacity 0.15s',
            flexShrink: 0,
          }}
          onMouseEnter={e => e.currentTarget.style.opacity = '0.9'}
          onMouseLeave={e => e.currentTarget.style.opacity = '1'}
        >
          <Plus size={16} /> Connect Repository
        </button>
      </header>

      {/* Search input */}
      {repos.length > 0 && (
        <div style={{ position: 'relative', marginBottom: '1.5rem' }}>
          <Search
            size={15}
            style={{
              position: 'absolute', left: '0.875rem', top: '50%',
              transform: 'translateY(-50%)',
              color: 'rgba(255,255,255,0.3)', pointerEvents: 'none',
            }}
          />
          <input
            type="text"
            placeholder="Filter by repository name or owner…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '0.65rem 1rem 0.65rem 2.4rem',
              backgroundColor: 'rgba(20,20,20,0.7)',
              color: '#fff',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '6px',
              outline: 'none',
              fontSize: '0.875rem',
              boxSizing: 'border-box',
              transition: 'border-color 0.15s',
            }}
            onFocus={e => e.currentTarget.style.borderColor = 'rgba(110,231,192,0.3)'}
            onBlur={e => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'}
          />
        </div>
      )}

      {/* Repository List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: '80px', borderRadius: '8px' }} />
          ))
        ) : filteredRepos.length === 0 ? (
          <div style={{
            padding: '5rem 2rem', textAlign: 'center',
            color: 'rgba(255,255,255,0.35)',
            backgroundColor: 'rgba(255,255,255,0.02)',
            borderRadius: '12px', border: '1px dashed rgba(255,255,255,0.07)',
          }}>
            <GitBranch size={44} style={{ opacity: 0.12, display: 'block', margin: '0 auto 1.25rem' }} />
            <h3 style={{ margin: '0 0 0.5rem', color: '#fff', fontWeight: 400, fontSize: '1.1rem' }}>
              {searchQuery ? 'No repositories matched your filter' : 'No repositories connected'}
            </h3>
            <p style={{ margin: '0 0 1.5rem', fontSize: '0.875rem', lineHeight: 1.6 }}>
              {searchQuery
                ? 'Try a different search term.'
                : 'Connect a repository to begin symbol extraction and multi-agent analysis.'}
            </p>
            {!searchQuery && (
              <button
                onClick={() => setIsModalOpen(true)}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
                  padding: '0.65rem 1.25rem',
                  backgroundColor: '#fff', color: '#000',
                  border: 'none', borderRadius: '6px',
                  fontWeight: 600, fontSize: '0.875rem', cursor: 'pointer',
                }}
              >
                <Plus size={15} /> Connect Repository
              </button>
            )}
          </div>
        ) : (
          filteredRepos.map((repo, idx) => {
            const latestRun = latestRunByRepo[repo.id];
            const isAnalyzing = analyzingId === repo.id;

            return (
              <motion.div
                key={repo.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.04 }}
                className="dash-card"
                onClick={() => navigate(`/dashboard/search?repo_id=${repo.id}`)}
                style={{
                  display: 'flex', alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '1.1rem 1.25rem',
                  cursor: 'pointer',
                }}
              >
                {/* Left: icon + name */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flex: 1, overflow: 'hidden' }}>
                  <div style={{
                    width: '38px', height: '38px', borderRadius: '8px',
                    backgroundColor: 'rgba(255,255,255,0.06)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: 'rgba(255,255,255,0.65)',
                    flexShrink: 0,
                  }}>
                    <ProviderIcon provider={repo.provider} />
                  </div>
                  <div style={{ overflow: 'hidden' }}>
                    <h3 style={{
                      margin: 0, fontSize: '0.95rem', fontWeight: 500, color: '#fff',
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                    }}>
                      <span style={{ color: 'rgba(255,255,255,0.45)' }}>{repo.owner}/</span>
                      {repo.name}
                    </h3>
                    <div style={{ display: 'flex', gap: '1rem', marginTop: '0.2rem' }}>
                      <span style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        {repo.provider}
                      </span>
                      <span style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.3)', fontFamily: 'ui-monospace, monospace' }}>
                        {repo.default_branch || 'main'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Right: status + actions */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexShrink: 0, marginLeft: '1.5rem' }}>
                  <RepoStatus latestRun={latestRun} />

                  <button
                    type="button"
                    onClick={(e) => handleAnalyze(e, repo.id)}
                    disabled={isAnalyzing}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '0.4rem',
                      padding: '0.45rem 0.875rem',
                      backgroundColor: isAnalyzing ? 'rgba(255,255,255,0.05)' : 'rgba(96,165,250,0.1)',
                      color: isAnalyzing ? 'rgba(255,255,255,0.3)' : '#60a5fa',
                      border: `1px solid ${isAnalyzing ? 'rgba(255,255,255,0.08)' : 'rgba(96,165,250,0.25)'}`,
                      borderRadius: '5px', fontSize: '0.78rem', fontWeight: 500,
                      cursor: isAnalyzing ? 'wait' : 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    {isAnalyzing
                      ? <><Loader2 size={12} style={{ animation: 'spin 0.8s linear infinite' }} /> Queuing…</>
                      : <><Zap size={12} /> Analyze</>
                    }
                  </button>

                  <button
                    type="button"
                    onClick={e => { e.stopPropagation(); navigate(`/dashboard/analysis?repo=${repo.id}`); }}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '0.4rem',
                      padding: '0.45rem 0.875rem',
                      backgroundColor: 'rgba(52,211,153,0.08)',
                      color: '#34d399',
                      border: '1px solid rgba(52,211,153,0.2)',
                      borderRadius: '5px', fontSize: '0.78rem', fontWeight: 500,
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <Activity size={12} /> History
                  </button>

                  <ArrowRight size={16} color="rgba(255,255,255,0.2)" />
                </div>
              </motion.div>
            );
          })
        )}
      </div>

      {/* Count summary */}
      {!isLoading && filteredRepos.length > 0 && (
        <p style={{
          marginTop: '1rem', fontSize: '0.75rem',
          color: 'rgba(255,255,255,0.25)', textAlign: 'right',
        }}>
          {filteredRepos.length} {filteredRepos.length === 1 ? 'repository' : 'repositories'}
          {searchQuery && ` matching "${searchQuery}"`}
        </p>
      )}

      <ConnectRepoModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={fetchData}
      />
    </div>
  );
}
