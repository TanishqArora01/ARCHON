import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Cpu, Zap, GitBranch, Wrench, TrendingUp, FlaskConical, CheckCircle, AlertCircle, Loader2, ExternalLink } from 'lucide-react';
import { checkAgentHealth, listRepositories, runAgents, type AgentHealthResponse, type Repository } from '../../api';

const AGENT_ICONS: Record<string, React.ReactNode> = {
  planner: <GitBranch size={20} />,
  architecture: <Cpu size={20} />,
  maintainability: <Wrench size={20} />,
  technical_debt: <TrendingUp size={20} />,
  impact: <Zap size={20} />,
  synthesis: <FlaskConical size={20} />,
};

const AGENT_COLORS: Record<string, string> = {
  planner: '#60a5fa',
  architecture: '#f59e0b',
  maintainability: '#4ade80',
  technical_debt: '#f87171',
  impact: '#a78bfa',
  synthesis: '#34d399',
};

const PROVIDER_BADGE_COLORS: Record<string, { bg: string; text: string }> = {
  nvidia: { bg: 'rgba(118, 185, 0, 0.15)', text: '#76b900' },
  ollama: { bg: 'rgba(255, 255, 255, 0.08)', text: 'rgba(255,255,255,0.7)' },
  mock: { bg: 'rgba(255,255,255,0.05)', text: 'rgba(255,255,255,0.4)' },
  deterministic: { bg: 'rgba(52, 211, 153, 0.1)', text: '#34d399' },
  openai: { bg: 'rgba(16, 185, 129, 0.15)', text: '#10b981' },
};

