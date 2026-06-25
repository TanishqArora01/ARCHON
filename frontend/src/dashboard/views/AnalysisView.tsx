import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Activity, Box, ChevronDown, ChevronUp } from 'lucide-react';
import { listAnalysisRuns, listJobs, listReports, type AnalysisRun, type Job, type ReviewReport } from '../../api';

export function AnalysisView() {
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [reportsByRun, setReportsByRun] = useState<Record<string, ReviewReport[]>>({});
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [runsData, jobsData] = await Promise.all([listAnalysisRuns(), listJobs()]);
        setRuns(runsData);
        setJobs(jobsData);
      } catch (err) {
        console.error('Failed to fetch analysis data', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const toggleRun = async (runId: string) => {
    if (expandedRunId === runId) {
      setExpandedRunId(null);
      return;
    }
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

  const jobForRun = (runId: string) => jobs.find(job => job.analysis_run_id === runId);

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem 0' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '3rem' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 300, margin: 0, letterSpacing: '-0.02em', color: '#fff' }}>Analysis Runs</h1>
          <p style={{ color: 'rgba(255,255,255,0.5)', margin: '0.5rem 0 0 0', fontSize: '0.9rem' }}>
            Multi-agent architectural intelligence: Planner → Architecture / Maintainability / Technical Debt → Synthesis
          </p>
        </div>
      </header>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {isLoading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>Loading analysis history...</div>
        ) : runs.length === 0 ? (
          <div style={{ padding: '4rem 2rem', textAlign: 'center', color: 'rgba(255,255,255,0.5)', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px dashed rgba(255,255,255,0.1)' }}>
            <Activity size={48} style={{ opacity: 0.2, margin: '0 auto 1rem auto' }} />
            <h3 style={{ margin: '0 0 0.5rem 0', color: '#fff' }}>No analysis runs yet</h3>
            <p style={{ margin: 0, fontSize: '0.9rem' }}>Connect a repository to trigger graph ingestion and agent analysis.</p>
          </div>
        ) : (
          runs.map(run => {
            const job = jobForRun(run.id);
            const reports = reportsByRun[run.id] || [];
            const isExpanded = expandedRunId === run.id;

            return (
              <motion.div 
                key={run.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  backgroundColor: 'rgba(20, 20, 20, 0.6)',
                  border: '1px solid rgba(255,255,255,0.05)',
                  borderRadius: '8px',
                  overflow: 'hidden',
                }}
              >
                <button
                  type="button"
                  onClick={() => toggleRun(run.id)}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '1.5rem',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: '#fff',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', width: '40%' }}>
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
                      <Box size={20} />
                    </div>
                    <div>
                      <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 500, color: '#fff' }}>
                        Run {run.id.substring(0, 8)}
                      </h3>
                      <span style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>
                        Snapshot: {run.snapshot_id ? run.snapshot_id.substring(0, 8) : 'N/A'}
                      </span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '3rem', alignItems: 'center' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                      <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)' }}>STATUS</span>
                      <span style={{ 
                        fontSize: '0.9rem', 
                        color: run.status === 'completed' ? '#4ade80' : 
                               run.status === 'failed' ? '#ff6b6b' : '#60a5fa',
                        fontWeight: 500 
                      }}>
                        {run.status.toUpperCase()}
                      </span>
                    </div>
                    {job && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)' }}>JOB</span>
                        <span style={{ fontSize: '0.9rem', color: job.status === 'completed' ? '#4ade80' : job.status === 'failed' ? '#ff6b6b' : '#60a5fa' }}>
                          {job.status.toUpperCase()}
                        </span>
                      </div>
                    )}
                    {isExpanded ? <ChevronUp size={18} color="rgba(255,255,255,0.4)" /> : <ChevronDown size={18} color="rgba(255,255,255,0.4)" />}
                  </div>
                </button>

                {isExpanded && (
                  <div style={{ padding: '0 1.5rem 1.5rem 1.5rem', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                    {job?.last_error && (
                      <div style={{ padding: '0.75rem', marginTop: '1rem', backgroundColor: 'rgba(255,50,50,0.1)', borderRadius: '6px', color: '#ff6b6b', fontSize: '0.85rem' }}>
                        {job.last_error}
                      </div>
                    )}
                    {reports.length === 0 ? (
                      <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.9rem', margin: '1rem 0 0 0' }}>
                        {job?.status === 'running' ? 'Analysis in progress...' : 'No agent findings report yet.'}
                      </p>
                    ) : (
                      reports.map(report => (
                        <div key={report.id} style={{ marginTop: '1rem' }}>
                          {(report.report.findings || []).length === 0 ? (
                            <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.9rem' }}>No findings — repository passed all agent checks.</p>
                          ) : (
                            (report.report.findings || []).map((finding, idx) => (
                              <div key={idx} style={{
                                padding: '1rem',
                                marginBottom: '0.5rem',
                                backgroundColor: 'rgba(255,255,255,0.03)',
                                borderRadius: '6px',
                                borderLeft: `3px solid ${finding.severity === 'HIGH' ? '#ef4444' : finding.severity === 'MEDIUM' ? '#f59e0b' : '#4ade80'}`,
                              }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                  <strong style={{ color: '#fff' }}>{finding.issue}</strong>
                                  <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)' }}>{finding.severity}</span>
                                </div>
                                <p style={{ margin: '0.25rem 0', fontSize: '0.85rem', color: 'rgba(255,255,255,0.6)' }}><strong>Evidence:</strong> {finding.evidence}</p>
                                <p style={{ margin: '0.25rem 0', fontSize: '0.85rem', color: 'rgba(255,255,255,0.6)' }}><strong>Recommendation:</strong> {finding.recommendation}</p>
                              </div>
                            ))
                          )}
                        </div>
                      ))
                    )}
                  </div>
                )}
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}
