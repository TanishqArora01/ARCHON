import React, { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity, Box, ChevronDown, ChevronUp,
  Zap, Loader2, CheckCircle, XCircle, Clock, AlertCircle, Calendar,
  GitBranch, GitCommit, FileCode, Network, Database, Layers, ShieldCheck, Search, FileText, Code
} from 'lucide-react';
import {
  listAnalysisRuns, listJobs, listReports, listRepositories,
  triggerAnalysis,
  type AnalysisRun, type Job, type ReviewReport, type Repository,
} from '../../api';

// ── Helpers ───────────────────────────────────────────────────────────────

const TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled']);

function formatRelativeTime(iso: string | null): string {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

function formatAbsoluteTime(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleString();
}

function countSeverity(reports: ReviewReport[], level: string) {
  return reports.reduce((acc, r) => {
    const findings: Array<{ severity: string }> = r.report?.findings ?? [];
    return acc + findings.filter(f => f.severity === level).length;
  }, 0);
}

// Temporary mapping from agent_name to engineering domains.
// This will be replaced by finding.category when the backend supports it.
function extractFindingsCategories(reports: ReviewReport[]) {
  let archCount = 0;
  let techDebtCount = 0;
  let impactCount = 0;
  let securityCount = 0;
  let testCount = 0;
  const executedAgents = new Set<string>();

  reports.forEach(r => {
    const agent = r.report.agent_name || 'Unknown';
    if (agent !== 'Unknown' && !agent.toLowerCase().includes('synthesis')) {
      executedAgents.add(agent.replace(' Agent', ''));
    }
    const findings = r.report.findings || [];
    const aName = agent.toLowerCase();
    if (aName.includes('architecture')) archCount += findings.length;
    else if (aName.includes('maintainability')) techDebtCount += findings.length;
    else if (aName.includes('impact')) impactCount += findings.length;
    else if (aName.includes('security')) securityCount += findings.length;
    else if (aName.includes('testing')) testCount += findings.length;
  });

  return { archCount, techDebtCount, impactCount, securityCount, testCount, executedAgents };
}

// Group runs temporally
function groupRuns(runs: AnalysisRun[]) {
  // Sort descending
  const sorted = [...runs].sort((a, b) => {
    if (!a.created_at) return 1;
    if (!b.created_at) return -1;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  const now = new Date();
  const todayDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  
  const groups: { title: string; runs: AnalysisRun[] }[] = [
    { title: 'Today', runs: [] },
    { title: 'Yesterday', runs: [] },
    { title: 'Last Week', runs: [] },
    { title: 'Older', runs: [] },
  ];

  sorted.forEach(run => {
    if (!run.created_at) {
      groups[3].runs.push(run);
      return;
    }
    const runDateObj = new Date(run.created_at);
    const runDay = new Date(runDateObj.getFullYear(), runDateObj.getMonth(), runDateObj.getDate());
    const diffDays = Math.round((todayDate.getTime() - runDay.getTime()) / (1000 * 3600 * 24));
    
    if (diffDays === 0) groups[0].runs.push(run);
    else if (diffDays === 1) groups[1].runs.push(run);
    else if (diffDays <= 7) groups[2].runs.push(run);
    else groups[3].runs.push(run);
  });
  return groups.filter(g => g.runs.length > 0);
}

// ── Status Badge ──────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; icon: React.ReactNode }> = {
    completed: { color: '#4ade80', icon: <CheckCircle size={12} /> },
    failed:    { color: '#f87171', icon: <XCircle    size={12} /> },
    running:   { color: '#60a5fa', icon: <Loader2    size={12} style={{ animation: 'spin 1s linear infinite' }} /> },
    pending:   { color: '#f59e0b', icon: <Clock      size={12} /> },
    queued:    { color: '#a78bfa', icon: <Clock      size={12} /> },
  };
  const s = map[status] ?? { color: 'rgba(255,255,255,0.4)', icon: null };
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', color: s.color, fontWeight: 500, fontSize: '0.85rem' }}>
      {s.icon} {status.toUpperCase()}
    </span>
  );
}