export function AgentsView() {
  const [health, setHealth] = useState<AgentHealthResponse | null>(null);
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [runMessage, setRunMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [healthData, reposData] = await Promise.all([checkAgentHealth(), listRepositories()]);
        setHealth(healthData);
        setRepos(reposData);
        if (reposData.length > 0) setSelectedRepoId(reposData[0].id);
      } catch (err) {
        setError('Failed to load agent status');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleRunAgents = async () => {
    if (!selectedRepoId) return;
    try {
      setIsRunning(true);
      setRunMessage(null);
      const result = await runAgents(selectedRepoId);
      setRunMessage({ text: result.message, type: 'success' });
    } catch (err) {
      setRunMessage({ text: err instanceof Error ? err.message : 'Failed to trigger agent run', type: 'error' });
    } finally {
      setIsRunning(false);
    }
  };

  const providerStyle = (p: string) => PROVIDER_BADGE_COLORS[p] || PROVIDER_BADGE_COLORS.mock;

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem 0' }}>
      <header style={{ marginBottom: '3rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 300, margin: 0, letterSpacing: '-0.02em', color: '#fff' }}>
          Agent System
        </h1>
        <p style={{ color: 'rgba(255,255,255,0.5)', margin: '0.5rem 0 0 0', fontSize: '0.9rem' }}>
          Multi-agent intelligence pipeline: Planner → Specialists → Synthesis
        </p>
      </header>

      {/* Provider Status Banner */}
      {!isLoading && health && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1rem 1.5rem',
            backgroundColor: 'rgba(20,20,20,0.6)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '8px',
            marginBottom: '2rem',
          }}
        >
          <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
              <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Active Provider</span>
              <span style={{ color: '#fff', fontWeight: 500, textTransform: 'capitalize' }}>{health.active_provider}</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
              <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>NVIDIA NIM</span>
              <span style={{ color: health.nvidia_configured && health.nvidia_reachable ? '#76b900' : health.nvidia_configured ? '#f59e0b' : 'rgba(255,255,255,0.4)', fontWeight: 500 }}>
                {!health.nvidia_configured ? '✗ Not configured' : health.nvidia_reachable ? '✓ Reachable' : '✗ Unreachable'}
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
              <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Ollama</span>
              <span style={{ color: health.ollama_reachable ? '#4ade80' : '#f87171', fontWeight: 500 }}>
                {health.ollama_reachable ? '✓ Running' : '✗ Unreachable'}
              </span>
            </div>
          </div>

          {!health.nvidia_configured && (
            <a
              href="https://build.nvidia.com"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem 1rem',
                backgroundColor: 'rgba(118, 185, 0, 0.1)',
                border: '1px solid rgba(118, 185, 0, 0.3)',
                borderRadius: '6px',
                color: '#76b900',
                textDecoration: 'none',
                fontSize: '0.85rem',
                fontWeight: 500,
              }}
            >
              <ExternalLink size={14} />
              Get NVIDIA API Key
            </a>
          )}
        </motion.div>
      )}

      {/* Pipeline Visualization */}
      <div style={{ marginBottom: '2.5rem' }}>
        <h2 style={{ fontSize: '0.78rem', fontWeight: 500, color: 'rgba(255,255,255,0.3)', marginBottom: '1.25rem', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
          Analysis Pipeline
        </h2>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', overflowX: 'auto', paddingBottom: '0.5rem' }}>
          {/* Planner */}
          <PipelineNode name="Planner" color="#60a5fa" icon={<GitBranch size={18} />} agents={health?.agents} />
          <Arrow />
          {/* Specialist cluster */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {['architecture', 'maintainability', 'technical_debt', 'impact'].map(name => (
              <PipelineNode key={name} name={name.replace('_', ' ')} color={AGENT_COLORS[name]} icon={AGENT_ICONS[name]} agents={health?.agents} compact />
            ))}
          </div>
          <Arrow />
          {/* Synthesis */}
          <PipelineNode name="Synthesis" color="#34d399" icon={<FlaskConical size={18} />} agents={health?.agents} />
        </div>
      </div>

      {/* Agent Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '1rem', marginBottom: '2.5rem' }}>
        {isLoading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} style={{ height: '160px', backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }} />
          ))
        ) : (
          (health?.agents || []).map((agent, idx) => (
            <motion.div
              key={agent.name}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.06 }}
              style={{
                backgroundColor: 'rgba(20,20,20,0.6)',
                border: `1px solid rgba(255,255,255,0.06)`,
                borderLeft: `3px solid ${AGENT_COLORS[agent.name] || '#fff'}`,
                borderRadius: '8px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.75rem',
              }}
            >
              {/* Header */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <div style={{
                    width: '36px', height: '36px', borderRadius: '8px',
                    backgroundColor: `${AGENT_COLORS[agent.name]}18`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: AGENT_COLORS[agent.name] || '#fff',
                  }}>
                    {AGENT_ICONS[agent.name] || <Cpu size={18} />}
                  </div>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 500, color: '#fff' }}>{agent.label}</h3>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '0.2rem' }}>
                      <StatusDot status={agent.status} />
                      <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)', textTransform: 'capitalize' }}>{agent.status}</span>
                    </div>
                  </div>
                </div>
                <span style={{
                  padding: '0.25rem 0.5rem',
                  borderRadius: '4px',
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                  backgroundColor: providerStyle(agent.provider).bg,
                  color: providerStyle(agent.provider).text,
                }}>
                  {agent.provider}
                </span>
              </div>

              {/* Role */}
              <p style={{ margin: 0, fontSize: '0.83rem', color: 'rgba(255,255,255,0.55)', lineHeight: 1.4 }}>
                {agent.role}
              </p>

              {/* Model */}
              <div style={{
                padding: '0.5rem 0.75rem',
                backgroundColor: 'rgba(255,255,255,0.04)',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}>
                <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>
                  {agent.model}
                </span>
                {agent.model_url && (
                  <a href={agent.model_url} target="_blank" rel="noopener noreferrer" style={{ color: 'rgba(255,255,255,0.3)' }}>
                    <ExternalLink size={12} />
                  </a>
                )}
              </div>
            </motion.div>
          ))
        )}
      </div>

      {/* Run Agents Panel */}
      <div style={{
        backgroundColor: 'rgba(20,20,20,0.6)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '8px',
        padding: '1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '1rem',
        flexWrap: 'wrap',
      }}>
        <div>
          <h3 style={{ margin: '0 0 0.25rem 0', fontSize: '1rem', fontWeight: 500, color: '#fff' }}>
            Trigger Agent Analysis
          </h3>
          <p style={{ margin: 0, fontSize: '0.85rem', color: 'rgba(255,255,255,0.5)' }}>
            Run the full multi-agent pipeline on a connected repository.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {repos.length > 0 && (
            <select
              value={selectedRepoId}
              onChange={(e) => setSelectedRepoId(e.target.value)}
              style={{
                padding: '0.5rem 0.75rem',
                backgroundColor: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '4px',
                color: '#fff',
                fontSize: '0.85rem',
              }}
            >
              {repos.map(r => (
                <option key={r.id} value={r.id}>{r.name} ({r.owner})</option>
              ))}
            </select>
          )}
          <button
            onClick={handleRunAgents}
            disabled={isRunning || !selectedRepoId || repos.length === 0}
            style={{
              padding: '0.6rem 1.25rem',
              backgroundColor: '#fff',
              color: '#000',
              border: 'none',
              borderRadius: '6px',
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: (isRunning || !selectedRepoId || repos.length === 0) ? 'not-allowed' : 'pointer',
              opacity: (isRunning || !selectedRepoId || repos.length === 0) ? 0.5 : 1,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            {isRunning ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Zap size={16} />}
            {isRunning ? 'Running...' : 'Run Agents'}
          </button>
        </div>
      </div>

      {runMessage && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            marginTop: '1rem',
            padding: '0.75rem 1rem',
            borderRadius: '6px',
            backgroundColor: runMessage.type === 'success' ? 'rgba(74, 222, 128, 0.1)' : 'rgba(248, 113, 113, 0.1)',
            border: `1px solid ${runMessage.type === 'success' ? 'rgba(74,222,128,0.2)' : 'rgba(248,113,113,0.2)'}`,
            color: runMessage.type === 'success' ? '#4ade80' : '#f87171',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          {runMessage.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
          {runMessage.text}
        </motion.div>
      )}

      {error && (
        <div style={{ marginTop: '1rem', color: '#f87171', fontSize: '0.85rem' }}>{error}</div>
      )}

    </div>
  );
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    ready: '#4ade80',
    unreachable: '#f87171',
    unconfigured: '#f59e0b',
    unknown: 'rgba(255,255,255,0.3)',
  };
  return (
    <div style={{
      width: '6px', height: '6px', borderRadius: '50%',
      backgroundColor: colors[status] || colors.unknown,
    }} />
  );
}

