import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Code2, GitMerge, RefreshCw, Lock, UploadCloud, ExternalLink, AlertCircle } from 'lucide-react';
import { createRepository, importProviderRepository, listProviderRepositories, getErrorMessage, ApiError, type ProviderRepository } from '../../api';

interface ConnectRepoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const API_BASE = import.meta.env.VITE_API_URL || 'https://archon-ixrh.onrender.com';

type ErrorState =
  | { kind: 'message'; text: string }
  | { kind: 'oauth'; provider: 'github' | 'gitlab' };


export function ConnectRepoModal({ isOpen, onClose, onSuccess }: ConnectRepoModalProps) {
  const [provider, setProvider] = useState<'github' | 'gitlab'>('github');
  const [owner, setOwner] = useState('');
  const [name, setName] = useState('');
  const [cloneUrl, setCloneUrl] = useState('');
  const [providerRepos, setProviderRepos] = useState<ProviderRepository[]>([]);
  const [isLoadingProviderRepos, setIsLoadingProviderRepos] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<ErrorState | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await createRepository({
        provider,
        owner,
        name,
        clone_url: cloneUrl,
      });
      onSuccess();
      onClose();
      // Reset state for next open
      setOwner('');
      setName('');
      setCloneUrl('');
    } catch (err: unknown) {
      setError({ kind: 'message', text: getErrorMessage(err, 'Failed to connect repository') });
    } finally {
      setIsSubmitting(false);
    }
  };

  const loadProviderRepos = async () => {
    setError(null);
    setIsLoadingProviderRepos(true);
    try {
      const repos = await listProviderRepositories(provider);
      setProviderRepos(repos);
    } catch (err: unknown) {
      setProviderRepos([]);
      // Detect OAuth-not-connected error (404 = no installation, 401 = not authenticated)
      if (err instanceof ApiError && (err.status === 404 || err.status === 401)) {
        setError({ kind: 'oauth', provider });
      } else {
        setError({ kind: 'message', text: getErrorMessage(err, `Failed to load ${provider} repositories`) });
      }
    } finally {
      setIsLoadingProviderRepos(false);
    }
  };

  const handleImport = async (repo: ProviderRepository) => {
    setError(null);
    setIsSubmitting(true);
    try {
      await importProviderRepository(repo);
      onSuccess();
      onClose();
      setProviderRepos([]);
    } catch (err: unknown) {
      setError({ kind: 'message', text: getErrorMessage(err, 'Failed to import repository') });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          backdropFilter: 'blur(10px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          fontFamily: '"Inter", sans-serif',
        }}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          style={{
            backgroundColor: '#111',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '12px',
            width: '100%',
            maxWidth: '500px',
            padding: '2rem',
            position: 'relative',
          }}
        >
          <button
            onClick={onClose}
            style={{
              position: 'absolute',
              top: '1.5rem',
              right: '1.5rem',
              background: 'none',
              border: 'none',
              color: 'rgba(255, 255, 255, 0.5)',
              cursor: 'pointer',
            }}
          >
            <X size={20} />
          </button>

          <h2 style={{ margin: '0 0 0.5rem 0', fontWeight: 500, fontSize: '1.25rem', color: '#fff' }}>
            Connect Repository
          </h2>
          <p style={{ margin: '0 0 2rem 0', color: 'rgba(255, 255, 255, 0.5)', fontSize: '0.9rem' }}>
            Add a repository to begin architectural analysis.
          </p>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            
            {/* Provider Selection */}
            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.7)', marginBottom: '0.5rem' }}>
                Provider
              </label>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button
                  type="button"
                  onClick={() => setProvider('github')}
                  style={{
                    flex: 1,
                    padding: '0.75rem',
                    backgroundColor: provider === 'github' ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
                    border: `1px solid ${provider === 'github' ? 'rgba(255, 255, 255, 0.3)' : 'rgba(255, 255, 255, 0.1)'}`,
                    borderRadius: '8px',
                    color: provider === 'github' ? '#fff' : 'rgba(255, 255, 255, 0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                >
                  <Code2 size={16} /> GitHub
                </button>
                <button
                  type="button"
                  onClick={() => setProvider('gitlab')}
                  style={{
                    flex: 1,
                    padding: '0.75rem',
                    backgroundColor: provider === 'gitlab' ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
                    border: `1px solid ${provider === 'gitlab' ? 'rgba(255, 255, 255, 0.3)' : 'rgba(255, 255, 255, 0.1)'}`,
                    borderRadius: '8px',
                    color: provider === 'gitlab' ? '#fff' : 'rgba(255, 255, 255, 0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                >
                  <GitMerge size={16} /> GitLab
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <button
                type="button"
                onClick={loadProviderRepos}
                disabled={isLoadingProviderRepos}
                style={{
                  padding: '0.75rem 1rem',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  cursor: isLoadingProviderRepos ? 'wait' : 'pointer',
                }}
              >
                <RefreshCw size={16} /> {isLoadingProviderRepos ? 'Loading repositories...' : `Load ${provider} repositories`}
              </button>

              {providerRepos.length > 0 && (
                <div style={{
                  maxHeight: '180px',
                  overflowY: 'auto',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                }}>
                  {providerRepos.map((repo) => (
                    <button
                      key={`${repo.provider}:${repo.owner}/${repo.name}`}
                      type="button"
                      onClick={() => handleImport(repo)}
                      disabled={isSubmitting}
                      style={{
                        width: '100%',
                        padding: '0.75rem',
                        backgroundColor: 'transparent',
                        border: 'none',
                        borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                        color: '#fff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: isSubmitting ? 'wait' : 'pointer',
                        textAlign: 'left',
                      }}
                    >
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        {repo.private ? <Lock size={14} /> : <UploadCloud size={14} />}
                        {repo.owner}/{repo.name}
                      </span>
                      <span style={{ color: 'rgba(255,255,255,0.45)', fontSize: '0.75rem' }}>
                        {repo.default_branch || 'default'}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div style={{ display: 'flex', gap: '1rem' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.7)', marginBottom: '0.5rem' }}>
                  Owner / Organization
                </label>
                <input
                  required
                  type="text"
                  value={owner}
                  onChange={(e) => setOwner(e.target.value)}
                  placeholder="e.g. tiangolo"
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '8px',
                    color: '#fff',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.7)', marginBottom: '0.5rem' }}>
                  Repository Name
                </label>
                <input
                  required
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. fastapi"
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '8px',
                    color: '#fff',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.7)', marginBottom: '0.5rem' }}>
                Clone URL
              </label>
              <input
                required
                type="url"
                value={cloneUrl}
                onChange={(e) => setCloneUrl(e.target.value)}
                placeholder="https://github.com/tiangolo/fastapi.git"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  color: '#fff',
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            {error && error.kind === 'oauth' && (
              <div style={{
                padding: '1rem',
                backgroundColor: 'rgba(96, 165, 250, 0.08)',
                border: '1px solid rgba(96, 165, 250, 0.2)',
                borderRadius: '8px',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.75rem',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#60a5fa', fontSize: '0.85rem' }}>
                  <AlertCircle size={15} />
                  Not connected to {error.provider === 'github' ? 'GitHub' : 'GitLab'} — you need to authorize access first.
                </div>
                <a
                  href={`${API_BASE}/api/v1/oauth/${error.provider}/start`}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.6rem 1rem',
                    backgroundColor: error.provider === 'github' ? 'rgba(255,255,255,0.1)' : 'rgba(252,109,38,0.15)',
                    border: `1px solid ${error.provider === 'github' ? 'rgba(255,255,255,0.2)' : 'rgba(252,109,38,0.3)'}`,
                    borderRadius: '6px',
                    color: '#fff',
                    textDecoration: 'none',
                    fontSize: '0.875rem',
                    fontWeight: 500,
                    alignSelf: 'flex-start',
                  }}
                >
                  <ExternalLink size={14} />
                  Connect with {error.provider === 'github' ? 'GitHub' : 'GitLab'}
                </a>
                <p style={{ margin: 0, fontSize: '0.78rem', color: 'rgba(255,255,255,0.4)' }}>
                  Or use the manual entry form below to connect any public repository without OAuth.
                </p>
              </div>
            )}
            {error && error.kind === 'message' && (
              <div style={{ padding: '0.75rem', backgroundColor: 'rgba(255, 0, 0, 0.1)', border: '1px solid rgba(255, 0, 0, 0.2)', borderRadius: '8px', color: '#ff6b6b', fontSize: '0.85rem' }}>
                {error.text}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
              <button
                type="button"
                onClick={onClose}
                style={{
                  padding: '0.75rem 1.5rem',
                  backgroundColor: 'transparent',
                  border: 'none',
                  color: 'rgba(255, 255, 255, 0.7)',
                  cursor: 'pointer',
                  fontWeight: 500,
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                style={{
                  padding: '0.75rem 1.5rem',
                  backgroundColor: '#fff',
                  color: '#000',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: isSubmitting ? 'not-allowed' : 'pointer',
                  fontWeight: 500,
                  opacity: isSubmitting ? 0.7 : 1,
                }}
              >
                {isSubmitting ? 'Connecting...' : 'Connect Repository'}
              </button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
