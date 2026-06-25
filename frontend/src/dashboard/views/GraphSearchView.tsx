import React, { useCallback, useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Search, Activity, GitCommit } from 'lucide-react';
import { getErrorMessage, listRepositories, searchGraph, type Repository, type SymbolNodeRead } from '../../api';

export function GraphSearchView() {
  const [searchParams] = useSearchParams();
  const initialRepoId = searchParams.get('repo_id');

  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState<SymbolNodeRead[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  useEffect(() => {
    listRepositories().then(data => {
      setRepos(data);
      if (initialRepoId && data.some(r => r.id === initialRepoId)) {
        setSelectedRepoId(initialRepoId);
      } else if (data.length > 0) {
        setSelectedRepoId(data[0].id);
      }
    }).catch(err => {
      console.error('Failed to fetch repos', err);
    });
  }, [initialRepoId]);

  const runSearch = useCallback(async (repoId: string, query: string) => {
    if (!repoId) return;

    try {
      setIsSearching(true);
      setError(null);
      const data = await searchGraph(repoId, query);
      setResults(data);
      setHasSearched(true);
    } catch (err: unknown) {
      console.error('Search failed', err);
      setError(getErrorMessage(err, 'An error occurred during search'));
      setResults([]);
      setHasSearched(true);
    } finally {
      setIsSearching(false);
    }
  }, []);

  useEffect(() => {
    if (selectedRepoId) {
      runSearch(selectedRepoId, searchQuery);
    }
  }, [selectedRepoId, runSearch]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRepoId) return;
    await runSearch(selectedRepoId, searchQuery);
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem 0' }}>
      <header style={{ marginBottom: '3rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 300, margin: 0, letterSpacing: '-0.02em', color: '#fff' }}>Graph Search</h1>
        <p style={{ color: 'rgba(255,255,255,0.5)', margin: '0.5rem 0 0 0', fontSize: '0.9rem' }}>
          Search the parsed knowledge graph for symbols, files, and architectural elements.
        </p>
      </header>

      <form onSubmit={handleSearch} style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
        <select 
          value={selectedRepoId}
          onChange={(e) => setSelectedRepoId(e.target.value)}
          style={{
            padding: '0.75rem 1rem',
            backgroundColor: 'rgba(20, 20, 20, 0.6)',
            color: '#fff',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '4px',
            minWidth: '200px'
          }}
        >
          {repos.length === 0 && <option value="">No repositories available</option>}
          {repos.map(repo => (
            <option key={repo.id} value={repo.id}>{repo.name} ({repo.owner})</option>
          ))}
        </select>

        <div style={{ position: 'relative', flexGrow: 1 }}>
          <Search size={18} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'rgba(255,255,255,0.4)' }} />
          <input 
            type="text" 
            placeholder="Search symbols, functions, or file paths..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '0.75rem 1rem 0.75rem 3rem',
              backgroundColor: 'rgba(20, 20, 20, 0.6)',
              color: '#fff',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '4px',
              outline: 'none'
            }}
          />
        </div>

        <button type="submit" disabled={isSearching || !selectedRepoId} style={{
          padding: '0.75rem 1.5rem',
          backgroundColor: '#fff',
          color: '#000',
          border: 'none',
          borderRadius: '4px',
          fontWeight: 600,
          cursor: (isSearching || !selectedRepoId) ? 'not-allowed' : 'pointer',
          opacity: (isSearching || !selectedRepoId) ? 0.5 : 1
        }}>
          {isSearching ? 'Searching...' : 'Search'}
        </button>
      </form>

      {error && (
        <div style={{ padding: '1rem', backgroundColor: 'rgba(255, 50, 50, 0.1)', color: '#ff6b6b', borderRadius: '4px', marginBottom: '2rem' }}>
          {error}
          {error.includes('No snapshots') && (
            <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.85rem' }}>
              Connect a repository and wait for analysis to complete, or trigger analysis from the Repositories page.
            </p>
          )}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {results.length === 0 && !isSearching && hasSearched && !error && (
          <div style={{ padding: '4rem 2rem', textAlign: 'center', color: 'rgba(255,255,255,0.5)', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px dashed rgba(255,255,255,0.1)' }}>
            <Activity size={48} style={{ opacity: 0.2, margin: '0 auto 1rem auto' }} />
            <p style={{ margin: 0, fontSize: '0.9rem' }}>No symbols matched your query.</p>
          </div>
        )}

        {results.length === 0 && !isSearching && !hasSearched && (
          <div style={{ padding: '4rem 2rem', textAlign: 'center', color: 'rgba(255,255,255,0.5)', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px dashed rgba(255,255,255,0.1)' }}>
            <Activity size={48} style={{ opacity: 0.2, margin: '0 auto 1rem auto' }} />
            <p style={{ margin: 0, fontSize: '0.9rem' }}>Select a repository to explore its knowledge graph.</p>
          </div>
        )}

        {results.map(node => (
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
            <Link 
              to={`/dashboard/impact?snapshot_id=${node.snapshot_id}&node_id=${encodeURIComponent(node.id)}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem 1rem',
                backgroundColor: 'rgba(74, 222, 128, 0.1)',
                color: '#4ade80',
                textDecoration: 'none',
                borderRadius: '4px',
                fontSize: '0.85rem',
                fontWeight: 500
              }}
            >
              <GitCommit size={14} />
              Analyze Impact
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