function PipelineNode({
  name, color, icon, agents, compact,
}: {
  name: string;
  color: string;
  icon: React.ReactNode;
  agents?: AgentHealthResponse['agents'];
  compact?: boolean;
}) {
  const agentKey = name.toLowerCase().replace(' ', '_');
  const agent = agents?.find(a => a.name === agentKey);

  return (
    <div style={{
      backgroundColor: 'rgba(20,20,20,0.7)',
      border: `1px solid ${color}40`,
      borderRadius: '8px',
      padding: compact ? '0.5rem 0.75rem' : '0.75rem 1rem',
      minWidth: compact ? '160px' : '130px',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    }}>
      <span style={{ color }}>{icon}</span>
      <div>
        <div style={{ fontSize: compact ? '0.78rem' : '0.85rem', fontWeight: 500, color: '#fff', textTransform: 'capitalize' }}>{name}</div>
        {agent && !compact && (
          <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.35)', fontFamily: 'monospace', marginTop: '0.1rem' }}>
            {agent.provider === 'nvidia' ? 'NVIDIA NIM' : agent.provider}
          </div>
        )}
        {agent && compact && (
          <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)', marginTop: '0.1rem', textTransform: 'uppercase', letterSpacing: '0.02em' }}>
            {agent.model.split('/').pop()?.split('-').slice(0, 3).join('-')}
          </div>
        )}
      </div>
    </div>
  );
}

function Arrow() {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      alignSelf: 'center',
      color: 'rgba(255,255,255,0.2)',
      fontSize: '1.1rem',
      flexShrink: 0,
    }}>
      →
    </div>
  );
}
