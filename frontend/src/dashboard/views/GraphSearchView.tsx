import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Search, Zap, GitCommit, AlertCircle } from 'lucide-react';
import {
  getErrorMessage,
  listRepositories,
  searchGraph,
  type Repository,
  type SymbolNodeRead,
} from '../../api';

// ── Helpers ───────────────────────────────────────────────────────────────

function symbolBadgeClass(type: string): string {
  const t = type.toLowerCase();
  if (['class', 'class_def'].includes(t))             return 'class';
  if (['function', 'function_def', 'def'].includes(t)) return 'function';
  if (['method'].includes(t))                          return 'method';
  if (['module', 'file'].includes(t))                  return 'module';
  if (['import', 'import_from'].includes(t))           return 'import';
  if (['variable', 'assignment'].includes(t))          return 'variable';
  if (['database'].includes(t))                        return 'database';
  if (['api', 'endpoint'].includes(t))                 return 'api';
  return 'default';
}

function SkeletonRow() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '1rem',
      padding: '1rem', borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.04)',
    }}>
      <div className="skeleton" style={{ width: '52px', height: '22px', borderRadius: '4px' }} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        <div className="skeleton" style={{ width: '40%', height: '14px' }} />
        <div className="skeleton" style={{ width: '65%', height: '11px' }} />
      </div>
      <div className="skeleton" style={{ width: '110px', height: '30px', borderRadius: '4px' }} />
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────

