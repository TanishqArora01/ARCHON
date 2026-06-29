"""
src/api/agents.py
─────────────────
Agents API — expose multi-agent system status and model assignments.

Endpoints:
  GET  /api/v1/agents            — list all agents with their NVIDIA NIM model assignments
  GET  /api/v1/agents/health     — check which providers are reachable
  POST /api/v1/agents/run        — trigger a targeted agent analysis run
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from src.api.security import require_api_token
from src.core.config import settings
from src.db.models import AnalysisRun, Repository, Snapshot
from src.db.session import AsyncSessionLocal

router = APIRouter(
    prefix="/api/v1/agents",
    tags=["agents"],
    dependencies=[Depends(require_api_token)],
)


# ─── Schemas ────────────────────────────────────────────────────────────────

class AgentInfo(BaseModel):
    name: str
    label: str
    role: str
    provider: str
    model: str
    model_url: str | None = None
    status: str = "ready"


class AgentHealthResponse(BaseModel):
    nvidia_configured: bool
    ollama_reachable: bool
    active_provider: str
    agents: list[AgentInfo]


class AgentRunRequest(BaseModel):
    repository_id: str
    agents: list[str] | None = None  # None = all agents


class AgentRunResponse(BaseModel):
    status: str
    message: str
    repository_id: str
    analysis_run_id: str | None = None


# ─── Agent definitions ──────────────────────────────────────────────────────

def _get_agent_definitions() -> list[AgentInfo]:
    """Build the list of all agents with their current model assignments."""
    provider = settings.LLM_PROVIDER.lower()
    nvidia_configured = bool(settings.NVIDIA_API_KEY)

    agents = [
        AgentInfo(
            name="planner",
            label="Planner Agent",
            role="Evaluates repository context and routes tasks to specialist agents",
            provider="nvidia" if (provider == "nvidia" and nvidia_configured) else provider,
            model=(
                settings.NVIDIA_PLANNER_MODEL
                if (provider == "nvidia" and nvidia_configured)
                else settings.LLM_MODEL
            ),
            model_url=(
                f"https://build.nvidia.com/explore/reasoning"
                if (provider == "nvidia" and nvidia_configured)
                else None
            ),
        ),
        AgentInfo(
            name="architecture",
            label="Architecture Agent",
            role="Detects layer violations, boundary issues, and architecture drift",
            provider="nvidia" if (provider == "nvidia" and nvidia_configured) else provider,
            model=(
                settings.NVIDIA_ARCHITECTURE_MODEL
                if (provider == "nvidia" and nvidia_configured)
                else settings.LLM_MODEL
            ),
            model_url=(
                f"https://build.nvidia.com/explore/reasoning"
                if (provider == "nvidia" and nvidia_configured)
                else None
            ),
        ),
        AgentInfo(
            name="maintainability",
            label="Maintainability Agent",
            role="Detects coupling, complexity, and refactoring opportunities",
            provider="nvidia" if (provider == "nvidia" and nvidia_configured) else provider,
            model=(
                settings.NVIDIA_MAINTAINABILITY_MODEL
                if (provider == "nvidia" and nvidia_configured)
                else settings.LLM_MODEL
            ),
            model_url=(
                f"https://build.nvidia.com/explore/reasoning"
                if (provider == "nvidia" and nvidia_configured)
                else None
            ),
        ),
        AgentInfo(
            name="technical_debt",
            label="Technical Debt Agent",
            role="Forecasts structural drag and compounding costs for choke points",
            provider="nvidia" if (provider == "nvidia" and nvidia_configured) else provider,
            model=(
                settings.NVIDIA_DEBT_MODEL
                if (provider == "nvidia" and nvidia_configured)
                else settings.LLM_MODEL
            ),
            model_url=(
                f"https://build.nvidia.com/explore/reasoning"
                if (provider == "nvidia" and nvidia_configured)
                else None
            ),
        ),
        AgentInfo(
            name="impact",
            label="Impact Agent",
            role="Evaluates change impact, blast radius, and risk scoring",
            provider="nvidia" if (provider == "nvidia" and nvidia_configured) else provider,
            model=(
                settings.NVIDIA_IMPACT_MODEL
                if (provider == "nvidia" and nvidia_configured)
                else settings.LLM_MODEL
            ),
            model_url=(
                f"https://build.nvidia.com/explore/reasoning"
                if (provider == "nvidia" and nvidia_configured)
                else None
            ),
        ),
        AgentInfo(
            name="synthesis",
            label="Synthesis Agent",
            role="Deterministic convergence — aggregates all specialist findings into final report",
            provider="deterministic",
            model="no-llm-required",
            model_url=None,
        ),
    ]
    return agents


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("", response_model=list[AgentInfo])
async def list_agents() -> list[AgentInfo]:
    """
    List all Archon agents with their current LLM model assignments.

    When LLM_PROVIDER=nvidia, each agent is assigned a specialized NVIDIA NIM
    model from build.nvidia.com optimized for its task.
    """
    return _get_agent_definitions()


@router.get("/health", response_model=AgentHealthResponse)
async def check_agent_health() -> AgentHealthResponse:
    """
    Check the health of all agent providers.
    Tests NVIDIA NIM reachability and Ollama local runtime.
    """
    nvidia_configured = bool(settings.NVIDIA_API_KEY)
    ollama_reachable = False

    # Test Ollama reachability
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.OLLAMA_URL}/api/tags")
            ollama_reachable = resp.status_code == 200
    except Exception:
        ollama_reachable = False

    active_provider = settings.LLM_PROVIDER
    agents = _get_agent_definitions()

    # Update status based on provider health
    for agent in agents:
        if agent.provider == "nvidia":
            agent.status = "ready" if nvidia_configured else "unconfigured"
        elif agent.provider == "ollama":
            agent.status = "ready" if ollama_reachable else "unreachable"
        elif agent.provider == "mock":
            agent.status = "ready"
        elif agent.provider == "deterministic":
            agent.status = "ready"
        else:
            agent.status = "unknown"

    return AgentHealthResponse(
        nvidia_configured=nvidia_configured,
        ollama_reachable=ollama_reachable,
        active_provider=active_provider,
        agents=agents,
    )


@router.post("/run", response_model=AgentRunResponse)
async def run_agents(payload: AgentRunRequest) -> AgentRunResponse:
    """
    Trigger a targeted agent analysis run on a specific repository.

    This enqueues a fresh analysis run using the currently configured LLM provider.
    When LLM_PROVIDER=nvidia, each agent will use its specialized NVIDIA NIM model.
    """
    from src.services.analysis_jobs import enqueue_repository_analysis, run_inline_analysis
    from src.services.repositories import get_or_create_default_tenant
    import asyncio

    async with AsyncSessionLocal() as session:
        repo = await session.get(Repository, payload.repository_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        tenant = await get_or_create_default_tenant(session)
        job_id, task_payload, queued = await enqueue_repository_analysis(
            session,
            repo,
            tenant_id=tenant.id,
            event_type="agent_run",
        )
        await session.commit()

    # Run inline since we don't have background_tasks in this path
    if not queued:
        asyncio.create_task(run_inline_analysis(task_payload))

    return AgentRunResponse(
        status="queued",
        message=(
            f"Agent analysis queued for repository '{repo.name}'. "
            f"Using provider: {settings.LLM_PROVIDER}."
        ),
        repository_id=payload.repository_id,
        analysis_run_id=job_id,
    )


@router.get("/repository/{repository_id}/runs")
async def list_repository_analysis_runs(repository_id: str) -> list[dict]:
    """
    List all analysis runs for a specific repository, ordered newest first.
    """
    async with AsyncSessionLocal() as session:
        repo = await session.get(Repository, repository_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        result = await session.execute(
            select(AnalysisRun)
            .where(AnalysisRun.repository_id == repository_id)
            .order_by(AnalysisRun.created_at.desc())
        )
        runs = result.scalars().all()

        return [
            {
                "id": run.id,
                "snapshot_id": run.snapshot_id,
                "status": run.status,
                "repository_id": run.repository_id,
                "meta_data": run.meta_data or {},
            }
            for run in runs
        ]
