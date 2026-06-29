/**
 * Archon API Client
 *
 * Central API client for communicating with the FastAPI backend.
 * Automatically attaches the JWT Bearer token from localStorage.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ─── Helpers ────────────────────────────────────────────────────────────────

function getToken(): string | null {
  return localStorage.getItem('archon_auth_token');
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  if (typeof error === 'string' && error) {
    return error;
  }
  return fallback;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...authHeaders(), ...(options?.headers || {}) },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      // Handle both {"detail": "..."} and {"detail": "...", "error": {...}} formats
      if (body.detail) {
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      } else if (body.error?.message) {
        detail = body.error.message;
      }
    } catch {
      // Response body was not JSON — use statusText
    }
    throw new ApiError(response.status, detail);
  }
  return response.json();
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

// ─── Auth ───────────────────────────────────────────────────────────────────

export interface UserProfile {
  installation_id: string;
  provider: string;
  tenant_id: string;
  username: string;
  connected_providers: string[];
}

export async function fetchMe(): Promise<UserProfile> {
  return request<UserProfile>('/api/v1/auth/me');
}

export async function validateToken(): Promise<{ status: string; provider: string }> {
  return request('/api/v1/auth/validate', { method: 'POST' });
}

export async function demoLogin(): Promise<{ token: string; provider: string }> {
  return request('/api/v1/auth/demo', { method: 'POST' });
}

// ─── Repositories ───────────────────────────────────────────────────────────

export interface Repository {
  id: string;
  provider: string;
  owner: string;
  name: string;
  clone_url: string;
  default_branch: string | null;
}

export interface RepositoryCreate {
  provider: string;
  owner: string;
  name: string;
  clone_url: string;
  default_branch?: string;
}

export interface ProviderRepository {
  provider: string;
  owner: string;
  name: string;
  clone_url: string;
  default_branch: string | null;
  private: boolean;
}

export async function listRepositories(): Promise<Repository[]> {
  return request<Repository[]>('/api/v1/repositories');
}

export async function createRepository(data: RepositoryCreate): Promise<Repository> {
  return request<Repository>('/api/v1/repositories', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getRepository(id: string): Promise<Repository> {
  return request<Repository>(`/api/v1/repositories/${id}`);
}

export async function listProviderRepositories(provider: 'github' | 'gitlab'): Promise<ProviderRepository[]> {
  return request<ProviderRepository[]>(`/api/v1/repositories/provider/${provider}`);
}

export async function importProviderRepository(data: ProviderRepository): Promise<Repository> {
  return request<Repository>('/api/v1/repositories/provider/import', {
    method: 'POST',
    body: JSON.stringify({
      provider: data.provider,
      owner: data.owner,
      name: data.name,
      clone_url: data.clone_url,
      default_branch: data.default_branch,
    }),
  });
}

// ─── Analysis Runs ──────────────────────────────────────────────────────────

export interface AnalysisRun {
  id: string;
  snapshot_id: string | null;
  status: string;
  repository_id: string | null;
  meta_data: Record<string, unknown>;
  created_at: string | null;
}

export async function listAnalysisRuns(): Promise<AnalysisRun[]> {
  return request<AnalysisRun[]>('/api/v1/analysis-runs');
}

export async function getAnalysisRun(id: string): Promise<AnalysisRun> {
  return request<AnalysisRun>(`/api/v1/analysis-runs/${id}`);
}

export async function listRepositoryAnalysisRuns(repositoryId: string): Promise<AnalysisRun[]> {
  return request<AnalysisRun[]>(`/api/v1/repositories/${repositoryId}/analysis-runs`);
}

// ─── Jobs ───────────────────────────────────────────────────────────────────

export interface Job {
  id: string;
  status: string;
  repository_id: string | null;
  analysis_run_id: string | null;
  attempts: number;
  last_error: string | null;
  payload: Record<string, unknown>;
  created_at: string | null;
}

export async function listJobs(): Promise<Job[]> {
  return request<Job[]>('/api/v1/jobs');
}

// ─── Health ─────────────────────────────────────────────────────────────────

export async function healthCheck(): Promise<{ status: string; service: string }> {
  return request('/healthz');
}

// ─── Graph & Impact Analysis ────────────────────────────────────────────────

export interface SymbolNodeRead {
  id: string;
  snapshot_id: string;
  file_path: string;
  symbol_name: string;
  symbol_type: string;
  meta_data: Record<string, unknown>;
}

export interface ImpactAnalysisResponse {
  impacted_nodes: SymbolNodeRead[];
  blast_radius_score: number;
}

export async function searchGraph(repository_id: string, query: string = ''): Promise<SymbolNodeRead[]> {
  const params = new URLSearchParams({ repository_id });
  if (query) {
    params.append('query', query);
  }
  return request<SymbolNodeRead[]>(`/api/v1/graph/search?${params.toString()}`);
}

export async function getImpactAnalysis(snapshot_id: string, node_id: string): Promise<ImpactAnalysisResponse> {
  const params = new URLSearchParams({ snapshot_id, node_id });
  return request<ImpactAnalysisResponse>(`/api/v1/graph/impact?${params.toString()}`);
}

export interface ReviewReport {
  id: string;
  analysis_run_id: string;
  tracking_token: string;
  report: {
    findings?: Array<{
      issue: string;
      evidence: string;
      reasoning: string;
      impact: string;
      recommendation: string;
      severity: string;
    }>;
    agent_name?: string;
  };
}

export async function listReports(analysisRunId: string): Promise<ReviewReport[]> {
  return request<ReviewReport[]>(`/api/v1/analysis-runs/${analysisRunId}/reports`);
}

export async function triggerAnalysis(repositoryId: string): Promise<Job> {
  return request<Job>(`/api/v1/repositories/${repositoryId}/analyze`, { method: 'POST' });
}

// ─── Agents ─────────────────────────────────────────────────────────────────

export interface AgentInfo {
  name: string;
  label: string;
  role: string;
  provider: string;
  model: string;
  model_url: string | null;
  status: string;
}

export interface AgentHealthResponse {
  nvidia_configured: boolean;
  ollama_reachable: boolean;
  active_provider: string;
  agents: AgentInfo[];
}

export async function listAgents(): Promise<AgentInfo[]> {
  return request<AgentInfo[]>('/api/v1/agents');
}

export async function checkAgentHealth(): Promise<AgentHealthResponse> {
  return request<AgentHealthResponse>('/api/v1/agents/health');
}

export async function runAgents(repositoryId: string, agents?: string[]): Promise<{
  status: string;
  message: string;
  repository_id: string;
  analysis_run_id: string | null;
}> {
  return request('/api/v1/agents/run', {
    method: 'POST',
    body: JSON.stringify({ repository_id: repositoryId, agents }),
  });
}