export function GraphSearchView() {
  const [searchParams] = useSearchParams();
  const initialRepoId = searchParams.get('repo_id');

  const [repos, setRepos]               = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>('');
  const [searchQuery, setSearchQuery]   = useState('');
  const [results, setResults]           = useState<SymbolNodeRead[]>([]);
  const [isSearching, setIsSearching]   = useState(false);
  const [isLoadingRepos, setIsLoadingRepos] = useState(true);
  const [error, setError]               = useState<string | null>(null);
  const [hasSearched, setHasSearched]   = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load repositories
  useEffect(() => {
    setIsLoadingRepos(true);
    listRepositories()
      .then(data => {
        setRepos(data);
        const target = initialRepoId && data.some(r => r.id === initialRepoId)
          ? initialRepoId
          : data[0]?.id ?? '';
        setSelectedRepoId(target);
      })
      .catch(err => console.error('Failed to fetch repos', err))
      .finally(() => setIsLoadingRepos(false));
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
      setError(getErrorMessage(err, 'An error occurred during search'));
      setResults([]);
      setHasSearched(true);
    } finally {
      setIsSearching(false);
    }
  }, []);

  // Auto-search when repo changes
  useEffect(() => {
    if (selectedRepoId) runSearch(selectedRepoId, searchQuery);
  }, [selectedRepoId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounced live search as user types
  const handleQueryChange = (q: string) => {
    setSearchQuery(q);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (selectedRepoId) runSearch(selectedRepoId, q);
    }, 350);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (selectedRepoId) runSearch(selectedRepoId, searchQuery);
  };

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '2rem 0' }}>
      {/* Header */}
      <header style={{ marginBottom: '2.5rem' }}>
        <h1 className="dash-page-title">Graph Search</h1>
        <p className="dash-page-subtitle">
          Explore the knowledge graph — symbols, functions, classes, and architectural elements.
        </p>
      </header>

      {/* Search Form */}
      <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        {/* Repository Selector */}
        <select
          value={selectedRepoId}
          onChange={(e) => setSelectedRepoId(e.target.value)}
          disabled={isLoadingRepos}
          style={{
            padding: '0.7rem 0.875rem',
            backgroundColor: 'rgba(20,20,20,0.7)',
            color: isLoadingRepos ? 'rgba(255,255,255,0.3)' : '#fff',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '6px',
            minWidth: '210px',
            fontSize: '0.875rem',
            cursor: isLoadingRepos ? 'wait' : 'default',
          }}
        >
          {isLoadingRepos
            ? <option value="">Loading repositories...</option>
            : repos.length === 0
              ? <option value="">No repositories connected</option>
              : repos.map(repo => (
                  <option key={repo.id} value={repo.id}>
                    {repo.owner}/{repo.name}
                  </option>
                ))
          }
        </select>

        {/* Search Input */}
        <div style={{ position: 'relative', flex: 1, minWidth: '220px' }}>
          <Search
            size={16}
            style={{
              position: 'absolute', left: '0.875rem', top: '50%',
              transform: 'translateY(-50%)',
              color: 'rgba(255,255,255,0.35)',
              pointerEvents: 'none',
            }}
          />
          <input
            type="text"
            placeholder="Search symbols, functions, file paths…"
            value={searchQuery}
            onChange={(e) => handleQueryChange(e.target.value)}
            disabled={!selectedRepoId}
            style={{
              width: '100%',
              padding: '0.7rem 1rem 0.7rem 2.5rem',
              backgroundColor: 'rgba(20,20,20,0.7)',
              color: '#fff',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '6px',
              outline: 'none',
              fontSize: '0.875rem',
              transition: 'border-color 0.15s ease',
            }}
            onFocus={e => e.currentTarget.style.borderColor = 'rgba(110,231,192,0.3)'}
            onBlur={e => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'}
          />
          {isSearching && (
            <div style={{
              position: 'absolute', right: '0.875rem', top: '50%',
              transform: 'translateY(-50%)',
              width: '14px', height: '14px', borderRadius: '50%',
              border: '2px solid rgba(255,255,255,0.1)',
              borderTopColor: '#6ee7c0',
              animation: 'spin 0.7s linear infinite',
            }} />
          )}
        </div>

        <button
          type="submit"
          disabled={isSearching || !selectedRepoId}
          style={{
            padding: '0.7rem 1.25rem',
            backgroundColor: selectedRepoId ? '#fff' : 'rgba(255,255,255,0.1)',
            color: selectedRepoId ? '#000' : 'rgba(255,255,255,0.3)',
            border: 'none',
            borderRadius: '6px',
            fontWeight: 600,
            fontSize: '0.875rem',
            cursor: (isSearching || !selectedRepoId) ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', gap: '0.4rem',
            transition: 'all 0.15s ease',
          }}
        >
          <Search size={14} /> Search
        </button>
      </form>

      {/* Stats bar */}
      {hasSearched && !error && results.length > 0 && (
        <div style={{
          fontSize: '0.78rem',
          color: 'rgba(255,255,255,0.35)',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}>
          <Zap size={12} color="rgba(110,231,192,0.5)" />
          {results.length} symbol{results.length !== 1 ? 's' : ''} found
          {searchQuery && <> matching <em style={{ color: 'rgba(255,255,255,0.5)' }}>"{searchQuery}"</em></>}
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{
          padding: '1rem 1.25rem',
          backgroundColor: 'rgba(255,50,50,0.08)',
          border: '1px solid rgba(255,80,80,0.2)',
          borderRadius: '8px',
          marginBottom: '1.5rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#f87171', fontWeight: 500, fontSize: '0.875rem' }}>
            <AlertCircle size={16} /> {error}
          </div>
          {error.includes('No snapshots') && (
            <p style={{ margin: 0, fontSize: '0.82rem', color: 'rgba(255,255,255,0.4)' }}>
              Connect a repository and trigger analysis from the{' '}
              <Link to="/dashboard/repositories" style={{ color: '#60a5fa' }}>Repositories</Link> page to build the knowledge graph.
            </p>
          )}
        </div>
      )}

      {/* Results List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {/* Skeleton loading state */}
        {isSearching && results.length === 0 && (
          Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)
        )}

        {/* No results — not yet searched */}
        {!isSearching && !hasSearched && !error && (
          <div style={{
            padding: '5rem 2rem', textAlign: 'center',
            color: 'rgba(255,255,255,0.3)',
            backgroundColor: 'rgba(255,255,255,0.02)',
            borderRadius: '12px',
            border: '1px dashed rgba(255,255,255,0.06)',
          }}>
            <Search size={40} style={{ opacity: 0.15, display: 'block', margin: '0 auto 1rem' }} />
            <p style={{ margin: 0, fontSize: '0.9rem' }}>
              Select a repository to explore its knowledge graph.
            </p>
          </div>
        )}

        {/* No results — searched but empty */}
        {!isSearching && hasSearched && !error && results.length === 0 && (
          <div style={{
            padding: '4rem 2rem', textAlign: 'center',
            color: 'rgba(255,255,255,0.35)',
            backgroundColor: 'rgba(255,255,255,0.02)',
            borderRadius: '12px',
            border: '1px dashed rgba(255,255,255,0.06)',
          }}>
            <Search size={36} style={{ opacity: 0.15, display: 'block', margin: '0 auto 1rem' }} />
            <p style={{ margin: 0, fontSize: '0.9rem' }}>No symbols matched your query.</p>
            {searchQuery && (
              <button
                onClick={() => handleQueryChange('')}
                style={{
                  marginTop: '0.75rem', padding: '0.4rem 0.875rem',
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '4px', color: 'rgba(255,255,255,0.5)',
                  fontSize: '0.8rem', cursor: 'pointer',
                }}
              >
                Clear filter
              </button>
            )}
          </div>
        )}

        {/* Results */}
        {results.map(node => (
          <div
            key={node.id}
            className="dash-card"
            style={{
              display: 'flex', alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0.875rem 1rem',
              animation: 'fade-slide-up 0.2s ease',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem', overflow: 'hidden', flex: 1 }}>
              <span className={`symbol-badge ${symbolBadgeClass(node.symbol_type)}`}>
                {node.symbol_type.replace('_def', '').replace('_', ' ')}
              </span>
              <div style={{ overflow: 'hidden' }}>
                <div style={{ color: '#fff', fontWeight: 500, fontSize: '0.9rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {node.symbol_name}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.35)', fontFamily: 'ui-monospace, monospace', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {node.file_path}
                </div>
              </div>
            </div>

            <Link
              to={`/dashboard/impact?snapshot_id=${node.snapshot_id}&node_id=${encodeURIComponent(node.id)}`}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.4rem',
                padding: '0.45rem 0.875rem',
                backgroundColor: 'rgba(52,211,153,0.1)',
                border: '1px solid rgba(52,211,153,0.2)',
                color: '#34d399',
                textDecoration: 'none',
                borderRadius: '5px',
                fontSize: '0.8rem',
                fontWeight: 500,
                flexShrink: 0,
                marginLeft: '1rem',
                transition: 'background 0.15s ease',
              }}
              onMouseEnter={e => e.currentTarget.style.backgroundColor = 'rgba(52,211,153,0.18)'}
              onMouseLeave={e => e.currentTarget.style.backgroundColor = 'rgba(52,211,153,0.1)'}
            >
              <GitCommit size={12} /> Analyze Impact
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