// ── Main Component ────────────────────────────────────────────────────────

const PIPELINE_STEPS = [
  { id: 'parsing',      label: 'Parsing' },
  { id: 'extraction',   label: 'Symbol Extraction' },
  { id: 'resolution',   label: 'Symbol Resolution' },
  { id: 'graph',        label: 'Graph Construction' },
  { id: 'impact',       label: 'Impact Analysis' },
  { id: 'retrieval',    label: 'Retrieval' },
  { id: 'context',      label: 'Context Assembly' },
  { id: 'reasoning',    label: 'Agent Reasoning' },
  { id: 'synthesis',    label: 'Synthesis' },
];

export function AnalysisView() {
  const [runs, setRuns]         = useState<AnalysisRun[]>([]);
  const [jobs, setJobs]         = useState<Job[]>([]);
  const [repos, setRepos]       = useState<Repository[]>([]);
  const [reportsByRun, setReportsByRun] = useState<Record<string, ReviewReport[]>>({});
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  const [isLoading, setIsLoading]       = useState(true);
  const [triggering, setTriggering]     = useState(false);
  const [selectedRepoId, setSelectedRepoId] = useState('');
  const [triggerMsg, setTriggerMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [runsData, jobsData, reposData] = await Promise.all([
        listAnalysisRuns(), listJobs(), listRepositories(),
      ]);
      setRuns(runsData);
      setJobs(jobsData);
      setRepos(reposData);
      setSelectedRepoId(prev => (prev || reposData[0]?.id || ''));

      // Stop polling when all active runs are in terminal state
      const hasActiveRuns = runsData.some(r => !TERMINAL_STATUSES.has(r.status));
      if (!hasActiveRuns && intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    } catch (err) {
      console.error('Failed to fetch analysis data', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    intervalRef.current = setInterval(fetchData, 8000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchData]);

  const toggleRun = async (runId: string) => {
    if (expandedRunId === runId) { setExpandedRunId(null); return; }
    setExpandedRunId(runId);
    if (!reportsByRun[runId]) {
      try {
        const reports = await listReports(runId);
        setReportsByRun(prev => ({ ...prev, [runId]: reports }));
      } catch (err) {
        console.error('Failed to fetch reports', err);
      }
    }
  };

  const handleTrigger = async () => {
    if (!selectedRepoId) return;
    setTriggering(true);
    setTriggerMsg(null);
    try {
      await triggerAnalysis(selectedRepoId);
      setTriggerMsg({ text: 'Repository analysis queued.', ok: true });
      // Restart polling
      if (!intervalRef.current) intervalRef.current = setInterval(fetchData, 8000);
      setTimeout(fetchData, 1500);
    } catch (err) {
      setTriggerMsg({ text: err instanceof Error ? err.message : 'Failed to trigger analysis', ok: false });
    } finally {
      setTriggering(false);
    }
  };

  const jobForRun = (runId: string) => jobs.find(j => j.analysis_run_id === runId);

  const groupedRuns = groupRuns(runs);

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '2rem 0' }}>
      {/* Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
        <div>
          <h1 className="dash-page-title">Repository Intelligence</h1>
          <p className="dash-page-subtitle" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            Repository Intelligence Report
          </p>
        </div>
      </header>

      {/* Pipeline Strip */}
      <div style={{ marginBottom: '1.75rem' }}>
        <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: '0.5rem', letterSpacing: '0.05em', fontWeight: 600 }}>
          Reference Intelligence Architecture
        </div>
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.5rem',
          padding: '0.875rem 1.25rem',
          backgroundColor: 'rgba(20,20,20,0.6)',
          border: '1px dashed rgba(255,255,255,0.1)',
          borderRadius: '8px',
          overflowX: 'auto',
        }}>
          {PIPELINE_STEPS.map((step, i) => (
            <React.Fragment key={step.id}>
              <div style={{
                padding: '0.35rem 0.875rem', borderRadius: '20px',
                border: '1px solid rgba(255,255,255,0.1)',
                backgroundColor: 'rgba(255,255,255,0.03)',
                color: 'rgba(255,255,255,0.6)', fontSize: '0.75rem', fontWeight: 500,
                whiteSpace: 'nowrap', flexShrink: 0, letterSpacing: '0.02em'
              }}>
                {step.label}
              </div>
              {i < PIPELINE_STEPS.length - 1 && (
                <span style={{ color: 'rgba(255,255,255,0.15)', flexShrink: 0, fontSize: '0.85rem' }}>↓</span>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Trigger Panel */}
      {repos.length > 0 && (
        <div className="dash-card" style={{
          display: 'flex', alignItems: 'center', gap: '1rem',
          padding: '1rem 1.25rem', marginBottom: '2rem', flexWrap: 'wrap',
        }}>
          <select
            value={selectedRepoId}
            onChange={(e) => setSelectedRepoId(e.target.value)}
            style={{
              padding: '0.5rem 0.75rem',
              backgroundColor: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '5px', color: '#fff', fontSize: '0.875rem',
              flex: '1', minWidth: '200px',
            }}
          >
            {repos.map(r => <option key={r.id} value={r.id}>{r.owner}/{r.name}</option>)}
          </select>

          <button
            onClick={handleTrigger}
            disabled={triggering || !selectedRepoId}
            style={{
              padding: '0.55rem 1.1rem',
              backgroundColor: triggering ? 'rgba(255,255,255,0.15)' : '#fff',
              color: triggering ? 'rgba(255,255,255,0.4)' : '#000',
              border: 'none', borderRadius: '6px', fontWeight: 600,
              fontSize: '0.875rem', cursor: (triggering || !selectedRepoId) ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0,
              transition: 'all 0.15s ease',
            }}
          >
            {triggering
              ? <><Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> Analyzing...</>
              : <><Zap size={14} /> Trigger Analysis</>
            }
          </button>

          {triggerMsg && (
            <motion.span
              initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
              style={{
                fontSize: '0.82rem', fontWeight: 500,
                color: triggerMsg.ok ? '#4ade80' : '#f87171',
                display: 'flex', alignItems: 'center', gap: '0.4rem',
              }}
            >
              {triggerMsg.ok
                ? <CheckCircle size={13} />
                : <AlertCircle size={13} />
              }
              {triggerMsg.text}
            </motion.span>
          )}
        </div>
      )}

      {/* Runs List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: '76px', borderRadius: '8px' }} />
          ))
        ) : runs.length === 0 ? (
          <div style={{
            padding: '5rem 2rem', textAlign: 'center',
            color: 'rgba(255,255,255,0.4)',
            backgroundColor: 'rgba(255,255,255,0.02)',
            borderRadius: '12px', border: '1px dashed rgba(255,255,255,0.08)',
          }}>
            <Activity size={48} style={{ opacity: 0.15, display: 'block', margin: '0 auto 1rem' }} />
            <h3 style={{ margin: '0 0 0.5rem 0', color: '#fff', fontWeight: 400 }}>No repository intelligence generated yet</h3>
            <p style={{ margin: 0, fontSize: '0.875rem' }}>
              Connect a repository and click "Trigger Analysis" to map the dependency graph and discover architectural insights.
            </p>
          </div>
        ) : (
          groupedRuns.map((group) => (
            <div key={group.title}>
              <h3 style={{ 
                fontSize: '0.85rem', color: 'rgba(255,255,255,0.5)', 
                textTransform: 'uppercase', letterSpacing: '0.05em', 
                marginBottom: '0.75rem', marginTop: '0', fontWeight: 600 
              }}>
                {group.title}
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {group.runs.map((run, idx) => {
                  const job     = jobForRun(run.id);
                  const reports = reportsByRun[run.id] ?? [];
                  const isExpanded = expandedRunId === run.id;
                  const repo    = repos.find(r => r.id === run.repository_id);
                  const highCount   = countSeverity(reports, 'HIGH');
                  const mediumCount = countSeverity(reports, 'MEDIUM');
                  const lowCount    = countSeverity(reports, 'LOW');
                  const totalFindings = highCount + mediumCount + lowCount;

                  const hasMetaData = run.meta_data && Object.keys(run.meta_data).length > 0;
                  
                  // Extract payload metadata
                  const commitSha = job?.payload?.commit_sha as string | undefined;
                  const branch = (job?.payload as any)?.branch as string | undefined || 'main';

                  // Calculate structured summary metrics using temporary agent_name mappings
                  const overallRisk = highCount > 0 ? 'High' : (mediumCount > 0 ? 'Medium' : (lowCount > 0 ? 'Low' : 'None'));
                  
                  const { 
                    archCount, techDebtCount, impactCount, 
                    securityCount, testCount, executedAgents 
                  } = extractFindingsCategories(reports);

                  // Try to compute duration
                  let durationStr = '—';
                  if (job && job.created_at && job.updated_at && job.status === 'completed') {
                    const diffMs = new Date(job.updated_at).getTime() - new Date(job.created_at).getTime();
                    durationStr = `${(diffMs / 1000).toFixed(1)} s`;
                  }

                  return (
                    <motion.div
                      key={run.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.04 }}
                      className="dash-card"
                      style={{ overflow: 'hidden' }}
                    >
                      {/* Run header (clickable) */}
                      <button
                        type="button"
                        onClick={() => toggleRun(run.id)}
                        style={{
                          width: '100%', display: 'flex', alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '1.1rem 1.25rem',
                          background: 'none', border: 'none',
                          cursor: 'pointer', color: '#fff', textAlign: 'left',
                        }}
                      >
                        {/* Left: icon + name + meta */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem', overflow: 'hidden' }}>
                          <div style={{
                            width: '36px', height: '36px', borderRadius: '8px',
                            backgroundColor: 'rgba(255,255,255,0.05)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            color: 'rgba(255,255,255,0.5)',
                            flexShrink: 0,
                          }}>
                            <Box size={17} />
                          </div>
                          <div style={{ overflow: 'hidden' }}>
                            <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 500, color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {repo ? `${repo.owner}/${repo.name}` : `Run ${run.id.substring(0, 8)}`}
                            </h3>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.15rem' }}>
                              <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.3)', fontFamily: 'ui-monospace, monospace' }}>
                                {run.id.substring(0, 16)}
                              </span>
                              {run.created_at && (
                                <span
                                  title={formatAbsoluteTime(run.created_at)}
                                  style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.3)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                                >
                                  <Calendar size={10} />
                                  {formatRelativeTime(run.created_at)}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Right: status + finding counts + chevron */}
                        <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', flexShrink: 0 }}>
                          {/* Severity Indicator */}
                          {reports.length > 0 && totalFindings > 0 && (
                            <div style={{ display: 'flex', gap: '0.4rem' }}>
                              {highCount   > 0 && <SeverityPill count={highCount}   level="HIGH" />}
                              {mediumCount > 0 && <SeverityPill count={mediumCount} level="MEDIUM" />}
                              {lowCount    > 0 && <SeverityPill count={lowCount}    level="LOW" />}
                            </div>
                          )}
                          {reports.length > 0 && totalFindings === 0 && (
                            <span style={{ fontSize: '0.75rem', color: '#4ade80', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                              <ShieldCheck size={14} /> Repository Healthy
                            </span>
                          )}

                          <div style={{ textAlign: 'right' }}>
                            <StatusBadge status={run.status} />
                          </div>
                          {isExpanded
                            ? <ChevronUp  size={15} color="rgba(255,255,255,0.3)" />
                            : <ChevronDown size={15} color="rgba(255,255,255,0.3)" />
                          }
                        </div>
                      </button>

                      {/* Expandable detail */}
                      <AnimatePresence>
                        {isExpanded && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            style={{ overflow: 'hidden' }}
                          >
                            <div style={{ padding: '0 1.25rem 1.25rem', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                              
                              {/* Structured Analysis Summary */}
                              {reports.length > 0 && (
                                <div style={{ marginTop: '1.5rem', marginBottom: '1.5rem', padding: '1.25rem', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                                    <h4 style={{ color: '#fff', fontSize: '1rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                      <Search size={16} color="#60a5fa" /> Analysis Summary
                                    </h4>
                                  </div>

                                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1.5rem' }}>
                                    {executedAgents.size > 0 && (
                                      <div style={{ gridColumn: '1 / -1' }}>
                                        <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.4rem' }}>Executed Specialists</div>
                                        <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.9rem', color: '#fff', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                                          {Array.from(executedAgents).map(a => (
                                            <li key={a}>{a}</li>
                                          ))}
                                        </ul>
                                      </div>
                                    )}
                                    <div>
                                      <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.2rem' }}>Repository Risk</div>
                                      <div style={{ fontSize: '0.9rem', color: overallRisk === 'High' ? '#ef4444' : overallRisk === 'Medium' ? '#f59e0b' : overallRisk === 'Low' ? '#4ade80' : '#fff', fontWeight: 600 }}>{overallRisk}</div>
                                    </div>
                                    <div>
                                      <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.2rem' }}>Total Findings</div>
                                      <div style={{ fontSize: '0.9rem', color: '#fff', fontWeight: 600 }}>{totalFindings}</div>
                                    </div>
                                    {archCount > 0 && (
                                      <div>
                                        <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.2rem' }}>Architecture Violations</div>
                                        <div style={{ fontSize: '0.9rem', color: '#fff', fontWeight: 600 }}>{archCount}</div>
                                      </div>
                                    )}
                                    {techDebtCount > 0 && (
                                      <div>
                                        <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.2rem' }}>Technical Debt</div>
                                        <div style={{ fontSize: '0.9rem', color: '#fff', fontWeight: 600 }}>{techDebtCount}</div>
                                      </div>
                                    )}
                                    {impactCount > 0 && (
                                      <div>
                                        <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.2rem' }}>Impact Findings</div>
                                        <div style={{ fontSize: '0.9rem', color: '#fff', fontWeight: 600 }}>{impactCount}</div>
                                      </div>
                                    )}
                                    {securityCount > 0 && (
                                      <div>
                                        <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.2rem' }}>Security Risks</div>
                                        <div style={{ fontSize: '0.9rem', color: '#fff', fontWeight: 600 }}>{securityCount}</div>
                                      </div>
                                    )}
                                    {testCount > 0 && (
                                      <div>
                                        <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.2rem' }}>Testing Deficits</div>
                                        <div style={{ fontSize: '0.9rem', color: '#fff', fontWeight: 600 }}>{testCount}</div>
                                      </div>
                                    )}
                                    <div>
                                      <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.2rem' }}>Analysis Duration</div>
                                      <div style={{ fontSize: '0.9rem', color: '#fff', fontWeight: 600 }}>{durationStr}</div>
                                    </div>
                                  </div>
                                </div>
                              )}

                              {/* Findings List */}
                              {reports.length === 0 ? (
                                <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.875rem', margin: '1rem 0 0', fontStyle: 'italic' }}>
                                  {run.status === 'running'
                                    ? '⟳ Constructing repository intelligence and analyzing impact...'
                                    : 'No engineering findings were generated for this run.'
                                  }
                                </p>
                              ) : (
                                reports.map(report => (
                                  <div key={report.id}>
                                    {(report.report.findings ?? []).length > 0 && (
                                      (report.report.findings ?? []).map((finding: Record<string, any>, idx: number) => (
                                        <div
                                          key={idx}
                                          className={`finding-card ${finding.severity?.toLowerCase() ?? 'low'}`}
                                          style={{ padding: '1.25rem', marginTop: '1rem', backgroundColor: 'rgba(20,20,20,0.5)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}
                                        >
                                          {/* Title: The specific issue discovered */}
                                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem', gap: '1rem' }}>
                                            <strong style={{ color: '#fff', fontSize: '1.05rem', lineHeight: 1.4 }}>
                                              {finding.issue}
                                            </strong>
                                            <span style={{
                                              fontSize: '0.68rem', padding: '0.2rem 0.5rem',
                                              borderRadius: '4px', fontWeight: 700, flexShrink: 0,
                                              backgroundColor: finding.severity === 'HIGH'   ? 'rgba(239,68,68,0.15)'  :
                                                               finding.severity === 'MEDIUM' ? 'rgba(245,158,11,0.15)' : 'rgba(74,222,128,0.15)',
                                              color:           finding.severity === 'HIGH'   ? '#ef4444'              :
                                                               finding.severity === 'MEDIUM' ? '#f59e0b'              : '#4ade80',
                                            }}>
                                              {finding.severity}
                                            </span>
                                          </div>
                                          
                                          {/* Standard Content: Evidence, Reasoning, Impact, Recommendation */}
                                          <div style={{ display: 'grid', gap: '0.75rem' }}>
                                            <div style={{ fontSize: '0.875rem', color: 'rgba(255,255,255,0.7)', lineHeight: 1.5 }}>
                                              <strong style={{ color: 'rgba(255,255,255,0.9)', display: 'block', marginBottom: '0.2rem' }}>Evidence</strong>
                                              {finding.evidence}
                                            </div>
                                            <div style={{ fontSize: '0.875rem', color: 'rgba(255,255,255,0.7)', lineHeight: 1.5 }}>
                                              <strong style={{ color: 'rgba(255,255,255,0.9)', display: 'block', marginBottom: '0.2rem' }}>Reasoning</strong>
                                              {finding.reasoning}
                                            </div>
                                            {finding.impact && (
                                              <div style={{ fontSize: '0.875rem', color: 'rgba(255,255,255,0.7)', lineHeight: 1.5 }}>
                                                <strong style={{ color: 'rgba(255,255,255,0.9)', display: 'block', marginBottom: '0.2rem' }}>Impact</strong>
                                                {finding.impact}
                                              </div>
                                            )}
                                            <div style={{ fontSize: '0.875rem', color: 'rgba(255,255,255,0.7)', lineHeight: 1.5 }}>
                                              <strong style={{ color: 'rgba(255,255,255,0.9)', display: 'block', marginBottom: '0.2rem' }}>Recommendation</strong>
                                              {finding.recommendation}
                                            </div>
                                            
                                            {/* Optional: Evidence Sources */}
                                            {finding.evidence_sources && Array.isArray(finding.evidence_sources) && finding.evidence_sources.length > 0 && (
                                              <div style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.6)', marginTop: '0.5rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                                                <strong style={{ color: 'rgba(255,255,255,0.8)' }}>Evidence Sources:</strong>
                                                {finding.evidence_sources.map((src: string, i: number) => (
                                                  <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.2rem', backgroundColor: 'rgba(255,255,255,0.05)', padding: '0.1rem 0.4rem', borderRadius: '4px' }}>
                                                    <CheckCircle size={10} color="#4ade80" /> {src}
                                                  </span>
                                                ))}
                                              </div>
                                            )}
                                          </div>

                                          {/* Repository-Aware Details Collapsible (Only if fields exist) */}
                                          {(finding.affected_files || finding.affected_modules || finding.affected_symbols || finding.dependency_chain || finding.blast_radius || finding.architecture_rules) && (
                                            <details style={{ marginTop: '1.25rem' }}>
                                              <summary style={{ 
                                                fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', 
                                                cursor: 'pointer', outline: 'none', userSelect: 'none',
                                                display: 'inline-flex', alignItems: 'center', gap: '0.3rem'
                                              }}>
                                                Show Repository Context
                                              </summary>
                                              <div style={{ 
                                                marginTop: '0.75rem', padding: '0.875rem', 
                                                backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: '6px',
                                                border: '1px solid rgba(255,255,255,0.03)',
                                                fontSize: '0.8rem', color: 'rgba(255,255,255,0.6)'
                                              }}>
                                                {finding.affected_files && <div style={{ marginBottom: '0.4rem' }}><strong>Affected Files:</strong> {finding.affected_files}</div>}
                                                {finding.affected_modules && <div style={{ marginBottom: '0.4rem' }}><strong>Affected Modules:</strong> {finding.affected_modules}</div>}
                                                {finding.affected_symbols && <div style={{ marginBottom: '0.4rem' }}><strong>Affected Symbols:</strong> {finding.affected_symbols}</div>}
                                                {finding.dependency_chain && <div style={{ marginBottom: '0.4rem' }}><strong>Dependency Chain:</strong> {finding.dependency_chain}</div>}
                                                {finding.blast_radius && <div style={{ marginBottom: '0.4rem' }}><strong>Blast Radius:</strong> {finding.blast_radius}</div>}
                                                {finding.architecture_rules && <div><strong>Architecture Rules:</strong> {finding.architecture_rules}</div>}
                                              </div>
                                            </details>
                                          )}
                                        </div>
                                      ))
                                    )}
                                  </div>
                                ))
                              )}

                              {/* Diagnostics Collapsible */}
                              <details style={{ marginTop: '2rem' }}>
                                <summary style={{ 
                                  fontSize: '0.75rem', color: 'rgba(255,255,255,0.3)', 
                                  cursor: 'pointer', outline: 'none', userSelect: 'none',
                                  display: 'inline-flex', alignItems: 'center', gap: '0.3rem'
                                }}>
                                  Diagnostics & Execution Details
                                </summary>
                                <div style={{ 
                                  marginTop: '0.75rem', padding: '0.875rem', 
                                  backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: '6px',
                                  border: '1px solid rgba(255,255,255,0.03)',
                                  fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)',
                                  fontFamily: 'ui-monospace, monospace'
                                }}>
                                  <div style={{ marginBottom: '0.4rem' }}>Job ID: {job?.id || 'Unknown'}</div>
                                  <div style={{ marginBottom: '0.4rem' }}>Status: {job?.status || 'Unknown'}</div>
                                  <div style={{ marginBottom: '0.4rem' }}>Attempts: {job?.attempts || 0}</div>
                                  
                                  {reports.map((report, idx) => (
                                    report.report.agent_name && (
                                      <div key={idx} style={{ marginBottom: '0.4rem' }}>Provider/Agent: {report.report.agent_name}</div>
                                    )
                                  ))}

                                  {job?.last_error && (
                                    <div style={{ marginTop: '0.8rem', color: '#f87171' }}>
                                      <strong>Job Error:</strong> {job.last_error}
                                    </div>
                                  )}
                                </div>
                              </details>

                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ── Severity Pill ─────────────────────────────────────────────────────────

function SeverityPill({ count, level }: { count: number; level: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    HIGH:   { bg: 'rgba(239,68,68,0.15)',  text: '#ef4444' },
    MEDIUM: { bg: 'rgba(245,158,11,0.15)', text: '#f59e0b' },
    LOW:    { bg: 'rgba(74,222,128,0.12)', text: '#4ade80' },
  };
  const c = colors[level] ?? colors.LOW;
  return (
    <span style={{
      padding: '0.2rem 0.6rem', borderRadius: '4px',
      fontSize: '0.75rem', fontWeight: 700,
      backgroundColor: c.bg, color: c.text,
      display: 'inline-flex', alignItems: 'center', gap: '0.3rem'
    }}>
      {count} {level}
    </span>
  );
}
