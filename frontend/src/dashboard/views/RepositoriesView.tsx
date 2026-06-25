import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GitMerge, Code2, ArrowRight } from 'lucide-react';
import { listRepositories, triggerAnalysis, type Repository } from '../../api';
import { ConnectRepoModal } from '../components/ConnectRepoModal';

export function RepositoriesView() {
  const navigate = useNavigate();
  const [searchQuery] = useState('');
  const [repos, setRepos] = useState<Repository[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const [analyzingId, setAnalyzingId] = useState<string | null>(null);

  const fetchRepos = async () => {
    try {
      setIsLoading(true);
      const data = await listRepositories();
      setRepos(data);
    } catch (err) {
      console.error('Failed to fetch repos', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRepos();
  }, []);

  const filteredRepos = repos.filter(repo => 
    repo.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleAnalyze = async (e: React.MouseEvent, repoId: string) => {
    e.stopPropagation();
    try {
      setAnalyzingId(repoId);
      await triggerAnalysis(repoId);
    } catch (err) {
      console.error('Failed to trigger analysis', err);
    } finally {
      setAnalyzingId(null);
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem 0' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '3rem' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 300, margin: 0, letterSpacing: '-0.02em', color: '#fff' }}>Repositories</h1>
          <p style={{ color: 'rgba(255,255,255,0.5)', margin: '0.5rem 0 0 0', fontSize: '0.9rem' }}>
            Connect and analyze your engineering systems.
          </p>
        </div>
        <button style={{
          padding: '0.75rem 1.5rem',
          backgroundColor: '#fff',
          color: '#000',
          border: 'none',
          borderRadius: '4px',
          fontWeight: 600,
          fontSize: '0.9rem',
          cursor: 'pointer',
          transition: 'all 0.2s ease'
        }}
        onClick={() => setIsModalOpen(true)}
        >
          + Connect Repository
        </button>
      </header>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {isLoading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>Loading repositories...</div>
        ) : filteredRepos.length === 0 ? (
          <div style={{ padding: '4rem 2rem', textAlign: 'center', color: 'rgba(255,255,255,0.5)', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px dashed rgba(255,255,255,0.1)' }}>
            <Code2 size={48} style={{ opacity: 0.2, margin: '0 auto 1rem auto' }} />
            <h3 style={{ margin: '0 0 0.5rem 0', color: '#fff' }}>No repositories found</h3>
            <p style={{ margin: 0, fontSize: '0.9rem' }}>Connect a new repository to begin analysis.</p>
          </div>
        ) : (
          filteredRepos.map(repo => (
            <div key={repo.id} style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '1.5rem',
              backgroundColor: 'rgba(20, 20, 20, 0.6)',
              border: '1px solid rgba(255,255,255,0.05)',
              borderRadius: '8px',
              transition: 'all 0.2s ease',
              cursor: 'pointer'
            }}
            onClick={() => navigate(`/dashboard/search?repo_id=${repo.id}`)}
            onMouseOver={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(30, 30, 30, 0.8)';
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(20, 20, 20, 0.6)';
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.05)';
            }}
            >
              {/* Left side: Icon and Name */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', width: '30%' }}>
                <div style={{ 
                  width: '40px', 
                  height: '40px', 
                  borderRadius: '8px', 
                  backgroundColor: 'rgba(255,255,255,0.05)', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  color: 'rgba(255,255,255,0.8)'
                }}>
                  {repo.provider === 'github' ? <Code2 size={20} /> : <GitMerge size={20} />}
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 500, color: '#fff' }}>{repo.name}</h3>
                  <span style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {repo.provider}
                  </span>
                </div>
              </div>

              {/* Middle: Stats */}
              <div style={{ display: 'flex', gap: '3rem', width: '40%' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)' }}>OWNER</span>
                  <span style={{ fontSize: '1.1rem', color: '#fff', fontFamily: 'monospace' }}>{repo.owner}</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)' }}>BRANCH</span>
                  <span style={{ fontSize: '1.1rem', color: '#fff', fontFamily: 'monospace' }}>{repo.default_branch || 'main'}</span>
                </div>
              </div>

              {/* Right side: Status and Arrow */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '1rem', width: '25%' }}>
                <button
                  type="button"
                  onClick={(e) => handleAnalyze(e, repo.id)}
                  disabled={analyzingId === repo.id}
                  style={{
                    padding: '0.5rem 0.75rem',
                    backgroundColor: 'rgba(96, 165, 250, 0.15)',
                    color: '#60a5fa',
                    border: '1px solid rgba(96, 165, 250, 0.3)',
                    borderRadius: '4px',
                    fontSize: '0.8rem',
                    cursor: analyzingId === repo.id ? 'wait' : 'pointer',
                  }}
                >
                  {analyzingId === repo.id ? 'Analyzing...' : 'Analyze'}
                </button>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#4ade80' }} />
                  <span style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.6)' }}>Connected</span>
                </div>
                <ArrowRight size={20} color="rgba(255,255,255,0.3)" />
              </div>
            </div>
          ))
        )}
      </div>

      <ConnectRepoModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        onSuccess={fetchRepos}
      />
    </div>
  );
}
